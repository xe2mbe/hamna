"""
HAMNA Web — API HTTP y página. Funciona con Python 3.5 a 3.13 sin paquetes extra.
"""
import binascii
import datetime as dt
import json
import logging
import os
import re
import shutil
import threading
import time
import urllib.parse
import uuid
from pathlib import Path

from . import VERSION, anuncios, audio, auth, horas, pronuncia, autobackup, backends, backup, diagnose, health, cron, db, export, links, notify, numeracion, paths, sessions, settings, share, sync, sysmon, tts, tz, updates
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
    anuncios.init()
    from . import biblioteca
    biblioteca.init()
    biblioteca.a_secciones()           # desde la v1.56 la biblioteca son las Secciones
    from . import historial
    historial.init()
    anuncios.emisor.start()
    from . import hub
    hub.init()
    from . import control
    control.init()
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
                  "usuario": {k: u.get(k) for k in ("id", "usuario", "nombre", "rol", "rol_nombre", "idioma", "foto")} if u else None})


def _foto_path(uid):
    return paths.data_dir() / "fotos" / "{}.jpg".format(int(uid))


@app.route("/api/mi-foto", ("POST", "DELETE"), rol="colaborador")
def mi_foto(req):
    """Foto de perfil: el navegador ya la manda recortada a 256×256 en JPEG."""
    uid = req.user["id"]
    p = _foto_path(uid)
    if req.method == "DELETE":
        paths.rm(p)
        auth.set_photo(uid, "")
        return ok(foto="")
    up = req.files.get("foto")
    if not up:
        raise ValueError("Elige una imagen")
    with open(up.path, "rb") as f:
        cabeza = f.read(3)
    if cabeza != b"\xff\xd8\xff":
        raise ValueError("La foto debe ser JPEG")
    if os.path.getsize(up.path) > 2 * 1024 * 1024:
        raise ValueError("La foto es muy grande")
    os.makedirs(str(p.parent), exist_ok=True)
    shutil.move(up.path, str(p))
    up.path = None
    v = str(int(time.time()))
    auth.set_photo(uid, v)
    return ok(foto=v)


@app.route("/api/fotos/<int:uid>", rol="colaborador")
def foto_usuario(req, uid):
    p = _foto_path(uid)
    if not p.is_file():
        raise HTTPError(404)
    return send_file(p, "image/jpeg")


@app.route("/api/mi-telegram", rol="colaborador")
def mi_telegram(req):
    from . import bot
    u = db.row("SELECT tg_id, tg_nombre FROM usuarios WHERE id=?", (req.user["id"],)) or {}
    return jsonr({"vinculado": bool(u.get("tg_id")), "nombre": u.get("tg_nombre") or "",
                  "disponible": bot.activo(), "bot": ("@" + bot.estado()["bot"]) if bot.estado()["bot"] else ""})


@app.route("/api/mi-telegram", ("POST", "DELETE"), rol="colaborador")
def mi_telegram_cambiar(req):
    from . import bot
    if req.method == "DELETE":
        auth.set_tg(req.user["id"], "", "")
        log.info("%s desvinculó su Telegram", req.user["usuario"])
        return ok()
    return ok(**bot.nuevo_codigo(req.user["id"]))


@app.route("/api/bot", rol="admin")
def bot_estado(req):
    from . import bot
    return jsonr(bot.estado())


@app.route("/api/mi-nombre", ("PUT",), rol="colaborador")
def mi_nombre(req):
    """Cada quien cambia el nombre con que aparece (no el usuario para entrar)."""
    nombre = (req.json().get("nombre") or "").strip()[:60]
    auth.update_user(req.user["id"], nombre=nombre)
    log.info("%s cambió su nombre a «%s»", req.user["usuario"], nombre)
    return ok(nombre=nombre)


@app.route("/api/mi-idioma", ("PUT",), rol="colaborador")
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
    if "secciones" in b:
        auth.set_user_sections(uid, b["secciones"])
    log.info("%s creó el usuario %s (%s)", req.user["usuario"], b.get("usuario"), b.get("rol"))
    return ok(id=uid)


@app.route("/api/usuarios/<int:uid>", ("PUT",), rol="admin")
def usuarios_editar(req, uid):
    b = req.json()
    f = {k: b[k] for k in ("nombre", "rol", "activo", "password") if k in b}
    if uid == req.user["id"] and (f.get("rol", "admin") != "admin" or f.get("activo") is False):
        raise ValueError("No puedes quitarte el rol de administrador ni desactivarte a ti mismo")
    if b.get("desvincular_tg"):                     # solo quitar su Telegram (Ajustes → Usuarios)
        auth.set_tg(uid, "", "")
        log.info("%s desvinculó el Telegram del usuario #%s", req.user["usuario"], uid)
        if set(b) == {"desvincular_tg"}:
            return ok()
    auth.update_user(uid, cur_sid=req.user["sid"], **f)
    if "secciones" in b:
        auth.set_user_sections(uid, b["secciones"])
    log.info("%s modificó el usuario #%s (%s)", req.user["usuario"], uid, ", ".join(sorted(f)))
    return ok()


@app.route("/api/usuarios/<int:uid>", ("DELETE",), rol="admin")
def usuarios_borrar(req, uid):
    auth.delete_user(uid, req.user["id"])
    paths.rm(_foto_path(uid))
    log.info("%s borró el usuario #%s", req.user["usuario"], uid)
    return ok()


@app.route("/api/usuarios/desbloquear", ("POST",), rol="admin")
def usuarios_desbloquear(req):
    auth.unlock_all()
    return ok()


@app.route("/api/mis-sesiones", rol="colaborador")
def mis_sesiones(req):
    return jsonr({"sesiones": auth.sessions(req.user["id"]), "mi_sesion": req.user["sid"]})


@app.route("/api/mis-sesiones/<int:sid>", ("DELETE",), rol="colaborador")
def cerrar_sesion(req, sid):
    if req.user["rol"] == "admin":
        auth.revoke(sid)                   # el administrador puede cerrar cualquiera
    else:
        auth.revoke(sid, req.user["id"])
    return ok()


@app.route("/api/mis-sesiones/otras", ("POST",), rol="colaborador")
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
    from . import grabar
    s["grabacion"] = grabar.grabadora.estado()
    s["salud"] = health.worst()
    return jsonr(s)


@app.route("/api/salud")
def salud(req):
    return jsonr(health.status())


@app.route("/api/diagnostico", ("POST",), rol="admin")
def diagnostico(req):
    return jsonr(diagnose.run())


@app.route("/api/salud/revisar", ("POST",), rol="admin")
def salud_revisar(req):
    return jsonr(health.check_now())


# ── Escuchar en vivo ─────────────────────────────────────────────────────────
@app.route("/api/en-vivo/irlp", ("POST",), rol="admin")
def en_vivo_irlp(req):
    on = bool((req.json() or {}).get("on"))
    if engine.st.get("on_air"):
        raise HTTPError(409, "Espera a que termine lo que está al aire")
    try:
        r = live.irlp_cambiar(on)
    except RuntimeError as e:
        raise HTTPError(400, str(e))
    log.info("%s %s escuchar en vivo (IRLP)", req.user["usuario"], "encendió" if on else "apagó")
    return jsonr(r)


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
        "pronuncia": settings.get("pron_dict") or [],     # para resaltar en el editor de secciones
        "historial": db.get_historial(15),
    })


# ── Secciones ────────────────────────────────────────────────────────────────
def _sec_out(s):
    s = dict(s)
    s["tiene_audio"] = bool(s.get("ruta_archivo")) and (paths.audios_dir() / s["ruta_archivo"]).is_file()
    s["tiene_anterior"] = bool(s.get("anterior_archivo")) and (_anteriores_dir() / s["anterior_archivo"]).is_file()
    return s


# ── Versión anterior del audio de una sección ───────────────────────────────
def _anteriores_dir():
    d = paths.audios_dir() / "anteriores"
    if not d.is_dir():
        os.makedirs(str(d), exist_ok=True)
    return d


