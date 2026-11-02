"""
HAMNA Web — servidor HTTP (Flask). Compatible con Flask 1.1 (Raspbian 11)
hasta Flask 3 (Debian 13).
"""
from __future__ import annotations

import datetime as dt
import functools
import logging
import os
import re
import secrets
import shutil
import time
import uuid
from pathlib import Path

from flask import Flask, abort, jsonify, request, send_file, session
from werkzeug.security import check_password_hash, generate_password_hash

from . import VERSION, audio, backends, db, paths, settings, tts
from .engine import engine

log = logging.getLogger("hamna.web")

STATIC = Path(__file__).parent / "static"
AUDIO_EXT = {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".aac", ".wma", ".opus", ".gsm", ".ul"}

app = Flask(__name__, static_folder=str(STATIC), static_url_path="/static")
app.config["MAX_CONTENT_LENGTH"] = 300 * 1024 * 1024
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["PERMANENT_SESSION_LIFETIME"] = dt.timedelta(days=30)


def init_app():
    db.init_db()
    cfg = settings.load()
    if not cfg.get("secret_key"):
        cfg = settings.save({"secret_key": secrets.token_hex(32)})
    app.secret_key = cfg["secret_key"]


# ── Utilidades ────────────────────────────────────────────────────────────────
def ok(**kw):
    return jsonify({"ok": True, **kw})


def fail(msg, code=400):
    return jsonify({"ok": False, "error": str(msg)}), code


@app.errorhandler(413)
def too_big(_e):
    return fail("El archivo es demasiado grande (máximo 300 MB)", 413)


def login_required(fn):
    @functools.wraps(fn)
    def wrapper(*a, **kw):
        if not session.get("auth"):
            return fail("Inicia sesión", 401)
        # Defensa CSRF: un formulario de otro sitio no puede mandar esta cabecera
        if request.method not in ("GET", "HEAD") and request.headers.get("X-HAMNA") != "1":
            return fail("Petición rechazada", 403)
        try:
            return fn(*a, **kw)
        except (ValueError, FileNotFoundError, RuntimeError) as e:
            return fail(e)
    return wrapper


def body() -> dict:
    if request.is_json:
        return request.get_json(silent=True) or {}
    return request.form.to_dict()


def safe_name(name: str) -> str:
    stem = Path(name).stem
    stem = re.sub(r"[^A-Za-z0-9_-]+", "_", stem).strip("_")[:50] or "audio"
    return stem


def save_upload(fs, dest_dir: Path, prefix: str) -> Path:
    ext = Path(fs.filename or "").suffix.lower()
    if ext not in AUDIO_EXT:
        raise ValueError(f"Formato no soportado ({ext or 'sin extensión'}). Usa MP3, WAV, M4A, OGG o FLAC")
    dest = dest_dir / f"{prefix}_{safe_name(fs.filename)}{ext}"
    fs.save(str(dest))
    if audio.duration(dest) <= 0:
        dest.unlink(missing_ok=True)
        raise ValueError("No pude leer el audio; ¿está dañado el archivo?")
    return dest


def truthy(v) -> bool:
    return str(v).lower() in ("1", "true", "on", "yes", "si", "sí")


# ── Páginas y sesión ─────────────────────────────────────────────────────────
@app.route("/")
def index():
    return send_file(str(STATIC / "index.html"))


@app.route("/api/login", methods=["POST"])
def login():
    pw = (body().get("password") or "")
    h = settings.get("password_hash")
    if not h:
        return fail("Aún no hay contraseña. Ejecuta: sudo hamna-web-passwd", 403)
    if not check_password_hash(h, pw):
        time.sleep(1.5)
        return fail("Contraseña incorrecta", 401)
    session.permanent = True
    session["auth"] = True
    return ok()


@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return ok()


@app.route("/api/me")
def me():
    return jsonify({"auth": bool(session.get("auth")), "version": VERSION,
                    "station": settings.get("station_name") or ""})


