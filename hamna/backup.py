"""
HAMNA Web — respaldo y restauración de todos los datos.

El respaldo es un .tar.gz con:
  hamna-respaldo.json   qué es, de qué nodo y versión
  hamna.db              eventos, secciones, programación, usuarios, compartidos…
  settings.json         ajustes (incluye las claves de Azure y Telegram)
  logo_*.png|jpg|…      logo de la estación
  sonidos/              audios de pausa (alerta, pausa, continuamos)
  audios/               audios de las secciones (opcional)

Se arma mientras se descarga (no ocupa espacio en la tarjeta SD salvo una
copia de la base de datos) y se comprime con nivel 1: los audios casi no se
comprimen y en una Raspberry el nivel 9 tardaría muchísimo.
No se respaldan cache/ (se regenera), tmp/ ni la bitácora.
"""
import datetime as dt
import io
import json
import logging
import os
import queue
import re
import shutil
import sqlite3
import tarfile
import threading
import time
import uuid
import zlib
from pathlib import Path

from . import VERSION, db, paths, settings

log = logging.getLogger("hamna.respaldo")

MANIFEST = "hamna-respaldo.json"
FORMATO = 1
LOGO_RE = re.compile(r"^logo_[A-Za-z0-9]+\.(png|jpg|webp|gif)$")
CARPETAS = ("sonidos", "audios")
# Ajustes que describen a ESTE nodo; se conservan al restaurar un respaldo
# de otro nodo si así se pide. secret_key nunca se toma del respaldo.
NODE_KEYS = {"backend", "node", "asl_mode", "asl_flush_cmd", "station_name", "logo_file"}
GUARDAR = 2           # copias "antes-de-restaurar-*" que se conservan


# ── Utilidades ────────────────────────────────────────────────────────────────
def _snapshot_db(dest):
    """Copia consistente de hamna.db (aunque haya escrituras en curso)."""
    src = str(paths.db_file())
    dest = str(dest)
    with db._lock:
        c = sqlite3.connect(src, timeout=15)
        try:
            if hasattr(c, "backup"):                     # Python 3.7+
                d = sqlite3.connect(dest)
                try:
                    c.backup(d)
                finally:
                    d.close()
            else:                                        # Python 3.5/3.6 (HamVOIP)
                c.isolation_level = None
                c.execute("BEGIN IMMEDIATE")             # nadie más escribe
                try:
                    shutil.copyfile(src, dest)
                    if os.path.isfile(src + "-wal"):
                        shutil.copyfile(src + "-wal", dest + "-wal")
                finally:
                    c.execute("ROLLBACK")
        finally:
            c.close()
    d = sqlite3.connect(dest)                            # un solo archivo, sin WAL
    try:
        d.execute("PRAGMA journal_mode = DELETE")
    finally:
        d.close()
    for suf in ("-wal", "-shm"):
        paths.rm(dest + suf)


def _files(folder):
    d = paths.data_dir() / folder
    if not d.is_dir():
        return []
    return sorted(p for p in d.iterdir() if p.is_file() and not p.name.startswith("."))


def estimate():
    """Tamaño aproximado (bytes) con y sin audios, para mostrarlo antes."""
    base = sum(f.stat().st_size for f in [paths.db_file(), paths.settings_file()] if f.is_file())
    base += sum(f.stat().st_size for f in _files("sonidos"))
    logo = settings.get("logo_file") or ""
    if logo and (paths.data_dir() / logo).is_file():
        base += (paths.data_dir() / logo).stat().st_size
    aud = _files("audios")
    return {"base": base, "audios": sum(f.stat().st_size for f in aud), "n_audios": len(aud)}


def filename(con_audios):
    node = re.sub(r"[^A-Za-z0-9]", "", str(settings.get("node") or "")) or "nodo"
    return "hamna-respaldo-{}-{}{}.tar.gz".format(
        node, dt.datetime.now().strftime("%Y%m%d_%H%M"), "-con-audios" if con_audios else "")


# ── Crear (en streaming) ─────────────────────────────────────────────────────
class _Cancel(Exception):
    pass


class _GzQueue:
    """Objeto tipo archivo: comprime con gzip nivel 1 y deja los trozos en
    una cola limitada; si nadie la vacía (descarga lenta), el que escribe espera."""

    def __init__(self):
        self.q = queue.Queue(maxsize=16)
        self.z = zlib.compressobj(1, zlib.DEFLATED, 31)  # 31 = con encabezado gzip
        self.cancel = threading.Event()

    def _put(self, data):
        while data:
            try:
                self.q.put(data, timeout=1)
                return
            except queue.Full:
                if self.cancel.is_set():
                    raise _Cancel()

    def write(self, data):
        if self.cancel.is_set():
            raise _Cancel()
        out = self.z.compress(bytes(data))
        if out:
            self._put(out)
        return len(data)

    def finish(self):
        self._put(self.z.flush())