def _reemplazar_audio(sid, up):
    """Guarda el archivo subido como audio de la sección. Si está activado,
    el audio que tenía pasa a ser la versión anterior (una sola por sección).
    Devuelve los campos para db.update_seccion."""
    s = db.get_seccion(sid) or {}
    old = s.get("ruta_archivo") or ""
    oldp = paths.audios_dir() / old if old else None
    prev = None
    if oldp and oldp.is_file() and settings.load().get("keep_previous", True):
        d = _anteriores_dir()
        if s.get("anterior_archivo"):
            paths.rm(d / s["anterior_archivo"])
        shutil.move(str(oldp), str(d / old))       # antes de guardar: el nuevo puede llamarse igual
        prev = {"anterior_archivo": old, "anterior_duracion": float(s.get("duracion") or 0),
                "anterior_fecha": dt.datetime.now().strftime("%Y-%m-%d %H:%M"), "anterior_ts": s.get("audio_ts")}
    try:
        dest = save_upload(up, paths.audios_dir(), str(sid))
    except Exception:
        if prev:
            shutil.move(str(_anteriores_dir() / old), str(oldp))
            prev = None
        raise
    if not prev and old and old != dest.name:
        paths.rm(oldp)
    f = {"ruta_archivo": dest.name, "duracion": audio.duration(dest), "audio_ts": time.time()}
    f.update(prev or {})
    return f


def _restaurar_anterior(sid):
    """Intercambia el audio actual con la versión anterior."""
    s = db.get_seccion(sid)
    if not s or not s.get("anterior_archivo"):
        raise ValueError("Esta sección no tiene versión anterior")
    d = _anteriores_dir()
    ap = d / s["anterior_archivo"]
    if not ap.is_file():
        raise ValueError("No encontré el archivo de la versión anterior")
    tmp = d / ("cambio_" + uuid.uuid4().hex)
    shutil.move(str(ap), str(tmp))
    cur = s.get("ruta_archivo") or ""
    cp = paths.audios_dir() / cur if cur else None
    campos = {"anterior_archivo": "", "anterior_duracion": 0, "anterior_fecha": "", "anterior_ts": None}
    target = paths.audios_dir() / s["anterior_archivo"]
    movido = False
    try:
        if cp and cp.is_file():
            shutil.move(str(cp), str(d / cur))
            movido = True
            campos = {"anterior_archivo": cur, "anterior_duracion": float(s.get("duracion") or 0),
                      "anterior_fecha": dt.datetime.now().strftime("%Y-%m-%d %H:%M"), "anterior_ts": s.get("audio_ts")}
        shutil.move(str(tmp), str(target))
    except Exception:
        log.exception("No se pudo regresar la versión anterior de la sección #%s", sid)
        # dejar todo como estaba
        if movido and not cp.exists():
            shutil.move(str(d / cur), str(cp))
        if tmp.exists():
            shutil.move(str(tmp), str(ap))
        raise ValueError("No se pudo cambiar el audio (¿se está usando en este momento?). Intenta de nuevo en un momento.")
    campos.update(ruta_archivo=target.name, duracion=audio.duration(target),
                  audio_ts=s.get("anterior_ts") or target.stat().st_mtime)
    db.update_seccion(sid, **campos)
    threading.Thread(target=_prep_eventos_de, args=(sid,), daemon=True).start()


def _audio_anterior(s):
    if not s or not s.get("anterior_archivo") or not (_anteriores_dir() / s["anterior_archivo"]).is_file():
        raise HTTPError(404)
    return _browser_file(_anteriores_dir() / s["anterior_archivo"])


@app.route("/api/secciones")
def secciones(req):
    usos = {}
    for r in db.rows("""SELECT es.seccion_id, e.nombre FROM evento_secciones es JOIN eventos e ON e.id=es.evento_id
                        ORDER BY e.nombre COLLATE NOCASE"""):
        usos.setdefault(r["seccion_id"], []).append(r["nombre"])
    out = []
    for s in db.get_secciones():
        s = _sec_out(s)
        s["eventos"] = usos.get(s["id"], [])
        s["actualizado"] = dt.datetime.fromtimestamp(s["audio_ts"]).strftime("%Y-%m-%d %H:%M") if s.get("audio_ts") else None
        out.append(s)
    return jsonr(out)


@app.route("/api/secciones/grupos")
def secciones_grupos(req):
    """Vista por evento: sus secciones en orden y si las que «se renuevan»
    ya se cambiaron desde la última vez que ese evento salió al aire."""
    now = dt.datetime.now()
    progs = db.get_programacion(solo_activos=True)
    grupos, usadas = [], set()
    for e in db.get_eventos():
        ev = numeracion.aplicar(e)
        nxt = []
        for r in progs:
            if r["evento_id"] == e["id"]:
                try:
                    t = engine.next_run(r, now)
                except Exception:
                    t = None
                if t:
                    nxt.append(t)
        ult = db.row("SELECT MAX(inicio) AS i FROM historial WHERE evento_id=? AND inicio < ?",
                     (e["id"], now.strftime("%Y-%m-%d %H:%M:%S")))
        ult_dt = dt.datetime.strptime(ult["i"], "%Y-%m-%d %H:%M:%S") if ult and ult.get("i") else None
        ult_ts = time.mktime(ult_dt.timetuple()) if ult_dt else None
        items = []
        for s in db.get_secciones_by_evento(e["id"]):
            usadas.add(s["id"])
            fresca = None
            if s.get("renovar"):
                fresca = bool(s.get("audio_ts")) and (ult_ts is None or s["audio_ts"] > ult_ts)
            items.append({"id": s["id"], "fresca": fresca})
        grupos.append({"id": e["id"], "nombre": e["nombre"],
                       "etiqueta": numeracion.etiqueta(ev) if (ev.get("num") or ev.get("numero")) else "",
                       "proxima": min(nxt).strftime("%Y-%m-%d %H:%M") if nxt else None,
                       "ultima": ult_dt.strftime("%Y-%m-%d %H:%M") if ult_dt else None, "secciones": items})
    grupos.sort(key=lambda g: (g["proxima"] is None, g["proxima"] or "", g["nombre"].lower()))
    sin = [s["id"] for s in db.get_secciones() if s["id"] not in usadas]
    return jsonr({"grupos": grupos, "sin_usar": sin})


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
    c2 = anuncios.cfg_con_voz(cfg, s.get("voz"))
    src = tts.synthesize(s["texto_tts"], c2, paths.tmp_dir() / ("tts_" + uuid.uuid4().hex[:8]), ctx, respaldo=c2 is cfg)
    dest = paths.audios_dir() / "{}_{}{}".format(sid, safe_name(s["nombre"]), src.suffix)
    shutil.move(str(src), str(dest))
    if s.get("ruta_archivo") and s["ruta_archivo"] != dest.name:
        paths.rm(paths.audios_dir() / s["ruta_archivo"])
    db.update_seccion(sid, ruta_archivo=dest.name, duracion=audio.duration(dest), audio_ts=time.time())
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
    if tipo == "TTS" and "voz" in form:
        try:
            v = anuncios.voz_limpia(json.loads(form.get("voz") or "{}"))
        except ValueError as e:
            raise ValueError(str(e))
        fields["voz"] = json.dumps(v, sort_keys=True) if v else ""
    if "renovar" in form:
        fields["renovar"] = 1 if truthy(form["renovar"]) else 0
    if "nombre" in fields and not fields["nombre"]:
        raise ValueError("La sección necesita un nombre")
    if tipo == "TTS" and "url" in form:
        # Texto desde una dirección: solo el administrador la pone o la cambia
        antes = db.get_seccion(sid) or {}
        u = (form.get("url") or "").strip()
        if req.user["rol"] != "admin":
            if u != (antes.get("url") or "") or (u and form.get("url_falla") not in (None, antes.get("url_falla"))):
                raise HTTPError(403, "Solo un administrador puede poner o cambiar la dirección del texto")
        else:
            from . import textourl
            fields["url"] = textourl.validar(u) if u else ""
            fields["url_falla"] = "saltar" if form.get("url_falla") == "saltar" else "respaldo"
            texto = fields.get("texto_tts", antes.get("texto_tts") or "")
            if fields["url"] and fields["url_falla"] == "respaldo" and not (texto or "").strip():
                raise ValueError("Escribe el texto de respaldo, o elige «omitir la sección» si la dirección falla")
    up = req.files.get("archivo")
    if not up and tipo != "TTS" and form.get("biblioteca_id"):
        # Audio de la biblioteca: la sección se queda con una copia
        from . import biblioteca
        _b, up = biblioteca.como_subida(int(form["biblioteca_id"]))
    if up:
        fields.update(_reemplazar_audio(sid, up))
    db.update_seccion(sid, **fields)
    if up and not settings.load().get("keep_originals", True):
        _compact_section(sid)
    if tipo == "TTS" and (is_new or truthy(form.get("generar", "0"))):
        _generate_tts(sid)