# ── Estado e información ─────────────────────────────────────────────────────
@app.route("/api/status")
@login_required
def status():
    s = engine.status()
    s["now"] = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    s["utc"] = dt.datetime.utcnow().strftime("%H:%M")
    return jsonify(s)


@app.route("/api/info")
@login_required
def info():
    cfg = settings.load()
    be = backends.make(cfg)
    du = shutil.disk_usage(str(paths.data_dir()))
    tz = time.strftime("%Z")
    try:
        tz = Path("/etc/timezone").read_text().strip() or tz
    except Exception:
        try:
            tz = os.path.realpath("/etc/localtime").split("zoneinfo/")[-1]
        except Exception:
            pass
    return jsonify({
        "version": VERSION, "backend": be.info(), "detectado": backends.detect(),
        "nodo_detectado": backends.detect_asl_node(),
        "zona_horaria": tz, "disco_libre_mb": du.free // 2**20,
        "ffmpeg": audio.ffmpeg_ok(), "piper": tts.piper_available(),
        "espeak": bool(shutil.which("espeak-ng") or shutil.which("espeak")),
        "variables": tts.VARIABLES,
        "historial": db.get_historial(15),
    })


# ── Secciones ────────────────────────────────────────────────────────────────
def _sec_out(s):
    s = dict(s)
    s["tiene_audio"] = bool(s.get("ruta_archivo")) and (paths.audios_dir() / s["ruta_archivo"]).is_file()
    return s


@app.route("/api/secciones")
@login_required
def secciones():
    return jsonify([_sec_out(s) for s in db.get_secciones()])


def _apply_section(sid: int, form, files, tipo: str, is_new: bool):
    fields = {}
    for k in ("nombre", "titulo", "descripcion", "texto_tts"):
        if k in form:
            fields[k] = form[k].strip()
    if "regenerar_antes" in form:
        fields["regenerar_antes"] = truthy(form["regenerar_antes"])
    if "nombre" in fields and not fields["nombre"]:
        raise ValueError("La sección necesita un nombre")
    fs = files.get("archivo")
    old = db.get_seccion(sid)
    if fs and fs.filename:
        dest = save_upload(fs, paths.audios_dir(), f"{sid}")
        fields["ruta_archivo"] = dest.name
        fields["duracion"] = audio.duration(dest)
        if old and old.get("ruta_archivo") and old["ruta_archivo"] != dest.name:
            (paths.audios_dir() / old["ruta_archivo"]).unlink(missing_ok=True)
    db.update_seccion(sid, **fields)
    if tipo == "TTS" and (truthy(form.get("generar", "0")) or is_new):
        _generate_tts(sid)


def _generate_tts(sid: int):
    s = db.get_seccion(sid)
    if not s or not (s.get("texto_tts") or "").strip():
        return
    cfg = settings.load()
    ctx = {"titulo": s.get("titulo") or s["nombre"], "descripcion": s.get("descripcion") or ""}
    src = tts.synthesize(s["texto_tts"], cfg, paths.tmp_dir() / f"tts_{uuid.uuid4().hex[:8]}", ctx)
    dest = paths.audios_dir() / f"{sid}_{safe_name(s['nombre'])}{src.suffix}"
    shutil.move(str(src), str(dest))
    if s.get("ruta_archivo") and s["ruta_archivo"] != dest.name:
        (paths.audios_dir() / s["ruta_archivo"]).unlink(missing_ok=True)
    db.update_seccion(sid, nombre=s["nombre"], ruta_archivo=dest.name, duracion=audio.duration(dest))


