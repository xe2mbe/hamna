"""
HAMNA Web — anuncios cortos programados (Programación → Anuncios).

Cada anuncio es un audio corto (texto → voz, o un audio subido/grabado en el
navegador, siempre WAV 8 kHz mono) que el nodo transmite solo:

  · a ciertas horas, cada N minutos dentro de un horario, o una sola vez;
  · los días de la semana elegidos y, si se pide, solo entre dos fechas;
  · por el radio de este nodo (rpt localplay) o también a los nodos enlazados
    (rpt playback).

Nunca interrumpe: espera a que el canal quede en silencio (nadie recibiendo,
transmitiendo ni hablando por un enlace) unos segundos seguidos. Si en
ESPERA_MAX no se libera, ese turno se salta y queda en la bitácora.

Si el texto lleva variables ({hora}, {dia}…) la voz se genera otra vez al
momento de salir; si eso falla, sale el audio guardado.

En HAMNA además: nunca sale mientras HAMNA transmite un evento, y un evento
que empieza espera a que termine el anuncio en curso (engine.py). Sale por
el mismo backend que los eventos (ASL o IRLP).
"""
import datetime as dt
import json
import logging
import os
import re
import shutil
import threading
import time
import uuid
from pathlib import Path

from . import audio, backends, db, paths, sessions, settings, tts

log = logging.getLogger("hamna.anuncios")

MAX_SEG = 60                 # duración máxima de un anuncio
ESPERA_MAX = 300             # s que se espera a que el canal se libere
SILENCIO = 3                 # s seguidos sin actividad para considerar el canal libre
BITACORA_MAX = 300
MODOS = ("horas", "cada", "una")
HORA_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
FECHA_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
VARS = ("{hora}", "{dia}", "{fecha}", "{fecha_larga}", "{saludo}", "{despedida}", "{nodo}")


def _tiene_variables(t):
    return any(v in (t or "") for v in VARS)


def _nivel(cfg):
    return float(cfg.get("normalize_target", -18)) if cfg.get("section_normalize") else None


def _a_aire(src, dest, cfg):
    """Cualquier audio → WAV 8 kHz mono del aire, con el nivel de Ajustes → Nivel de audio. Devuelve la duración."""
    shutil.copyfile(str(audio.prepare(src, _nivel(cfg))), str(dest))
    return audio.wav_duration(dest)


def _sintetizar(texto, cfg, dest):
    src = tts.synthesize(texto, cfg, paths.tmp_dir() / ("an_voz_" + uuid.uuid4().hex[:8]))
    try:
        return _a_aire(src, dest, cfg)
    finally:
        paths.rm(src)


def carpeta():
    d = paths.data_dir() / "anuncios"
    if not d.is_dir():
        os.makedirs(str(d), exist_ok=True)
    return d


