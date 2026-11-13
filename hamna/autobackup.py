"""
HAMNA Web — respaldo automático.

Cada día a la hora elegida arma un respaldo (ver backup.py) y lo manda:
  • a otro nodo HAMNA (por ejemplo el hub), con un código de acceso que da
    ese nodo en Ajustes → Respaldo → Recibir respaldos;
  • a Google Drive u OneDrive con rclone (rclone.conf en la carpeta de datos).

Audios de las secciones: solo se incluyen cuando cambiaron desde el último
respaldo con audios que llegó bien a todos los destinos.

Lado que recibe: /api/remoto/respaldo (sin sesión, con código) guarda los
archivos en /var/lib/hamna/respaldos/<nodo>/ y conserva los últimos.
"""
import datetime as dt
import hashlib
import http.client
import json
import logging
import os
import re
import shutil
import ssl
import subprocess
import tarfile
import threading
import time
import urllib.request

from . import VERSION, backup, db, notify, paths, settings

log = logging.getLogger("hamna.autorespaldo")

KEEP_CON_AUDIOS = 2          # respaldos con audios que se conservan (por nodo / en la nube)
REMOTE = "hamna"             # nombre del remoto en rclone.conf
NAME_RE = re.compile(r"^hamna-respaldo-[A-Za-z0-9]+-\d{8}_\d{4,6}(-con-audios)?\.tar\.gz$")
_run_lock = threading.Lock()
_fired = set()


# ═════════════════════════════════════════════════════════════════════════════
#  Estado
# ═════════════════════════════════════════════════════════════════════════════
def _state_file():
    return paths.data_dir() / "autorespaldo.json"