def stream(con_audios, usuario):
    """Generador con el .tar.gz; arma el archivo en un hilo aparte."""
    w = _GzQueue()
    END = object()
    err = []
    snap = paths.tmp_dir() / ("respaldo_{}.db".format(uuid.uuid4().hex[:8]))
    try:
        _snapshot_db(snap)          # antes de responder: si falla, se ve el error
    except Exception:
        paths.rm(snap)
        raise

    def producir():
        try:
            cfg = settings.load()
            logo = cfg.get("logo_file") or ""
            man = {"app": "hamna-web", "formato": FORMATO, "version": VERSION,
                   "fecha": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                   "nodo": cfg.get("node") or "", "estacion": cfg.get("station_name") or "",
                   "incluye_audios": bool(con_audios), "creado_por": usuario}
            with tarfile.open(fileobj=w, mode="w|", format=tarfile.GNU_FORMAT) as tf:
                data = json.dumps(man, indent=2, ensure_ascii=False).encode("utf-8")
                ti = tarfile.TarInfo(MANIFEST)
                ti.size, ti.mtime, ti.mode = len(data), int(time.time()), 0o600
                tf.addfile(ti, io.BytesIO(data))
                tf.add(str(snap), arcname="hamna.db")
                if paths.settings_file().is_file():
                    tf.add(str(paths.settings_file()), arcname="settings.json")
                if logo and LOGO_RE.match(logo) and (paths.data_dir() / logo).is_file():
                    tf.add(str(paths.data_dir() / logo), arcname=logo)
                for folder in CARPETAS:
                    if folder == "audios" and not con_audios:
                        continue
                    for f in _files(folder):
                        try:
                            tf.add(str(f), arcname=folder + "/" + f.name)
                        except FileNotFoundError:      # se borró mientras tanto
                            pass
            w.finish()
            log.info("Respaldo descargado por %s (%s audios)", usuario, "con" if con_audios else "sin")
        except _Cancel:
            log.info("Respaldo cancelado (se cerró la descarga)")
        except Exception as e:
            log.exception("Error al crear el respaldo")
            err.append(e)
        finally:
            paths.rm(snap)
            try:
                w.q.put(END, timeout=5)
            except queue.Full:
                pass

    threading.Thread(target=producir, daemon=True, name="respaldo").start()

    def gen():
        try:
            while True:
                try:
                    chunk = w.q.get(timeout=120)
                except queue.Empty:
                    break
                if chunk is END:
                    break
                yield chunk
        finally:
            w.cancel.set()

    return gen()


# ── Restaurar ────────────────────────────────────────────────────────────────
def _safe_member(name):
    """Devuelve la ruta destino relativa permitida o None."""
    if name in (MANIFEST, "hamna.db", "settings.json") or LOGO_RE.match(name):
        return name
    parts = name.split("/")
    if (len(parts) == 2 and parts[0] in CARPETAS and parts[1]
            and not parts[1].startswith(".") and "\\" not in parts[1] and "\0" not in parts[1]):
        return name
    return None


def _old_copies():
    return sorted(p for p in paths.data_dir().iterdir()
                  if p.is_dir() and p.name.startswith("antes-de-restaurar-"))