@app.route("/api/secciones", methods=["POST"])
@login_required
def seccion_new():
    f = request.form
    tipo = f.get("tipo", "Audio")
    if tipo not in ("TTS", "Audio", "Sonido"):
        raise ValueError("Tipo inválido")
    nombre = (f.get("nombre") or "").strip()
    if not nombre:
        raise ValueError("La sección necesita un nombre")
    if tipo != "TTS" and not (request.files.get("archivo") and request.files["archivo"].filename):
        raise ValueError("Sube un archivo de audio")
    if tipo == "TTS" and not (f.get("texto_tts") or "").strip():
        raise ValueError("Escribe el texto a sintetizar")
    sid = db.insert_seccion(nombre, tipo)
    try:
        _apply_section(sid, f, request.files, tipo, True)
    except Exception:
        db.delete_seccion(sid)
        raise
    return ok(seccion=_sec_out(db.get_seccion(sid)))


@app.route("/api/secciones/<int:sid>", methods=["POST"])
@login_required
def seccion_edit(sid):
    s = db.get_seccion(sid)
    if not s:
        abort(404)
    _apply_section(sid, request.form, request.files, s["tipo"], False)
    return ok(seccion=_sec_out(db.get_seccion(sid)))


@app.route("/api/secciones/<int:sid>", methods=["DELETE"])
@login_required
def seccion_del(sid):
    s = db.get_seccion(sid)
    if s:
        if s.get("ruta_archivo"):
            (paths.audios_dir() / s["ruta_archivo"]).unlink(missing_ok=True)
        db.delete_seccion(sid)
    return ok()


@app.route("/api/secciones/<int:sid>/audio")
@login_required
def seccion_audio(sid):
    s = db.get_seccion(sid)
    if not s or not s.get("ruta_archivo"):
        abort(404)
    p = paths.audios_dir() / s["ruta_archivo"]
    if not p.is_file():
        abort(404)
    if p.suffix.lower() in (".mp3", ".wav", ".ogg", ".m4a", ".opus", ".flac", ".aac"):
        return send_file(str(p), conditional=True)
    return send_file(str(audio.to_mp3_preview(p)), mimetype="audio/mpeg")


@app.route("/api/secciones/<int:sid>/aire", methods=["POST"])
@login_required
def seccion_aire(sid):
    s = db.get_seccion(sid)
    if not s or not s.get("ruta_archivo"):
        raise ValueError("La sección no tiene audio")
    engine.play_single(paths.audios_dir() / s["ruta_archivo"], s["nombre"])
    return ok()


@app.route("/api/tts/preview", methods=["POST"])
@login_required
def tts_preview():
    b = body()
    text = (b.get("texto") or "").strip()
    if not text:
        raise ValueError("Escribe algún texto")
    cfg = settings.load()
    ctx = {"titulo": b.get("titulo") or "", "descripcion": b.get("descripcion") or "",
           "evento": "Evento de prueba", "numero": "1"}
    src = tts.synthesize(text, cfg, paths.tmp_dir() / f"preview_{uuid.uuid4().hex[:8]}", ctx)
    return ok(url=f"/api/tmp/{src.name}", texto=tts.resolve_variables(text, cfg, ctx))


@app.route("/api/tmp/<name>")
@login_required
def tmp_file(name):
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", name):
        abort(404)
    p = paths.tmp_dir() / name
    if not p.is_file():
        abort(404)
    return send_file(str(p), conditional=True)


# ── Eventos ──────────────────────────────────────────────────────────────────
@app.route("/api/eventos")
@login_required
def eventos():
    return jsonify({"eventos": db.get_eventos(), "tipos": db.get_eventos_types()})


@app.route("/api/eventos/<int:eid>")
@login_required
def evento(eid):
    ev = db.get_evento(eid)
    if not ev:
        abort(404)
    ev["secciones"] = [_sec_out(s) for s in db.get_secciones_by_evento(eid)]
    return jsonify(ev)


def _ev_fields(b):
    nombre = (b.get("nombre") or "").strip()
    if not nombre:
        raise ValueError("El evento necesita un nombre")
    tipo = b.get("tipo_evento_id") or None
    numero = b.get("numero")
    numero = int(numero) if str(numero or "").strip().isdigit() else None
    return nombre, (int(tipo) if tipo else None), numero