# ── Mis secciones (rol colaborador) ──────────────────────────────────────────
def _mi_seccion(req, sid):
    s = db.get_seccion(sid)
    if not s or sid not in auth.user_sections(req.user["id"]):
        raise HTTPError(404)
    return s


@app.route("/api/mis-secciones", rol="colaborador")
def mis_secciones(req):
    ids = auth.user_sections(req.user["id"])
    progs = db.get_programacion(solo_activos=True)
    now = dt.datetime.now()
    out = []
    for sid in ids:
        s = db.get_seccion(sid)
        if not s:
            continue
        p = paths.audios_dir() / s["ruta_archivo"] if s.get("ruta_archivo") else None
        evs = db.rows("""SELECT e.id, e.nombre FROM evento_secciones es JOIN eventos e ON e.id=es.evento_id
                         WHERE es.seccion_id=? ORDER BY e.nombre COLLATE NOCASE""", (sid,))
        for e in evs:
            nxt = [t for t in (engine.next_run(r, now) for r in progs if r["evento_id"] == e["id"]) if t]
            e["proxima"] = min(nxt).strftime("%Y-%m-%d %H:%M") if nxt else None
        out.append({"id": sid, "nombre": s["nombre"], "tipo": s["tipo"], "titulo": s.get("titulo") or "",
                    "texto_tts": s.get("texto_tts") or "" if s["tipo"] == "TTS" else "",
                    "duracion": float(s.get("duracion") or 0), "tiene_audio": bool(p and p.is_file()),
                    "actualizado": dt.datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
                    if p and p.is_file() else None, "eventos": evs,
                    "anterior": {"duracion": float(s.get("anterior_duracion") or 0), "fecha": s.get("anterior_fecha") or ""}
                    if _sec_out(s)["tiene_anterior"] else None})
    eids = _mis_eventos(req)
    from . import bot
    tg = db.row("SELECT tg_id FROM usuarios WHERE id=?", (req.user["id"],)) or {}
    return jsonr({"secciones": out, "formatos": audio.formats(), "pronuncia": settings.get("pron_dict") or [],
                  "programacion": _prog_rows(eids),
                  "ahora": now.strftime("%Y-%m-%d %H:%M:%S"),
                  "telegram": {"disponible": bot.activo(), "vinculado": bool(tg.get("tg_id")),
                               "bot": ("@" + bot.estado()["bot"]) if bot.estado()["bot"] else ""}})


def _mis_eventos(req):
    ids = auth.user_sections(req.user["id"])
    if not ids:
        return set()
    q = ",".join("?" * len(ids))
    return {r["evento_id"] for r in db.rows(
        "SELECT DISTINCT evento_id FROM evento_secciones WHERE seccion_id IN (" + q + ")", ids)}


@app.route("/api/mis-eventos/<int:eid>", rol="colaborador")
def mi_evento(req, eid):
    """Solo lectura: las secciones del evento donde sale la colaboración."""
    if eid not in _mis_eventos(req):
        raise HTTPError(404)
    ev = numeracion.aplicar(db.get_evento(eid))
    mias = set(auth.user_sections(req.user["id"]))
    secs = []
    for s in db.get_secciones_by_evento(eid):
        o = _sec_out(s)
        secs.append({"id": s["id"], "nombre": s["nombre"], "tipo": s["tipo"], "duracion": float(s.get("duracion") or 0),
                     "tiene_audio": o["tiene_audio"], "contabilizable": bool(s.get("contabilizable")),
                     "mia": s["id"] in mias})
    return jsonr({"id": eid, "nombre": ev["nombre"], "tipo": ev.get("tipo") or "", "num": ev.get("num"),
                  "numero": ev.get("numero"), "num_auto": ev.get("num_auto"), "secciones": secs,
                  "pausa": float(settings.load().get("section_gap", 3) or 0)})


@app.route("/api/mis-eventos/<int:eid>/secciones/<int:sid>/audio", rol="colaborador")
def mi_evento_audio(req, eid, sid):
    """Escuchar (solo escuchar) cualquier sección del evento donde sale la colaboración."""
    if eid not in _mis_eventos(req):
        raise HTTPError(404)
    s = next((x for x in db.get_secciones_by_evento(eid) if x["id"] == sid), None)
    if not s or not s.get("ruta_archivo") or not (paths.audios_dir() / s["ruta_archivo"]).is_file():
        raise HTTPError(404)
    return _browser_file(paths.audios_dir() / s["ruta_archivo"])


@app.route("/api/mis-secciones/<int:sid>/audio", rol="colaborador")
def mi_seccion_audio(req, sid):
    s = _mi_seccion(req, sid)
    if not s.get("ruta_archivo"):
        raise HTTPError(404)
    return _browser_file(paths.audios_dir() / s["ruta_archivo"])


@app.route("/api/mis-secciones/<int:sid>/anterior", rol="colaborador")
def mi_seccion_anterior(req, sid):
    return _audio_anterior(_mi_seccion(req, sid))


@app.route("/api/mis-secciones/<int:sid>/anterior", ("POST",), rol="colaborador")
def mi_seccion_regresar(req, sid):
    s = _mi_seccion(req, sid)
    _restaurar_anterior(sid)
    quien = req.user["usuario"].upper()
    log.info("%s (colaborador) regresó la versión anterior de «%s»", req.user["usuario"], s["nombre"])
    notify.send("colaborador", "↩ <b>{}</b> regresó la versión anterior de «{}»".format(
        notify.esc(quien), notify.esc(s["nombre"])))
    return ok()


@app.route("/api/secciones/<int:sid>/anterior")
def seccion_anterior(req, sid):
    return _audio_anterior(db.get_seccion(sid))


@app.route("/api/secciones/<int:sid>/anterior", ("POST",))
def seccion_regresar(req, sid):
    _restaurar_anterior(sid)
    log.info("%s regresó la versión anterior de la sección #%s", req.user["usuario"], sid)
    return ok(seccion=_sec_out(db.get_seccion(sid)))


@app.route("/api/mis-secciones/<int:sid>", ("POST",), rol="colaborador")
def mi_seccion_subir(req, sid):
    s = _mi_seccion(req, sid)
    if s["tipo"] == "TTS":
        texto = (req.form.get("texto_tts") or "").strip()
        if not texto:
            raise ValueError("Escribe el texto")
        db.update_seccion(sid, texto_tts=texto)
        _generate_tts(sid)
        _aviso_colaborador(req.user, sid, "cambió el texto de")
    else:
        up = req.files.get("archivo")
        if not up:
            raise ValueError("Elige el archivo de audio")
        colaborador_audio(req.user, sid, up)
    s = db.get_seccion(sid)
    return ok(seccion={"id": sid, "duracion": float(s.get("duracion") or 0)})


def colaborador_audio(user, sid, up, via=""):
    """El colaborador reemplaza el audio de su sección (desde la página o por
    Telegram): guarda la versión anterior, avisa al admin y prepara los eventos."""
    db.update_seccion(sid, **_reemplazar_audio(sid, up))
    if not settings.load().get("keep_originals", True):
        _compact_section(sid)
    _aviso_colaborador(user, sid, "subió un audio nuevo para", via)
    return db.get_seccion(sid)