def restore(archivo, conservar_nodo, usuario):
    """Restaura desde un .tar.gz subido. Devuelve un resumen.
    Lo actual se mueve a antes-de-restaurar-<fecha>/ (no se borra)."""
    data = paths.data_dir()
    size = os.path.getsize(archivo)
    free = shutil.disk_usage(str(data)).free
    if free < size * 1.3 + 20 * 2**20:
        raise ValueError("No hay espacio suficiente en el nodo para restaurar ({} MB libres)".format(free // 2**20))

    stage = paths.tmp_dir() / ("restaurar_" + uuid.uuid4().hex[:8])
    os.makedirs(str(stage))
    try:
        # 1) Extraer solo lo permitido a una carpeta temporal
        n_aud = n_son = 0
        try:
            tf = tarfile.open(archivo, "r:*")
        except (tarfile.TarError, OSError):
            raise ValueError("El archivo no es un respaldo de HAMNA (.tar.gz)")
        with tf:
            for m in tf:
                rel = _safe_member(m.name)
                if rel is None or not m.isfile():
                    continue
                dest = stage / rel
                if not dest.parent.is_dir():
                    os.makedirs(str(dest.parent))
                src = tf.extractfile(m)
                with open(str(dest), "wb") as out:
                    shutil.copyfileobj(src, out, 1048576)
                if rel.startswith("audios/"):
                    n_aud += 1
                elif rel.startswith("sonidos/"):
                    n_son += 1

        # 2) Validar
        mf = stage / MANIFEST
        try:
            man = json.loads(mf.read_text(encoding="utf-8"))
        except Exception:
            raise ValueError("El archivo no es un respaldo de HAMNA (falta {})".format(MANIFEST))
        if man.get("app") != "hamna-web":
            raise ValueError("El archivo no es un respaldo de HAMNA Web")
        if int(man.get("formato") or 0) > FORMATO:
            raise ValueError("El respaldo es de una versión más nueva de HAMNA (v{}); actualiza este nodo primero"
                             .format(man.get("version")))
        if not (stage / "hamna.db").is_file():
            raise ValueError("El respaldo no trae la base de datos")
        c = sqlite3.connect(str(stage / "hamna.db"))
        try:
            ok = c.execute("PRAGMA integrity_check").fetchone()[0]
            tablas = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        except sqlite3.DatabaseError:
            ok, tablas = "dañada", set()
        finally:
            c.close()
        if ok != "ok" or not {"eventos", "secciones"} <= tablas:
            raise ValueError("La base de datos del respaldo está dañada")
        incluye_audios = bool(man.get("incluye_audios"))

        # 3) Ajustes: mezclar con los de este nodo
        cur = settings.load()
        nuevo = {}
        if (stage / "settings.json").is_file():
            try:
                nuevo = json.loads((stage / "settings.json").read_text(encoding="utf-8"))
            except Exception:
                raise ValueError("Los ajustes del respaldo están dañados")
        nuevo["secret_key"] = cur.get("secret_key", "")
        if conservar_nodo:
            for k in list(cur):
                if k in NODE_KEYS or k.startswith("irlp_"):
                    nuevo[k] = cur[k]
            for k in list(nuevo):
                if (k in NODE_KEYS or k.startswith("irlp_")) and k not in cur:
                    del nuevo[k]
        logo = nuevo.get("logo_file") or ""
        logo_src = (data / logo) if conservar_nodo else (stage / logo)
        if logo and not (LOGO_RE.match(logo) and logo_src.is_file()):
            nuevo["logo_file"] = ""
        (stage / "settings.json").write_text(json.dumps(nuevo, indent=2, ensure_ascii=False), encoding="utf-8")

        # 4) Cambiar: lo actual a antes-de-restaurar-<fecha>/, lo nuevo a su lugar
        old = data / ("antes-de-restaurar-" + dt.datetime.now().strftime("%Y%m%d_%H%M%S"))
        os.makedirs(str(old))
        with db._lock:
            for name in ("hamna.db", "hamna.db-wal", "hamna.db-shm", "settings.json"):
                if (data / name).exists():
                    os.replace(str(data / name), str(old / name))
            cur_logo = cur.get("logo_file") or ""
            if cur_logo and not conservar_nodo and (data / cur_logo).is_file():
                os.replace(str(data / cur_logo), str(old / cur_logo))
            folders = ["sonidos"] + (["audios"] if incluye_audios else [])
            for folder in folders:
                if (data / folder).is_dir():
                    os.replace(str(data / folder), str(old / folder))
                os.makedirs(str(data / folder), exist_ok=True)
                if (stage / folder).is_dir():
                    for f in (stage / folder).iterdir():
                        os.replace(str(f), str(data / folder / f.name))
            if not conservar_nodo and logo and (stage / logo).is_file():
                os.replace(str(stage / logo), str(data / logo))
            os.replace(str(stage / "hamna.db"), str(data / "hamna.db"))
            os.replace(str(stage / "settings.json"), str(data / "settings.json"))
            try:
                os.chmod(str(data / "settings.json"), 0o600)
            except OSError:
                pass
            settings._cache = None
        # Los audios ya convertidos pueden no corresponder a los nuevos
        for f in paths.cache_dir().iterdir():
            if f.is_file():
                paths.rm(f)
        # Conservar solo las últimas copias de seguridad
        for d in _old_copies()[:-GUARDAR]:
            shutil.rmtree(str(d), ignore_errors=True)

        log.warning("Respaldo restaurado por %s: del nodo %s, %s (v%s), %d audios, %d sonidos; lo anterior en %s",
                    usuario, man.get("nodo") or "?", man.get("fecha"), man.get("version"),
                    n_aud, n_son, old.name)
        return {"nodo": man.get("nodo") or "", "fecha": man.get("fecha") or "",
                "version": man.get("version") or "", "audios": n_aud if incluye_audios else None,
                "sonidos": n_son, "anterior": old.name}
    finally:
        shutil.rmtree(str(stage), ignore_errors=True)


def restart_soon(delay=1.5):
    """Sale con código 1 para que systemd (Restart=on-failure) arranque
    HAMNA de nuevo con la base de datos y los ajustes restaurados."""
    def bye():
        log.warning("Reiniciando HAMNA Web después de restaurar")
        logging.shutdown()
        os._exit(1)
    threading.Timer(delay, bye).start()
