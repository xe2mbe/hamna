"""
HAMNA Web — API HTTP y página. Funciona con Python 3.5 a 3.13 sin paquetes extra.
"""
import binascii
import datetime as dt
import logging
import os
import re
import shutil
import threading
import time
import urllib.parse
import uuid
from pathlib import Path

from . import VERSION, audio, auth, autobackup, backends, backup, cron, db, export, links, notify, paths, sessions, settings, share, sync, sysmon, tts, tz, updates
from .engine import engine
from .live import live
from .web import App, HTTPError, Response, jsonr, send_file

log = logging.getLogger("hamna.web")

STATIC = Path(__file__).parent / "static"
app = App(STATIC)


def init_app():
    db.init_db()
    cfg = settings.load()
    if not cfg.get("secret_key"):
        cfg = settings.save({"secret_key": binascii.hexlify(os.urandom(32)).decode()})
    app.secret = cfg["secret_key"]
    auth.init()
    share.init()
    sync.init()
    autobackup.init()
    app.roles = auth.ROLES
    app.user_loader = lambda req: auth.user_for(req.token, req.ip)
    app.upload_limits["/api/respaldo/restaurar"] = 4 * 2**30
    app.raw_uploads["/api/remoto/respaldo"] = (
        4 * 2**30, lambda req: autobackup.code_check(req.headers.get("X-HAMNA-Backup", "")) is not None)


def require(req, rol):
    if auth.ROLES.get((req.user or {}).get("rol"), 0) < auth.ROLES[rol]:
        raise HTTPError(403, "Tu usuario no tiene permiso para esto")


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
    b = req.json()
    if not auth.has_admin():
        raise HTTPError(403, "Aún no hay usuarios. En el nodo ejecuta: hamna-web-passwd")
    try:
        token, user = auth.login(b.get("usuario") or "admin", b.get("password") or "",
                                 req.ip, req.headers.get("User-Agent", ""))
    except auth.AuthError as e:
        log.warning("Entrada fallida de «%s» desde %s: %s", (b.get("usuario") or "")[:32], req.ip, e)
        raise HTTPError(401, str(e))
    log.info("Entró %s (%s) desde %s", user["usuario"], user["rol"], req.ip)
    req.login(token)
    return ok(usuario=user)


@app.route("/api/logout", ("POST",), auth=False)
def logout(req):
    auth.logout(req.token)
    req.logout()
    return ok()


@app.route("/api/me", auth=False)
def me(req):
    u = req.user
    return jsonr({"auth": req.authed, "version": VERSION,
                  "station": settings.get("station_name") or "",
                  "logo": _logo_url(),
                  "usuario": {k: u.get(k) for k in ("id", "usuario", "nombre", "rol", "rol_nombre", "idioma")} if u else None})


@app.route("/api/mi-idioma", ("PUT",), rol="lectura")
def mi_idioma(req):
    auth.set_language(req.user["id"], (req.json().get("idioma") or "").lower())
    return ok()


# ── Usuarios y sesiones abiertas ─────────────────────────────────────────────
@app.route("/api/usuarios", rol="admin")
def usuarios(req):
    return jsonr({"usuarios": auth.users(), "sesiones": auth.sessions(),
                  "bloqueos": auth.locked_list(), "roles": auth.ROL_NOMBRE, "yo": req.user["id"],
                  "mi_sesion": req.user["sid"]})


@app.route("/api/usuarios", ("POST",), rol="admin")
def usuarios_crear(req):
    b = req.json()
    uid = auth.create_user(b.get("usuario"), b.get("nombre"), b.get("rol") or "operador", b.get("password"))
    log.info("%s creó el usuario %s (%s)", req.user["usuario"], b.get("usuario"), b.get("rol"))
    return ok(id=uid)


@app.route("/api/usuarios/<int:uid>", ("PUT",), rol="admin")
def usuarios_editar(req, uid):
    b = req.json()
    f = {k: b[k] for k in ("nombre", "rol", "activo", "password") if k in b}
    if uid == req.user["id"] and (f.get("rol", "admin") != "admin" or f.get("activo") is False):
        raise ValueError("No puedes quitarte el rol de administrador ni desactivarte a ti mismo")
    auth.update_user(uid, cur_sid=req.user["sid"], **f)
    log.info("%s modificó el usuario #%s (%s)", req.user["usuario"], uid, ", ".join(sorted(f)))
    return ok()