def _aviso_colaborador(user, sid, que, via=""):
    s = db.get_seccion(sid)
    quien = user["usuario"].upper()
    log.info("%s (colaborador) %s la sección «%s»%s", user["usuario"], que, s["nombre"], " por Telegram" if via else "")
    evs = [e["nombre"] for e in db.rows("""SELECT e.nombre FROM evento_secciones es JOIN eventos e ON e.id=es.evento_id
                                          WHERE es.seccion_id=?""", (sid,))]
    notify.send("colaborador", "📤 <b>{}</b> {} «{}» ({}){}{}".format(
        notify.esc(quien), que, notify.esc(s["nombre"]), notify.dur(s.get("duracion") or 0),
        " · 📲 por Telegram" if via else "",
        "\n📋 Se usa en: " + notify.esc(", ".join(evs)) if evs else ""))
    threading.Thread(target=_prep_eventos_de, args=(sid,), daemon=True).start()


def _prep_eventos_de(sid):
    for r in db.rows("SELECT evento_id FROM evento_secciones WHERE seccion_id=?", (sid,)):
        try:
            engine.prepare_event(r["evento_id"])
        except Exception as e:
            log.warning("No se pudo preparar el evento #%s: %s", r["evento_id"], e)


@app.route("/api/secciones", ("POST",))
def seccion_new(req):
    f = req.form
    tipo = f.get("tipo", "Audio")
    if tipo not in ("TTS", "Audio", "Sonido"):
        raise ValueError("Tipo inválido")
    nombre = (f.get("nombre") or "").strip()
    if not nombre:
        raise ValueError("La sección necesita un nombre")
    if tipo != "TTS" and "archivo" not in req.files and not f.get("biblioteca_id"):
        raise ValueError("Sube un archivo de audio o elige uno de la biblioteca")
    if tipo == "TTS" and not (f.get("texto_tts") or "").strip() and not (f.get("url") or "").strip():
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
        if s.get("anterior_archivo"):
            paths.rm(_anteriores_dir() / s["anterior_archivo"])
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


@app.route("/api/secciones/<int:sid>/descargar", rol="lectura")
def seccion_descargar(req, sid):
    """El audio de una sección con su nombre: el archivo tal cual si es un formato común
    (MP3, WAV…); si no (µ-law, GSM…), convertido a WAV."""
    s = db.get_seccion(sid)
    if not s or not s.get("ruta_archivo"):
        raise HTTPError(404, "La sección no tiene audio")
    p = paths.audios_dir() / s["ruta_archivo"]
    if not p.is_file():
        raise HTTPError(404, "No encontré el audio de la sección")
    if audio.can_play_in_browser(p):
        src, ext = p, p.suffix.lower()
    else:
        src, ext = audio.prepare(p, None), ".wav"
    nombre = (re.sub(r'[\\/:*?"<>|\r\n\t]+', " ", s.get("nombre") or "").strip(" .") or "seccion")[:120]
    nombre = re.sub(r"\s{2,}", " ", nombre) + ext
    ascii_name = re.sub(r"[^A-Za-z0-9._ -]", "_", nombre)
    r = send_file(src, "audio/mpeg" if ext == ".mp3" else None)
    r.headers["Content-Disposition"] = "attachment; filename=\"{}\"; filename*=UTF-8''{}".format(
        ascii_name, urllib.parse.quote(nombre))
    log.info("%s descargó la sección «%s»", req.user["usuario"], s.get("nombre"))
    return r


@app.route("/api/secciones/<int:sid>/aire", ("POST",))
def seccion_aire(req, sid):
    """Transmite la sección una vez por la cola de los anuncios: espera canal libre y nunca corta
    lo que esté al aire. destino: local (solo este nodo) | red (también los enlazados)."""
    s = db.get_seccion(sid)
    if not s or not s.get("ruta_archivo") or not (paths.audios_dir() / s["ruta_archivo"]).is_file():
        raise ValueError("La sección no tiene audio")
    destino = (req.json() or {}).get("destino") or "local"
    if destino not in ("local", "red"):
        raise ValueError("Destino inválido")
    wav = audio.prepare(paths.audios_dir() / s["ruta_archivo"], _air_target(settings.load()))
    if not anuncios.emisor.encolar_audio({"clave": "sec:{}".format(sid), "nombre": "🎚 " + s["nombre"], "wav": str(wav),
                                          "texto": "", "voz": ""}, "sección · " + req.user["usuario"], destino):
        raise ValueError("Esa sección ya está en espera o al aire")
    log.info("%s mandó al aire la sección «%s»", req.user["usuario"], s["nombre"])
    return ok()


@app.route("/api/secciones/<int:sid>/duplicar", ("POST",))
def seccion_duplicar(req, sid):
    s = db.get_seccion(sid)
    if not s:
        raise HTTPError(404)
    nid = db.insert_seccion((s["nombre"] + " (copia)")[:120], s["tipo"], s.get("texto_tts"), s.get("regenerar_antes"),
                            s.get("titulo"), s.get("descripcion"))
    campos = {"renovar": s.get("renovar") or 0, "voz": s.get("voz") or ""}
    if req.user["rol"] == "admin":          # la dirección del texto solo la pone un administrador
        campos.update(url=s.get("url") or "", url_falla=s.get("url_falla") or "respaldo")
    p = paths.audios_dir() / s["ruta_archivo"] if s.get("ruta_archivo") else None
    if p and p.is_file():
        dest = paths.audios_dir() / "{}_{}{}".format(nid, safe_name(s["nombre"]), p.suffix)
        shutil.copyfile(str(p), str(dest))
        campos.update(ruta_archivo=dest.name, duracion=s.get("duracion") or 0, audio_ts=time.time())
    db.update_seccion(nid, **campos)
    log.info("%s duplicó la sección «%s»", req.user["usuario"], s["nombre"])
    return ok(seccion=_sec_out(db.get_seccion(nid)))


@app.route("/api/secciones/txt", ("POST",))
def secciones_txt(req):
    """«Cargar varios .txt»: una sección de voz por archivo, con el nombre del archivo."""
    b = req.json()
    archivos = b.get("archivos")
    if not isinstance(archivos, list) or not archivos:
        raise ValueError("No llegó ningún archivo")
    if len(archivos) > 20:
        raise ValueError("Máximo 20 archivos a la vez")
    voz = anuncios.voz_limpia(b.get("voz") or {})
    out = []
    for f in archivos:
        nombre = os.path.splitext(str((f or {}).get("nombre") or "texto").strip())[0][:120] or "texto"
        texto = str((f or {}).get("texto") or "").strip()
        if not texto:
            out.append({"nombre": nombre, "ok": False, "error": "El archivo está vacío"})
            continue
        sid = db.insert_seccion(nombre, "TTS", texto)
        try:
            if voz:
                db.update_seccion(sid, voz=json.dumps(voz, sort_keys=True))
            _generate_tts(sid)
            out.append({"nombre": nombre, "ok": True, "id": sid})
        except Exception as e:
            db.delete_seccion(sid)
            out.append({"nombre": nombre, "ok": False, "error": str(e)[:200]})
    log.info("%s cargó %d secciones desde .txt", req.user["usuario"], sum(1 for x in out if x["ok"]))
    return ok(resultados=out)


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
    if isinstance(b.get("diccionario"), list):         # probar el diccionario antes de guardarlo
        cfg = dict(cfg, pron_dict=pronuncia.normalizar(b["diccionario"]))
    ctx = {"titulo": b.get("titulo") or "", "descripcion": b.get("descripcion") or "",
           "evento": "Evento de prueba", "numero": "92", "emision": "92", "emision_anio": "46"}
    # La prueba de Ajustes → Voz oye exactamente el motor elegido (sin respaldo)
    c2 = anuncios.cfg_con_voz(cfg, anuncios.voz_limpia(b.get("voz") or {}))
    src = tts.synthesize(text, c2, paths.tmp_dir() / ("preview_" + uuid.uuid4().hex[:8]), ctx,
                         respaldo=not b.get("sin_respaldo") and c2 is cfg)
    if not audio.can_play_in_browser(src):
        src = audio.prepare(src, None)
    return ok(url="api/archivo/" + src.parent.name + "/" + src.name,
              texto=pronuncia.para_voz(tts.resolve_variables(text, cfg, ctx), cfg))