@app.route("/api/eventos", methods=["POST"])
@login_required
def evento_new():
    eid = db.insert_evento(*_ev_fields(body()))
    return ok(id=eid)


@app.route("/api/eventos/<int:eid>", methods=["PUT"])
@login_required
def evento_edit(eid):
    db.update_evento(eid, *_ev_fields(body()))
    return ok()


@app.route("/api/eventos/<int:eid>", methods=["DELETE"])
@login_required
def evento_del(eid):
    if engine.busy() and engine.st.get("evento_id") == eid:
        raise ValueError("No se puede borrar un evento que está al aire")
    db.delete_evento(eid)
    return ok()


@app.route("/api/eventos/<int:eid>/secciones", methods=["POST"])
@login_required
def evento_add_sec(eid):
    for sid in body().get("ids", []):
        db.add_seccion_to_evento(eid, int(sid))
    return ok()


@app.route("/api/eventos/<int:eid>/secciones/<int:sid>", methods=["DELETE"])
@login_required
def evento_rm_sec(eid, sid):
    db.remove_seccion_from_evento(eid, sid)
    return ok()


@app.route("/api/eventos/<int:eid>/orden", methods=["PUT"])
@login_required
def evento_orden(eid):
    db.set_orden_evento(eid, [int(x) for x in body().get("ids", [])])
    return ok()


@app.route("/api/eventos/<int:eid>/secciones/<int:sid>/contabilizable", methods=["PUT"])
@login_required
def evento_cont(eid, sid):
    db.set_contabilizable(eid, sid, bool(body().get("value")))
    return ok()


# ── Programación ─────────────────────────────────────────────────────────────
@app.route("/api/programacion")
@login_required
def programacion():
    out = []
    now = dt.datetime.now()
    for r in db.get_programacion():
        nxt = engine.next_run(r, now) if r["activo"] else None
        r["proxima"] = nxt.strftime("%Y-%m-%d %H:%M") if nxt else None
        r["faltan_s"] = int((nxt - now).total_seconds()) if nxt else None
        out.append(r)
    out.sort(key=lambda r: (r["faltan_s"] is None, r["faltan_s"] or 0))
    return jsonify(out)


def _prog_fields(b):
    eid = int(b.get("evento_id") or 0)
    if not db.get_evento(eid):
        raise ValueError("Elige un evento")
    fecha = (b.get("fecha") or "").strip()
    hora = (b.get("hora") or "").strip()[:5]
    rec = b.get("recurrencia") or "ninguna"
    dt.date.fromisoformat(fecha)
    if not re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", hora):
        raise ValueError("Hora inválida (HH:MM)")
    if rec not in ("ninguna", "diaria", "semanal", "lun-vie"):
        raise ValueError("Recurrencia inválida")
    return eid, fecha, hora, rec, b.get("activo", True) not in (False, 0, "0", "false")


@app.route("/api/programacion", methods=["POST"])
@login_required
def prog_new():
    return ok(id=db.insert_programacion(*_prog_fields(body())))


@app.route("/api/programacion/<int:pid>", methods=["PUT"])
@login_required
def prog_edit(pid):
    db.update_programacion(pid, *_prog_fields(body()))
    return ok()


@app.route("/api/programacion/<int:pid>", methods=["DELETE"])
@login_required
def prog_del(pid):
    db.delete_programacion(pid)
    return ok()


# ── Control de transmisión ───────────────────────────────────────────────────
@app.route("/api/tx/start", methods=["POST"])
@login_required
def tx_start():
    engine.start_event(int(body().get("evento_id") or 0), origen="manual")
    return ok()


@app.route("/api/tx/<cmd>", methods=["POST"])
@login_required
def tx_cmd(cmd):
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
BOOL_KEYS = {"pause_enabled", "retroceso_enabled", "section_normalize"}
STR_KEYS = {"backend", "node", "asl_mode", "irlp_env", "irlp_key_cmd", "irlp_unkey_cmd",
            "irlp_player", "station_name", "tts_engine", "azure_region", "azure_voice",
            "azure_style", "espeak_voice"}