@app.route("/api/usuarios/<int:uid>", ("DELETE",), rol="admin")
def usuarios_borrar(req, uid):
    auth.delete_user(uid, req.user["id"])
    log.info("%s borró el usuario #%s", req.user["usuario"], uid)
    return ok()


@app.route("/api/usuarios/desbloquear", ("POST",), rol="admin")
def usuarios_desbloquear(req):
    auth.unlock_all()
    return ok()


@app.route("/api/mis-sesiones", rol="lectura")
def mis_sesiones(req):
    return jsonr({"sesiones": auth.sessions(req.user["id"]), "mi_sesion": req.user["sid"]})


@app.route("/api/mis-sesiones/<int:sid>", ("DELETE",), rol="lectura")
def cerrar_sesion(req, sid):
    if req.user["rol"] == "admin":
        auth.revoke(sid)                   # el administrador puede cerrar cualquiera
    else:
        auth.revoke(sid, req.user["id"])
    return ok()


@app.route("/api/mis-sesiones/otras", ("POST",), rol="lectura")
def cerrar_otras(req):
    auth.revoke_user(req.user["id"], except_sid=req.user["sid"])
    return ok()


# ── Logo de la estación ──────────────────────────────────────────────────────
# El navegador lo reduce antes de subirlo; aquí solo se valida y se guarda,
# para no gastar CPU de la Raspberry procesando imágenes.
LOGO_MAX = 2 * 2**20
LOGO_TYPES = ((b"\x89PNG\r\n\x1a\n", "png"), (b"\xff\xd8\xff", "jpg"),
              (b"GIF87a", "gif"), (b"GIF89a", "gif"))


def _logo_ext(head):
    for magic, ext in LOGO_TYPES:
        if head.startswith(magic):
            return ext
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "webp"
    return None


def _logo_url():
    name = settings.get("logo_file") or ""
    return "api/logo?v=" + name if name and (paths.data_dir() / name).is_file() else ""


@app.route("/api/logo", auth=False)
def logo(req):
    name = settings.get("logo_file") or ""
    if not name:
        raise HTTPError(404)
    r = send_file(paths.data_dir() / name, cache=True)
    r.headers["X-Content-Type-Options"] = "nosniff"
    return r


@app.route("/api/ajustes/logo", ("POST", "DELETE"), rol="admin")
def ajustes_logo(req):
    cur = settings.get("logo_file") or ""
    dest = None
    if req.method == "POST":
        up = req.files.get("archivo")
        if not up:
            raise ValueError("Elige una imagen")
        if os.path.getsize(up.path) > LOGO_MAX:
            raise ValueError("La imagen pesa más de 2 MB")
        with open(up.path, "rb") as f:
            ext = _logo_ext(f.read(16))
        if not ext:
            raise ValueError("Formato no soportado. Usa PNG, JPG, WEBP o GIF")
        dest = paths.data_dir() / "logo_{}.{}".format(uuid.uuid4().hex[:6], ext)
        shutil.move(up.path, str(dest))
        up.path = None
    if cur and (dest is None or cur != dest.name):
        paths.rm(paths.data_dir() / cur)
    settings.save({"logo_file": dest.name if dest else ""})
    return ok(logo=_logo_url())


# ── Estado e información ─────────────────────────────────────────────────────
@app.route("/api/status")
def status(req):
    s = engine.status()
    s["now"] = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    s["utc"] = dt.datetime.utcnow().strftime("%H:%M")
    s["ts"] = round(time.time(), 1)
    s["sys"] = sysmon.snapshot()
    s["version"] = VERSION
    s["envivo"] = live.status()
    return jsonr(s)


# ── Escuchar en vivo ─────────────────────────────────────────────────────────
@app.route("/api/en-vivo")
def en_vivo(req):
    if not live.started:
        raise RuntimeError("El audio en vivo no está activo en este nodo")
    gen = live.stream(req.ip, req.user["usuario"] if req.user else "-")
    return Response(stream=gen, ctype="application/octet-stream",
                    headers={"X-Audio-Format": "mulaw;rate=8000"})