# ── Programación → Anuncios ──────────────────────────────────────────────────
def _anuncio_req(req, aid=None):
    try:
        datos = json.loads(req.form.get("datos") or "{}")
    except ValueError:
        raise ValueError("Datos del anuncio inválidos")
    up = req.files.get("archivo")
    actual = anuncios.uno(aid) if aid else {}
    # «Texto desde una dirección»: es una petición que sale del nodo; solo el administrador pone o cambia la dirección
    if req.user["rol"] != "admin":
        if datos.get("tipo") == "url" and actual.get("tipo") != "url":
            raise HTTPError(403, "Solo un administrador puede crear un anuncio desde una dirección")
        if actual.get("tipo") == "url":
            datos["url"] = actual.get("url", "")
    return anuncios.guardar(datos, up.path if up else None, up.filename if up else "",
                            req.user["usuario"], aid)


@app.route("/api/anuncios", rol="lectura")
def anuncios_lista(req):
    return jsonr(anuncios.resumen())


@app.route("/api/anuncios", ("POST",), rol="operador")
def anuncios_nuevo(req):
    return ok(anuncio=_anuncio_req(req))


@app.route("/api/anuncios/<int:aid>", ("PUT",), rol="operador")
def anuncios_editar(req, aid):
    return ok(anuncio=_anuncio_req(req, aid))


@app.route("/api/anuncios/<int:aid>", ("DELETE",), rol="operador")
def anuncios_borrar(req, aid):
    anuncios.borrar(aid, req.user["usuario"])
    return ok()


@app.route("/api/anuncios/<int:aid>/activo", ("POST",), rol="operador")
def anuncios_activo(req, aid):
    return ok(anuncio=anuncios.activar(aid, truthy(req.json().get("activo")), req.user["usuario"]))


@app.route("/api/anuncios/<int:aid>/ahora", ("POST",), rol="operador")
def anuncios_ahora(req, aid):
    a = anuncios.uno(aid)
    destino = (req.json() or {}).get("destino")
    if destino not in (None, "local", "red"):
        raise ValueError("Destino inválido")
    if not anuncios.emisor.encolar(aid, "manual:" + req.user["usuario"], destino):
        raise ValueError("Ese anuncio ya está en espera o al aire")
    log.info("%s mandó al aire el anuncio «%s»", req.user["usuario"], a["nombre"])
    return ok()


@app.route("/api/anuncios/<int:aid>/audio", rol="lectura")
def anuncios_audio(req, aid):
    p = anuncios.ruta(anuncios.uno(aid))
    if not p or not p.is_file():
        raise HTTPError(404)
    return send_file(p, "audio/wav")


@app.route("/api/anuncios/<int:aid>/descargar", rol="lectura")
def anuncios_descargar(req, aid):
    """El WAV del anuncio (8 kHz, el que sale al aire) con el nombre del anuncio."""
    a = anuncios.uno(aid)
    p = anuncios.ruta(a)
    if not p or not p.is_file():
        raise HTTPError(404, "El anuncio no tiene audio")
    nombre = (re.sub(r'[\\/:*?"<>|\r\n\t]+', " ", a.get("nombre") or "").strip(" .") or "anuncio")[:120]
    nombre = re.sub(r"\s{2,}", " ", nombre) + ".wav"
    ascii_name = re.sub(r"[^A-Za-z0-9._ -]", "_", nombre)
    r = send_file(p, "audio/wav")
    r.headers["Content-Disposition"] = "attachment; filename=\"{}\"; filename*=UTF-8''{}".format(
        ascii_name, urllib.parse.quote(nombre))
    log.info("%s descargó el anuncio «%s»", req.user["usuario"], a["nombre"])
    return r


_voces_cache = {"t": 0.0, "key": "", "voces": []}


@app.route("/api/anuncios/voces", rol="operador")
def anuncios_voces(req):
    """Voces de Azure con la clave guardada, para elegir la voz de un anuncio (1 h en memoria)."""
    cfg = settings.load()
    key, region = (cfg.get("azure_key") or "").strip(), (cfg.get("azure_region") or "").strip()
    if not key or not region:
        raise ValueError("Falta la clave o la región de Azure (Ajustes → Voz)")
    marca = region + ":" + key[-6:]
    if _voces_cache["key"] != marca or time.time() - _voces_cache["t"] > 3600 or not _voces_cache["voces"]:
        _voces_cache.update(voces=tts.azure_voices(key, region), key=marca, t=time.time())
    return jsonr({"voces": _voces_cache["voces"]})


@app.route("/api/anuncios/url/probar", ("POST",), rol="admin")
def anuncios_url_probar(req):
    """Baja el texto de la dirección y muestra cómo llegó y cómo se dirá; con voz=1 también lo hace voz."""
    b = req.json()
    cfg = settings.load()
    r = anuncios.probar_url(b.get("url"), cfg, anuncios.voz_limpia(b.get("voz") or {}), truthy(b.get("con_voz")),
                            str(b.get("respaldo") or "")[:anuncios.max_chars(cfg)], tramos_de=not truthy(b.get("seccion")))
    if r.get("url_audio"):
        r["url_audio"] = "api/archivo/tmp/" + r["url_audio"]
    return ok(**r)


# ── Programación → Biblioteca de voz ─────────────────────────────────────────
def _bib_req(req, bid=None):
    from . import biblioteca
    try:
        datos = json.loads(req.form.get("datos") or "{}")
    except ValueError:
        raise ValueError("Datos inválidos")
    up = req.files.get("archivo")
    return biblioteca.guardar(datos, up.path if up else None, up.filename if up else "", req.user["usuario"], bid)


@app.route("/api/biblioteca", rol="lectura")
def biblioteca_lista(req):
    from . import biblioteca
    return jsonr({"items": biblioteca.lista(req.query.get("q") or "", req.query.get("orden") or "fecha"),
                  "max_seg": biblioteca.MAX_SEG, "max_lote": biblioteca.MAX_TXT_LOTE})


@app.route("/api/biblioteca", ("POST",), rol="operador")
def biblioteca_nuevo(req):
    return ok(item=_bib_req(req))


@app.route("/api/biblioteca/<int:bid>", ("PUT",), rol="operador")
def biblioteca_editar(req, bid):
    return ok(item=_bib_req(req, bid))


@app.route("/api/biblioteca/<int:bid>", ("DELETE",), rol="operador")
def biblioteca_borrar(req, bid):
    from . import biblioteca
    biblioteca.borrar(bid, req.user["usuario"])
    return ok()


@app.route("/api/biblioteca/<int:bid>/duplicar", ("POST",), rol="operador")
def biblioteca_duplicar(req, bid):
    from . import biblioteca
    return ok(item=biblioteca.duplicar(bid, req.user["usuario"]))


@app.route("/api/biblioteca/<int:bid>/ahora", ("POST",), rol="operador")
def biblioteca_ahora(req, bid):
    from . import biblioteca
    destino = (req.json() or {}).get("destino")
    if destino not in ("local", "red"):
        raise ValueError("Destino inválido")
    biblioteca.transmitir(bid, destino, req.user["usuario"])
    return ok()


@app.route("/api/biblioteca/txt", ("POST",), rol="operador")
def biblioteca_txt(req):
    from . import biblioteca
    b = req.json()
    return ok(resultados=biblioteca.varios_txt(b.get("archivos"), req.user["usuario"],
                                               anuncios.voz_limpia(b.get("voz") or {})))


@app.route("/api/biblioteca/<int:bid>/audio", rol="lectura")
def biblioteca_audio(req, bid):
    from . import biblioteca
    p = biblioteca.ruta(biblioteca.uno(bid))
    if not p or not p.is_file():
        raise HTTPError(404)
    return send_file(p, "audio/wav")