@app.route("/api/ajustes")
@login_required
def ajustes():
    return jsonify(settings.public())


@app.route("/api/ajustes", methods=["PUT"])
@login_required
def ajustes_save():
    b = body()
    upd = {}
    for k, v in b.items():
        if k in NUM_KEYS:
            upd[k] = NUM_KEYS[k](float(v))
        elif k in BOOL_KEYS:
            upd[k] = bool(v) if isinstance(v, bool) else truthy(v)
        elif k in STR_KEYS:
            upd[k] = str(v).strip()
        elif k == "azure_key" and str(v).strip():
            upd[k] = str(v).strip()
    if "node" in upd and upd["node"] and not re.fullmatch(r"[A-Za-z0-9]{1,10}", upd["node"]):
        raise ValueError("Número de nodo inválido")
    if upd.get("backend") not in (None, "auto", "asl", "irlp", "simulado"):
        raise ValueError("Tipo de nodo inválido")
    settings.save(upd)
    return ok(ajustes=settings.public())


PAUSE_KINDS = {"alerta": "pause_alert_file", "pausa": "pause_announcement_file",
               "continuamos": "pause_resume_file"}


@app.route("/api/ajustes/sonido/<kind>", methods=["POST", "DELETE", "GET"])
@login_required
def ajustes_sonido(kind):
    key = PAUSE_KINDS.get(kind)
    if not key:
        abort(404)
    cur = settings.get(key) or ""
    if request.method == "GET":
        p = paths.sonidos_dir() / cur if cur else None
        if not p or not p.is_file():
            abort(404)
        return send_file(str(p), conditional=True)
    if cur:
        (paths.sonidos_dir() / cur).unlink(missing_ok=True)
    if request.method == "DELETE":
        settings.save({key: ""})
        return ok()
    fs = request.files.get("archivo")
    if not fs or not fs.filename:
        raise ValueError("Elige un archivo")
    dest = save_upload(fs, paths.sonidos_dir(), kind)
    settings.save({key: dest.name})
    return ok(nombre=dest.name)


@app.route("/api/ajustes/password", methods=["POST"])
@login_required
def ajustes_password():
    b = body()
    if not check_password_hash(settings.get("password_hash"), b.get("actual") or ""):
        raise ValueError("La contraseña actual no coincide")
    nueva = b.get("nueva") or ""
    if len(nueva) < 6:
        raise ValueError("La contraseña nueva debe tener al menos 6 caracteres")
    settings.save({"password_hash": generate_password_hash(nueva, method="pbkdf2:sha256")})
    return ok()


@app.route("/api/azure/voces", methods=["POST"])
@login_required
def azure_voces():
    cfg = settings.load()
    b = body()
    key = (b.get("azure_key") or cfg.get("azure_key") or "").strip()
    region = (b.get("azure_region") or cfg.get("azure_region") or "").strip()
    if not key or not region:
        raise ValueError("Escribe la clave y la región de Azure")
    try:
        return ok(voces=tts.azure_voices(key, region))
    except Exception as e:
        raise RuntimeError(f"Azure no respondió: {e}")


@app.route("/api/prueba/nodo", methods=["POST"])
@login_required
def prueba_nodo():
    good, msg = backends.make(settings.load()).test()
    return jsonify({"ok": good, "mensaje": msg})


@app.route("/api/prueba/aire", methods=["POST"])
@login_required
def prueba_aire():
    cfg = settings.load()
    text = (body().get("texto") or "").strip() or \
        "Prueba de HAMNA Web. Son las {hora} del {dia} {fecha_larga}."
    src = tts.synthesize(text, cfg, paths.tmp_dir() / f"prueba_{uuid.uuid4().hex[:8]}")
    engine.play_single(src, "Prueba de transmisión")
    return ok()