def _timezone():
    return tz.node_zone() or time.strftime("%Z")


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


@app.route("/api/secciones/compactar", ("POST",), rol="admin")
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
    return ok(url="api/archivo/" + src.parent.name + "/" + src.name,
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


# Preparar en segundo plano los audios de un evento en cuanto cambia (sección
# agregada, programación guardada), para no esperar a los 20 min antes.
_prep_busy = set()
_prep_lock = threading.Lock()


def _prep_bg(evento_id):
    with _prep_lock:
        if evento_id in _prep_busy:
            return
        _prep_busy.add(evento_id)

    def work():
        try:
            n = engine.prepare_event(evento_id)
            log.info("Audios del evento #%s listos (%s)", evento_id, n)
        except Exception as e:
            log.warning("No se pudieron preparar los audios del evento #%s: %s", evento_id, e)
        finally:
            with _prep_lock:
                _prep_busy.discard(evento_id)
    threading.Thread(target=work, daemon=True).start()


@app.route("/api/eventos/<int:eid>/secciones", ("POST",))
def evento_add_sec(req, eid):
    for sid in req.json().get("ids", []):
        db.add_seccion_to_evento(eid, int(sid))
    _prep_bg(eid)
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
@app.route("/api/cron", rol="operador")
def cron_list(req):
    if not cron.available():
        return jsonr({"disponible": False, "tablas": []})
    return jsonr({"disponible": True, "tablas": cron.list_tables()})


@app.route("/api/cron", ("PUT",), rol="admin")
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
    durs = {e["id"]: e["duracion_total"] for e in db.get_eventos()}
    nodo_zona = tz.node_zone()
    nodo_corta = tz.short(nodo_zona) or time.strftime("%Z")

    def _horario(zona, antes, despues):
        """'verano' o 'invierno' para la nueva hora: se mira la zona que
        cambia de horario (la del evento o, si esa no cambia, la del nodo)."""
        t0, t1 = time.mktime(antes.timetuple()), time.mktime(despues.timetuple())
        for z in (zona, ""):
            try:
                a, b = tz.is_dst(z, t0), tz.is_dst(z, t1)
            except Exception:
                continue
            if a != b:
                return "verano" if b else "invierno"
        return ""
    conex = {}
    for r in db.get_programacion():
        eid = r["evento_id"]
        if eid not in conex:
            conex[eid] = db.get_conexiones(eid)
        r["duracion"] = durs.get(eid) or 0
        r["conexiones"] = conex[eid]
        try:
            nxt = engine.next_run(r, now) if r["activo"] else None
        except Exception as e:
            log.warning("Programación #%s: %s", r["id"], e)
            nxt = None
        r["proxima"] = nxt.strftime("%Y-%m-%d %H:%M") if nxt else None
        r["faltan_s"] = int((nxt - now).total_seconds()) if nxt else None
        # Con zona propia: la hora en el nodo y si cambiará pronto (horario de verano)
        r["zona"] = r.get("zona") or ""
        r["hora_local"] = nxt.strftime("%H:%M") if nxt else r["hora"]
        if not nxt and r["zona"]:
            # Desactivada o sin fechas: convertir la hora como si fuera hoy
            try:
                h, m = map(int, r["hora"][:5].split(":"))
                r["hora_local"] = tz.to_node(dt.datetime.combine(now.date(), dt.time(h, m)), r["zona"]).strftime("%H:%M")
            except Exception:
                pass
        r["fecha_local"] = nxt.strftime("%Y-%m-%d") if nxt else r["fecha"]
        r["cambio"] = None
        r["zona_corta"] = tz.short(r["zona"])
        r["nodo_zona"] = nodo_zona
        r["nodo_zona_corta"] = nodo_corta
        if r["zona"] and nxt:
            r["zona_nombre"] = tz.label(r["zona"])
            for o in engine.occurrences(r, nxt, nxt + dt.timedelta(days=200)):
                if o.strftime("%H:%M") != r["hora_local"]:
                    r["cambio"] = {"fecha": o.strftime("%Y-%m-%d"), "hora_local": o.strftime("%H:%M"),
                                   "horario": _horario(r["zona"], nxt, o)}
                    break
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
    zona = (b.get("zona") or "").strip()
    if zona == tz.node_zone():
        zona = ""
    if not tz.valid(zona):
        raise ValueError("Zona horaria desconocida: " + zona)
    return eid, fecha, hora, rec, b.get("activo", True) not in (False, 0, "0", "false"), zona


@app.route("/api/actualizaciones", rol="admin")
def actualizaciones(req):
    d = updates.check(force=req.query.get("forzar") == "1")
    d["sabor"] = backends.detect_flavor()
    return jsonr(d)


# ── Compartir un evento con otros nodos (el que comparte) ────────────────────
@app.route("/api/eventos/<int:eid>/compartir", rol="admin")
def compartir_list(req, eid):
    return jsonr({"codigos": share.codes(eid)})


@app.route("/api/eventos/<int:eid>/compartir", ("POST",), rol="admin")
def compartir_new(req, eid):
    if not db.get_evento(eid):
        raise ValueError("El evento no existe")
    token = share.create(eid, req.json().get("etiqueta") or "")
    log.info("%s creó un código para compartir el evento #%s", req.user["usuario"], eid)
    return ok(codigo=token)


@app.route("/api/compartir/<int:cid>", ("DELETE",), rol="admin")
def compartir_del(req, cid):
    share.revoke(cid)
    return ok()


def _share_event(req):
    """Evento al que da acceso el código del encabezado X-HAMNA-Share."""
    if auth.locked_for("share", req.ip):
        raise HTTPError(429, "Demasiados intentos")
    eid = share.event_for(req.headers.get("X-HAMNA-Share", ""), req.ip)
    if not eid:
        auth._fail("share", req.ip)
        time.sleep(1)
        raise HTTPError(401, "Código de acceso inválido")
    return eid


@app.route("/api/remoto/evento", auth=False)
def remoto_evento(req):
    eid = _share_event(req)
    data = share.payload(eid)
    if not data:
        raise HTTPError(404, "El evento ya no existe")
    return jsonr(data)


@app.route("/api/remoto/audio/<int:sid>", auth=False)
def remoto_audio(req, sid):
    eid = _share_event(req)
    p = share.file_for(eid, sid)
    if not p:
        raise HTTPError(404, "Esa sección no tiene audio")
    return send_file(p, "application/octet-stream")


# ── Sincronizar un evento desde otro nodo (el que recibe) ────────────────────
def _sync_out(eid):
    c = sync.get_config(eid)
    out = {"config": None, "secciones": [], "ocupado": sync.busy(eid)}
    if c:
        c = dict(c)
        c["token_set"] = bool(c.pop("token", ""))
        out["config"] = c
        m = sync.mapping(eid)
        for s in db.get_secciones_by_evento(eid):
            r = m.get(s["id"])
            out["secciones"].append({"id": s["id"], "nombre": s["nombre"], "tipo": s.get("tipo"),
                                     "sincronizada": bool(r), "local": bool(r and r["local"])})
    return out


@app.route("/api/eventos/<int:eid>/sincronizacion")
def sync_get(req, eid):
    return jsonr(_sync_out(eid))


@app.route("/api/eventos/<int:eid>/sincronizacion", ("PUT",), rol="admin")
def sync_put(req, eid):
    b = req.json()
    sync.save_config(eid, b.get("url") or "", (b.get("codigo") or "").strip(), b.get("huella") or "",
                     b.get("remoto") or "", b.get("dias") or [], (b.get("hora") or "").strip(),
                     b.get("antes_horas") or 0, b.get("activo", True) not in (False, 0, "0"))
    log.info("%s configuró la sincronización del evento #%s desde %s", req.user["usuario"], eid, b.get("url"))
    return ok(**_sync_out(eid))


@app.route("/api/eventos/<int:eid>/sincronizacion", ("DELETE",), rol="admin")
def sync_del(req, eid):
    sync.delete_config(eid)
    return ok()


@app.route("/api/sincronizacion/probar", ("POST",), rol="admin")
def sync_probe(req):
    b = req.json()
    cfg = None
    codigo = (b.get("codigo") or "").strip()
    if not codigo and b.get("evento_id"):
        cfg = sync.get_config(int(b["evento_id"]))
        codigo = cfg["token"] if cfg else ""
    if not codigo:
        raise ValueError("Falta el código de acceso")
    return ok(**sync.probe(b.get("url") or "", codigo))


@app.route("/api/eventos/<int:eid>/sincronizar", ("POST",))
def sync_now(req, eid):
    if not sync.get_config(eid):
        raise ValueError("Este evento no tiene sincronización configurada")
    if sync.busy(eid):
        raise ValueError("Ya se está sincronizando")
    log.info("%s pidió sincronizar el evento #%s", req.user["usuario"], eid)
    sync.run_bg(eid, "manual · " + req.user["usuario"])
    return ok()


@app.route("/api/eventos/<int:eid>/sincronizacion/local", ("PUT",), rol="admin")
def sync_local(req, eid):
    b = req.json()
    sync.set_local(eid, int(b.get("seccion_id") or 0), bool(b.get("local")))
    return ok(**_sync_out(eid))


# ── Avisos por Telegram ──────────────────────────────────────────────────────
@app.route("/api/avisos/chats", ("POST",), rol="admin")
def avisos_chats(req):
    return ok(**notify.find_chats(req.json().get("token")))


@app.route("/api/avisos/probar", ("POST",), rol="admin")
def avisos_probar(req):
    """Envía un aviso de prueba. Con tipo y evento manda un ejemplo real de
    ese aviso armado con los datos del evento (sin transmitir nada)."""
    b = req.json()
    tipo = b.get("tipo") or "simple"
    quien = notify.esc(req.user["usuario"])
    if tipo == "simple":
        txt = "✅ Prueba de avisos de HAMNA Web (enviada por {}).".format(quien)
    else:
        ev = db.get_evento(int(b.get("evento_id") or 0))
        if not ev:
            raise ValueError("Elige un evento para el ejemplo")
        cfg = settings.load()
        secs = [dict(s) for s in db.get_secciones_by_evento(ev["id"])]
        if not secs:
            raise ValueError("Ese evento no tiene secciones")
        for s in secs:
            s["tiene_audio"] = bool(engine._file_of(s))
        gap = cfg.get("section_gap", 3)
        con = db.get_conexiones(ev["id"])
        now = dt.datetime.now()
        if tipo == "proximo":
            m = (notify.upcoming_minutes(cfg) or [15])[-1]
            txt = notify.msg_upcoming(ev, secs, now + dt.timedelta(minutes=m), m, con, gap)
        elif tipo == "inicio":
            nodo = "nodo {}".format(cfg.get("node")) if cfg.get("node") else ""
            txt = notify.msg_start(ev, secs, "prueba · " + req.user["usuario"], now, gap, nodo, con)
        elif tipo == "seccion":
            i = next((j for j, s in enumerate(secs) if s["tiene_audio"]), 0)
            txt = notify.msg_section(ev, secs, i, now)
        elif tipo == "fin":
            est = ["ok" if s["tiene_audio"] else "sin_audio" for s in secs]
            total = sum(float(s.get("duracion") or 0) for s in secs if s["tiene_audio"])
            txt = notify.msg_end(ev, secs, est, now - dt.timedelta(seconds=total), now, "completo")
        else:
            raise ValueError("Tipo de aviso desconocido")
        txt = "🧪 <i>Ejemplo (prueba de {}; no se transmitió nada)</i>\n".format(quien) + txt
    notify.send_now(notify.header() + "\n" + txt, b.get("token"), b.get("chat"))
    return ok()


# ── Exportar secciones a un archivo ──────────────────────────────────────────
@app.route("/api/exportar/formatos", rol="lectura")
def exportar_formatos(req):
    cfg = settings.load()
    return jsonr({"formatos": export.formats(), "objetivo": float(cfg.get("normalize_target", -18))})


@app.route("/api/eventos/<int:eid>/exportar", ("POST",), rol="lectura")
def exportar_start(req, eid):
    b = req.json()
    try:
        silencio = float(b.get("silencio", 5))
        objetivo = float(b.get("objetivo", -18))
        ids = [int(x) for x in (b.get("secciones") or [])]
    except (TypeError, ValueError):
        raise ValueError("Valor inválido")
    jid = export.start(eid, ids, silencio, str(b.get("formato") or "mp3").lower(),
                       bool(b.get("normalizar")), objetivo, req.user["usuario"])
    return ok(id=jid)


@app.route("/api/exportar/<jid>", rol="lectura")
def exportar_status(req, jid):
    j = export.get(str(jid))
    if not j:
        raise HTTPError(404, "La exportación ya no existe")
    return jsonr(j)


@app.route("/api/exportar/<jid>/archivo", rol="lectura")
def exportar_archivo(req, jid):
    path, nombre = export.file_of(str(jid))
    if not path:
        raise HTTPError(404, "El archivo ya no existe; vuelve a exportar")
    ascii_name = re.sub(r"[^A-Za-z0-9._ -]", "_", nombre)
    r = send_file(path, "audio/mpeg" if nombre.endswith(".mp3") else "audio/wav")
    r.headers["Content-Disposition"] = "attachment; filename=\"{}\"; filename*=UTF-8''{}".format(
        ascii_name, urllib.parse.quote(nombre))
    return r


@app.route("/api/zonas")
def zonas(req):
    return jsonr({"nodo": tz.node_zone(),
                  "zonas": [{"id": z, "nombre": n} for z, n in tz.ZONAS if tz.valid(z)]})


@app.route("/api/programacion", ("POST",))
def prog_new(req):
    f = _prog_fields(req.json())
    pid = db.insert_programacion(*f)
    if f[4]:
        _prep_bg(f[0])
    return ok(id=pid)


@app.route("/api/programacion/<int:pid>", ("PUT",))
def prog_edit(req, pid):
    f = _prog_fields(req.json())
    db.update_programacion(pid, *f)
    if f[4]:
        _prep_bg(f[0])
    return ok()


@app.route("/api/programacion/<int:pid>", ("DELETE",))
def prog_del(req, pid):
    db.delete_programacion(pid)
    return ok()


# ── Control de transmisión ───────────────────────────────────────────────────
@app.route("/api/tx/start", ("POST",))
def tx_start(req):
    engine.start_event(int(req.json().get("evento_id") or 0), origen="manual · " + req.user["usuario"])
    return ok()


@app.route("/api/tx/<cmd>", ("POST",))
def tx_cmd(req, cmd):
    if cmd == "stop":
        engine.stop()
    else:
        engine.command(cmd)
    return ok()


# ── Sesiones (nodos conectados) ──────────────────────────────────────────────
@app.route("/api/sesiones")
def sesiones_get(req):
    s = sessions.status(settings.load(), req.query.get("nodo"))
    e = engine.status()
    s["hamna"] = {"on_air": bool(e.get("on_air")), "state": e.get("state"), "evento": e.get("evento") or ""}
    return jsonr(s)


@app.route("/api/sesiones/<accion>", ("POST",))
def sesiones_accion(req, accion):
    b = req.json()
    destino = str(b.get("destino") or "").strip()
    if accion == "conectar":
        acc = "conectar"
    elif accion == "desconectar":
        acc = "desconectar" if destino else "desconectar_todo"
    else:
        raise HTTPError(404)
    cmd = sessions.action(settings.load(), acc, destino, b.get("modo") or "transceptor", b.get("nodo"))
    log.info("Sesiones: %s", cmd)
    return ok(comando=cmd)


# ── Ajustes ──────────────────────────────────────────────────────────────────
NUM_KEYS = {"azure_rate": int, "azure_pitch": int, "espeak_speed": int, "espeak_pitch": int,
            "pause_tx_time": float, "pause_duration": float, "pause_alert_before": float,
            "ptt_on_delay": float, "retroceso_secs": float, "section_gap": float,
            "normalize_target": float, "pause_volume": int, "ab_keep": int, "ab_recv_keep": int}
BOOL_KEYS = {"pause_enabled", "retroceso_enabled", "section_normalize", "keep_originals",
             "tg_enabled", "tg_on_error", "tg_on_preflight", "tg_on_sync", "tg_on_start", "tg_on_end",
             "tg_on_upcoming", "tg_on_section", "tg_on_backup", "ab_enabled", "ab_node_on", "ab_cloud_on"}
STR_KEYS = {"backend", "node", "asl_mode", "asl_flush_cmd", "irlp_env", "irlp_key_cmd",
            "irlp_unkey_cmd", "irlp_player", "irlp_mode", "station_name", "tts_engine", "azure_region",
            "azure_voice", "azure_style", "espeak_voice", "tg_chat", "tg_upcoming_mins",
            "ab_hora", "ab_node_url", "ab_node_pin", "ab_cloud_folder"}


@app.route("/api/ajustes")
def ajustes(req):
    return jsonr(settings.public())


@app.route("/api/ajustes", ("PUT",), rol="admin")
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
        elif k in ("azure_key", "tg_token", "ab_node_token") and str(v).strip():
            upd[k] = str(v).strip()
    if "tg_upcoming_mins" in upd:
        bad = [x for x in re.split(r"[,;\s]+", upd["tg_upcoming_mins"])
               if x and not (x.isdigit() and 1 <= int(x) <= 1440)]
        if bad:
            raise ValueError("Minutos de aviso inválidos: usa números de 1 a 1440 separados por coma")
        upd["tg_upcoming_mins"] = ", ".join(str(m) for m in notify.upcoming_minutes(upd))
    if "ab_hora" in upd and not re.match(r"^([01]\d|2[0-3]):[0-5]\d$", upd["ab_hora"]):
        raise ValueError("Hora del respaldo inválida (HH:MM)")
    for k in ("ab_keep", "ab_recv_keep"):
        if k in upd and not 1 <= upd[k] <= 60:
            raise ValueError("Copias a conservar: de 1 a 60")
    if upd.get("node") and not re.match(r"^[A-Za-z0-9]{1,10}$", upd["node"]):
        raise ValueError("Número de nodo inválido")
    if upd.get("irlp_mode") not in (None, "red", "local"):
        raise ValueError("Modo IRLP inválido")
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
    if req.method != "GET":
        require(req, "admin")
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


# ── Respaldo y restauración ──────────────────────────────────────────────────
@app.route("/api/respaldo", rol="admin")
def respaldo_info(req):
    e = backup.estimate()
    e["copias"] = [d.name for d in backup._old_copies()]
    e["libre"] = shutil.disk_usage(str(paths.data_dir())).free
    return jsonr(e)


@app.route("/api/respaldo/descargar", rol="admin")
def respaldo_descargar(req):
    con = truthy(req.query.get("audios", "0"))
    nombre = backup.filename(con)
    gen = backup.stream(con, req.user["usuario"])
    return Response(stream=gen, ctype="application/gzip",
                    headers={"Content-Disposition": 'attachment; filename="{}"'.format(nombre)})


@app.route("/api/respaldo/restaurar", ("POST",), rol="admin")
def respaldo_restaurar(req):
    up = req.files.get("archivo")
    if not up:
        raise ValueError("Elige el archivo de respaldo (.tar.gz)")
    if engine.busy():
        raise ValueError("Hay una transmisión en curso; detenla antes de restaurar")
    r = backup.restore(up.path, truthy(req.form.get("conservar_nodo", "1")), req.user["usuario"])
    backup.restart_soon()
    return ok(**r)


# ── Respaldo automático ──────────────────────────────────────────────────────
@app.route("/api/autorespaldo", rol="admin")
def autorespaldo_info(req):
    cfg = settings.load()
    st = autobackup.load_state()
    return jsonr({"estado": st, "corriendo": autobackup.running(),
                  "destinos": autobackup.destinations(cfg), "rclone": autobackup.rclone_version(),
                  "nube": autobackup.cloud_info(), "nube_carpeta": autobackup._cloud_dir(cfg).split(":", 1)[1],
                  "audios_cambiaron": autobackup.audios_changed(st)})


@app.route("/api/autorespaldo/ahora", ("POST",), rol="admin")
def autorespaldo_ahora(req):
    audios = str(req.json().get("audios") or "auto")
    if audios not in ("auto", "si", "no"):
        raise ValueError("Opción de audios inválida")
    if autobackup.running():
        raise ValueError("Ya se está haciendo un respaldo")
    if not autobackup.destinations(settings.load()):
        raise ValueError("Primero configura y guarda al menos un destino (otro nodo o nube)")
    autobackup.run_bg("manual · " + req.user["usuario"], audios)
    return ok()


@app.route("/api/autorespaldo/probar-nodo", ("POST",), rol="admin")
def autorespaldo_probar(req):
    b = req.json()
    codigo = (b.get("codigo") or "").strip() or settings.get("ab_node_token") or ""
    if not codigo:
        raise ValueError("Falta el código de acceso del nodo destino")
    return ok(**autobackup.probe_node(b.get("url") or "", codigo))


@app.route("/api/autorespaldo/nube", ("POST", "DELETE"), rol="admin")
def autorespaldo_nube(req):
    if req.method == "DELETE":
        autobackup.cloud_remove()
        log.info("%s quitó la nube de respaldos", req.user["usuario"])
        return ok()
    b = req.json()
    tipo = autobackup.cloud_setup(str(b.get("tipo") or ""), str(b.get("token") or ""))
    log.info("%s configuró la nube de respaldos (%s)", req.user["usuario"], tipo)
    return ok(nube=tipo)


# Lado que recibe
@app.route("/api/respaldos-recibidos", rol="admin")
def recibidos(req):
    return jsonr({"codigos": autobackup.codes(), "nodos": autobackup.received(),
                  "conservar": int(settings.get("ab_recv_keep") or 7), "con_audios": autobackup.KEEP_CON_AUDIOS})


@app.route("/api/respaldos-recibidos/codigos", ("POST",), rol="admin")
def recibidos_codigo(req):
    token = autobackup.code_create(req.json().get("etiqueta") or "")
    log.info("%s creó un código para recibir respaldos", req.user["usuario"])
    return ok(codigo=token)


@app.route("/api/respaldos-recibidos/codigos/<int:cid>", ("DELETE",), rol="admin")
def recibidos_codigo_del(req, cid):
    autobackup.code_revoke(cid)
    return ok()


@app.route("/api/respaldos-recibidos/<nodo>/<nombre>", rol="admin")
def recibidos_archivo(req, nodo, nombre):
    f = autobackup.received_file(str(nodo), str(nombre))
    if not f:
        raise HTTPError(404, "Ese respaldo ya no existe")
    r = send_file(f, "application/gzip")
    r.headers["Content-Disposition"] = 'attachment; filename="{}"'.format(f.name)
    return r


@app.route("/api/remoto/respaldo", ("GET", "POST"), auth=False)
def remoto_respaldo(req):
    token = req.headers.get("X-HAMNA-Backup", "")
    if not autobackup.code_check(token):
        raise HTTPError(401, "Código de acceso inválido")
    if req.method == "GET":
        cfg = settings.load()
        return ok(estacion=cfg.get("station_name") or "", nodo=cfg.get("node") or "", version=VERSION,
                  libre_mb=shutil.disk_usage(str(paths.data_dir())).free // 2**20)
    up = req.files.get("cuerpo")
    if not up:
        raise ValueError("No llegó el respaldo")
    try:
        est = bytes.fromhex(req.headers.get("X-HAMNA-Estacion", "")).decode("utf-8", "replace")[:80]
    except ValueError:
        est = ""
    name = autobackup.receive(token, up.path, req.headers.get("X-HAMNA-Nodo", ""), est,
                              req.headers.get("X-HAMNA-Version", "")[:20], req.ip)
    up.path = None
    return ok(guardado=name)


@app.route("/api/ajustes/password", ("POST",), rol="lectura")
def ajustes_password(req):
    """Cada quien cambia su propia contraseña; cierra sus otras sesiones."""
    b = req.json()
    auth.change_own_password(req.user, b.get("actual"), b.get("nueva"))
    log.info("%s cambió su contraseña", req.user["usuario"])
    return ok()


@app.route("/api/azure/voces", ("POST",), rol="admin")
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