@app.route("/api/biblioteca/<int:bid>/descargar", rol="lectura")
def biblioteca_descargar(req, bid):
    from . import biblioteca
    b = biblioteca.uno(bid)
    p = biblioteca.ruta(b)
    if not p or not p.is_file():
        raise HTTPError(404, "No tiene audio")
    nombre = (re.sub(r'[\\/:*?"<>|\r\n\t]+', " ", b.get("nombre") or "").strip(" .") or "audio")[:120]
    nombre = re.sub(r"\s{2,}", " ", nombre) + ".wav"
    ascii_name = re.sub(r"[^A-Za-z0-9._ -]", "_", nombre)
    r = send_file(p, "audio/wav")
    r.headers["Content-Disposition"] = "attachment; filename=\"{}\"; filename*=UTF-8''{}".format(
        ascii_name, urllib.parse.quote(nombre))
    return r


@app.route("/api/anuncios/voz", ("POST",), rol="operador")
def anuncios_voz(req):
    """Escuchar el texto con la voz configurada antes de guardar."""
    b = req.json()
    cfg = settings.load()
    if isinstance(b.get("diccionario"), list):
        cfg = dict(cfg, pron_dict=pronuncia.normalizar(b["diccionario"]))
    voz = anuncios.voz_limpia(b.get("voz") or {})
    nombre, dicho, dur = anuncios.vista_previa(str(b.get("texto") or "")[:anuncios.max_chars(cfg)], cfg, voz)
    return ok(url="api/archivo/tmp/" + nombre, texto=dicho, duracion=round(dur, 1), max_seg=anuncios.max_seg(cfg))


# ── Variables de hora con zona ({hora 21:00 America/Chicago}, {hora_evento …}) ──
@app.route("/api/horas/probar", ("POST",), rol="colaborador")
def horas_probar(req):
    return ok(items=horas.revisar(str(req.json().get("texto") or "")[:4000]))


# ── Diccionario de pronunciación ────────────────────────────────────────────
@app.route("/api/pronuncia", rol="admin")
def pronuncia_ver(req):
    return jsonr({"lista": settings.get("pron_dict") or [], "max": pronuncia.MAX})


@app.route("/api/pronuncia/probar", ("POST",), rol="admin")
def pronuncia_probar(req):
    b = req.json()
    lista = pronuncia.normalizar(b.get("diccionario")) if isinstance(b.get("diccionario"), list) else settings.get("pron_dict") or []
    texto, usados = pronuncia.aplicar(str(b.get("texto") or "")[:2000], lista)
    return ok(texto=texto, usados=usados)


@app.route("/api/pronuncia", ("PUT",), rol="admin")
def pronuncia_guardar(req):
    nueva = pronuncia.normalizar(req.json().get("lista"))
    vieja = settings.get("pron_dict") or []
    settings.save({"pron_dict": nueva})
    cambios = pronuncia.cambiados(vieja, nueva)
    log.info("%s guardó el diccionario de pronunciación (%d términos, %d cambios)", req.user["usuario"], len(nueva), len(cambios))
    # Las voces ya generadas que usan un término cambiado se vuelven a generar (en segundo plano)
    secs = [s for s in db.get_secciones() if s.get("tipo") == "TTS" and (s.get("texto_tts") or "").strip()
            and pronuncia.toca(s["texto_tts"], cambios)] if cambios else []
    ans = anuncios.usan(cambios) if cambios else []

    def rehacer():
        for s in secs:
            try:
                _generate_tts(s["id"])
            except Exception as e:
                log.warning("No pude volver a generar la voz de «%s»: %s", s.get("nombre"), e)
        if ans:
            anuncios.rehacer_voces(cambios)
    if secs or ans:
        threading.Thread(target=rehacer, daemon=True, name="hamna-pronuncia").start()
    return ok(lista=nueva, secciones=[s["nombre"] for s in secs], anuncios=ans)


@app.route("/api/archivo/<carpeta>/<name>")
def tmp_file(req, carpeta, name):
    if carpeta not in ("tmp", "cache") or not re.match(r"^[A-Za-z0-9_.-]+$", name):
        raise HTTPError(404)
    base = paths.tmp_dir() if carpeta == "tmp" else paths.cache_dir()
    return send_file(base / name)


# ── Eventos ──────────────────────────────────────────────────────────────────
@app.route("/api/eventos")
def eventos(req):
    evs = [numeracion.aplicar(e) for e in db.get_eventos()]
    return jsonr({"eventos": evs, "tipos": db.get_eventos_types()})


@app.route("/api/eventos/<int:eid>")
def evento(req, eid):
    ev = db.get_evento(eid)
    if not ev:
        raise HTTPError(404)
    ev["secciones"] = [_sec_out(s) for s in db.get_secciones_by_evento(eid)]
    ev["conexiones"] = db.get_conexiones(eid)
    try:
        ev["num_calc"] = numeracion.calcular(ev)      # también sin activar: para sugerir la referencia
    except ValueError:
        ev["num_calc"] = None
    ev = numeracion.aplicar(ev)
    return jsonr(ev)


@app.route("/api/eventos/<int:eid>/numeracion", ("POST",))
def evento_numeracion(req, eid):
    """Vista previa de la numeración con la referencia que se está escribiendo."""
    ev = db.get_evento(eid)
    if not ev:
        raise HTTPError(404)
    _a, f, g = _num_fields(dict(req.json(), num_auto=True))
    return ok(num=numeracion.calcular(ev, ref_fecha=f, ref_global=g))


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


def _num_fields(b):
    auto = bool(b.get("num_auto"))
    f = str(b.get("num_ref_fecha") or "").strip()
    g = str(b.get("num_ref_global") or "").strip()
    if f and not re.match(r"^\d{4}-\d{2}-\d{2}$", f):
        raise ValueError("Fecha de referencia inválida")
    if g and not re.match(r"^-?\d{1,7}$", g):
        raise ValueError("El número de emisión global debe ser un número entero")
    if auto and not (f and g):
        raise ValueError("Para numerar solo, indica qué número global tiene la emisión de qué fecha")
    return auto, f, (int(g) if g else None)


@app.route("/api/eventos", ("POST",))
def evento_new(req):
    b = req.json()
    num = _num_fields(b)
    eid = db.insert_evento(*_ev_fields(b))
    db.set_numeracion(eid, *num)
    return ok(id=eid)


@app.route("/api/eventos/<int:eid>", ("PUT",))
def evento_edit(req, eid):
    b = req.json()
    num = _num_fields(b)
    db.update_evento(eid, *_ev_fields(b))
    if "num_auto" in b:
        db.set_numeracion(eid, *num)
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
    return jsonr(_prog_rows())


def _prog_rows(eventos=None):
    """Programaciones con próxima fecha, zona, conexiones… (eventos: solo esos ids)."""
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
    conex, nums = {}, {}
    for r in db.get_programacion():
        eid = r["evento_id"]
        if eventos is not None and eid not in eventos:
            continue
        if eid not in conex:
            conex[eid] = db.get_conexiones(eid)
            ev = numeracion.aplicar(db.get_evento(eid) or {})
            nums[eid] = {"num_auto": ev.get("num_auto"), "num": ev.get("num"), "numero": ev.get("numero")}
        r.update(nums[eid])                     # número de edición / emisión
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
    return out


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


@app.route("/api/sesiones/historial")
def sesiones_historial(req):
    from . import historial
    try:
        dias = int(req.query.get("dias") or 1)
    except ValueError:
        dias = 1
    return jsonr(historial.listar(dias, req.query.get("nodo") or ""))


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
    cmd = sessions.action(settings.load(), acc, destino, b.get("modo") or "transceptor", b.get("nodo"),
                          origen="Dashboard · " + req.user["usuario"])
    log.info("Sesiones: %s", cmd)
    return ok(comando=cmd)


# ── Control del nodo IRLP (lo que hacía IRLPvCON) ───────────────────────────
def _irlp_requerido(cfg):
    kind = cfg.get("backend") or "auto"
    if kind == "auto":
        kind = backends.detect()
    if kind != "irlp":
        raise HTTPError(404, "Este nodo no es IRLP")


@app.route("/api/irlp")
def irlp_estado(req):
    from . import irlpctl
    cfg = settings.load()
    _irlp_requerido(cfg)
    return jsonr(irlpctl.estado(cfg))


@app.route("/api/irlp/bitacora")
def irlp_bitacora(req):
    from . import irlpctl
    _irlp_requerido(settings.load())
    try:
        n = int(req.query.get("n") or 100)
    except ValueError:
        n = 100
    return jsonr({"lineas": irlpctl.bitacora(n)})


