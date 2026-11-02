"""
HAMNA Web — API HTTP y página. Funciona con Python 3.5 a 3.13 sin paquetes extra.
"""
import binascii
import datetime as dt
import logging
import os
import re
import shutil
import time
import uuid
from pathlib import Path

from . import VERSION, audio, backends, cron, db, links, paths, settings, tts
from .engine import engine
from .web import App, HTTPError, check_password, hash_password, jsonr, send_file

log = logging.getLogger("hamna.web")

STATIC = Path(__file__).parent / "static"
app = App(STATIC)


def init_app():
    db.init_db()
    cfg = settings.load()
    if not cfg.get("secret_key"):
        cfg = settings.save({"secret_key": binascii.hexlify(os.urandom(32)).decode()})
    app.secret = cfg["secret_key"]


# ── Utilidades ────────────────────────────────────────────────────────────────
def ok(**kw):
    d = {"ok": True}
    d.update(kw)
    return jsonr(d)


def safe_name(name):
    stem = re.sub(r"[^A-Za-z0-9_-]+", "_", Path(name).stem).strip("_")[:50]
    return stem or "audio"


def save_upload(up, dest_dir, prefix):
    ext = Path(up.filename or "").suffix.lower()
    allowed = audio.formats()
    if ext not in allowed:
        raise ValueError("Formato {} no soportado en este nodo. Usa: {}".format(
            ext or "sin extensión", ", ".join(e[1:].upper() for e in allowed)))
    dest = Path(dest_dir) / "{}_{}{}".format(prefix, safe_name(up.filename), ext)
    shutil.move(up.path, str(dest))
    up.path = None
    if audio.duration(dest) <= 0:
        paths.rm(dest)
        raise ValueError("No pude leer el audio; ¿está dañado el archivo?")
    return dest


def truthy(v):
    return str(v).lower() in ("1", "true", "on", "yes", "si", "sí")