def load_state():
    try:
        return json.loads(_state_file().read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_state(st):
    f = _state_file()
    tmp = f.with_suffix(".tmp")
    tmp.write_text(json.dumps(st, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(str(tmp), str(f))


def audios_changed(st=None):
    """¿Hay audios que todavía no salieron en un respaldo con audios?"""
    if not backup._files("audios"):
        return False
    return audios_fingerprint() != (st if st is not None else load_state()).get("fp_audios")


def audios_fingerprint():
    h = hashlib.sha1()
    for f in backup._files("audios"):
        s = f.stat()
        h.update("{}|{}|{}\n".format(f.name, s.st_size, int(s.st_mtime)).encode("utf-8"))
    return h.hexdigest()


def running():
    return _run_lock.locked()


# ═════════════════════════════════════════════════════════════════════════════
#  Lado que RECIBE
# ═════════════════════════════════════════════════════════════════════════════
def init():
    with db.conn() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS respaldo_codigos (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            token_hash TEXT NOT NULL UNIQUE,
            etiqueta   TEXT DEFAULT '',
            creado     REAL NOT NULL,
            ultimo_uso REAL,
            ultima_ip  TEXT DEFAULT '',
            ultimo_nodo TEXT DEFAULT '')""")


def _th(token):
    return hashlib.sha256(token.encode()).hexdigest()


def code_create(etiqueta=""):
    token = "hb_" + os.urandom(24).hex()
    db.execute("INSERT INTO respaldo_codigos (token_hash, etiqueta, creado) VALUES (?,?,?)",
               (_th(token), (etiqueta or "").strip()[:60], time.time()))
    return token


def codes():
    return db.rows("SELECT id, etiqueta, creado, ultimo_uso, ultima_ip, ultimo_nodo FROM respaldo_codigos ORDER BY id")


def code_revoke(cid):
    db.execute("DELETE FROM respaldo_codigos WHERE id=?", (cid,))


def code_check(token):
    """Fila del código o None (no actualiza nada)."""
    if not token or not token.startswith("hb_") or len(token) > 80:
        return None
    return db.row("SELECT * FROM respaldo_codigos WHERE token_hash=?", (_th(token),))


def recv_dir(nodo=None):
    d = paths.data_dir() / "respaldos"
    if nodo:
        d = d / nodo
    os.makedirs(str(d), exist_ok=True)
    return d


def _safe_node(s):
    s = re.sub(r"[^A-Za-z0-9]", "", str(s or ""))[:12]
    if not s:
        raise ValueError("Falta el número del nodo que manda el respaldo")
    return s


def _prune(files, keep_sin, keep_con):
    """files: nombres; devuelve los que sobran (los más viejos)."""
    con = sorted(f for f in files if f.endswith("-con-audios.tar.gz"))
    sin = sorted(f for f in files if not f.endswith("-con-audios.tar.gz"))
    return sin[:max(0, len(sin) - keep_sin)] + con[:max(0, len(con) - keep_con)]


def receive(token, tmp_path, nodo, estacion, version, ip):
    """Guarda un respaldo que mandó otro nodo. Devuelve el nombre guardado."""
    row = code_check(token)
    if not row:
        raise PermissionError("Código de acceso inválido")
    nodo = _safe_node(nodo)
    # ¿es de verdad un respaldo de HAMNA? (solo se lee el primer archivo)
    try:
        with tarfile.open(tmp_path, "r:gz") as tf:
            first = tf.next()
            if not first or first.name != backup.MANIFEST:
                raise ValueError()
            man = json.loads(tf.extractfile(first).read().decode("utf-8"))
            if man.get("app") != "hamna-web":
                raise ValueError()
    except Exception:
        raise ValueError("El archivo recibido no es un respaldo de HAMNA")
    con = bool(man.get("incluye_audios"))
    d = recv_dir(nodo)
    name = "hamna-respaldo-{}-{}{}.tar.gz".format(nodo, dt.datetime.now().strftime("%Y%m%d_%H%M%S"),
                                                  "-con-audios" if con else "")
    shutil.move(tmp_path, str(d / name))
    keep = int(settings.get("ab_recv_keep") or 7)
    for old in _prune([f.name for f in d.iterdir() if NAME_RE.match(f.name)], keep, KEEP_CON_AUDIOS):
        paths.rm(d / old)
    meta = {"nodo": nodo, "estacion": estacion or man.get("estacion") or "", "version": version or man.get("version"),
            "ultimo": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "ip": ip, "archivo": name,
            "codigo": row.get("etiqueta") or ""}
    (d / "ultimo.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    db.execute("UPDATE respaldo_codigos SET ultimo_uso=?, ultima_ip=?, ultimo_nodo=? WHERE id=?",
               (time.time(), ip, nodo, row["id"]))
    log.info("Respaldo recibido del nodo %s (%s) desde %s: %s", nodo, estacion, ip, name)
    return name


def received():
    out = []
    base = recv_dir()
    for d in sorted(base.iterdir()):
        if not d.is_dir():
            continue
        files = sorted((f for f in d.iterdir() if NAME_RE.match(f.name)), key=lambda f: f.name, reverse=True)
        try:
            meta = json.loads((d / "ultimo.json").read_text(encoding="utf-8"))
        except Exception:
            meta = {"nodo": d.name}
        meta["archivos"] = [{"nombre": f.name, "tam": f.stat().st_size,
                             "fecha": dt.datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M")}
                            for f in files]
        out.append(meta)
    return out


def received_file(nodo, nombre):
    if not re.match(r"^[A-Za-z0-9]{1,12}$", nodo or "") or not NAME_RE.match(nombre or ""):
        return None
    f = recv_dir() / nodo / nombre
    return f if f.is_file() else None


# ═════════════════════════════════════════════════════════════════════════════
#  Lado que MANDA: a otro nodo
# ═════════════════════════════════════════════════════════════════════════════
def _connect(url, pin="", timeout=60):
    from .sync import _norm_url
    scheme, host, port, base = _norm_url(url)
    if scheme == "https":
        ctx = ssl.SSLContext(getattr(ssl, "PROTOCOL_TLS_CLIENT", ssl.PROTOCOL_SSLv23))
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE                # certificados propios: se fija la huella
        conn = http.client.HTTPSConnection(host, port or 443, timeout=timeout, context=ctx)
        conn.connect()
        fp = hashlib.sha256(conn.sock.getpeercert(True)).hexdigest()
        if pin and fp != pin:
            conn.close()
            raise RuntimeError("El certificado del nodo destino cambió. Si lo renovaron, "
                               "vuelve a probar la conexión y guarda los ajustes.")
    else:
        conn = http.client.HTTPConnection(host, port or 80, timeout=timeout)
        fp = ""
    return conn, base, fp


def _answer(r):
    body = r.read().decode("utf-8", "replace")
    try:
        data = json.loads(body)
    except ValueError:
        data = {}
    if r.status == 401:
        raise RuntimeError("El nodo destino rechazó el código de acceso")
    if r.status == 404:
        raise RuntimeError("El nodo destino no tiene esta función (actualízalo a HAMNA Web 1.16 o más nueva)")
    if r.status != 200 or data.get("ok") is False:
        raise RuntimeError("El nodo destino respondió {}: {}".format(r.status, data.get("error") or r.reason))
    return data


def probe_node(url, token):
    conn, base, fp = _connect(url, timeout=20)
    try:
        conn.request("GET", base + "api/remoto/respaldo",
                     headers={"X-HAMNA-Backup": token, "User-Agent": "HAMNA-Web/" + VERSION})
        data = _answer(conn.getresponse())
    finally:
        conn.close()
    data["huella"] = fp
    return data


def send_to_node(path, cfg, con_audios):
    size = os.path.getsize(path)
    conn, base, _ = _connect(cfg.get("ab_node_url"), cfg.get("ab_node_pin") or "", timeout=300)
    try:
        conn.putrequest("POST", base + "api/remoto/respaldo")
        for k, v in (("X-HAMNA-Backup", cfg.get("ab_node_token") or ""),
                     ("X-HAMNA-Nodo", str(cfg.get("node") or "")),
                     ("X-HAMNA-Estacion", (cfg.get("station_name") or "").encode("utf-8").hex()),
                     ("X-HAMNA-Version", VERSION),
                     ("User-Agent", "HAMNA-Web/" + VERSION),
                     ("Content-Type", "application/gzip"),
                     ("Content-Length", str(size))):
            conn.putheader(k, v)
        conn.endheaders()
        with open(path, "rb") as f:
            while True:
                chunk = f.read(262144)
                if not chunk:
                    break
                conn.send(chunk)
        data = _answer(conn.getresponse())
    finally:
        conn.close()
    return data.get("guardado") or ""


# ═════════════════════════════════════════════════════════════════════════════
#  Lado que MANDA: a la nube con rclone
# ═════════════════════════════════════════════════════════════════════════════
def rclone_conf():
    return paths.data_dir() / "rclone.conf"


def rclone_bin():
    for p in (shutil.which("rclone"), "/usr/local/bin/rclone", "/usr/bin/rclone"):
        if p and os.path.isfile(p) and os.access(p, os.X_OK):
            return p
    return None


def _rc(args, timeout=120):
    exe = rclone_bin()
    if not exe:
        raise RuntimeError("rclone no está instalado en este nodo")
    p = subprocess.run([exe, "--config", str(rclone_conf())] + list(args), stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE, universal_newlines=True, timeout=timeout)
    if p.returncode != 0:
        err = [l for l in (p.stderr or "").splitlines() if l.strip()]
        raise RuntimeError("rclone: " + (err[-1] if err else "falló (código {})".format(p.returncode))[-300:])
    return p.stdout


def rclone_version():
    try:
        return _rc(["version"], 20).splitlines()[0].strip()
    except Exception:
        return ""


def cloud_info():
    """Tipo de nube configurada (drive/onedrive) o ''."""
    try:
        txt = rclone_conf().read_text(encoding="utf-8")
    except OSError:
        return ""
    m = re.search(r"^\[" + REMOTE + r"\][^\[]*?^type\s*=\s*(\w+)", txt, re.M | re.S)
    return m.group(1) if m else ""


def cloud_setup(tipo, token_txt):
    """Escribe rclone.conf con el token de `rclone authorize` y prueba el acceso."""
    if tipo not in ("drive", "onedrive"):
        raise ValueError("Elige Google Drive u OneDrive")
    m = re.search(r"\{.*\}", token_txt or "", re.S)
    try:
        tok = json.loads(m.group(0)) if m else None
    except ValueError:
        tok = None
    if not isinstance(tok, dict) or not tok.get("access_token"):
        raise ValueError("No encontré el token. Pega todo el texto que aparece entre ---> y <--- en tu PC")
    lines = ["[{}]".format(REMOTE), "type = " + tipo]
    if tipo == "drive":
        lines.append("scope = drive")
    else:
        req = urllib.request.Request("https://graph.microsoft.com/v1.0/me/drive",
                                     headers={"Authorization": "Bearer " + tok["access_token"]})
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                d = json.loads(r.read().decode("utf-8"))
        except Exception as e:
            raise RuntimeError("OneDrive no aceptó el token ({}). Vuelve a correr rclone authorize".format(e))
        lines += ["drive_id = " + d["id"], "drive_type = " + d.get("driveType", "personal")]
    lines.append("token = " + json.dumps(tok, separators=(",", ":")))
    f = rclone_conf()
    old = f.read_text(encoding="utf-8") if f.is_file() else None
    f.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.chmod(str(f), 0o600)
    try:
        _rc(["lsd", REMOTE + ":", "--max-depth", "1"], 60)
    except Exception:
        if old is None:
            paths.rm(f)
        else:
            f.write_text(old, encoding="utf-8")
        raise
    log.info("Nube configurada para respaldos: %s", tipo)
    return tipo


def cloud_remove():
    paths.rm(rclone_conf())


def _cloud_dir(cfg):
    folder = re.sub(r"[^A-Za-z0-9 _.-]", "", cfg.get("ab_cloud_folder") or "HAMNA").strip(" .") or "HAMNA"
    nodo = re.sub(r"[^A-Za-z0-9]", "", str(cfg.get("node") or "")) or "nodo"
    return "{}:{}/{}".format(REMOTE, folder, nodo)


def send_to_cloud(path, name, cfg):
    dest = _cloud_dir(cfg)
    _rc(["copyto", path, dest + "/" + name, "--retries", "3"], 3600)
    try:
        files = [l.strip() for l in _rc(["lsf", dest, "--files-only"], 120).splitlines()]
        keep = int(cfg.get("ab_keep") or 7)
        for old in _prune([f for f in files if NAME_RE.match(f)], keep, KEEP_CON_AUDIOS):
            _rc(["deletefile", dest + "/" + old], 120)
    except Exception as e:
        log.warning("No se pudieron borrar respaldos viejos en la nube: %s", e)
    return dest + "/" + name


# ═════════════════════════════════════════════════════════════════════════════
#  Correr
# ═════════════════════════════════════════════════════════════════════════════
def destinations(cfg):
    out = []
    if cfg.get("ab_node_on") and cfg.get("ab_node_url") and cfg.get("ab_node_token"):
        out.append("nodo")
    if cfg.get("ab_cloud_on") and cloud_info():
        out.append("nube")
    return out


def run(origen="manual", audios="auto"):
    if not _run_lock.acquire(False):
        raise RuntimeError("Ya se está haciendo un respaldo")
    tmp = None
    try:
        cfg = settings.load()
        dests = destinations(cfg)
        if not dests:
            raise RuntimeError("No hay destinos configurados (otro nodo o nube)")
        st = load_state()
        fp = audios_fingerprint()
        con = audios == "si" or (audios == "auto" and fp != st.get("fp_audios"))
        nota = ""
        est = backup.estimate()
        if con and not est["n_audios"]:
            con = False
        need = est["base"] + (est["audios"] if con else 0)
        free = shutil.disk_usage(str(paths.tmp_dir())).free
        if con and free < need * 1.1 + 50 * 2**20:
            con, nota = False, "sin audios por falta de espacio en el nodo ({} MB libres)".format(free // 2**20)
        name = backup.filename(con)
        tmp = str(paths.tmp_dir() / ("autorespaldo_" + name))
        t0 = time.time()
        with open(tmp, "wb") as f:
            for chunk in backup.stream(con, "automático"):
                f.write(chunk)
        size = os.path.getsize(tmp)
        res = {}
        for d in dests:
            try:
                where = send_to_node(tmp, cfg, con) if d == "nodo" else send_to_cloud(tmp, name, cfg)
                res[d] = {"ok": True, "detalle": where}
            except Exception as e:
                log.warning("Respaldo a %s falló: %s", d, e)
                res[d] = {"ok": False, "detalle": str(e)}
        all_ok = all(r["ok"] for r in res.values())
        if con and all_ok:
            st["fp_audios"] = fp
        st["ultimo"] = {"fecha": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "origen": origen,
                        "con_audios": con, "tam": size, "segundos": round(time.time() - t0),
                        "resultados": res, "nota": nota, "ok": all_ok}
        if all_ok:
            st["ultimo_ok"] = st["ultimo"]["fecha"]
        if origen == "automático":
            st["auto_dia"] = st["ultimo"]["fecha"][:10]
        _save_state(st)
        log.info("Respaldo automático (%s): %s, %.1f MB, %s", origen, "con audios" if con else "sin audios",
                 size / 1048576.0, ", ".join("{} {}".format(k, "OK" if v["ok"] else "ERROR") for k, v in res.items()))
        if not all_ok:
            fallas = "\n".join("• {}: {}".format("otro nodo" if k == "nodo" else "nube", notify.esc(v["detalle"]))
                               for k, v in res.items() if not v["ok"])
            notify.send("respaldo", "❌ Falló el respaldo automático\n" + fallas, dedupe="respaldo")
        return st["ultimo"]
    except Exception as e:
        if origen != "manual":
            st = load_state()
            st["ultimo"] = {"fecha": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "origen": origen,
                            "ok": False, "resultados": {}, "nota": str(e)}
            if origen == "automático":
                st["auto_dia"] = st["ultimo"]["fecha"][:10]
            _save_state(st)
            notify.send("respaldo", "❌ Falló el respaldo automático\n" + notify.esc(e), dedupe="respaldo")
        raise
    finally:
        if tmp:
            paths.rm(tmp)
        _run_lock.release()


def run_bg(origen, audios="auto"):
    def work():
        try:
            run(origen, audios)
        except Exception as e:
            log.warning("Respaldo (%s) no se hizo: %s", origen, e)
    threading.Thread(target=work, daemon=True, name="autorespaldo").start()


def tick(now, on_air):
    """Lo llama el programador cada 5 s. Si a la hora elegida hay algo al
    aire, se reintenta cada minuto hasta que termine (solo ese día)."""
    cfg = settings.load()
    if not cfg.get("ab_enabled") or not destinations(cfg):
        return
    hora = cfg.get("ab_hora") or "03:30"
    day = now.strftime("%Y-%m-%d")
    if now.strftime("%H:%M") < hora or (day, "hecho") in _fired or running():
        return
    if load_state().get("auto_dia") == day:     # ya se hizo hoy (p. ej. antes de reiniciar)
        _fired.add((day, "hecho"))
        return
    if on_air:
        return
    _fired.add((day, "hecho"))
    for k in [k for k in _fired if k[0] != day]:
        _fired.discard(k)
    run_bg("automático")