@app.route("/api/irlp/favoritos", ("PUT",), rol="admin")
def irlp_favoritos(req):
    from . import irlpctl
    _irlp_requerido(settings.load())
    b = req.json()
    favs, cats = irlpctl.guardar_favoritos(b.get("favoritos"), b.get("categorias"))
    log.info("%s guardó %d favoritos de IRLP en %d categorías", req.user["usuario"], len(favs), len(cats))
    return ok(favoritos=favs, categorias=cats)


@app.route("/api/irlp/vcon", rol="admin")
def irlp_vcon_estado(req):
    from . import irlpctl
    _irlp_requerido(settings.load())
    return jsonr(irlpctl.vcon_estado())


@app.route("/api/irlp/vcon", ("POST",), rol="admin")
def irlp_vcon(req):
    from . import irlpctl
    _irlp_requerido(settings.load())
    encender = bool(req.json().get("encender"))
    st = irlpctl.vcon(encender)
    log.info("%s %s IRLPvCON", req.user["usuario"], "encendió" if encender else "apagó")
    return ok(**st)


@app.route("/api/sesiones/buscar")
def sesiones_buscar(req):
    """Buscar nodos en el directorio de AllStar por número, indicativo o lugar."""
    q = str(req.query.get("q") or "")[:40]
    res, total, hay = sessions.search(q)
    return jsonr({"resultados": res, "total": total, "directorio": hay, "max": sessions.BUSCAR_MAX})


@app.route("/api/sesiones/presencia")
def sesiones_presencia(req):
    """¿En línea? responde / registrado (no contesta) / fuera, para ?nodos=1,2,3."""
    from . import presencia
    nodos = [n for n in str(req.query.get("nodos") or "").split(",") if n][:presencia.MAX_NODOS]
    return jsonr({"estados": presencia.estado(nodos)})


@app.route("/api/sesiones/favoritos")
def sesiones_favoritos(req):
    """Favoritos de ASL (los mismos que ofrece el bot; la primera vez se importan de AllScan)."""
    from . import favoritos
    nodo = str(req.query.get("nodo") or settings.get("node") or "")
    favs, cats = favoritos.asl_todo(nodo if re.match(r"^\d{3,7}$", nodo) else "")
    return jsonr({"favoritos": favs, "categorias": cats})


@app.route("/api/sesiones/favoritos", ("PUT",), rol="admin")
def sesiones_favoritos_guardar(req):
    from . import favoritos
    b = req.json()
    favs, cats = favoritos.guardar_asl(b.get("favoritos"), b.get("categorias"))
    log.info("%s guardó %d favoritos de ASL en %d categorías", req.user["usuario"], len(favs), len(cats))
    return ok(favoritos=favs, categorias=cats)


@app.route("/api/irlp/<accion>", ("POST",))
def irlp_accion(req, accion):
    from . import irlpctl
    _irlp_requerido(settings.load())
    if accion not in ("habilitar", "deshabilitar", "dtmf", "timeout", "aux"):
        raise HTTPError(404)
    hecho = irlpctl.accion(accion, req.json().get("valor"))
    with sessions._cache_lock:
        sessions._cache["key"] = None
    log.info("IRLP: %s (%s)", hecho, req.user["usuario"])
    return ok(hecho=hecho)


# ── Ajustes ──────────────────────────────────────────────────────────────────
NUM_KEYS = {"azure_rate": int, "azure_pitch": int, "anuncio_max_seg": int, "anuncio_max_chars": int, "espeak_speed": int, "espeak_pitch": int,
            "google_rate": int, "google_pitch": float, "eleven_stability": int, "eleven_similarity": int,
            "eleven_speed": int,
            "pause_tx_time": float, "pause_duration": float, "pause_alert_before": float,
            "ptt_on_delay": float, "retroceso_secs": float, "section_gap": float,
            "normalize_target": float, "pause_volume": int, "ab_keep": int, "ab_recv_keep": int,
            "tg_recordar_dias": int, "hub_alerta_min": int, "rec_silencio_min": int, "rec_max_min": int,
            "rec_dias": int}
BOOL_KEYS = {"rc_on", "pause_enabled", "retroceso_enabled", "section_normalize", "keep_originals", "keep_previous",
             "tg_enabled", "tg_on_error", "tg_on_preflight", "tg_on_sync", "tg_on_start", "tg_on_end",
             "tg_on_upcoming", "tg_on_section", "tg_on_backup", "tg_on_health", "tg_on_collab", "tg_bot_on", "tg_collab_dm", "ab_tg_on", "hub_on", "tg_on_nodes", "rec_tg", "tg_on_rec", "ab_enabled", "ab_node_on", "ab_cloud_on", "ab_sin_claves_nodo", "ab_sin_claves_nube", "ab_sin_claves_tg", "tts_fallback"}
STR_KEYS = {"backend", "node", "asl_mode", "asl_flush_cmd", "irlp_env", "irlp_key_cmd",
            "irlp_unkey_cmd", "irlp_player", "irlp_mode", "station_name", "tts_engine", "azure_region",
            "azure_voice", "azure_style", "espeak_voice", "tg_chat", "tg_upcoming_mins",
            "google_voice", "eleven_voice", "eleven_voice_name", "eleven_model",
            "ab_hora", "ab_node_url", "ab_node_pin", "ab_cloud_folder", "hub_url", "hub_pin", "rec_auto", "rec_titulo",
            "url_dominios", "url_cafile"}


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
        elif k in ("azure_key", "google_key", "eleven_key", "tg_token", "ab_node_token", "hub_token") and str(v).strip():
            upd[k] = str(v).strip()
    if "tg_upcoming_mins" in upd:
        bad = [x for x in re.split(r"[,;\s]+", upd["tg_upcoming_mins"])
               if x and not (x.isdigit() and 1 <= int(x) <= 1440)]
        if bad:
            raise ValueError("Minutos de aviso inválidos: usa números de 1 a 1440 separados por coma")
        upd["tg_upcoming_mins"] = ", ".join(str(m) for m in notify.upcoming_minutes(upd))
    if "ab_hora" in upd and not re.match(r"^([01]\d|2[0-3]):[0-5]\d$", upd["ab_hora"]):
        raise ValueError("Hora del respaldo inválida (HH:MM)")
    if "rec_titulo" in upd:
        if len(upd["rec_titulo"]) > 120:
            raise ValueError("El título de la grabación es muy largo (máximo 120 caracteres)")
        if not upd["rec_titulo"]:
            from . import grabar
            upd["rec_titulo"] = grabar.TITULO_DEFAULT
    if upd.get("rec_auto") not in (None, "fin", "inicio", "no"):
        raise ValueError("Opción de grabación inválida")
    for k, a, b, txt in (("rec_silencio_min", 1, 60, "Minutos sin actividad: de 1 a 60"),
                         ("rec_max_min", 10, 600, "Duración máxima: de 10 a 600 min"),
                         ("rec_dias", 0, 3650, "Días a conservar: de 0 a 3650")):
        if k in upd and not a <= upd[k] <= b:
            raise ValueError(txt)
    if "hub_alerta_min" in upd and not 0 <= upd["hub_alerta_min"] <= 1440:
        raise ValueError("Minutos para avisar de un nodo: de 0 a 1440")
    if "tg_recordar_dias" in upd and not 0 <= upd["tg_recordar_dias"] <= 14:
        raise ValueError("Días para el recordatorio: de 0 a 14")
    for k in ("ab_keep", "ab_recv_keep"):
        if k in upd and not 1 <= upd[k] <= 60:
            raise ValueError("Copias a conservar: de 1 a 60")
    if upd.get("node") and not re.match(r"^[A-Za-z0-9]{1,10}$", upd["node"]):
        raise ValueError("Número de nodo inválido")
    if upd.get("irlp_mode") not in (None, "red", "local"):
        raise ValueError("Modo IRLP inválido")
    if upd.get("backend") not in (None, "auto", "asl", "irlp", "simulado"):
        raise ValueError("Tipo de nodo inválido")
    if upd.get("url_cafile") and not upd["url_cafile"].startswith("/"):
        raise ValueError("El archivo de certificados va con su ruta completa (p. ej. /etc/ssl/certs/ca-certificates.crt)")
    if "url_dominios" in upd:
        upd["url_dominios"] = ", ".join(x for x in re.split(r"[,\s]+", upd["url_dominios"].lower()) if x)[:400]
    lo, hi = anuncios.MAX_SEG_RANGO
    if "anuncio_max_seg" in upd and not lo <= upd["anuncio_max_seg"] <= hi:
        raise ValueError("Duración máxima de un anuncio: de {} a {} s".format(lo, hi))
    lo, hi = anuncios.MAX_CHARS_RANGO
    if "anuncio_max_chars" in upd and not lo <= upd["anuncio_max_chars"] <= hi:
        raise ValueError("Caracteres máximos de un anuncio: de {} a {}".format(lo, hi))
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
    sin = truthy(req.query.get("sin_claves", "0"))
    nombre = backup.filename(con)
    if sin:
        nombre = nombre.replace(".tar.gz", "-sin-claves.tar.gz")
    gen = backup.stream(con, req.user["usuario"], sin_claves=sin)
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
                  "audios_cambiaron": autobackup.audios_changed(st), "telegram": autobackup.tg_info(cfg)})


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


