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

MAX_SEG = 60                 # duración máxima de un anuncio (de fábrica; Ajustes → Voz la cambia)
MAX_SEG_RANGO = (30, 170)    # lo que se puede elegir: 170 s cabe en un TOT de 3 min
MAX_CHARS = 2000             # caracteres del texto (de fábrica)
MAX_CHARS_RANGO = (200, 4000)
VOZ_KEYS = ("azure_voice", "azure_style", "azure_rate", "azure_pitch")   # voz propia de un anuncio
ESPERA_MAX = 300             # s que se espera a que el canal se libere
SILENCIO = 3                 # s seguidos sin actividad para considerar el canal libre
BITACORA_MAX = 300
HORA_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
FECHA_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
VARS = ("{hora}", "{dia}", "{fecha}", "{fecha_larga}", "{saludo}", "{despedida}", "{nodo}")


def _tiene_variables(t):
    from . import horas
    return any(v in (t or "") for v in VARS) or horas.tiene(t)


def _nivel(cfg):
    return float(cfg.get("normalize_target", -18)) if cfg.get("section_normalize") else None


def _a_aire(src, dest, cfg):
    """Cualquier audio → WAV 8 kHz mono del aire, con el nivel de Ajustes → Nivel de audio. Devuelve la duración."""
    shutil.copyfile(str(audio.prepare(src, _nivel(cfg))), str(dest))
    return audio.wav_duration(dest)


def _sintetizar(texto, cfg, dest, respaldo=True):
    src = tts.synthesize(texto, cfg, paths.tmp_dir() / ("an_voz_" + uuid.uuid4().hex[:8]), respaldo=respaldo)
    try:
        return _a_aire(src, dest, cfg)
    finally:
        paths.rm(src)


def max_seg(cfg=None):
    cfg = cfg if cfg is not None else settings.load()
    try:
        v = int(cfg.get("anuncio_max_seg") or MAX_SEG)
    except (TypeError, ValueError):
        v = MAX_SEG
    return max(MAX_SEG_RANGO[0], min(MAX_SEG_RANGO[1], v))


def max_chars(cfg=None):
    cfg = cfg if cfg is not None else settings.load()
    try:
        v = int(cfg.get("anuncio_max_chars") or MAX_CHARS)
    except (TypeError, ValueError):
        v = MAX_CHARS
    return max(MAX_CHARS_RANGO[0], min(MAX_CHARS_RANGO[1], v))


def tot_nodo(cfg=None):
    """TOT del nodo en segundos (totime de rpt.conf en ms, también en su plantilla; app_rpt usa
    180 s si no está). None si no es ASL o no se puede leer."""
    cfg = cfg if cfg is not None else settings.load()
    kind = cfg.get("backend") or "auto"
    if kind == "auto":
        kind = backends.detect()
    if kind != "asl":
        return None
    try:
        with open("/etc/asterisk/rpt.conf", encoding="utf-8", errors="replace") as f:
            txt = f.read()
    except OSError:
        return None
    secs, cur = {}, None
    for ln in txt.splitlines():
        ln = ln.split(";", 1)[0].strip()
        m = re.match(r"^\[([^\]]+)\]\s*(?:\(([^)]*)\))?", ln)
        if m:
            cur = m.group(1).strip()
            plant = [x.strip() for x in (m.group(2) or "").split(",") if x.strip() and x.strip() != "!"]
            secs[cur] = {"plant": plant, "claves": {}}
            continue
        if cur and "=" in ln:
            k, _, v = ln.partition("=")
            secs[cur]["claves"][k.strip().rstrip(">").strip()] = v.strip()
    nodo = str(cfg.get("node") or backends.detect_asl_node() or "")

    def valor(s, visto):
        if s in visto or s not in secs:
            return None
        visto.add(s)
        if "totime" in secs[s]["claves"]:
            return secs[s]["claves"]["totime"]
        for t in secs[s]["plant"]:
            v = valor(t, visto)
            if v is not None:
                return v
        return None
    if nodo not in secs:
        return None
    v = valor(nodo, set())
    try:
        return (int(v) if v not in (None, "") else 180000) // 1000
    except ValueError:
        return None