def init():
    with db.conn() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS anuncios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            tipo TEXT NOT NULL DEFAULT 'tts',       -- tts | audio
            texto TEXT NOT NULL DEFAULT '',
            archivo TEXT NOT NULL DEFAULT '',       -- en anuncios/, WAV 8 kHz
            archivo_nombre TEXT NOT NULL DEFAULT '',
            duracion REAL NOT NULL DEFAULT 0,
            dias TEXT NOT NULL DEFAULT '0123456',   -- 0 = lunes
            modo TEXT NOT NULL DEFAULT 'horas',     -- horas | cada | una
            horas TEXT NOT NULL DEFAULT '[]',
            cada_min INTEGER NOT NULL DEFAULT 60,
            desde_h TEXT NOT NULL DEFAULT '08:00',
            hasta_h TEXT NOT NULL DEFAULT '22:00',
            una_vez TEXT NOT NULL DEFAULT '',       -- AAAA-MM-DD HH:MM
            vig_desde TEXT NOT NULL DEFAULT '',
            vig_hasta TEXT NOT NULL DEFAULT '',
            destino TEXT NOT NULL DEFAULT 'local',  -- local | red
            activo INTEGER NOT NULL DEFAULT 1,
            creado_por TEXT NOT NULL DEFAULT '',
            creado TEXT NOT NULL DEFAULT '',
            modificado TEXT NOT NULL DEFAULT '',
            ultima_clave TEXT NOT NULL DEFAULT '',  -- minuto del último turno tomado
            ultimo TEXT NOT NULL DEFAULT '',
            ultimo_estado TEXT NOT NULL DEFAULT '')""")
        c.execute("""CREATE TABLE IF NOT EXISTS anuncios_bitacora (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            anuncio_id INTEGER, nombre TEXT, cuando TEXT, estado TEXT, detalle TEXT)""")


def _ahora():
    return dt.datetime.now().replace(second=0, microsecond=0)


def _fmt(t):
    return t.strftime("%Y-%m-%d %H:%M")


def _min(hhmm):
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


# ── Cuándo toca ──────────────────────────────────────────────────────────────
def _vigente(a, fecha):
    f = fecha.strftime("%Y-%m-%d")
    return (not a["vig_desde"] or f >= a["vig_desde"]) and (not a["vig_hasta"] or f <= a["vig_hasta"])


def _minutos_del_dia(a, dia):
    """Minutos (desde medianoche) en que toca el anuncio ese día, en orden."""
    if not _vigente(a, dia):
        return []
    if a["modo"] == "una":
        try:
            t = dt.datetime.strptime(a["una_vez"], "%Y-%m-%d %H:%M")
        except ValueError:
            return []
        return [t.hour * 60 + t.minute] if t.date() == dia else []
    if str(dia.weekday()) not in a["dias"]:
        return []
    if a["modo"] == "horas":
        return sorted({_min(h) for h in a["horas"] if HORA_RE.match(h)})
    ini, fin, paso = _min(a["desde_h"]), _min(a["hasta_h"]), max(5, int(a["cada_min"] or 60))
    return list(range(ini, fin + 1, paso)) if fin >= ini else []


def toca(a, t):
    return bool(a["activo"]) and (t.hour * 60 + t.minute) in _minutos_del_dia(a, t.date())


def proximo(a, desde=None, dias=8):
    if not a["activo"]:
        return None
    desde = desde or _ahora()
    for d in range(dias):
        dia = desde.date() + dt.timedelta(days=d)
        for m in _minutos_del_dia(a, dia):
            t = dt.datetime.combine(dia, dt.time(m // 60, m % 60))
            if t > desde:
                return t
    return None


# ── Datos ────────────────────────────────────────────────────────────────────
def _fila(r):
    a = dict(r)
    try:
        a["horas"] = [h for h in json.loads(a["horas"] or "[]") if isinstance(h, str)]
    except ValueError:
        a["horas"] = []
    a["activo"] = bool(a["activo"])
    return a


def lista():
    return [_fila(r) for r in db.rows("SELECT * FROM anuncios ORDER BY nombre COLLATE NOCASE")]


def uno(aid):
    r = db.row("SELECT * FROM anuncios WHERE id=?", (aid,))
    if not r:
        raise ValueError("Ese anuncio ya no existe")
    return _fila(r)


def ruta(a):
    return carpeta() / a["archivo"] if a.get("archivo") else None


def _limpio(d, actual=None):
    """Valida lo que manda la página. Devuelve el dict listo para guardar."""
    actual = actual or {}
    a = {}
    a["nombre"] = str(d.get("nombre") or "").strip()[:80]
    if not a["nombre"]:
        raise ValueError("Ponle un nombre al anuncio")
    a["tipo"] = "audio" if d.get("tipo") == "audio" else "tts"
    a["texto"] = str(d.get("texto") or "").strip()[:2000]
    if a["tipo"] == "tts" and not a["texto"]:
        raise ValueError("Escribe lo que dirá el anuncio")
    a["modo"] = d.get("modo") if d.get("modo") in MODOS else "horas"
    dias = "".join(sorted({c for c in str(d.get("dias") or "") if c in "0123456"}))
    a["dias"] = dias
    if a["modo"] != "una" and not dias:
        raise ValueError("Elige al menos un día")
    horas = sorted({h for h in (d.get("horas") or []) if isinstance(h, str) and HORA_RE.match(h)})
    a["horas"] = json.dumps(horas)
    if a["modo"] == "horas" and not horas:
        raise ValueError("Agrega al menos una hora")
    try:
        a["cada_min"] = int(d.get("cada_min") or 60)
    except (TypeError, ValueError):
        raise ValueError("Cada cuántos minutos: escribe un número")
    if a["modo"] == "cada" and not 5 <= a["cada_min"] <= 1440:
        raise ValueError("Cada cuántos minutos: de 5 a 1440")
    a["desde_h"] = str(d.get("desde_h") or "08:00")
    a["hasta_h"] = str(d.get("hasta_h") or "22:00")
    if a["modo"] == "cada":
        if not (HORA_RE.match(a["desde_h"]) and HORA_RE.match(a["hasta_h"])):
            raise ValueError("Horario inválido (HH:MM)")
        if _min(a["hasta_h"]) < _min(a["desde_h"]):
            raise ValueError("La hora final debe ser después de la inicial")
    a["una_vez"] = str(d.get("una_vez") or "").replace("T", " ")[:16]
    if a["modo"] == "una":
        try:
            dt.datetime.strptime(a["una_vez"], "%Y-%m-%d %H:%M")
        except ValueError:
            raise ValueError("Elige la fecha y la hora")
    for k in ("vig_desde", "vig_hasta"):
        v = str(d.get(k) or "")
        if v and not FECHA_RE.match(v):
            raise ValueError("Fecha de vigencia inválida")
        a[k] = v
    if a["vig_desde"] and a["vig_hasta"] and a["vig_hasta"] < a["vig_desde"]:
        raise ValueError("La vigencia termina antes de empezar")
    a["destino"] = "red" if d.get("destino") == "red" else "local"
    a["activo"] = 1 if d.get("activo", actual.get("activo", True)) not in (False, 0, "0", "false") else 0
    return a


def _guardar_audio(src, nombre_original=""):
    """WAV que manda el navegador (ya en 8 kHz mono) → anuncios/. Devuelve (archivo, duración)."""
    nombre = "an_{}.wav".format(uuid.uuid4().hex[:10])
    dest = carpeta() / nombre
    tmp = paths.tmp_dir() / "an_up_{}.wav".format(uuid.uuid4().hex[:8])   # sox necesita la extensión
    try:
        shutil.copyfile(str(src), str(tmp))
        dur = _a_aire(tmp, dest, settings.load())
    except Exception as e:
        paths.rm(dest)
        raise ValueError("No pude leer el audio ({}). Súbelo otra vez desde la página.".format(e))
    finally:
        paths.rm(tmp)
    if dur > MAX_SEG + 0.5:
        paths.rm(dest)
        raise ValueError("El audio dura {:.0f} s; el máximo es {} s".format(dur, MAX_SEG))
    if dur < 0.3:
        paths.rm(dest)
        raise ValueError("El audio está vacío")
    return nombre, dur


def _voz(texto, cfg):
    nombre = "an_{}.wav".format(uuid.uuid4().hex[:10])
    dest = carpeta() / nombre
    try:
        dur = _sintetizar(texto, cfg, dest)
    except Exception:
        paths.rm(dest)
        raise
    if dur > MAX_SEG + 0.5:
        paths.rm(dest)
        raise ValueError("Con esa voz el anuncio dura {:.0f} s; el máximo es {} s. Acórtalo.".format(dur, MAX_SEG))
    return nombre, dur


def guardar(datos, archivo_subido=None, nombre_subido="", usuario="", aid=None):
    actual = uno(aid) if aid else {}
    a = _limpio(datos, actual)
    viejo = actual.get("archivo") or ""
    nuevo = None
    if a["tipo"] == "audio":
        if archivo_subido:
            nuevo, a["duracion"] = _guardar_audio(archivo_subido)
            a["archivo_nombre"] = (nombre_subido or "audio.wav")[:80]
        elif actual.get("tipo") == "audio" and viejo:
            a["duracion"], a["archivo_nombre"] = actual["duracion"], actual["archivo_nombre"]
        else:
            raise ValueError("Sube o graba el audio del anuncio")
    else:
        a["archivo_nombre"] = ""
        if actual.get("tipo") == "tts" and actual.get("texto") == a["texto"] and viejo and \
                (carpeta() / viejo).is_file() and not datos.get("rehacer_voz"):
            a["duracion"] = actual["duracion"]
        else:
            nuevo, a["duracion"] = _voz(a["texto"], settings.load())
    if nuevo:
        a["archivo"] = nuevo
    ahora = _fmt(dt.datetime.now())
    a["modificado"] = ahora
    try:
        if aid:
            cols = ", ".join("{}=?".format(k) for k in a)
            db.execute("UPDATE anuncios SET {} WHERE id=?".format(cols), list(a.values()) + [aid])
        else:
            a["creado"], a["creado_por"] = ahora, usuario
            aid = db.execute("INSERT INTO anuncios ({}) VALUES ({})".format(
                ", ".join(a), ", ".join("?" * len(a))), list(a.values()))
    except Exception:
        if nuevo:
            paths.rm(carpeta() / nuevo)
        raise
    if nuevo and viejo:
        paths.rm(carpeta() / viejo)
    log.info("%s %s el anuncio «%s»", usuario or "?", "editó" if actual else "creó", a["nombre"])
    return uno(aid)


def activar(aid, on, usuario=""):
    a = uno(aid)
    db.execute("UPDATE anuncios SET activo=? WHERE id=?", (1 if on else 0, aid))
    log.info("%s %s el anuncio «%s»", usuario, "activó" if on else "pausó", a["nombre"])
    return uno(aid)


def borrar(aid, usuario=""):
    a = uno(aid)
    db.execute("DELETE FROM anuncios WHERE id=?", (aid,))
    if a["archivo"]:
        paths.rm(carpeta() / a["archivo"])
    log.info("%s borró el anuncio «%s»", usuario, a["nombre"])


def vista_previa(texto, cfg):
    """Voz de prueba para el editor: (url, texto dicho, duración)."""
    texto = (texto or "").strip()
    if not texto:
        raise ValueError("Escribe el texto del anuncio")
    out = paths.tmp_dir() / "voz_{}.wav".format(uuid.uuid4().hex[:8])
    dur = _sintetizar(texto, cfg, out)
    return out.name, tts.resolve_variables(texto, cfg), dur


def bitacora(limite=50):
    return db.rows("SELECT * FROM anuncios_bitacora ORDER BY id DESC LIMIT ?", (limite,))


def _anotar(a, estado, detalle=""):
    cuando = _fmt(dt.datetime.now())
    with db.conn() as c:
        c.execute("INSERT INTO anuncios_bitacora (anuncio_id, nombre, cuando, estado, detalle) VALUES (?,?,?,?,?)",
                  (a["id"], a["nombre"], cuando, estado, detalle[:300]))
        c.execute("UPDATE anuncios SET ultimo=?, ultimo_estado=? WHERE id=?", (cuando, estado, a["id"]))
        c.execute("DELETE FROM anuncios_bitacora WHERE id <= (SELECT MAX(id) FROM anuncios_bitacora) - ?",
                  (BITACORA_MAX,))


# ── Al aire ──────────────────────────────────────────────────────────────────
class Emisor:
    """Una sola cola: los anuncios salen uno tras otro, cuando el canal está libre."""

    def __init__(self):
        self.cola = []                 # [(id, motivo)]
        self.lock = threading.Lock()
        self.evento = threading.Event()
        self.actual = None             # {"id", "nombre", "estado": esperando|al_aire, "desde"}
        self.hilo = None

    def start(self):
        if not self.hilo:
            self.hilo = threading.Thread(target=self._loop, daemon=True, name="hamna-anuncios")
            self.hilo.start()

    def encolar(self, aid, motivo="programado"):
        with self.lock:
            if any(x == aid for x, _ in self.cola) or (self.actual and self.actual["id"] == aid):
                return False
            self.cola.append((aid, motivo))
        self.evento.set()
        return True

    def estado(self):
        with self.lock:
            return {"actual": dict(self.actual) if self.actual else None, "en_cola": [x for x, _ in self.cola]}

    def al_aire(self):
        with self.lock:
            return bool(self.actual and self.actual.get("estado") == "al_aire")

    def esperar_fin(self, maximo=MAX_SEG + 15):
        """Para quien va a transmitir otra cosa: espera a que termine el anuncio en curso."""
        fin = time.time() + maximo
        while self.al_aire() and time.time() < fin:
            time.sleep(0.5)

    def _loop(self):
        while True:
            self.evento.wait(5)
            self.evento.clear()
            while True:
                with self.lock:
                    if not self.cola:
                        break
                    aid, motivo = self.cola.pop(0)
                    # Ya cuenta como «en curso»: que no se pueda encolar otra vez mientras arranca
                    self.actual = {"id": aid, "nombre": "", "estado": "esperando", "desde": time.time(), "motivo": motivo}
                try:
                    self._uno(aid, motivo)
                except Exception as e:
                    log.exception("Anuncio %s", aid)
                    try:
                        _anotar(uno(aid), "error", str(e))
                    except Exception:
                        pass
                finally:
                    with self.lock:
                        self.actual = None

    def _uno(self, aid, motivo):
        try:
            a = uno(aid)
        except ValueError:
            return
        cfg = settings.load()
        be = _backend(cfg, a["destino"])
        if be.name == "asl" and not be.node:
            _anotar(a, "error", "Falta el número de nodo (Ajustes → Nodo)")
            return
        with self.lock:
            self.actual = {"id": aid, "nombre": a["nombre"], "estado": "esperando", "desde": time.time(), "motivo": motivo}
        if not self._esperar_libre(be, cfg):
            log.info("Anuncio «%s» saltado: el canal no se liberó en %d min", a["nombre"], ESPERA_MAX // 60)
            _anotar(a, "saltado", "El canal estuvo ocupado {} min".format(ESPERA_MAX // 60))
            return
        wav, temporal = ruta(a), None
        if a["tipo"] == "tts" and _tiene_variables(a["texto"]):
            temporal = paths.tmp_dir() / "an_aire_{}.wav".format(uuid.uuid4().hex[:8])
            try:
                _sintetizar(a["texto"], cfg, temporal)
                wav = temporal
            except Exception as e:
                log.warning("No pude generar la voz al momento (%s); sale el audio guardado", e)
                paths.rm(temporal)
                temporal = None
        if not wav or not wav.is_file():
            _anotar(a, "error", "Falta el audio del anuncio; edítalo y guárdalo otra vez")
            return
        dur = audio.wav_duration(wav)
        try:
            with self.lock:
                self.actual.update(estado="al_aire", desde=time.time(), dur=dur)
            log.info("Anuncio «%s» al aire (%s, %.1f s, %s)", a["nombre"], be.name, dur, motivo)
            be.play(str(wav), dur, lambda: False)
            _anotar(a, "ok", ("manual · " if motivo != "programado" else "") +
                    ("nodo y enlaces" if a["destino"] == "red" else "solo este nodo"))
        finally:
            if temporal:
                # Asterisk ya lo leyó; se borra un poco después por si va retrasado
                threading.Timer(30, paths.rm, (temporal,)).start()

    def _esperar_libre(self, be, cfg):
        fin = time.time() + ESPERA_MAX
        quieto = 0
        while time.time() < fin:
            if canal_libre(be, cfg):
                quieto += 1
                if quieto >= SILENCIO:
                    return True
            else:
                quieto = 0
            time.sleep(1)
        return False


def _backend(cfg, destino):
    """El backend de los eventos, con el destino del anuncio: solo el radio local o también la red."""
    red = destino == "red"
    return backends.make(dict(cfg, asl_mode="playback" if red else "localplay", irlp_mode="red" if red else "local"))


def canal_libre(be, cfg):
    from .engine import engine
    if engine.busy():                       # HAMNA transmitiendo un evento
        return False
    if be.name == "irlp":
        try:
            st = sessions.irlp_status(cfg)
        except Exception:
            return False
        return not st.get("cos") and not st.get("ptt")
    if be.name != "asl":
        return True                         # simulado
    try:
        out = sessions._rx("rpt xnode {}".format(be.node), timeout=6)
    except Exception:
        return False
    if "RPT_" not in out:
        return False
    _e, _r, v = sessions.parse_xnode(out)
    if v.get("RPT_RXKEYED") == "1" or v.get("RPT_TXKEYED") == "1":
        return False
    # Alguien hablando por un enlace: RPT_ALINKS=2,59624TK,…  (K = transmitiendo)
    return not any(re.match(r"^\w+[TRCM]K$", x.strip()) for x in (v.get("RPT_ALINKS") or "").split(",")[1:])


emisor = Emisor()


# ── Programador (lo llama scheduler.loop cada pocos segundos) ────────────────
def tick(now=None):
    t = (now or dt.datetime.now()).replace(second=0, microsecond=0)
    clave = _fmt(t)
    for a in lista():
        if a["ultima_clave"] == clave or not toca(a, t):
            continue
        db.execute("UPDATE anuncios SET ultima_clave=? WHERE id=?", (clave, a["id"]))
        emisor.start()
        emisor.encolar(a["id"])
        log.info("Toca el anuncio «%s» (%s)", a["nombre"], clave)


def resumen():
    """Lo que necesita la página: anuncios con su próximo turno, el siguiente, la cola y la bitácora."""
    ahora = _ahora()
    out = []
    for a in lista():
        p = proximo(a, ahora)
        a["proximo"] = _fmt(p) if p else ""
        out.append(a)
    sig = min((a for a in out if a["proximo"]), key=lambda a: a["proximo"], default=None)
    cfg = settings.load()
    eng = cfg.get("tts_engine") or "azure"
    return {"anuncios": out, "siguiente": {"id": sig["id"], "nombre": sig["nombre"], "cuando": sig["proximo"]} if sig else None,
            "emisor": emisor.estado(), "bitacora": bitacora(30), "max_seg": MAX_SEG, "espera_min": ESPERA_MAX // 60,
            "voz": {"motor": eng, "nombre": tts.NOMBRES.get(eng, eng), "lista": tts.configurado(eng, cfg),
                    "variables": [v for v in tts.VARIABLES if v[0] in VARS]},
            "asl": True, "ahora": _fmt(ahora)}