# ── Grabaciones ─────────────────────────────────────────────────────────────
@app.route("/api/grabaciones")
def grabaciones(req):
    from . import grabar
    return jsonr({"grabaciones": grabar.lista(), "estado": grabar.grabadora.estado(), "envivo": live.status(),
                  "mp3": "mp3" in export.formats()})


@app.route("/api/grabaciones/iniciar", ("POST",))
def grabacion_iniciar(req):
    from . import grabar
    titulo = (req.json().get("titulo") or "").strip() or "Grabación de {}".format(req.user["usuario"].upper())
    st = grabar.grabadora.iniciar(titulo, "a mano · " + req.user["usuario"])
    return ok(estado=st)


@app.route("/api/grabaciones/detener", ("POST",))
def grabacion_detener(req):
    from . import grabar
    r = grabar.grabadora.detener("manual")
    if not r:
        raise ValueError("No se está grabando")
    log.info("%s detuvo la grabación «%s»", req.user["usuario"], r["titulo"])
    return ok()


@app.route("/api/grabaciones/<nombre>")
def grabacion_archivo(req, nombre):
    from . import grabar
    p = grabar.archivo(nombre)
    if not p:
        raise HTTPError(404)
    return send_file(p, "audio/mpeg" if p.suffix == ".mp3" else "audio/wav")


@app.route("/api/grabaciones/titulo", ("POST",))
def grabacion_titulo_prueba(req):
    """Vista previa del título con la plantilla que se está escribiendo (con el próximo evento)."""
    from . import bot, grabar
    ev = {}
    p = bot._proximos(1)
    if p:
        ev = numeracion.aplicar(db.get_evento(p[0][1]["evento_id"]) or {})
    return ok(titulo=grabar.titulo_de(ev, (req.json().get("plantilla") or "").strip() or grabar.TITULO_DEFAULT))


@app.route("/api/grabaciones/<nombre>", ("DELETE",))
def grabacion_borrar(req, nombre):
    from . import grabar
    grabar.borrar(nombre)
    log.info("%s borró la grabación %s", req.user["usuario"], nombre)
    return ok()


# ── Panel de nodos ───────────────────────────────────────────────────────────
@app.route("/api/remoto/latido", ("POST",), auth=False)
def remoto_latido(req):
    """Un nodo reporta su estado al hub (mismo código de acceso que el respaldo)."""
    from . import hub
    if not autobackup.code_check(req.headers.get("X-HAMNA-Backup", "")):
        raise HTTPError(401, "Código de acceso inválido")
    hub.recibir(req.json(), req.ip)
    cfg = settings.load()
    return ok(estacion=cfg.get("station_name") or "", nodo=cfg.get("node") or "", version=VERSION)


@app.route("/api/remoto/control", ("POST",), auth=False)
def remoto_control(req):
    """Un nodo pregunta si hay órdenes para él (y trae los resultados de las anteriores)."""
    from . import control
    fila = autobackup.code_check(req.headers.get("X-HAMNA-Backup", ""))
    if not fila:
        raise HTTPError(401, "Código de acceso inválido")
    try:
        return ok(ordenes=control.atender(fila, req.json(), req.ip), espera=control.ESPERA)
    except PermissionError as e:
        raise HTTPError(403, str(e))


@app.route("/api/nodos/<nodo>/control", rol="admin")
def nodos_control_ver(req, nodo):
    from . import control
    nodo = str(nodo)                 # el enrutador convierte a número lo que es solo dígitos
    info = control.nodos().get(nodo)
    usuarios = [{"id": u["id"], "usuario": u["usuario"], "nombre": u.get("nombre") or "", "rol": u["rol"],
                 "telegram": bool(u.get("tg"))} for u in auth.users() if u.get("activo", 1)]
    return jsonr({"nodo": nodo, "control": info, "permisos": control.permisos(nodo), "usuarios": usuarios})


@app.route("/api/nodos/<nodo>/control", ("PUT",), rol="admin")
def nodos_control_guardar(req, nodo):
    from . import control
    nodo = str(nodo)
    b = req.json()
    p = control.guardar_permisos(nodo, {int(k): int(v) for k, v in (b.get("permisos") or {}).items()})
    log.info("%s cambió quién controla el nodo %s desde el bot", req.user["usuario"], nodo)
    return ok(permisos=p)


@app.route("/api/nodos/<nodo>/control", ("DELETE",), rol="admin")
def nodos_control_olvidar(req, nodo):
    from . import control
    control.olvidar(str(nodo))
    return ok()


@app.route("/api/nodos")
def nodos_panel(req):
    from . import control, hub
    p = hub.panel()
    p["control"] = control.nodos()
    return jsonr(p)


@app.route("/api/nodos/<nodo>", ("DELETE",), rol="admin")
def nodos_quitar(req, nodo):
    from . import hub
    hub.quitar(nodo)
    log.info("%s quitó el nodo %s del panel", req.user["usuario"], nodo)
    return ok()


@app.route("/api/nodos/<nodo>/urls", ("PUT",), rol="admin")
def nodos_urls(req, nodo):
    from . import hub
    b = req.json()
    r = hub.guardar_urls(nodo, b.get("url_int"), b.get("url_ext"))
    log.info("%s cambió las direcciones del dashboard del nodo %s", req.user["usuario"], nodo)
    return ok(**r)


@app.route("/api/hub", rol="admin")
def hub_estado(req):
    from . import hub
    return jsonr(hub.estado_envio())


@app.route("/api/hub/probar", ("POST",), rol="admin")
def hub_probar(req):
    from . import hub
    b = req.json()
    url = (b.get("url") or "").strip()
    codigo = (b.get("codigo") or "").strip()
    d_url, d_tok, _pin = hub.destino()
    url, codigo = url or d_url, codigo or (settings.get("hub_token") if url else "") or d_tok
    if not url or not codigo:
        raise ValueError("Falta la dirección o el código de acceso del hub")
    return ok(**autobackup.probe_node(url, codigo))


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


@app.route("/api/ajustes/password", ("POST",), rol="colaborador")
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


@app.route("/api/google/voces", ("POST",), rol="admin")
def google_voces(req):
    key = (req.json().get("google_key") or settings.load().get("google_key") or "").strip()
    if not key:
        raise ValueError("Escribe la clave de Google")
    try:
        return ok(voces=tts.google_voices(key))
    except Exception as e:
        raise RuntimeError("Google no respondió: {}".format(e))


@app.route("/api/elevenlabs/voces", ("POST",), rol="admin")
def eleven_voces(req):
    key = (req.json().get("eleven_key") or settings.load().get("eleven_key") or "").strip()
    if not key:
        raise ValueError("Escribe la clave de ElevenLabs")
    try:
        return ok(voces=tts.eleven_voices(key))
    except Exception as e:
        raise RuntimeError("ElevenLabs no respondió: {}".format(e))


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