def voz_limpia(d):
    """La voz propia de un anuncio (solo Azure por ahora). {} = la de Ajustes."""
    if isinstance(d, str):
        try:
            d = json.loads(d or "{}")
        except ValueError:
            d = {}
    if not isinstance(d, dict) or not str(d.get("azure_voice") or "").strip():
        return {}
    v = {"azure_voice": str(d["azure_voice"]).strip()[:80]}
    if not re.match(r"^[A-Za-z]{2,3}-[A-Za-z0-9]{2,8}-[A-Za-z0-9:]+$", v["azure_voice"]):
        raise ValueError("Nombre de voz de Azure inválido")
    estilo = str(d.get("azure_style") or "general").strip()[:40]
    if not re.match(r"^[A-Za-z_-]+$", estilo):
        raise ValueError("Estilo de voz inválido")
    v["azure_style"] = estilo
    try:
        v["azure_rate"] = int(float(d.get("azure_rate") or 100))
        v["azure_pitch"] = int(float(d.get("azure_pitch") or 0))
    except (TypeError, ValueError):
        raise ValueError("Velocidad o tono inválidos")
    if not 50 <= v["azure_rate"] <= 200:
        raise ValueError("Velocidad de la voz: de 50 a 200 %")
    if not -50 <= v["azure_pitch"] <= 50:
        raise ValueError("Tono de la voz: de -50 a 50 Hz")
    return v


def cfg_con_voz(cfg, voz):
    try:
        voz = voz_limpia(voz)
    except ValueError:
        voz = {}
    if not voz or (cfg.get("tts_engine") or "azure") != "azure":
        return cfg
    return dict(cfg, **voz)


def sintetizar_voz(texto, cfg, voz, dest):
    """Con la voz propia del anuncio. Si esa voz falla (ya no existe…), sale con la de Ajustes
    (y su cadena de respaldo). Devuelve (duración, aviso)."""
    c2 = cfg_con_voz(cfg, voz)
    if c2 is cfg:
        return _sintetizar(texto, cfg, dest), ""
    try:
        return _sintetizar(texto, c2, dest, respaldo=False), ""
    except Exception as e:
        log.warning("La voz %s falló (%s); sale con la de Ajustes", c2.get("azure_voice"), e)
        return _sintetizar(texto, cfg, dest), "La voz {} falló; salió con la de Ajustes".format(c2.get("azure_voice"))


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
        cols = {r[1] for r in c.execute("PRAGMA table_info(anuncios)").fetchall()}
        if "evento_id" not in cols:                 # «antes de un evento» (HAMNA)
            c.execute("ALTER TABLE anuncios ADD COLUMN evento_id INTEGER NOT NULL DEFAULT 0")
        if "antes" not in cols:
            c.execute("ALTER TABLE anuncios ADD COLUMN antes TEXT NOT NULL DEFAULT '[]'")
        if "voz" not in cols:                       # voz propia (JSON con azure_voice…); vacío = la de Ajustes
            c.execute("ALTER TABLE anuncios ADD COLUMN voz TEXT NOT NULL DEFAULT ''")


def _ahora():
    return dt.datetime.now().replace(second=0, microsecond=0)


def _fmt(t):
    return t.strftime("%Y-%m-%d %H:%M")


def _min(hhmm):
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


# ── Antes de un evento ───────────────────────────────────────────────────────
EVENTOS = True


def _turnos_evento(a, dia):
    """Minutos antes de cada fecha en que sale el evento (las mismas que calcula el
    programador: zona horaria, recurrencia y pausas incluidas)."""
    from .engine import Engine
    antes = [m for m in (a.get("antes") or []) if 0 < m <= 720]
    if not antes or not a.get("evento_id"):
        return []
    ini = dt.datetime.combine(dia, dt.time(0, 0))
    fin = ini + dt.timedelta(days=1, minutes=max(antes))
    out = set()
    for r in db.get_programacion(solo_activos=True):
        if r["evento_id"] != a["evento_id"]:
            continue
        for occ in Engine.occurrences(r, ini, fin):
            for m in antes:
                t = occ - dt.timedelta(minutes=m)
                if t.date() == dia:
                    out.add(t.hour * 60 + t.minute)
    red = a["destino"] == "red"
    return [(m, red) for m in sorted(out)]


def _evento_valido(d):
    try:
        eid = int(d.get("evento_id") or 0)
    except (TypeError, ValueError):
        eid = 0
    if not eid or not db.get_evento(eid):
        raise ValueError("Elige el evento")
    antes = set()
    for x in d.get("antes") or []:
        try:
            x = int(x)
        except (TypeError, ValueError):
            continue
        if 1 <= x <= 720:
            antes.add(x)
    if not antes:
        raise ValueError("Agrega cuántos minutos antes del evento (de 1 a 720)")
    return eid, sorted(antes, reverse=True)