def parse_date(s):
    try:
        return dt.datetime.strptime(s, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        raise ValueError("Fecha inválida (AAAA-MM-DD)")


# ── Página y sesión ──────────────────────────────────────────────────────────
@app.route("/", auth=False)
def index(req):
    return send_file(STATIC / "index.html", "text/html; charset=utf-8")


@app.route("/api/login", ("POST",), auth=False)
def login(req):
    pw = req.json().get("password") or ""
    h = settings.get("password_hash")
    if not h:
        raise HTTPError(403, "Aún no hay contraseña. En el nodo ejecuta: hamna-web-passwd")
    if not check_password(h, pw):
        time.sleep(1.5)
        raise HTTPError(401, "Contraseña incorrecta")
    req.login()
    return ok()


@app.route("/api/logout", ("POST",), auth=False)
def logout(req):
    req.logout()
    return ok()


@app.route("/api/me", auth=False)
def me(req):
    return jsonr({"auth": req.authed, "version": VERSION,
                  "station": settings.get("station_name") or ""})


# ── Estado e información ─────────────────────────────────────────────────────
@app.route("/api/status")
def status(req):
    s = engine.status()
    s["now"] = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    s["utc"] = dt.datetime.utcnow().strftime("%H:%M")
    return jsonr(s)


def _timezone():
    try:
        tz = Path("/etc/timezone").read_text().strip()
        if tz:
            return tz
    except Exception:
        pass
    real = os.path.realpath("/etc/localtime")
    return real.split("zoneinfo/")[-1] if "zoneinfo/" in real else time.strftime("%Z")


@app.route("/api/info")
def info(req):
    cfg = settings.load()
    be = backends.make(cfg)
    du = shutil.disk_usage(str(paths.data_dir()))
    return jsonr({
        "version": VERSION, "backend": be.info(), "detectado": backends.detect(),
        "sabor": backends.detect_flavor(), "nodo_detectado": backends.detect_asl_node(),
        "zona_horaria": _timezone(), "disco_libre_mb": du.free // 2**20,
        "herramientas": audio.tools(), "formatos": audio.formats(),
        "sistemas": links.detect_systems(), "cron": cron.available(),
        "motores_tts": tts.engines(), "variables": tts.VARIABLES,
        "historial": db.get_historial(15),
    })


# ── Secciones ────────────────────────────────────────────────────────────────
def _sec_out(s):
    s = dict(s)
    s["tiene_audio"] = bool(s.get("ruta_archivo")) and (paths.audios_dir() / s["ruta_archivo"]).is_file()
    return s


@app.route("/api/secciones")
def secciones(req):
    return jsonr([_sec_out(s) for s in db.get_secciones()])


def _air_target(cfg):
    return float(cfg.get("normalize_target", -18)) if cfg.get("section_normalize") else None


def _compact_section(sid, cfg=None):
    """Si no se guardan los originales, deja solo la versión para el aire.
    Devuelve los bytes liberados."""
    cfg = cfg or settings.load()
    s = db.get_seccion(sid)
    if not s or not s.get("ruta_archivo"):
        return 0
    src = paths.audios_dir() / s["ruta_archivo"]
    if not src.is_file() or audio.is_aire(src):
        return 0
    dest, freed = audio.compact(src, _air_target(cfg))
    db.update_seccion(sid, ruta_archivo=dest.name, duracion=audio.duration(dest))
    return freed


def _generate_tts(sid):
    s = db.get_seccion(sid)
    if not s or not (s.get("texto_tts") or "").strip():
        return
    cfg = settings.load()
    ctx = {"titulo": s.get("titulo") or s["nombre"], "descripcion": s.get("descripcion") or ""}
    src = tts.synthesize(s["texto_tts"], cfg, paths.tmp_dir() / ("tts_" + uuid.uuid4().hex[:8]), ctx)
    dest = paths.audios_dir() / "{}_{}{}".format(sid, safe_name(s["nombre"]), src.suffix)
    shutil.move(str(src), str(dest))
    if s.get("ruta_archivo") and s["ruta_archivo"] != dest.name:
        paths.rm(paths.audios_dir() / s["ruta_archivo"])
    db.update_seccion(sid, ruta_archivo=dest.name, duracion=audio.duration(dest))
    if not settings.load().get("keep_originals", True):
        _compact_section(sid)


def _apply_section(req, sid, tipo, is_new):
    form = req.form
    fields = {}
    for k in ("nombre", "titulo", "descripcion", "texto_tts"):
        if k in form:
            fields[k] = form[k].strip()
    if "regenerar_antes" in form:
        fields["regenerar_antes"] = truthy(form["regenerar_antes"])
    if "nombre" in fields and not fields["nombre"]:
        raise ValueError("La sección necesita un nombre")
    up = req.files.get("archivo")
    old = db.get_seccion(sid)
    if up:
        dest = save_upload(up, paths.audios_dir(), str(sid))
        fields["ruta_archivo"] = dest.name
        fields["duracion"] = audio.duration(dest)
        if old and old.get("ruta_archivo") and old["ruta_archivo"] != dest.name:
            paths.rm(paths.audios_dir() / old["ruta_archivo"])
    db.update_seccion(sid, **fields)
    if up and not settings.load().get("keep_originals", True):
        _compact_section(sid)
    if tipo == "TTS" and (is_new or truthy(form.get("generar", "0"))):
        _generate_tts(sid)


@app.route("/api/secciones", ("POST",))
def seccion_new(req):
    f = req.form
    tipo = f.get("tipo", "Audio")
    if tipo not in ("TTS", "Audio", "Sonido"):
        raise ValueError("Tipo inválido")
    nombre = (f.get("nombre") or "").strip()
    if not nombre:
        raise ValueError("La sección necesita un nombre")
    if tipo != "TTS" and "archivo" not in req.files:
        raise ValueError("Sube un archivo de audio")
    if tipo == "TTS" and not (f.get("texto_tts") or "").strip():
        raise ValueError("Escribe el texto a sintetizar")
    sid = db.insert_seccion(nombre, tipo)
    try:
        _apply_section(req, sid, tipo, True)
    except Exception:
        db.delete_seccion(sid)
        raise
    return ok(seccion=_sec_out(db.get_seccion(sid)))


@app.route("/api/secciones/<int:sid>", ("POST",))
def seccion_edit(req, sid):
    s = db.get_seccion(sid)
    if not s:
        raise HTTPError(404)
    _apply_section(req, sid, s["tipo"], False)
    return ok(seccion=_sec_out(db.get_seccion(sid)))


@app.route("/api/secciones/<int:sid>", ("DELETE",))
def seccion_del(req, sid):
    s = db.get_seccion(sid)
    if s:
        if s.get("ruta_archivo"):
            paths.rm(paths.audios_dir() / s["ruta_archivo"])
        db.delete_seccion(sid)
    return ok()


def _browser_file(p):
    """Archivo que el navegador pueda reproducir (convierte si hace falta)."""
    p = Path(p)
    if audio.can_play_in_browser(p):
        return send_file(p)
    return send_file(audio.prepare(p, None), "audio/wav")


@app.route("/api/secciones/<int:sid>/audio")
def seccion_audio(req, sid):
    s = db.get_seccion(sid)
    if not s or not s.get("ruta_archivo"):
        raise HTTPError(404)
    return _browser_file(paths.audios_dir() / s["ruta_archivo"])


@app.route("/api/secciones/<int:sid>/aire", ("POST",))
def seccion_aire(req, sid):
    s = db.get_seccion(sid)
    if not s or not s.get("ruta_archivo"):
        raise ValueError("La sección no tiene audio")
    engine.play_single(paths.audios_dir() / s["ruta_archivo"], s["nombre"])
    return ok()


@app.route("/api/secciones/compactar", ("POST",))
def secciones_compactar(req):
    """Convierte todas las secciones al formato del aire y borra los originales."""
    if engine.status().get("on_air"):
        raise ValueError("Espera a que termine la transmisión")
    cfg = settings.load()
    n, freed, errores = 0, 0, []
    for s in db.get_secciones():
        try:
            b = _compact_section(s["id"], cfg)
        except Exception as e:
            log.warning("No pude convertir %s: %s", s["nombre"], e)
            errores.append(s["nombre"])
            continue
        if b:
            n += 1
            freed += b
    return ok(convertidas=n, liberado_mb=round(freed / 2.0**20, 1), errores=errores)


@app.route("/api/tts/preview", ("POST",))
def tts_preview(req):
    b = req.json()
    text = (b.get("texto") or "").strip()
    if not text:
        raise ValueError("Escribe algún texto")
    cfg = settings.load()
    ctx = {"titulo": b.get("titulo") or "", "descripcion": b.get("descripcion") or "",
           "evento": "Evento de prueba", "numero": "1"}
    src = tts.synthesize(text, cfg, paths.tmp_dir() / ("preview_" + uuid.uuid4().hex[:8]), ctx)
    if not audio.can_play_in_browser(src):
        src = audio.prepare(src, None)
    return ok(url="/api/archivo/" + src.parent.name + "/" + src.name,
              texto=tts.resolve_variables(text, cfg, ctx))


@app.route("/api/archivo/<carpeta>/<name>")
def tmp_file(req, carpeta, name):
    if carpeta not in ("tmp", "cache") or not re.match(r"^[A-Za-z0-9_.-]+$", name):
        raise HTTPError(404)
    base = paths.tmp_dir() if carpeta == "tmp" else paths.cache_dir()
    return send_file(base / name)


# ── Eventos ──────────────────────────────────────────────────────────────────
@app.route("/api/eventos")
def eventos(req):
    return jsonr({"eventos": db.get_eventos(), "tipos": db.get_eventos_types()})


@app.route("/api/eventos/<int:eid>")
def evento(req, eid):
    ev = db.get_evento(eid)
    if not ev:
        raise HTTPError(404)
    ev["secciones"] = [_sec_out(s) for s in db.get_secciones_by_evento(eid)]
    ev["conexiones"] = db.get_conexiones(eid)
    return jsonr(ev)


@app.route("/api/eventos/<int:eid>/conexiones", ("PUT",))
def evento_conexiones(req, eid):
    if not db.get_evento(eid):
        raise HTTPError(404)
    items = req.json().get("items") or []
    if len(items) > 20:
        raise ValueError("Máximo 20 acciones por evento")
    clean = []
    for i, a in enumerate(items, 1):
        try:
            clean.append(links.validate(a))
        except ValueError as e:
            raise ValueError("Acción {}: {}".format(i, e))
    db.set_conexiones(eid, clean)
    return ok(conexiones=db.get_conexiones(eid))


@app.route("/api/conexiones/probar", ("POST",))
def conexion_probar(req):
    a = links.validate(req.json())
    cmd = links.run(a, settings.load())
    return ok(comando=cmd, texto=links.describe(a))


def _ev_fields(b):
    nombre = (b.get("nombre") or "").strip()
    if not nombre:
        raise ValueError("El evento necesita un nombre")
    tipo = b.get("tipo_evento_id") or None
    numero = str(b.get("numero") or "").strip()
    return nombre, (int(tipo) if tipo else None), (int(numero) if numero.isdigit() else None)


@app.route("/api/eventos", ("POST",))
def evento_new(req):
    return ok(id=db.insert_evento(*_ev_fields(req.json())))


@app.route("/api/eventos/<int:eid>", ("PUT",))
def evento_edit(req, eid):
    db.update_evento(eid, *_ev_fields(req.json()))
    return ok()


@app.route("/api/eventos/<int:eid>", ("DELETE",))
def evento_del(req, eid):
    if engine.busy() and engine.st.get("evento_id") == eid:
        raise ValueError("No se puede borrar un evento que está al aire")
    db.delete_evento(eid)
    return ok()


@app.route("/api/eventos/<int:eid>/secciones", ("POST",))
def evento_add_sec(req, eid):
    for sid in req.json().get("ids", []):
        db.add_seccion_to_evento(eid, int(sid))
    return ok()


@app.route("/api/eventos/<int:eid>/secciones/<int:sid>", ("DELETE",))
def evento_rm_sec(req, eid, sid):
    db.remove_seccion_from_evento(eid, sid)
    return ok()


@app.route("/api/eventos/<int:eid>/orden", ("PUT",))
def evento_orden(req, eid):
    db.set_orden_evento(eid, [int(x) for x in req.json().get("ids", [])])
    return ok()


@app.route("/api/eventos/<int:eid>/secciones/<int:sid>/contabilizable", ("PUT",))
def evento_cont(req, eid, sid):
    db.set_contabilizable(eid, sid, bool(req.json().get("value")))
    return ok()


# ── Cron ─────────────────────────────────────────────────────────────────────
@app.route("/api/cron")
def cron_list(req):
    if not cron.available():
        return jsonr({"disponible": False, "tablas": []})
    return jsonr({"disponible": True, "tablas": cron.list_tables()})


@app.route("/api/cron", ("PUT",))
def cron_save(req):
    b = req.json()
    tid, h, text = b.get("id") or "", b.get("hash") or "", b.get("texto")
    if not isinstance(text, str) or not re.match(r"^(irlp|user:[a-z_][a-z0-9_-]{0,31})$", tid)             or not re.match(r"^[0-9a-f]{40}$", h):
        raise ValueError("Datos inválidos")
    try:
        r = cron.save_table(tid, h, text)
    except RuntimeError as e:
        if getattr(e, "conflicto", False):
            raise HTTPError(409, str(e))
        raise
    log.info("Cron %s guardado (respaldo %s)", tid, r.get("respaldo"))
    return ok(respaldo=r.get("respaldo"))


# ── Programación ─────────────────────────────────────────────────────────────
@app.route("/api/programacion")
def programacion(req):
    out = []
    now = dt.datetime.now()
    for r in db.get_programacion():
        nxt = engine.next_run(r, now) if r["activo"] else None
        r["proxima"] = nxt.strftime("%Y-%m-%d %H:%M") if nxt else None
        r["faltan_s"] = int((nxt - now).total_seconds()) if nxt else None
        out.append(r)
    out.sort(key=lambda r: (r["faltan_s"] is None, r["faltan_s"] or 0))
    return jsonr(out)


def _prog_fields(b):
    eid = int(b.get("evento_id") or 0)
    if not db.get_evento(eid):
        raise ValueError("Elige un evento")
    fecha = (b.get("fecha") or "").strip()
    hora = (b.get("hora") or "").strip()[:5]
    rec = b.get("recurrencia") or "ninguna"
    parse_date(fecha)
    if not re.match(r"^([01]\d|2[0-3]):[0-5]\d$", hora):
        raise ValueError("Hora inválida (HH:MM)")
    if rec not in ("ninguna", "diaria", "semanal", "lun-vie"):
        raise ValueError("Recurrencia inválida")
    return eid, fecha, hora, rec, b.get("activo", True) not in (False, 0, "0", "false")


@app.route("/api/programacion", ("POST",))
def prog_new(req):
    return ok(id=db.insert_programacion(*_prog_fields(req.json())))


@app.route("/api/programacion/<int:pid>", ("PUT",))
def prog_edit(req, pid):
    db.update_programacion(pid, *_prog_fields(req.json()))
    return ok()


@app.route("/api/programacion/<int:pid>", ("DELETE",))
def prog_del(req, pid):
    db.delete_programacion(pid)
    return ok()


# ── Control de transmisión ───────────────────────────────────────────────────
@app.route("/api/tx/start", ("POST",))
def tx_start(req):
    engine.start_event(int(req.json().get("evento_id") or 0), origen="manual")
    return ok()


@app.route("/api/tx/<cmd>", ("POST",))
def tx_cmd(req, cmd):
    if cmd == "stop":
        engine.stop()
    else:
        engine.command(cmd)
    return ok()


# ── Ajustes ──────────────────────────────────────────────────────────────────
NUM_KEYS = {"azure_rate": int, "azure_pitch": int, "espeak_speed": int, "espeak_pitch": int,
            "pause_tx_time": float, "pause_duration": float, "pause_alert_before": float,
            "ptt_on_delay": float, "retroceso_secs": float, "section_gap": float,
            "normalize_target": float, "pause_volume": int}
BOOL_KEYS = {"pause_enabled", "retroceso_enabled", "section_normalize", "keep_originals"}
STR_KEYS = {"backend", "node", "asl_mode", "asl_flush_cmd", "irlp_env", "irlp_key_cmd",
            "irlp_unkey_cmd", "irlp_player", "station_name", "tts_engine", "azure_region",
            "azure_voice", "azure_style", "espeak_voice"}


@app.route("/api/ajustes")
def ajustes(req):
    return jsonr(settings.public())


@app.route("/api/ajustes", ("PUT",))
def ajustes_save(req):
    upd = {}
    for k, v in req.json().items():
        if k in NUM_KEYS:
            try:
                upd[k] = NUM_KEYS[k](float(v))
            except (TypeError, ValueError):
                raise ValueError("Valor inválido en " + k)
        elif k in BOOL_KEYS:
            upd[k] = v if isinstance(v, bool) else truthy(v)
        elif k in STR_KEYS:
            upd[k] = str(v).strip()
        elif k == "azure_key" and str(v).strip():
            upd[k] = str(v).strip()
    if upd.get("node") and not re.match(r"^[A-Za-z0-9]{1,10}$", upd["node"]):
        raise ValueError("Número de nodo inválido")
    if upd.get("backend") not in (None, "auto", "asl", "irlp", "simulado"):
        raise ValueError("Tipo de nodo inválido")
    settings.save(upd)
    return ok(ajustes=settings.public())


PAUSE_KINDS = {"alerta": "pause_alert_file", "pausa": "pause_announcement_file",
               "continuamos": "pause_resume_file"}


@app.route("/api/ajustes/sonido/<kind>", ("GET", "POST", "DELETE"))
def ajustes_sonido(req, kind):
    key = PAUSE_KINDS.get(kind)
    if not key:
        raise HTTPError(404)
    cur = settings.get(key) or ""
    if req.method == "GET":
        if not cur:
            raise HTTPError(404)
        return _browser_file(paths.sonidos_dir() / cur)
    if req.method == "POST":
        up = req.files.get("archivo")
        if not up:
            raise ValueError("Elige un archivo")
        dest = save_upload(up, paths.sonidos_dir(), kind + "_" + uuid.uuid4().hex[:4])
    else:
        dest = None
    if cur and (dest is None or cur != dest.name):
        paths.rm(paths.sonidos_dir() / cur)
    settings.save({key: dest.name if dest else ""})
    return ok(nombre=dest.name if dest else "")


@app.route("/api/ajustes/password", ("POST",))
def ajustes_password(req):
    b = req.json()
    if not check_password(settings.get("password_hash"), b.get("actual") or ""):
        raise ValueError("La contraseña actual no coincide")
    nueva = b.get("nueva") or ""
    if len(nueva) < 6:
        raise ValueError("La contraseña nueva debe tener al menos 6 caracteres")
    settings.save({"password_hash": hash_password(nueva)})
    return ok()


@app.route("/api/azure/voces", ("POST",))
def azure_voces(req):
    cfg = settings.load()
    b = req.json()
    key = (b.get("azure_key") or cfg.get("azure_key") or "").strip()
    region = (b.get("azure_region") or cfg.get("azure_region") or "").strip()
    if not key or not region:
        raise ValueError("Escribe la clave y la región de Azure")
    try:
        return ok(voces=tts.azure_voices(key, region))
    except Exception as e:
        raise RuntimeError("Azure no respondió: {}".format(e))


@app.route("/api/prueba/nodo", ("POST",))
def prueba_nodo(req):
    good, msg = backends.make(settings.load()).test()
    return jsonr({"ok": good, "mensaje": msg})


@app.route("/api/prueba/aire", ("POST",))
def prueba_aire(req):
    cfg = settings.load()
    text = (req.json().get("texto") or "").strip() or \
        "Prueba de HAMNA Web. Son las {hora} del {dia} {fecha_larga}."
    src = tts.synthesize(text, cfg, paths.tmp_dir() / ("prueba_" + uuid.uuid4().hex[:8]))
    engine.play_single(src, "Prueba de transmisión")
    return ok()