def _eventos_resumen():
    prog = {r["evento_id"] for r in db.get_programacion(solo_activos=True)}
    return [{"id": e["id"], "nombre": e["nombre"], "programado": e["id"] in prog} for e in db.get_eventos()]
# ── fin eventos ──


MODOS = ("horas", "cada", "una") + (("evento",) if EVENTOS else ())


# ── Cuándo toca ──────────────────────────────────────────────────────────────
def _vigente(a, fecha):
    f = fecha.strftime("%Y-%m-%d")
    return (not a["vig_desde"] or f >= a["vig_desde"]) and (not a["vig_hasta"] or f <= a["vig_hasta"])


def _turnos_del_dia(a, dia):
    """[(minuto desde medianoche, red)] en que toca el anuncio ese día, en orden.
    red = también sale a los nodos enlazados (RF + Net). En «A estas horas» cada
    hora tiene su propio destino; en los demás modos vale el del anuncio."""
    red = a["destino"] == "red"
    if a["modo"] == "evento":
        return _turnos_evento(a, dia)
    if not _vigente(a, dia):
        return []
    if a["modo"] == "una":
        try:
            t = dt.datetime.strptime(a["una_vez"], "%Y-%m-%d %H:%M")
        except ValueError:
            return []
        return [(t.hour * 60 + t.minute, red)] if t.date() == dia else []
    if str(dia.weekday()) not in a["dias"]:
        return []
    if a["modo"] == "horas":
        d = {}
        for x in a["horas"]:
            if HORA_RE.match(x["h"]):
                d[_min(x["h"])] = d.get(_min(x["h"]), False) or x["red"]
        return sorted(d.items())
    ini, fin, paso = _min(a["desde_h"]), _min(a["hasta_h"]), max(5, int(a["cada_min"] or 60))
    return [(m, red) for m in range(ini, fin + 1, paso)] if fin >= ini else []


def _minutos_del_dia(a, dia):
    return [m for m, _r in _turnos_del_dia(a, dia)]


def turno(a, t):
    """None si a esa hora no toca; si toca, el destino de ese turno: "red" o "local"."""
    if not a["activo"]:
        return None
    m = t.hour * 60 + t.minute
    for x, red in _turnos_del_dia(a, t.date()):
        if x == m:
            return "red" if red else "local"
    return None


def toca(a, t):
    return turno(a, t) is not None


def proximo_turno(a, desde=None, dias=8):
    """(fecha-hora, red) del siguiente turno, o (None, None)."""
    if not a["activo"]:
        return None, None
    desde = desde or _ahora()
    for d in range(dias):
        dia = desde.date() + dt.timedelta(days=d)
        for m, red in _turnos_del_dia(a, dia):
            t = dt.datetime.combine(dia, dt.time(m // 60, m % 60))
            if t > desde:
                return t, red
    return None, None


def proximo(a, desde=None, dias=8):
    return proximo_turno(a, desde, dias)[0]


# ── Datos ────────────────────────────────────────────────────────────────────
def _fila(r):
    a = dict(r)
    # horas: [{"h": "HH:MM", "red": bool}]; las de antes eran solo "HH:MM" con el destino del anuncio
    red = a.get("destino") == "red"
    try:
        crudo = json.loads(a["horas"] or "[]")
    except ValueError:
        crudo = []
    a["horas"] = []
    for x in crudo:
        if isinstance(x, str):
            a["horas"].append({"h": x, "red": red})
        elif isinstance(x, dict) and isinstance(x.get("h"), str):
            a["horas"].append({"h": x["h"], "red": bool(x.get("red"))})
    try:
        a["antes"] = [int(x) for x in json.loads(a.get("antes") or "[]")]
    except (TypeError, ValueError):
        a["antes"] = []
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
    a["texto"] = str(d.get("texto") or "").strip()
    tope = max_chars()
    if len(a["texto"]) > tope:
        raise ValueError("El texto tiene {} caracteres; el máximo es {} (Ajustes → Voz)".format(len(a["texto"]), tope))
    if a["tipo"] == "tts" and not a["texto"]:
        raise ValueError("Escribe lo que dirá el anuncio")
    voz = voz_limpia(d.get("voz") or {}) if a["tipo"] == "tts" else {}
    a["voz"] = json.dumps(voz, sort_keys=True) if voz else ""
    a["modo"] = d.get("modo") if d.get("modo") in MODOS else "horas"
    dias = "".join(sorted({c for c in str(d.get("dias") or "") if c in "0123456"}))
    a["dias"] = dias
    if a["modo"] in ("horas", "cada") and not dias:
        raise ValueError("Elige al menos un día")
    red_def = d.get("destino") == "red"
    hs = {}
    for x in d.get("horas") or []:
        h, r = (x, red_def) if isinstance(x, str) else ((x or {}).get("h"), bool((x or {}).get("red")))
        if isinstance(h, str) and HORA_RE.match(h):
            hs[h] = hs.get(h, False) or r
    horas = [{"h": h, "red": hs[h]} for h in sorted(hs)]
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
    a["evento_id"], a["antes"] = 0, "[]"
    if a["modo"] == "evento":
        a["evento_id"], antes = _evento_valido(d)
        a["antes"] = json.dumps(antes)
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
    tope = max_seg()
    if dur > tope + 0.5:
        paths.rm(dest)
        raise ValueError("El audio dura {:.0f} s; el máximo es {} s".format(dur, tope))
    if dur < 0.3:
        paths.rm(dest)
        raise ValueError("El audio está vacío")
    return nombre, dur


def _voz(texto, cfg, voz=""):
    nombre = "an_{}.wav".format(uuid.uuid4().hex[:10])
    dest = carpeta() / nombre
    c2 = cfg_con_voz(cfg, voz)
    try:
        # Al guardar, si la voz elegida falla se avisa (no se cambia sola por otra)
        dur = _sintetizar(texto, c2, dest, respaldo=c2 is cfg)
    except Exception:
        paths.rm(dest)
        raise
    tope = max_seg(cfg)
    if dur > tope + 0.5:
        paths.rm(dest)
        raise ValueError("Con esa voz el anuncio dura {:.0f} s; el máximo es {} s. Acórtalo.".format(dur, tope))
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
                (actual.get("voz") or "") == a["voz"] and \
                (carpeta() / viejo).is_file() and not datos.get("rehacer_voz"):
            a["duracion"] = actual["duracion"]
        else:
            nuevo, a["duracion"] = _voz(a["texto"], settings.load(), a["voz"])
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


def vista_previa(texto, cfg, voz=None):
    """Voz de prueba para el editor: (url, texto dicho, duración)."""
    texto = (texto or "").strip()
    if not texto:
        raise ValueError("Escribe el texto del anuncio")
    out = paths.tmp_dir() / "voz_{}.wav".format(uuid.uuid4().hex[:8])
    c2 = cfg_con_voz(cfg, voz or {})
    dur = _sintetizar(texto, c2, out, respaldo=c2 is cfg)
    from . import pronuncia
    return out.name, pronuncia.para_voz(tts.resolve_variables(texto, cfg), cfg), dur


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
        self.cola = []                 # [(id, motivo, destino)]; destino None = el del anuncio
        self.lock = threading.Lock()
        self.evento = threading.Event()
        self.actual = None             # {"id", "nombre", "estado": esperando|al_aire, "desde"}
        self.hilo = None

    def start(self):
        if not self.hilo:
            self.hilo = threading.Thread(target=self._loop, daemon=True, name="hamna-anuncios")
            self.hilo.start()

    def encolar(self, aid, motivo="programado", destino=None):
        with self.lock:
            if any(x[0] == aid for x in self.cola) or (self.actual and self.actual["id"] == aid):
                return False
            self.cola.append((aid, motivo, destino))
        self.evento.set()
        return True

    def estado(self):
        with self.lock:
            return {"actual": dict(self.actual) if self.actual else None, "en_cola": [x[0] for x in self.cola]}

    def al_aire(self):
        with self.lock:
            return bool(self.actual and self.actual.get("estado") == "al_aire")

    def esperar_fin(self, maximo=MAX_SEG_RANGO[1] + 15):
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
                    aid, motivo, destino = self.cola.pop(0)
                    # Ya cuenta como «en curso»: que no se pueda encolar otra vez mientras arranca
                    self.actual = {"id": aid, "nombre": "", "estado": "esperando", "desde": time.time(), "motivo": motivo}
                try:
                    self._uno(aid, motivo, destino)
                except Exception as e:
                    log.exception("Anuncio %s", aid)
                    try:
                        _anotar(uno(aid), "error", str(e))
                    except Exception:
                        pass
                finally:
                    with self.lock:
                        self.actual = None

    def _uno(self, aid, motivo, destino=None):
        try:
            a = uno(aid)
        except ValueError:
            return
        destino = destino if destino in ("local", "red") else a["destino"]
        cfg = settings.load()
        be = _backend(cfg, destino)
        if be.name == "asl" and not be.node:
            _anotar(a, "error", "Falta el número de nodo (Ajustes → Nodo)")
            return
        with self.lock:
            self.actual = {"id": aid, "nombre": a["nombre"], "estado": "esperando", "desde": time.time(), "motivo": motivo,
                           "destino": destino}
        if not self._esperar_libre(be, cfg):
            log.info("Anuncio «%s» saltado: el canal no se liberó en %d min", a["nombre"], ESPERA_MAX // 60)
            _anotar(a, "saltado", "El canal estuvo ocupado {} min".format(ESPERA_MAX // 60))
            return
        wav, temporal, aviso = ruta(a), None, ""
        if a["tipo"] == "tts" and _tiene_variables(a["texto"]):
            temporal = paths.tmp_dir() / "an_aire_{}.wav".format(uuid.uuid4().hex[:8])
            try:
                _dur, aviso = sintetizar_voz(a["texto"], cfg, a.get("voz"), temporal)
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
                    ("nodo y enlaces" if destino == "red" else "solo este nodo") + (" · " + aviso if aviso else ""))
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
        if a["ultima_clave"] == clave:
            continue
        destino = turno(a, t)
        if not destino:
            continue
        db.execute("UPDATE anuncios SET ultima_clave=? WHERE id=?", (clave, a["id"]))
        emisor.start()
        emisor.encolar(a["id"], "programado", destino)
        log.info("Toca el anuncio «%s» (%s)", a["nombre"], clave)


def resumen():
    """Lo que necesita la página: anuncios con su próximo turno, el siguiente, la cola y la bitácora."""
    ahora = _ahora()
    out = []
    eventos = _eventos_resumen()
    nombres = {e["id"]: e["nombre"] for e in eventos or []}
    for a in lista():
        p, red = proximo_turno(a, ahora)
        a["proximo"] = _fmt(p) if p else ""
        a["proximo_red"] = bool(red)
        if a["modo"] == "evento":
            a["evento_nombre"] = nombres.get(a["evento_id"], "")
        out.append(a)
    sig = min((a for a in out if a["proximo"]), key=lambda a: a["proximo"], default=None)
    cfg = settings.load()
    eng = cfg.get("tts_engine") or "azure"
    return {"anuncios": out, "siguiente": {"id": sig["id"], "nombre": sig["nombre"], "cuando": sig["proximo"], "red": sig["proximo_red"]} if sig else None,
            "eventos": eventos,
            "emisor": emisor.estado(), "bitacora": bitacora(30), "max_seg": max_seg(cfg), "max_chars": max_chars(cfg),
            "max_seg_rango": MAX_SEG_RANGO, "max_chars_rango": MAX_CHARS_RANGO, "tot_s": tot_nodo(cfg),
            "espera_min": ESPERA_MAX // 60,
            "voz": {"motor": eng, "nombre": tts.NOMBRES.get(eng, eng), "lista": tts.configurado(eng, cfg),
                    "ajustes": {k: cfg.get(k) for k in VOZ_KEYS},
                    "variables": [v for v in tts.VARIABLES if v[0] in VARS]},
            "pronuncia": cfg.get("pron_dict") or [],
            "asl": True, "ahora": _fmt(ahora)}


def rehacer_voces(terminos, cfg=None):
    """El diccionario cambió: vuelve a generar la voz guardada de los anuncios que usan esos términos."""
    from . import pronuncia
    cfg = cfg or settings.load()
    n = 0
    for a in lista():
        if a["tipo"] != "tts" or not pronuncia.toca(a["texto"], terminos):
            continue
        try:
            nombre, dur = _voz(a["texto"], cfg, a.get("voz"))
        except Exception as e:
            log.warning("No pude rehacer la voz del anuncio «%s»: %s", a["nombre"], e)
            continue
        db.execute("UPDATE anuncios SET archivo=?, duracion=? WHERE id=?", (nombre, dur, a["id"]))
        if a["archivo"]:
            paths.rm(carpeta() / a["archivo"])
        n += 1
    return n


def usan(terminos):
    from . import pronuncia
    return [a["nombre"] for a in lista() if a["tipo"] == "tts" and pronuncia.toca(a["texto"], terminos)]
