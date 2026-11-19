"""
HAMNA Web — el bot de Telegram también escucha.

Un hilo le pregunta a Telegram por mensajes nuevos (getUpdates con espera
larga: casi no gasta), así funciona detrás del módem sin abrir puertos.

  Vincular   en «Mi perfil» se pide un código de 6 dígitos (10 min); el usuario
             se lo manda al bot (/start CÓDIGO o /vincular CÓDIGO) y su Telegram
             queda ligado a su usuario de HAMNA.
  Consultas  /estado /proximo (todos) · /salud /historial (lectura en adelante)
  Botones    en los avisos «Inicia…» (⏭ siguiente, ⏹ detener) y «Sale en N min»
             (▶ transmitir ya, ⏸ saltar esta vez); solo operador o admin, y
             siempre con confirmación.
  Colaboración  en el menú: eventos → secciones → mandar audio nuevo, cambiar el
             texto a voz, escuchar o regresar a la anterior; el operador y el
             admin además agregan secciones nuevas al evento.

A quien no está vinculado solo se le explica cómo vincularse.
"""
import datetime as dt
import json
import logging
import os
import random
import threading
import time
import urllib.request
import uuid

from . import audio, auth, db, health, notify, numeracion, paths, settings, sysmon

log = logging.getLogger("hamna.bot")

CODE_SECS = 10 * 60
_rand = random.SystemRandom()
_lock = threading.Lock()
_codes = {}                     # código → (usuario_id, vence)
_estado = {"activo": False, "error": "", "bot": "", "chats": {}, "token": ""}
_pend = {}                      # audios recibidos esperando «¿en cuál sección?» → datos
MAX_BAJAR = 20 * 1024 * 1024    # Telegram no deja que un bot baje archivos más grandes
_tick = {"t": 0.0}
# El menú ☰ de Telegram solo lleva estas dos; todo lo demás está en los botones
# del menú (los comandos /estado, /grabar… siguen funcionando si se escriben).
_COMANDOS = [
    ("menu", "Menú con botones"),
    ("start", "Iniciar"),
]
DIAS = ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"]


# ── Estado / vinculación ────────────────────────────────────────────────────
def activo():
    """¿El bot está escuchando? (si no, los botones no tendrían quién los atienda)"""
    return bool(_estado["activo"])


def estado():
    return {"activo": _estado["activo"], "error": _estado["error"], "bot": _estado["bot"]}


def chats_vistos():
    return list(_estado["chats"].values())


def nuevo_codigo(uid):
    if not activo():
        raise ValueError("El bot de Telegram no está escuchando en este nodo "
                         "(el administrador lo activa en Ajustes → Avisos)")
    now = time.time()
    with _lock:
        for c in [c for c, (_u, t) in _codes.items() if t < now or _u == uid]:
            del _codes[c]
        code = "{:06d}".format(_rand.randint(0, 999999))
        while code in _codes:
            code = "{:06d}".format(_rand.randint(0, 999999))
        _codes[code] = (uid, now + CODE_SECS)
    bot = _estado["bot"]
    return {"codigo": code, "bot": "@" + bot if bot else "",
            "enlace": "https://t.me/{}?start={}".format(bot, code) if bot else "",
            "minutos": CODE_SECS // 60}


def _usar_codigo(code):
    now = time.time()
    with _lock:
        v = _codes.pop(code, None)
    if not v or v[1] < now:
        return None
    return v[0]


# ── Hilo que escucha ────────────────────────────────────────────────────────
def start():
    threading.Thread(target=_loop, name="hamna-bot", daemon=True).start()


def _offset_file():
    return paths.data_dir() / "bot.json"


def _leer_offset():
    try:
        return int(json.loads(_offset_file().read_text()).get("offset") or 0)
    except Exception:
        return 0


def _guardar_offset(off):
    try:
        tmp = _offset_file().with_suffix(".tmp")
        tmp.write_text(json.dumps({"offset": off}))
        tmp.replace(_offset_file())
    except Exception:
        pass


def _loop():
    off = _leer_offset()
    avisado = ""
    while True:
        cfg = settings.load()
        token = (cfg.get("tg_token") or "").strip()
        if not (cfg.get("tg_enabled") and token and cfg.get("tg_bot_on", True)):
            _estado.update(activo=False, error="")
            time.sleep(15)
            continue
        try:
            if _estado["token"] != token:
                me = notify._call(token, "getMe", {})
                _estado.update(bot=(me or {}).get("username", ""), token=token, chats={})
                try:
                    notify._call(token, "setMyCommands", {"commands": json.dumps(
                        [{"command": c, "description": d} for c, d in _COMANDOS])})
                except Exception:
                    pass
            ups = notify._call(token, "getUpdates", {
                "offset": off, "timeout": 25,
                "allowed_updates": json.dumps(["message", "callback_query", "my_chat_member"])}, timeout=40)
            _estado.update(activo=True, error="")
            avisado = ""
            for u in ups or []:
                off = max(off, int(u.get("update_id", 0)) + 1)
                _guardar_offset(off)
                try:
                    _atender(token, u)
                except Exception:
                    log.exception("El bot no pudo atender un mensaje")
        except Exception as e:
            msg = str(e)
            if "Conflict" in msg:
                err = ("Otro programa está usando este mismo bot (¿otro nodo con el mismo token?). "
                       "Solo un nodo puede responder; apaga «Responder comandos» en los demás.")
            elif "Unauthorized" in msg or "Not Found" in msg:
                err = "Telegram no reconoce el token del bot"
            else:
                err = msg
            _estado.update(activo=False, error=err)
            if err != avisado:
                log.warning("Bot de Telegram: %s", err)
                avisado = err
            time.sleep(30 if "Conflict" in msg else 10)


# ── Atender mensajes y botones ──────────────────────────────────────────────
def _responder(token, chat, texto, botones=None, a=None, markup=None):
    p = {"chat_id": chat, "text": texto, "parse_mode": "HTML", "disable_web_page_preview": "true"}
    if a:
        p["reply_to_message_id"] = a
    if botones:
        p["reply_markup"] = teclado(botones)
    elif markup:
        p["reply_markup"] = markup
    notify._call(token, "sendMessage", p)


def teclado(filas):
    return json.dumps({"inline_keyboard": [[{"text": t, "callback_data": d} for t, d in fila] for fila in filas]})


def _indicativo(u):
    """Para saludar: el usuario de HAMNA es el indicativo (xe2mbe → XE2MBE)."""
    return ((u or {}).get("usuario") or (u or {}).get("nombre") or "").upper()


def _nivel(u):
    return auth.ROLES.get((u or {}).get("rol"), -1)


def _atender(token, u):
    m = u.get("message")
    if u.get("my_chat_member"):
        m = u["my_chat_member"]
    if m and m.get("chat"):
        c = m["chat"]
        nombre = c.get("title") or " ".join(x for x in (c.get("first_name"), c.get("last_name")) if x) \
            or c.get("username") or str(c["id"])
        _estado["chats"][str(c["id"])] = {"id": str(c["id"]), "nombre": nombre, "tipo": c.get("type", "")}
    if u.get("callback_query"):
        return _boton(token, u["callback_query"])
    if not u.get("message"):
        return
    m = u["message"]
    if m.get("date") and time.time() - float(m["date"]) > 600:
        return                                      # mensaje viejo (de antes de que el bot escuchara)
    texto = (m.get("text") or "").strip()
    chat = m["chat"]["id"]
    privado = m["chat"].get("type") == "private"
    quien = m.get("from") or {}
    if privado and (m.get("audio") or m.get("voice") or m.get("document")):
        return _audio_recibido(token, m, auth.user_by_tg(quien.get("id")))
    if not texto:
        return
    if privado and not texto.startswith("/") and texto != "📋 Menú":
        esp = _espera_de(quien.get("id"))
        user = auth.user_by_tg(quien.get("id")) if esp else None
        if esp and user:                            # «Colaboración»: estaba esperando un texto
            return _texto_recibido(token, m, user, texto, esp)
    if texto.startswith("/"):
        partes = texto.split(None, 1)
        cmd, _, para = partes[0][1:].partition("@")
        if para and _estado["bot"] and para.lower() != _estado["bot"].lower():
            return                                  # era para otro bot del grupo
        cmd = cmd.lower()
        arg = partes[1].strip() if len(partes) > 1 else ""
    elif privado and texto.isdigit() and len(texto) == 6:
        cmd, arg = "vincular", texto
    elif privado:
        cmd, arg = "menu", ""                         # «📋 Menú» o cualquier texto: el menú
    else:
        return                                      # conversación normal del grupo
    if cmd in ("start", "vincular") and arg:
        return _vincular(token, chat, quien, arg, m.get("message_id"))
    user = auth.user_by_tg(quien.get("id"))
    if not user:
        return _responder(token, chat, (
            "👋 Hola. Todavía no sé quién eres.\n\n"
            "Entra a HAMNA → <b>Mi perfil</b> (clic en tu foto o nombre) → <b>🔗 Vincular Telegram</b>, "
            "y mándame el código que te da."), a=None if privado else m.get("message_id"))
    if cmd in ("menu", "start"):
        _espera_quitar(quien.get("id"))
        if privado and cmd == "start":
            _responder(token, chat, "👋 Hola, <b>{}</b>. Abajo tienes el botón <b>📋 Menú</b> para abrirlo cuando quieras.".format(
                notify.esc(_indicativo(user))), markup=TECLADO_FIJO)
        texto, botones = _pantalla("menu", user)
        return _responder(token, chat, texto, botones=botones, a=None if privado else m.get("message_id"))
    resp = _comando(cmd, user, arg, chat)
    if isinstance(resp, tuple):
        resp, botones = resp
    else:
        botones = None
    if resp:
        _responder(token, chat, resp, botones=botones, a=None if privado else m.get("message_id"))


def _vincular(token, chat, quien, code, msg_id):
    uid = _usar_codigo(code.strip())
    if not uid:
        return _responder(token, chat, "❌ Ese código no existe o ya venció. Pide uno nuevo en HAMNA → Mi perfil.")
    tg_nombre = "@" + quien["username"] if quien.get("username") else \
        " ".join(x for x in (quien.get("first_name"), quien.get("last_name")) if x)
    auth.set_tg(uid, str(quien.get("id")), tg_nombre)
    u = auth.user_by_tg(quien.get("id")) or {}
    log.info("Telegram %s vinculado con el usuario %s", tg_nombre, u.get("usuario"))
    _responder(token, chat, "✅ Listo, <b>{}</b>. Tu Telegram quedó vinculado con tu usuario de HAMNA ({}).\n\n"
                            "Usa el botón <b>📋 Menú</b> de abajo para ver todo lo que puedo hacer.".format(
        notify.esc(_indicativo(u)), notify.esc(u.get("rol_nombre"))), markup=TECLADO_FIJO)
    texto, botones = _pantalla("menu", u)
    _responder(token, chat, texto, botones=botones)


def _ayuda(user):
    n = _nivel(user)
    t = ["<b>Lo que puedo hacer</b>",
         "/estado · qué está al aire ahora",
         "/proximo · los siguientes eventos"]
    if n >= auth.ROLES["lectura"]:
        t += ["/salud · temperatura, voltaje, disco y memoria", "/historial · las últimas emisiones",
              "/nodos · cómo están los nodos que reportan a este hub"]
    if _es_admin(user):
        t += ["", "📲 <b>Mándame un audio o nota de voz</b> y te pregunto en qué sección lo pongo "
                  "(cualquiera; primero te ofrezco las de los próximos eventos)."]
    elif _secciones_audio(user):
        t += ["", "📲 <b>Mándame un audio o nota de voz</b> y lo pongo en tu sección ({}).".format(
            ", ".join("«" + notify.esc(s["nombre"]) + "»" for s in _secciones_audio(user)))]
    if _gestor(user):
        t += ["", "🤝 <b>Colaboración</b> (en el menú): las secciones de cada evento; ahí cambias el audio o el "
                  "texto de cualquiera, la escuchas o agregas una sección nueva al evento."]
    elif auth.user_sections(user["id"]):
        t += ["", "🤝 <b>Colaboración</b> (en el menú): tus secciones por evento; ahí cambias su audio o "
                  "su texto, las escuchas o regresas a la versión anterior."]
    if n >= auth.ROLES["operador"]:
        t += ["/grabar · empezar a grabar lo que se escucha en el nodo (/grabar Toma de reportes le pone título)"]
        t += ["", "En los avisos te pongo botones para <b>detener</b>, pasar a la <b>siguiente sección</b>, "
                  "<b>transmitir ya</b> o <b>saltar</b> una emisión (siempre te pido confirmar)."]
    return "\n".join(t)


def _comando(cmd, user, arg="", chat=None):
    n = _nivel(user)
    if cmd == "grabar":
        return _grabar(user, arg, chat)
    if cmd in ("ayuda", "help", "start"):
        return _ayuda(user)
    if cmd == "estado":
        return _txt_estado()
    if cmd in ("proximo", "próximo", "proximos"):
        return _txt_proximo(user)
    if cmd in ("salud", "historial", "nodos"):
        if n < auth.ROLES["lectura"]:
            return "Ese comando no está disponible para tu usuario."
        return _txt_salud() if cmd == "salud" else _txt_historial() if cmd == "historial" else _txt_nodos()
    return "No conozco ese comando.\n\n" + _ayuda(user)


def _grabar(user, arg, chat):
    if _nivel(user) < auth.ROLES["operador"]:
        return "Solo un operador o el administrador pueden poner a grabar el nodo."
    from . import grabar
    e = grabar.grabadora.estado()
    parar = [[("⏹ Detener grabación", "rstop:0")]]
    if e.get("grabando"):
        return ("⏺ Ya se está grabando «{}» · lleva {}{}".format(
            notify.esc(e["titulo"]), _hm(e["dur"]),
            " · sin actividad desde hace {}, se detiene en {}".format(_hm(e["silencio"]), _hm(e["faltan"]))
            if e["silencio"] > 15 else ""), parar)
    titulo = (arg or "").strip()[:120] or "Grabación de {}".format(_indicativo(user))
    try:
        grabar.grabadora.iniciar(titulo, "Telegram · " + user["usuario"])
    except ValueError as ex:
        return str(ex)
    if str(chat) == str(settings.load().get("tg_chat") or "") and settings.load().get("tg_on_rec", True):
        return None                                 # el aviso de «empezó a grabar» ya llega a este chat
    return ("⏺ Listo, grabando «{}». Se detiene sola tras {} min sin actividad.".format(
        notify.esc(titulo), int(settings.load().get("rec_silencio_min", 5) or 5)), parar)


# ── Textos de las consultas ─────────────────────────────────────────────────
def _hm(s):
    s = int(max(0, s or 0))
    h, r = divmod(s, 3600)
    return "{}:{:02d}:{:02d}".format(h, r // 60, r % 60) if h else "{}:{:02d}".format(r // 60, r % 60)


def _falta(seg):
    seg = int(max(0, seg))
    d, r = divmod(seg, 86400)
    h, r = divmod(r, 3600)
    m = r // 60
    if d:
        return "{} d {} h".format(d, h)
    if h:
        return "{} h {} min".format(h, m)
    return "{} min".format(max(1, m))


def _cuando(t):
    return "{} {:02d}/{:02d} {}".format(DIAS[t.weekday()], t.day, t.month, t.strftime("%H:%M"))


def _txt_estado():
    from .engine import engine
    s = engine.status()
    if not s.get("on_air"):
        t = "⚪ <b>Fuera del aire</b>"
        prox = _proximos(1)
        if prox:
            t += "\nLo que sigue: " + _linea_proximo(*prox[0])
        return t
    secs = s.get("secciones") or []
    i = s.get("cur_sec", -1)
    t = ["🔴 <b>Al aire:</b> {}".format(notify.esc(s.get("evento") or "prueba"))]
    if s.get("origen"):
        t.append("Origen: " + notify.esc(s["origen"]))
    if 0 <= i < len(secs):
        t.append("Sección {}/{}: <b>{}</b>".format(i + 1, len(secs), notify.esc(secs[i]["nombre"])))
    if s.get("state") in ("paused", "manual_pause"):
        t.append("⏸ En pausa" + (" · faltan {} s".format(s["countdown"]) if s.get("countdown") is not None else ""))
    if s.get("total"):
        t.append("⏱ {} de {} · faltan ~{}".format(_hm(s.get("elapsed")), _hm(s["total"]),
                                                   _hm(s["total"] - (s.get("elapsed") or 0))))
    return "\n".join(t)


def _proximos(n, eventos=None):
    from .engine import engine
    now = dt.datetime.now()
    out = []
    for row in db.get_programacion(solo_activos=True):
        if eventos is not None and row["evento_id"] not in eventos:
            continue
        try:
            t = engine.next_run(row, now)
        except Exception:
            t = None
        if t:
            out.append((t, row))
    out.sort(key=lambda x: x[0])
    return out[:n]


def _linea_proximo(t, row):
    ev = numeracion.aplicar(db.get_evento(row["evento_id"]) or {})
    etq = numeracion.etiqueta(ev) if ev.get("num") or ev.get("numero") else ""
    return "<b>{}</b>{} · {} (en {})".format(notify.esc(row.get("evento_nombre") or ev.get("nombre")),
                                             " " + notify.esc(etq) if etq else "", _cuando(t),
                                             _falta((t - dt.datetime.now()).total_seconds()))


def _eventos_de(user):
    ids = auth.user_sections(user["id"])
    if not ids:
        return set()
    q = ",".join("?" * len(ids))
    return {r["evento_id"] for r in db.rows(
        "SELECT DISTINCT evento_id FROM evento_secciones WHERE seccion_id IN (" + q + ")", ids)}


def _txt_proximo(user):
    eventos = _eventos_de(user) if _nivel(user) < auth.ROLES["lectura"] else None
    prox = _proximos(6, eventos)
    if not prox:
        return "No hay nada programado en los próximos días."
    return "📅 <b>Próximos eventos</b>\n" + "\n".join("• " + _linea_proximo(t, r) for t, r in prox)


def _txt_salud():
    st = health.status()
    ico = {"ok": "✅", "nd": "➖", "aviso": "⚠️", "grave": "❌"}
    t = ["🩺 <b>Salud del nodo</b>"]
    for c in st.get("checks") or []:
        t.append("{} {}: {}".format(ico.get(c["nivel"], "•"), notify.esc(c["nombre"]), notify.esc(c["detalle"])))
    if not st.get("checks"):
        t.append("La revisión completa (SD, voltaje, temperatura) se hace un minuto después de arrancar.")
    s = sysmon.snapshot()
    extra = []
    if s.get("cpu") is not None:
        extra.append("CPU {}%".format(s["cpu"]))
    if s.get("temp") is not None:
        extra.append("{} °C".format(s["temp"]))
    m = s.get("mem") or {}
    if m.get("total"):
        extra.append("RAM {}%".format(int(round(100.0 * m.get("usada", 0) / m["total"]))))
    d = s.get("disco") or {}
    if d.get("total"):
        extra.append("disco {}%".format(int(round(100.0 * d.get("usada", 0) / d["total"]))))
    if s.get("encendido_s"):
        extra.append("encendido hace " + _falta(s["encendido_s"]))
    if extra:
        t += ["", " · ".join(extra)]
    return "\n".join(t)


def _txt_nodos():
    from . import hub
    p = hub.panel()
    if not p["nodos"]:
        return "Ningún nodo reporta a este hub todavía (en cada nodo: Ajustes → Nodo → Panel de nodos)."
    lim = (p["alerta_min"] or 10) * 60
    t = ["🗺 <b>Nodos</b>"]
    for d in p["nodos"]:
        ico = "🟢" if d["edad"] < 180 else "🟡" if d["edad"] < lim else "🔴"
        nombre = notify.esc(d.get("estacion") or "") + " · " if d.get("estacion") else ""
        linea = "{} {}nodo {}".format(ico, nombre, notify.esc(d["nodo"]))
        if d["edad"] >= 180:
            linea += " · sin reportar desde hace " + _falta(d["edad"])
        elif d.get("al_aire"):
            linea += " · 🔴 al aire: " + notify.esc(d["al_aire"].get("evento"))
        sal = (d.get("salud") or {}).get("peor")
        if sal in ("aviso", "grave"):
            linea += " · " + ("⚠️" if sal == "aviso" else "❌") + " salud"
        t.append(linea)
    return "\n".join(t)


def _txt_historial():
    ico = {"completo": "✅", "detenido": "⏹"}
    rows = db.get_historial(6)
    if not rows:
        return "Todavía no hay emisiones en el historial."
    t = ["🗂 <b>Últimas emisiones</b>"]
    for r in rows:
        res = r.get("resultado") or ("al aire" if not r.get("fin") else "")
        try:
            a = dt.datetime.strptime(r["inicio"], "%Y-%m-%d %H:%M:%S")
            cuando = _cuando(a)
            if r.get("fin"):
                b = dt.datetime.strptime(r["fin"], "%Y-%m-%d %H:%M:%S")
                cuando += " · " + _hm((b - a).total_seconds())
        except Exception:
            cuando = r.get("inicio") or ""
        t.append("{} {} · {} · {}".format(ico.get(res, "🔴" if res == "al aire" else "❌"),
                                          notify.esc(r.get("evento")), cuando, notify.esc(res)))
    return "\n".join(t)


# ── Botones de los avisos ───────────────────────────────────────────────────
def _occ_txt(occ):
    return occ.strftime("%Y%m%d%H%M")


def botones_inicio(eid):
    """Para el aviso «Inicia…». None si el bot no escucha (no habría quién los atienda)."""
    if not activo():
        return None
    return [[("⏭ Siguiente sección", "sig:{}".format(eid)), ("⏹ Detener", "det:{}".format(eid))]]


def botones_proximo(pid, occ):
    if not activo():
        return None
    o = _occ_txt(occ)
    return [[("▶ Transmitir ya", "tx:{}:{}".format(pid, o)), ("⏸ Saltar esta vez", "skip:{}:{}".format(pid, o))]]


_PREGUNTA = {"det": "✅ Sí, detener", "sig": "✅ Sí, siguiente sección", "tx": "✅ Sí, transmitir ya",
             "skip": "✅ Sí, saltar esta vez", "rstop": "✅ Sí, detener la grabación"}


def _original(data):
    p = data.split(":")
    if p[0] == "rstop":
        return [[("⏹ Detener grabación", "rstop:0")]]
    if p[0] in ("sig", "det"):
        return [[("⏭ Siguiente sección", "sig:" + p[1]), ("⏹ Detener", "det:" + p[1])]]
    return [[("▶ Transmitir ya", "tx:{}:{}".format(p[1], p[2])), ("⏸ Saltar esta vez", "skip:{}:{}".format(p[1], p[2]))]]


def _boton(token, q):
    data = q.get("data") or ""
    msg = q.get("message") or {}
    chat = (msg.get("chat") or {}).get("id")
    mid = msg.get("message_id")

    def avisa(texto, alerta=False):
        try:
            notify._call(token, "answerCallbackQuery", {"callback_query_id": q["id"], "text": texto[:190],
                                                        "show_alert": "true" if alerta else "false"})
        except RuntimeError as e:                   # botón de un mensaje viejo: Telegram ya no acepta la respuesta
            log.info("Telegram no aceptó la respuesta al botón: %s", e)

    def teclas(filas):
        notify._call(token, "editMessageReplyMarkup", {"chat_id": chat, "message_id": mid,
                                                       "reply_markup": teclado(filas) if filas else
                                                       json.dumps({"inline_keyboard": []})})
    user = auth.user_by_tg((q.get("from") or {}).get("id"))
    if not user:
        return avisa("Primero vincula tu Telegram en HAMNA → Mi perfil.", True)
    if data.startswith("m:"):
        return _boton_menu(token, q, user, data, avisa)
    if data.split(":")[0] in ("up", "upx", "ant", "upl"):
        return _boton_audio(token, q, user, data, avisa, teclas)
    if _nivel(user) < auth.ROLES["operador"]:
        return avisa("Solo un operador o el administrador pueden usar estos botones.", True)
    p = data.split(":")
    if p[0] in _PREGUNTA:                           # 1) pedir confirmación en el mismo mensaje
        teclas([[(_PREGUNTA[p[0]], "ok:" + data), ("Cancelar", "no:" + data)]])
        return avisa("¿Seguro?")
    if p[0] == "no":                                # 2a) cancelar: volver a los botones de antes
        teclas(_original(":".join(p[1:])))
        return avisa("Cancelado")
    if p[0] != "ok" or len(p) < 3:
        return avisa("Botón desconocido")
    accion, quien = p[1], notify.esc(_indicativo(user))
    try:
        texto, quitar = _ejecutar(accion, p[2:], user)
    except ValueError as e:
        teclas(None)
        return avisa(str(e), True)
    teclas(None if quitar else _original(":".join(p[1:])))
    avisa("Hecho")
    _responder(token, chat, texto.format(quien=quien), a=mid)


def _ejecutar(accion, args, user):
    """Hace lo pedido; devuelve (texto para el chat con {quien}, ¿quitar botones?)."""
    from .engine import engine
    who = user["usuario"]
    if accion == "rstop":
        from . import grabar
        e = grabar.grabadora.estado()
        if not e.get("grabando"):
            raise ValueError("Ya no se está grabando.")
        grabar.grabadora.detener("manual")
        engine.note("Grabación detenida desde Telegram por {}".format(who))
        return "⏹ {quien} detuvo la grabación «" + notify.esc(e["titulo"]) + "». Se está guardando.", True
    if accion in ("sig", "det"):
        eid = int(args[0])
        st = engine.status()
        if not (st.get("on_air") and st.get("evento_id") == eid):
            raise ValueError("Esa emisión ya no está al aire.")
        if accion == "det":
            engine.note("Detenido desde Telegram por {}".format(who), "warn")
            engine.command("stop")
            return "⏹ {quien} detuvo «" + notify.esc(st.get("evento")) + "» desde Telegram.", True
        engine.note("Siguiente sección desde Telegram ({})".format(who))
        engine.command("next")
        return "⏭ {quien} pasó a la siguiente sección.", False
    pid, occ = int(args[0]), dt.datetime.strptime(args[1], "%Y%m%d%H%M")
    row = db.row("""SELECT p.*, e.nombre AS evento_nombre FROM programacion p JOIN eventos e ON e.id=p.evento_id
                    WHERE p.id=?""", (pid,))
    if not row:
        raise ValueError("Esa programación ya no existe.")
    if occ < dt.datetime.now() - dt.timedelta(minutes=1):
        raise ValueError("Esa emisión ya pasó.")
    nombre = notify.esc(row["evento_nombre"])
    if accion == "skip":
        engine.skip(pid, occ)
        engine.note("«{}» de las {} se saltó desde Telegram ({})".format(row["evento_nombre"], occ.strftime("%H:%M"), who), "warn")
        return "⏸ {quien} saltó «" + nombre + "» del " + _cuando(occ) + ": no saldrá al aire esta vez.", True
    if accion == "tx":
        if engine.busy():
            raise ValueError("Ya hay algo al aire; detenlo primero.")
        engine.start_event(row["evento_id"], origen="telegram")
        engine.skip(pid, occ)                       # que no vuelva a arrancar a su hora
        engine.note("«{}» se adelantó desde Telegram ({})".format(row["evento_nombre"], who))
        return "▶ {quien} inició «" + nombre + "» ya (en lugar de las " + occ.strftime("%H:%M") + ").", True
    raise ValueError("Botón desconocido")


# ── El colaborador manda su audio por Telegram ──────────────────────────────
TIPOS = {"audio/mpeg": ".mp3", "audio/mp3": ".mp3", "audio/ogg": ".ogg", "audio/opus": ".opus", "audio/wav": ".wav",
         "audio/x-wav": ".wav", "audio/wave": ".wav", "audio/mp4": ".m4a", "audio/x-m4a": ".m4a", "audio/m4a": ".m4a",
         "audio/aac": ".aac", "audio/flac": ".flac", "audio/x-flac": ".flac"}


def _es_admin(user):
    return bool(user) and user.get("rol") == "admin"


def _secciones_audio(user):
    """Secciones de audio que puede cambiar: el admin, todas; los demás, las asignadas."""
    if _es_admin(user):
        return [s for s in db.get_secciones() if s["tipo"] in ("Audio", "Sonido")]
    out = []
    for sid in auth.user_sections(user["id"]) if user else []:
        s = db.get_seccion(sid)
        if s and s["tipo"] in ("Audio", "Sonido"):
            out.append(s)
    return out


def _puede(user, sid):
    if _es_admin(user):
        s = db.get_seccion(sid)
        return bool(s) and s["tipo"] in ("Audio", "Sonido")
    return sid in auth.user_sections(user["id"])


POR_PAGINA = 10


def _teclado_proximas(key):
    """Admin: primero las secciones de audio de los próximos eventos, luego «todas»."""
    vistos, filas = set(), []
    for _t, row in _proximos(5):
        for s in db.get_secciones_by_evento(row["evento_id"]):
            if s["tipo"] in ("Audio", "Sonido") and s["id"] not in vistos and len(filas) < 8:
                vistos.add(s["id"])
                filas.append([("🎙 {} · {}".format(s["nombre"][:28], (row.get("evento_nombre") or "")[:18]),
                               "up:{}:{}".format(key, s["id"]))])
    filas.append([("📚 Todas las secciones", "upl:{}:0".format(key))])
    filas.append([("Cancelar", "upx:" + key)])
    return filas


def _teclado_todas(key, pag, secs):
    n = max(1, (len(secs) + POR_PAGINA - 1) // POR_PAGINA)
    pag = max(0, min(pag, n - 1))
    filas = [[("🎙 " + s["nombre"][:40], "up:{}:{}".format(key, s["id"]))]
             for s in secs[pag * POR_PAGINA:(pag + 1) * POR_PAGINA]]
    nav = []
    if pag > 0:
        nav.append(("◀ Anteriores", "upl:{}:{}".format(key, pag - 1)))
    if pag < n - 1:
        nav.append(("Siguientes ▶", "upl:{}:{}".format(key, pag + 1)))
    if nav:
        filas.append(nav)
    filas.append([("Cancelar", "upx:" + key)])
    return filas


def _audio_recibido(token, m, user):
    chat, mid = m["chat"]["id"], m.get("message_id")
    if not user:
        return _responder(token, chat, "👋 Todavía no sé quién eres. Vincula tu Telegram en HAMNA → <b>Mi perfil</b> "
                                       "y después mándame tu audio.")
    secs = _secciones_audio(user)
    esp = _espera_de((m.get("from") or {}).get("id"), ("audio",))
    if not secs and not esp:
        return _responder(token, chat, "No tienes secciones de audio asignadas en HAMNA. "
                                       "El administrador te las asigna (rol Colaborador).", a=mid)
    f = m.get("audio") or m.get("voice") or m.get("document") or {}
    nombre = f.get("file_name") or ("nota de voz" if m.get("voice") else "audio")
    ext = os.path.splitext(nombre)[1].lower() or TIPOS.get((f.get("mime_type") or "").lower(), "")
    if m.get("voice") and not ext:
        ext = ".ogg"
    if m.get("document") and not (f.get("mime_type") or "").startswith("audio/") and ext not in audio.formats():
        return _responder(token, chat, "Eso no parece un audio. Mándame un MP3, una nota de voz o un archivo de audio.", a=mid)
    if ext not in audio.formats():
        return _responder(token, chat, "Este nodo no puede leer audios {}. Mándalo en MP3 o súbelo en la página.".format(
            notify.esc(ext.upper().lstrip(".") or "de ese tipo")), a=mid)
    if int(f.get("file_size") or 0) > MAX_BAJAR:
        return _responder(token, chat, "Pesa {:.0f} MB y Telegram no deja que un bot baje archivos de más de 20 MB. "
                                       "Mándalo en MP3 (pesa menos) o súbelo en la página.".format(
                                           int(f["file_size"]) / 1048576.0), a=mid)
    if not os.path.splitext(nombre)[1]:
        nombre += ext
    if esp:                                         # lo pidió desde «Colaboración»: ya sé dónde va
        _espera_quitar((m.get("from") or {}).get("id"))
        pend = {"file_id": f.get("file_id"), "nombre": nombre, "eid": esp.get("eid")}
        if esp.get("nueva"):
            _responder(token, chat, "📥 Recibí «{}». Creo la sección <b>{}</b>…".format(
                notify.esc(nombre), notify.esc(esp["nombre"])), a=mid)
            nueva = (esp["eid"], esp["nombre"])
            return threading.Thread(target=_poner_audio, args=(token, chat, mid, user, None, pend, nueva),
                                    daemon=True).start()
        s = db.get_seccion(esp["sid"])
        if not s or s["tipo"] == "TTS" or not _puede_editar(user, s["id"]):
            return _responder(token, chat, "Esa sección ya no está disponible.", a=mid)
        _responder(token, chat, "📥 Recibí «{}». Lo pongo en <b>{}</b>…".format(
            notify.esc(nombre), notify.esc(s["nombre"])), a=mid)
        return threading.Thread(target=_poner_audio, args=(token, chat, mid, user, s["id"], pend),
                                daemon=True).start()
    key = uuid.uuid4().hex[:8]
    now = time.time()
    with _lock:
        for k in [k for k, v in _pend.items() if v["exp"] < now]:
            del _pend[k]
        _pend[key] = {"tg": str(user.get("tg_id") or ""), "uid": user["id"], "file_id": f.get("file_id"),
                      "nombre": nombre, "exp": now + 30 * 60}
    dur = f.get("duration")
    desc = "«{}»{}".format(notify.esc(nombre), " ({})".format(_hm(dur)) if dur else "")
    if _es_admin(user):
        filas = _teclado_proximas(key)
        _responder(token, chat, "📥 Recibí {}. ¿En cuál sección lo pongo?\n{}".format(
            desc, "Te muestro primero las de los próximos eventos." if len(filas) > 2 else ""),
            botones=filas if len(filas) > 2 else _teclado_todas(key, 0, secs), a=mid)
    elif len(secs) == 1:
        _responder(token, chat, "📥 Recibí {}. ¿Lo pongo como el audio nuevo de <b>{}</b>?\n"
                                "El audio que tiene ahora queda como versión anterior.".format(desc, notify.esc(secs[0]["nombre"])),
                   botones=[[("✅ Sí, ponerlo", "up:{}:{}".format(key, secs[0]["id"])), ("Cancelar", "upx:" + key)]], a=mid)
    else:
        _responder(token, chat, "📥 Recibí {}. ¿En cuál de tus secciones lo pongo?".format(desc),
                   botones=[[("🎙 " + s["nombre"][:40], "up:{}:{}".format(key, s["id"]))] for s in secs] +
                   [[("Cancelar", "upx:" + key)]], a=mid)


def _boton_audio(token, q, user, data, avisa, teclas):
    p = data.split(":")
    chat = ((q.get("message") or {}).get("chat") or {}).get("id")
    mid = (q.get("message") or {}).get("message_id")
    if p[0] == "ant":
        sid = int(p[1])
        if not _puede(user, sid):
            return avisa("Esa sección no es tuya.", True)
        from . import app as webapp
        try:
            webapp._restaurar_anterior(sid)
        except ValueError as e:
            return avisa(str(e), True)
        teclas(None)
        avisa("Listo")
        s = db.get_seccion(sid)
        webapp._aviso_colaborador(user, sid, "regresó la versión anterior de", "telegram")
        return _responder(token, chat, "↩ «{}» volvió a la versión anterior ({}).".format(
            notify.esc(s["nombre"]), _hm(s.get("duracion"))), a=mid)
    with _lock:
        pend = _pend.get(p[1])
    if not pend:
        teclas(None)
        return avisa("Ese audio ya no está pendiente; mándamelo otra vez.", True)
    if pend["uid"] != user["id"]:
        return avisa("Ese audio no es tuyo.", True)
    if p[0] == "upx":
        with _lock:
            _pend.pop(p[1], None)
        teclas(None)
        return avisa("Cancelado: no cambié nada.")
    if p[0] == "upl":                               # admin: lista completa, por páginas
        teclas(_teclado_todas(p[1], int(p[2]), sorted(_secciones_audio(user), key=lambda s: s["nombre"].lower())))
        return avisa("Página {}".format(int(p[2]) + 1))
    sid = int(p[2])
    if not _puede(user, sid):
        return avisa("Esa sección no es tuya.", True)
    with _lock:
        _pend.pop(p[1], None)
    teclas(None)
    avisa("Descargando…")
    threading.Thread(target=_poner_audio, args=(token, chat, mid, user, sid, pend), daemon=True).start()


def _poner_audio(token, chat, mid, user, sid, pend, nueva=None):
    """Baja el audio de Telegram y lo pone en la sección. nueva=(evento, nombre):
    primero crea la sección y la agrega al final de ese evento."""
    from . import app as webapp
    from .web import UploadedFile
    tmp = paths.tmp_dir() / ("tg_" + uuid.uuid4().hex + os.path.splitext(pend["nombre"])[1])
    creada = None
    try:
        info = notify._call(token, "getFile", {"file_id": pend["file_id"]})
        req = urllib.request.Request(notify.FILE_API.format(token, info["file_path"]), headers={"User-Agent": "HAMNA-Web"})
        with notify.abrir(req, 180) as r, open(str(tmp), "wb") as out:
            while True:
                b = r.read(1 << 16)
                if not b:
                    break
                out.write(b)
        up = UploadedFile(pend["nombre"], str(tmp))
        if nueva:
            sid = creada = _crear_seccion(nueva[0], nueva[1], "Audio")
        s = webapp.colaborador_audio(user, sid, up, via="telegram")
        creada = None
        sale = [_linea_proximo(t, r) for t, r in _proximos(20, {e["evento_id"] for e in db.rows(
            "SELECT evento_id FROM evento_secciones WHERE seccion_id=?", (sid,))})][:2]
        filas = [[("↩ Regresar a la anterior", "ant:{}".format(sid))]] if s.get("anterior_archivo") else []
        if pend.get("eid"):
            filas.append([("🎧 Escuchar", "m:coloir:{}:{}".format(sid, pend["eid"])),
                          ("« Ver sección", "m:cols:{}:{}".format(sid, pend["eid"]))])
        if nueva:
            ev = db.get_evento(nueva[0]) or {}
            texto = "✅ Listo: agregué la sección <b>{}</b> ({}) al final de «{}». ¿La dejas ahí o la mueves?".format(
                notify.esc(s["nombre"]), _hm(s.get("duracion")), notify.esc(ev.get("nombre")))
            if len(db.get_secciones_by_evento(nueva[0])) > 1:
                filas.insert(0, [("↕ Mover de lugar", "m:colmv:{}:{}".format(sid, nueva[0])),
                                 ("✅ Dejarla al final", "m:cole:{}".format(nueva[0]))])
        else:
            texto = "✅ Listo: <b>{}</b> ya tiene tu audio nuevo ({}).".format(notify.esc(s["nombre"]), _hm(s.get("duracion")))
        texto += "\n📡 Sale: " + "\n".join(sale) if sale else ""
        if s.get("anterior_archivo"):
            texto += "\n\nSi te equivocaste, puedes regresar al anterior."
        _responder(token, chat, texto, botones=filas or None, a=mid)
    except ValueError as e:
        _responder(token, chat, "❌ No lo pude poner: {}".format(notify.esc(e)), a=mid)
    except Exception as e:
        log.exception("No pude bajar el audio de Telegram")
        _responder(token, chat, "❌ No pude bajar el audio de Telegram ({}). Intenta otra vez o súbelo en la página.".format(
            notify.esc(e)), a=mid)
    finally:
        if creada:                                  # la sección nueva se quedó sin audio: quitarla
            _borrar_seccion(creada)
        if tmp.exists():
            paths.rm(tmp)


# ── Mensajes privados al colaborador ────────────────────────────────────────
def _colaboradores_de(sid):
    """Usuarios activos con esa sección asignada y Telegram vinculado."""
    return db.rows("""SELECT u.* FROM usuario_secciones us JOIN usuarios u ON u.id=us.usuario_id
                      WHERE us.seccion_id=? AND u.activo=1 AND u.tg_id<>''""", (sid,))


def _dm_listo(cfg):
    return cfg.get("tg_enabled") and cfg.get("tg_token") and cfg.get("tg_collab_dm", True)


def al_aire(ev, secs, estados):
    """Al terminar una emisión: «tu sección salió al aire» a cada colaborador cuya sección salió completa."""
    cfg = settings.load()
    if not _dm_listo(cfg):
        return
    token = cfg["tg_token"].strip()
    etq = numeracion.etiqueta(ev) if ev.get("num") or ev.get("numero") else ""

    def work():
        for i, s in enumerate(secs):
            if i >= len(estados) or estados[i] != "ok":
                continue
            for u in _colaboradores_de(s["id"]):
                try:
                    notify._call(token, "sendMessage", {"chat_id": u["tg_id"], "parse_mode": "HTML", "text":
                        "📡 Tu sección <b>{}</b> salió al aire en «{}»{} ✓".format(
                            notify.esc(s["nombre"]), notify.esc(ev.get("nombre")), " " + notify.esc(etq) if etq else "")})
                except Exception as e:
                    log.warning("No pude avisarle a %s: %s", u["usuario"], e)
    threading.Thread(target=work, daemon=True).start()


def _avisos_file():
    return paths.data_dir() / "recordatorios.json"


def tick(now):
    """Recordatorio al colaborador si se acerca la emisión y no ha subido su audio
    desde la última vez que salió al aire. Se revisa cada 10 min, de 9 a 21 h."""
    cfg = settings.load()
    dias = int(cfg.get("tg_recordar_dias", 2) or 0)
    if not _dm_listo(cfg) or dias <= 0 or not 9 <= now.hour < 21:
        return
    if time.time() - _tick["t"] < 600:
        return
    _tick["t"] = time.time()
    try:
        hechos = json.loads(_avisos_file().read_text())
    except Exception:
        hechos = {}
    hechos = {k: v for k, v in hechos.items() if time.time() - v < 40 * 86400}
    token, cambio = cfg["tg_token"].strip(), False
    for r in db.rows("""SELECT DISTINCT us.seccion_id FROM usuario_secciones us JOIN usuarios u ON u.id=us.usuario_id
                        WHERE u.activo=1 AND u.tg_id<>''"""):
        s = db.get_seccion(r["seccion_id"])
        if not s or s["tipo"] not in ("Audio", "Sonido"):
            continue
        p = paths.audios_dir() / s["ruta_archivo"] if s.get("ruta_archivo") else None
        mt = dt.datetime.fromtimestamp(p.stat().st_mtime) if p and p.is_file() else None
        eids = {e["evento_id"] for e in db.rows("SELECT evento_id FROM evento_secciones WHERE seccion_id=?", (s["id"],))}
        for t, row in _proximos(1, eids):
            if (t - now).total_seconds() > dias * 86400:
                continue
            ult = db.row("SELECT MAX(inicio) AS i FROM historial WHERE evento_id=? AND inicio < ?",
                         (row["evento_id"], now.strftime("%Y-%m-%d %H:%M:%S")))
            ult = dt.datetime.strptime(ult["i"], "%Y-%m-%d %H:%M:%S") if ult and ult.get("i") else None
            if mt and (not ult or mt > ult):
                continue                            # ya la actualizó desde la última emisión
            for u in _colaboradores_de(s["id"]):
                key = "{}:{}:{}".format(u["id"], s["id"], t.strftime("%Y%m%d%H%M"))
                if key in hechos:
                    continue
                try:
                    notify._call(token, "sendMessage", {"chat_id": u["tg_id"], "parse_mode": "HTML", "text":
                        "⏰ Hola, {}. Recuerda subir tu audio para <b>{}</b>: sale en «{}» el {} (en {}).\n\n"
                        "📲 Mándamelo por aquí (audio o nota de voz) o súbelo en la página.".format(
                            notify.esc(_indicativo(u)), notify.esc(s["nombre"]),
                            notify.esc(row.get("evento_nombre")), _cuando(t), _falta((t - now).total_seconds()))})
                    hechos[key] = time.time()
                    cambio = True
                    log.info("Recordatorio a %s para «%s»", u["usuario"], s["nombre"])
                except Exception as e:
                    log.warning("No pude mandar el recordatorio a %s: %s", u["usuario"], e)
    if cambio:
        try:
            _avisos_file().write_text(json.dumps(hechos))
        except Exception:
            pass


# ── Menú con botones («tarjetas» que se reemplazan en el mismo mensaje) ────
TECLADO_FIJO = json.dumps({"keyboard": [[{"text": "📋 Menú"}]], "resize_keyboard": True, "is_persistent": True})
VOLVER = ("« Menú", "m:menu")
EV_PAG = 8


def _editar(token, chat, mid, texto, botones):
    p = {"chat_id": chat, "message_id": mid, "text": texto, "parse_mode": "HTML", "disable_web_page_preview": "true",
         "reply_markup": teclado(botones) if botones else json.dumps({"inline_keyboard": []})}
    try:
        notify._call(token, "editMessageText", p)
    except RuntimeError as e:
        if "not modified" not in str(e):
            raise


def _resumen():
    from .engine import engine
    s = engine.status()
    if s.get("on_air"):
        return "🔴 Al aire: <b>{}</b>".format(notify.esc(s.get("evento") or "prueba"))
    prox = _proximos(1)
    return "⚪ Fuera del aire" + (" · sigue " + _linea_proximo(*prox[0]) if prox else "")


def _pantalla(cual, user, arg=""):
    """(texto, botones) de cada pantalla del menú."""
    from .engine import engine
    from . import grabar
    n = _nivel(user)
    op, lec = n >= auth.ROLES["operador"], n >= auth.ROLES["lectura"]
    if cual == "menu":
        cfg = settings.load()
        est = cfg.get("station_name") or "HAMNA"
        e = grabar.grabadora.estado()
        t = "📻 <b>{}</b>{}\n{}{}\n\n¿Qué quieres hacer?".format(
            notify.esc(est), " · nodo " + notify.esc(cfg.get("node")) if cfg.get("node") else "", _resumen(),
            "\n⏺ Grabando «{}» · {}".format(notify.esc(e["titulo"]), _hm(e["dur"])) if e.get("grabando") else "")
        filas = [[("📡 Estado", "m:estado"), ("📅 Próximos", "m:prox")]]
        if op:
            filas.append([("▶ Transmitir evento", "m:ev:0"),
                          ("⏹ Detener grabación", "rstop:0") if e.get("grabando") else ("⏺ Grabar", "m:grab")])
        if lec:
            filas.append([("🩺 Salud", "m:salud"), ("🗂 Historial", "m:hist"), ("🗺 Nodos", "m:nodos")])
        if _gestor(user) or auth.user_sections(user["id"]):
            filas.append([("🤝 Colaboración", "m:col:0"), ("❓ Ayuda", "m:ayuda")])
        else:
            filas.append([("❓ Ayuda", "m:ayuda")])
        if _secciones_audio(user) and not _es_admin(user):
            t += "\n📲 Para cambiar tu sección, mándame tu audio o una nota de voz."
        return t, filas
    if cual == "estado":
        s = engine.status()
        filas = []
        if s.get("on_air") and op and s.get("evento_id"):
            filas.append([("⏭ Siguiente sección", "sig:{}".format(s["evento_id"])), ("⏹ Detener", "det:{}".format(s["evento_id"]))])
        filas.append([("🔄 Actualizar", "m:estado"), VOLVER])
        return _txt_estado(), filas
    if cual == "prox":
        return _txt_proximo(user), [[VOLVER]]
    if cual in ("salud", "hist", "nodos"):
        if not lec:
            return "Esa opción no está disponible para tu usuario.", [[VOLVER]]
        filas = [[("🔄 Actualizar", "m:" + cual), VOLVER]]
        if cual == "nodos":
            filas.insert(0, [("🔗 Conexiones de este nodo", "m:con")])
        return {"salud": _txt_salud, "hist": _txt_historial, "nodos": _txt_nodos}[cual](), filas
    if cual == "ayuda":
        return _ayuda(user), [[VOLVER]]
    if cual == "grab":
        if not op:
            return "Solo un operador o el administrador pueden grabar.", [[VOLVER]]
        e = grabar.grabadora.estado()
        if e.get("grabando"):
            return "⏺ Ya se está grabando «{}» · lleva {}".format(notify.esc(e["titulo"]), _hm(e["dur"])), \
                [[("⏹ Detener grabación", "rstop:0")], [VOLVER]]
        return ("⏺ <b>¿Empezar a grabar lo que se escucha en el nodo?</b>\nSe llamará «Grabación de {}» y se detiene sola tras {} min "
                "sin actividad.\nPara otro título escribe <code>/grabar Título</code>.".format(
                    notify.esc(_indicativo(user)), int(settings.load().get("rec_silencio_min", 5) or 5)),
                [[("⏺ Sí, grabar", "m:grabgo"), VOLVER]])
    if cual == "ev":
        if not op:
            return "Solo un operador o el administrador pueden transmitir.", [[VOLVER]]
        evs = [e for e in db.get_eventos() if e.get("num_secciones")]
        if not evs:
            return "No hay eventos con secciones.", [[VOLVER]]
        prox = {}
        for t, row in _proximos(50):
            prox.setdefault(row["evento_id"], t)
        evs.sort(key=lambda e: (e["id"] not in prox, prox.get(e["id"], dt.datetime.max), e["nombre"].lower()))
        pag = max(0, int(arg or 0))
        trozo = evs[pag * EV_PAG:(pag + 1) * EV_PAG]
        filas = [[("▶ {} · {}".format(e["nombre"][:34], _hm(e.get("duracion_total"))), "m:evc:{}".format(e["id"]))] for e in trozo]
        nav = []
        if pag > 0:
            nav.append(("◀", "m:ev:{}".format(pag - 1)))
        if (pag + 1) * EV_PAG < len(evs):
            nav.append(("▶▶", "m:ev:{}".format(pag + 1)))
        if nav:
            filas.append(nav)
        filas.append([VOLVER])
        aviso = "\n⚠ Ahora hay algo al aire: al transmitir otro evento se detiene." if engine.status().get("on_air") else ""
        return "▶ <b>¿Qué evento quieres transmitir?</b>\nPrimero van los que salen pronto.{}".format(aviso), filas
    if cual == "evc":
        if not op:
            return "Solo un operador o el administrador pueden transmitir.", [[VOLVER]]
        ev = db.get_evento(int(arg))
        if not ev:
            return "Ese evento ya no existe.", [[("« Eventos", "m:ev:0"), VOLVER]]
        ev = numeracion.aplicar(ev)
        secs = db.get_secciones_by_evento(ev["id"])
        etq = numeracion.etiqueta(ev) if (ev.get("num") or ev.get("numero")) else ""
        st = engine.status()
        aviso = "\n\n⚠ Ahora está al aire «{}»: se va a detener.".format(notify.esc(st.get("evento") or "prueba")) if st.get("on_air") else ""
        return ("▶ <b>¿Transmitir «{}»{} ahora?</b>\n{} secciones · {} aprox.{}".format(
            notify.esc(ev["nombre"]), " " + notify.esc(etq) if etq else "", len(secs),
            _hm(sum(float(s.get("duracion") or 0) for s in secs)), aviso),
            [[("✅ Sí, transmitir", "m:evgo:{}".format(ev["id"]))], [("« Eventos", "m:ev:0"), VOLVER]])
    if cual in ("col", "cole", "cols", "colantq", "colmv", "coldelq"):
        return _pantalla_colab(cual, user, arg)
    if cual in ("con", "conl", "condq"):
        if not lec:
            return "Esa opción no está disponible para tu usuario.", [[VOLVER]]
        return _pantalla_con(cual, user, arg)
    return "No conozco esa opción.", [[VOLVER]]


def _boton_menu(token, q, user, data, avisa):
    from .engine import engine
    from . import grabar
    msg = q.get("message") or {}
    chat, mid = (msg.get("chat") or {}).get("id"), msg.get("message_id")
    p = data.split(":")
    cual, arg = p[1], ":".join(p[2:])
    op = _nivel(user) >= auth.ROLES["operador"]
    try:
        if cual in COL_ACCIONES:
            return _boton_colab(token, chat, mid, user, cual, arg, avisa, (q.get("from") or {}).get("id"))
        if cual in CON_ACCIONES:
            return _boton_con(token, chat, mid, user, cual, arg, avisa, (q.get("from") or {}).get("id"))
        if cual == "evgo":
            if not op:
                return avisa("Solo un operador o el administrador pueden transmitir.", True)
            ev = db.get_evento(int(arg))
            if not ev:
                return avisa("Ese evento ya no existe.", True)
            try:
                engine.start_event(ev["id"], origen="Telegram · " + user["usuario"])
            except ValueError as e:
                return avisa(str(e), True)
            engine.note("«{}» iniciado desde Telegram por {}".format(ev["nombre"], user["usuario"]))
            avisa("Iniciando…")
            return _editar(token, chat, mid, "▶ <b>{}</b> inició «{}».\nEl resumen y los botones para controlarlo llegan en el aviso de inicio.".format(
                notify.esc(_indicativo(user)), notify.esc(ev["nombre"])),
                [[("📡 Estado", "m:estado"), VOLVER]])
        if cual == "grabgo":
            if not op:
                return avisa("Solo un operador o el administrador pueden grabar.", True)
            titulo = "Grabación de {}".format(_indicativo(user))
            try:
                grabar.grabadora.iniciar(titulo, "Telegram · " + user["usuario"])
            except ValueError as e:
                return avisa(str(e), True)
            avisa("Grabando")
            return _editar(token, chat, mid, "⏺ Grabando «{}». Se detiene sola tras {} min sin actividad.".format(
                notify.esc(titulo), int(settings.load().get("rec_silencio_min", 5) or 5)),
                [[("⏹ Detener grabación", "rstop:0")], [VOLVER]])
        texto, botones = _pantalla(cual, user, arg)
        _editar(token, chat, mid, texto, botones)
        avisa("")
    except Exception as e:
        log.exception("Menú del bot")
        avisa("No pude: {}".format(e), True)


# ── «Colaboración»: las secciones de cada evento ────────────────────────────
#   Colaborador        ve los eventos donde salen sus secciones y edita las suyas.
#   Operador / admin   ve todos los eventos, edita cualquier sección y agrega nuevas.
#   Editar             audio: «mándame el audio» · texto a voz: «escríbeme el texto».
ESPERA_SECS = 15 * 60
_espera = {}                    # Telegram id → qué le estoy esperando (audio, texto, nombre…)
COL_ACCIONES = ("colx", "colup", "coltx", "colgen", "coloir", "colanty", "coln", "colnt", "colmvx", "coldel")
MOVER = {"t": "⏫ Al inicio", "u": "⬆ Subir", "d": "⬇ Bajar", "b": "⏬ Al final"}
TIPO_NOMBRE = {"TTS": "Texto a voz", "Audio": "Audio", "Sonido": "Sonido"}


def _gestor(user):
    return _nivel(user) >= auth.ROLES["operador"]


def _puede_editar(user, sid):
    if _gestor(user):
        return bool(db.get_seccion(sid))
    return sid in auth.user_sections(user["id"])


def _espera_de(tg, modos=None):
    now = time.time()
    with _lock:
        for k in [k for k, v in _espera.items() if v["exp"] < now]:
            del _espera[k]
        e = _espera.get(str(tg or ""))
    return e if e and (modos is None or e["modo"] in modos) else None


def _espera_poner(tg, **datos):
    datos["exp"] = time.time() + ESPERA_SECS
    with _lock:
        _espera[str(tg)] = datos


def _espera_quitar(tg):
    with _lock:
        _espera.pop(str(tg or ""), None)


def _ints(arg):
    out = []
    for x in (arg or "").split(":"):
        try:
            out.append(int(x))
        except ValueError:
            out.append(0)
    return out + [0, 0]


def _ev_titulo(ev):
    ev = numeracion.aplicar(ev)
    etq = numeracion.etiqueta(ev) if (ev.get("num") or ev.get("numero")) else ""
    return notify.esc(ev["nombre"]) + (" " + notify.esc(etq) if etq else "")


def _colab_eventos(user):
    """[(evento, próxima salida o None)] que ve este usuario, primero los que salen pronto."""
    if _gestor(user):
        evs = [e for e in db.get_eventos() if e.get("num_secciones")]
    else:
        ids = _eventos_de(user)
        evs = [e for e in db.get_eventos() if e["id"] in ids]
    prox = {}
    for t, row in _proximos(200):
        prox.setdefault(row["evento_id"], t)
    evs.sort(key=lambda e: (e["id"] not in prox, prox.get(e["id"], dt.datetime.max), e["nombre"].lower()))
    return [(e, prox.get(e["id"])) for e in evs]


def _ve_evento(user, eid):
    return _gestor(user) or eid in _eventos_de(user)


def _archivo(s):
    p = paths.audios_dir() / s["ruta_archivo"] if s and s.get("ruta_archivo") else None
    return p if p and p.is_file() else None


def _actualizada(s):
    p = _archivo(s)
    ts = s.get("audio_ts") or (p.stat().st_mtime if p else None)
    return dt.datetime.fromtimestamp(ts) if ts else None


def _ultima_salida(eid):
    r = db.row("SELECT MAX(inicio) AS i FROM historial WHERE evento_id=? AND inicio < ?",
               (eid, dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    return dt.datetime.strptime(r["i"], "%Y-%m-%d %H:%M:%S") if r and r.get("i") else None


def _pantalla_colab(cual, user, arg):
    volver_ev = ("« Eventos", "m:col:0")
    if cual == "col":
        evs = _colab_eventos(user)
        if not evs:
            return ("🤝 <b>Colaboración</b>\nTodavía no tienes secciones asignadas en ningún evento. "
                    "El administrador te las asigna en HAMNA (rol Colaborador)."), [[VOLVER]]
        pag = max(0, _ints(arg)[0])
        trozo = evs[pag * EV_PAG:(pag + 1) * EV_PAG]
        filas = [[("{} · {}".format(e["nombre"][:30], _cuando(t) if t else "sin programar"),
                   "m:cole:{}".format(e["id"]))] for e, t in trozo]
        nav = []
        if pag > 0:
            nav.append(("◀", "m:col:{}".format(pag - 1)))
        if (pag + 1) * EV_PAG < len(evs):
            nav.append(("▶▶", "m:col:{}".format(pag + 1)))
        if nav:
            filas.append(nav)
        filas.append([VOLVER])
        que = "editar cualquiera o agregar una nueva" if _gestor(user) else "editar las tuyas"
        return ("🤝 <b>Colaboración</b>\nElige el evento para ver sus secciones y {}.\n"
                "Primero van los que salen pronto.".format(que)), filas

    if cual == "cole":
        eid = _ints(arg)[0]
        ev = db.get_evento(eid)
        if not ev or not _ve_evento(user, eid):
            return "Ese evento ya no está disponible.", [[volver_ev, VOLVER]]
        secs = db.get_secciones_by_evento(eid)
        mias = None if _gestor(user) else set(auth.user_sections(user["id"]))
        ult = _ultima_salida(eid)
        prox = _proximos(1, {eid})
        t = ["🤝 <b>{}</b>".format(_ev_titulo(ev)),
             "📡 Sale: {} (en {})".format(_cuando(prox[0][0]), _falta((prox[0][0] - dt.datetime.now()).total_seconds()))
             if prox else "📡 Sin programar", ""]
        filas = []
        for i, s in enumerate(secs, 1):
            mia = mias is None or s["id"] in mias
            ico = "🗣" if s["tipo"] == "TTS" else "🔔" if s["tipo"] == "Sonido" else "🎙"
            linea = "{}. {} {}".format(i, ico, "<b>{}</b>".format(notify.esc(s["nombre"])) if mia else notify.esc(s["nombre"]))
            linea += " · " + _hm(s.get("duracion")) if _archivo(s) else " · ⚠ sin audio"
            if mia and s.get("renovar"):
                fresca = s.get("audio_ts") and (ult is None or dt.datetime.fromtimestamp(s["audio_ts"]) > ult)
                linea += " · ✅ ya actualizada" if fresca else " · ⏰ falta actualizar"
            if mia and mias is not None:
                linea += " · ✏ tuya"
            t.append(linea)
            if mia:
                filas.append([("✏ {}. {}".format(i, s["nombre"][:36]), "m:cols:{}:{}".format(s["id"], eid))])
        if not secs:
            t.append("Este evento no tiene secciones." + (" Agrega una con «➕ Nueva sección»." if _gestor(user) else ""))
        else:
            t += ["", "Toca la sección que quieres editar." if filas else "No tienes secciones para editar aquí."]
        if _gestor(user):
            filas.append([("➕ Nueva sección", "m:coln:{}".format(eid))])
        filas.append([volver_ev, VOLVER])
        return "\n".join(t), filas

    sid, eid = _ints(arg)[:2]
    s = db.get_seccion(sid)
    volver_sec = ("« Secciones", "m:cole:{}".format(eid)) if eid else volver_ev
    if not s or not _puede_editar(user, sid):
        return "Esa sección ya no está disponible.", [[volver_sec, VOLVER]]
    from . import app as webapp
    o = webapp._sec_out(s)

    if cual == "colmv":                             # cambiar el lugar de la sección en el evento
        ev = db.get_evento(eid) if eid else None
        ids = [x["id"] for x in db.get_secciones_by_evento(eid)] if ev else []
        if not _gestor(user) or sid not in ids:
            return "Esa sección ya no está en el evento.", [[volver_sec, VOLVER]]
        i = ids.index(sid)
        t = ["↕ <b>Mover «{}»</b> en «{}»".format(notify.esc(s["nombre"]), _ev_titulo(ev)),
             "Está en el lugar <b>{} de {}</b>. El cambio se guarda al momento.".format(i + 1, len(ids)), ""]
        for j, x in enumerate(db.get_secciones_by_evento(eid), 1):
            t.append("👉 <b>{}. {}</b>".format(j, notify.esc(x["nombre"])) if x["id"] == sid
                     else "{}. {}".format(j, notify.esc(x["nombre"])))
        b = lambda d: (MOVER[d], "m:colmvx:{}:{}:{}".format(sid, eid, d))
        filas = [f for f in ([b(d) for d in ("t", "u") if i > 0], [b(d) for d in ("d", "b") if i < len(ids) - 1]) if f]
        filas.append([("✅ Listo", "m:cols:{}:{}".format(sid, eid))])
        return "\n".join(t), filas

    if cual == "coldelq":                           # ¿quitar del evento o borrar por completo?
        if not _gestor(user):
            return "Solo un operador o el administrador pueden borrar secciones.", [[volver_sec, VOLVER]]
        usos = db.rows("""SELECT e.id, e.nombre FROM evento_secciones es JOIN eventos e ON e.id=es.evento_id
                          WHERE es.seccion_id=? ORDER BY e.nombre COLLATE NOCASE""", (sid,))
        otros = [u_["nombre"] for u_ in usos if u_["id"] != eid]
        ev = db.get_evento(eid) if eid else None
        t = ["🗑 <b>¿Qué hago con «{}»?</b>".format(notify.esc(s["nombre"])), ""]
        filas = []
        if ev and any(u_["id"] == eid for u_ in usos):
            t.append("➖ <b>Quitar de «{}»</b>: deja de salir en este evento, pero la sección y su audio se "
                     "conservan{}.".format(_ev_titulo(ev), " (sigue en: " + notify.esc(", ".join(otros)) + ")" if otros
                                           else " en la pestaña Secciones, por si la usas después"))
            filas.append([("➖ Quitar de este evento", "m:coldel:{}:{}:q".format(sid, eid))])
        t.append("🗑 <b>Borrar por completo</b>: se borra la sección y su audio{}. <b>No se puede deshacer.</b>".format(
            ", y deja de salir también en " + notify.esc(", ".join(otros)) if otros else ""))
        filas.append([("🗑 Borrar por completo", "m:coldel:{}:{}:b".format(sid, eid))])
        filas.append([("Cancelar", "m:cols:{}:{}".format(sid, eid))])
        return "\n".join(t), filas

    if cual == "colantq":
        if not o["tiene_anterior"]:
            return "Esta sección no tiene versión anterior.", [[("« Sección", "m:cols:{}:{}".format(sid, eid)), VOLVER]]
        return ("↩ <b>¿Regresar «{}» a la versión anterior?</b>\nAnterior: {} · del {}\nAhora: {}\n\n"
                "El audio de ahora pasa a ser la versión anterior, así que puedes volver a cambiarlo.".format(
                    notify.esc(s["nombre"]), _hm(s.get("anterior_duracion")), notify.esc(s.get("anterior_fecha") or "?"),
                    _hm(s.get("duracion")))), \
            [[("✅ Sí, regresar", "m:colanty:{}:{}".format(sid, eid))], [("Cancelar", "m:cols:{}:{}".format(sid, eid))]]

    # cols: la tarjeta de la sección
    tts_ = s["tipo"] == "TTS"
    t = ["{} <b>{}</b>".format("🗣" if tts_ else "🎙", notify.esc(s["nombre"])),
         "Tipo: " + TIPO_NOMBRE.get(s["tipo"], s["tipo"] or "?")]
    t.append("Duración: " + _hm(s.get("duracion")) if o["tiene_audio"] else "⚠ Todavía no tiene audio")
    act = _actualizada(s)
    if act and o["tiene_audio"]:
        t.append("Actualizada: " + _cuando(act))
    if o["tiene_anterior"]:
        t.append("Versión anterior: {} · del {}".format(_hm(s.get("anterior_duracion")), notify.esc(s.get("anterior_fecha") or "?")))
    evs = {r["evento_id"] for r in db.rows("SELECT evento_id FROM evento_secciones WHERE seccion_id=?", (sid,))}
    sale = [_linea_proximo(tt, r) for tt, r in _proximos(3, evs)]
    if sale:
        t.append("📡 Sale: " + "\n".join(sale))
    if tts_:
        texto = s.get("texto_tts") or ""
        t += ["", "<b>Texto que lee la voz:</b>",
              "<i>{}</i>".format(notify.esc(texto[:2500] + ("…" if len(texto) > 2500 else ""))) if texto.strip() else "(sin texto)"]
    filas = []
    if tts_:
        filas.append([("✏ Cambiar texto", "m:coltx:{}:{}".format(sid, eid)),
                      ("🔁 Generar de nuevo", "m:colgen:{}:{}".format(sid, eid))])
    else:
        filas.append([("📤 Mandar audio nuevo", "m:colup:{}:{}".format(sid, eid))])
    fila = []
    if o["tiene_audio"]:
        fila.append(("🎧 Escuchar", "m:coloir:{}:{}".format(sid, eid)))
    if o["tiene_anterior"]:
        fila.append(("↩ Regresar a la anterior", "m:colantq:{}:{}".format(sid, eid)))
    if fila:
        filas.append(fila)
    if _gestor(user):
        fila = [("🗑 Borrar", "m:coldelq:{}:{}".format(sid, eid))]
        if eid and len(db.get_secciones_by_evento(eid)) > 1:
            fila.insert(0, ("↕ Mover de lugar", "m:colmv:{}:{}".format(sid, eid)))
        filas.append(fila)
    filas.append([volver_sec, VOLVER])
    return "\n".join(t), filas


def _boton_colab(token, chat, mid, user, cual, arg, avisa, tg):
    """Botones de «Colaboración» que hacen algo (no solo cambian de pantalla)."""
    n = _ints(arg)
    sid, eid = n[0], n[1]

    def pantalla(c, a, pre=""):
        texto, botones = _pantalla(c, user, a)
        _editar(token, chat, mid, pre + texto, botones)

    if cual == "colmvx":
        if not _gestor(user):
            return avisa("Solo un operador o el administrador pueden mover secciones.", True)
        ids = [x["id"] for x in db.get_secciones_by_evento(eid)]
        if sid not in ids:
            return avisa("Esa sección ya no está en el evento.", True)
        d = arg.split(":")[-1]
        i = ids.index(sid)
        j = {"t": 0, "u": i - 1, "d": i + 1, "b": len(ids) - 1}.get(d, i)
        j = max(0, min(j, len(ids) - 1))
        if j != i:
            ids.insert(j, ids.pop(i))
            db.set_orden_evento(eid, ids)
            s = db.get_seccion(sid) or {}
            log.info("%s movió «%s» al lugar %d del evento #%s desde Telegram", user["usuario"], s.get("nombre"), j + 1, eid)
        avisa("Ahora está en el lugar {} de {}".format(j + 1, len(ids)))
        return pantalla("colmv", "{}:{}".format(sid, eid))

    if cual == "coldel":                            # q: quitar de este evento · b: borrar por completo
        if not _gestor(user):
            return avisa("Solo un operador o el administrador pueden borrar secciones.", True)
        s = db.get_seccion(sid)
        if not s:
            return avisa("Esa sección ya no existe.", True)
        completo = arg.split(":")[-1] == "b"
        eids = {r["evento_id"] for r in db.rows("SELECT evento_id FROM evento_secciones WHERE seccion_id=?", (sid,))}
        from .engine import engine
        st = engine.status()
        if st.get("on_air") and st.get("evento_id") in (eids if completo else {eid}):
            return avisa("Ese evento está al aire; espera a que termine para borrarla.", True)
        quien = notify.esc(_indicativo(user))
        ev = db.get_evento(eid) if eid else None
        if completo:
            from . import app as webapp
            for archivo, carpeta in ((s.get("ruta_archivo"), paths.audios_dir()),
                                     (s.get("anterior_archivo"), webapp._anteriores_dir())):
                if archivo:
                    paths.rm(carpeta / archivo)
            db.delete_seccion(sid)                  # se va de todos sus eventos (ON DELETE CASCADE)
            log.info("%s borró la sección «%s» desde Telegram", user["usuario"], s["nombre"])
            notify.send("colaborador", "🗑 <b>{}</b> borró la sección «{}» · 📲 por Telegram".format(quien, notify.esc(s["nombre"])))
            pre = "🗑 Borré la sección «{}».\n\n".format(notify.esc(s["nombre"]))
        else:
            db.remove_seccion_from_evento(eid, sid)
            db.set_orden_evento(eid, [x["id"] for x in db.get_secciones_by_evento(eid)])
            eids = {eid}
            log.info("%s quitó «%s» del evento #%s desde Telegram", user["usuario"], s["nombre"], eid)
            notify.send("colaborador", "➖ <b>{}</b> quitó «{}» de «{}» · 📲 por Telegram".format(
                quien, notify.esc(s["nombre"]), notify.esc((ev or {}).get("nombre"))))
            pre = "➖ Quité «{}» de este evento.\n\n".format(notify.esc(s["nombre"]))

        def preparar():
            for e in eids:
                try:
                    engine.prepare_event(e)
                except Exception as ex:
                    log.warning("No se pudo preparar el evento #%s: %s", e, ex)
        threading.Thread(target=preparar, daemon=True).start()
        avisa("Listo")
        return pantalla("cole", str(eid), pre) if ev else pantalla("col", "0", pre)

    if cual == "colx":
        _espera_quitar(tg)
        avisa("Cancelado")
        return pantalla("cols", arg) if sid else pantalla("cole", str(eid))

    if cual in ("coln", "colnt"):                   # sección nueva en el evento (operador / admin)
        eid = sid                                   # aquí el primer número es el evento
        if not _gestor(user):
            return avisa("Solo un operador o el administrador pueden agregar secciones.", True)
        ev = db.get_evento(eid)
        if not ev:
            return avisa("Ese evento ya no existe.", True)
        cancelar = [[("Cancelar", "m:colx:0:{}".format(eid))]]
        if cual == "coln":
            _espera_poner(tg, modo="nombre", eid=eid)
            avisa("")
            return _editar(token, chat, mid, "➕ <b>Nueva sección en «{}»</b>\n\n✍ Escríbeme el <b>nombre</b> de la sección "
                                             "(se agrega al final del evento).".format(_ev_titulo(ev)), cancelar)
        esp = _espera_de(tg, ("tipo",))
        if not esp or esp.get("eid") != eid:
            return avisa("Esto ya se venció; toca «➕ Nueva sección» otra vez.", True)
        tts_ = arg.split(":")[-1] == "T"
        _espera_poner(tg, modo="texto" if tts_ else "audio", eid=eid, nombre=esp["nombre"], nueva=True)
        avisa("")
        return _editar(token, chat, mid, "➕ <b>{}</b> en «{}»\n\n{}".format(
            notify.esc(esp["nombre"]), _ev_titulo(ev),
            "✍ Escríbeme el <b>texto</b> que va a leer la voz. Puedes usar variables como {saludo} o {emision}."
            if tts_ else "📤 Mándame el <b>audio</b> (MP3, nota de voz o archivo de audio)."), cancelar)

    s = db.get_seccion(sid)
    if not s or not _puede_editar(user, sid):
        return avisa("Esa sección ya no está disponible.", True)
    nombre = notify.esc(s["nombre"])
    cancelar = [[("Cancelar", "m:colx:{}:{}".format(sid, eid))]]

    if cual == "colup":
        if s["tipo"] == "TTS":
            return avisa("Esa sección es de texto a voz.", True)
        _espera_poner(tg, modo="audio", sid=sid, eid=eid)
        avisa("")
        return _editar(token, chat, mid, "📤 <b>{}</b>\n\nMándame ahora el audio nuevo (MP3, nota de voz o archivo de audio). "
                                         "El que tiene ahora queda como versión anterior.\nTe espero {} min.".format(
                                             nombre, ESPERA_SECS // 60), cancelar)
    if cual == "coltx":
        if s["tipo"] != "TTS":
            return avisa("Esa sección no es de texto a voz.", True)
        _espera_poner(tg, modo="texto", sid=sid, eid=eid)
        avisa("")
        actual = s.get("texto_tts") or ""
        return _editar(token, chat, mid, "✏ <b>{}</b>\n\nEscríbeme el texto nuevo completo y genero la voz.\n"
                                         "Texto de ahora (tócalo para copiarlo y edítalo si solo cambias una parte):\n\n"
                                         "<code>{}</code>".format(nombre, notify.esc(actual[:3000])), cancelar)
    if cual == "colgen":
        if s["tipo"] != "TTS":
            return avisa("Esa sección no es de texto a voz.", True)
        avisa("Generando…")
        _editar(token, chat, mid, "⏳ Generando la voz de <b>{}</b>…".format(nombre), None)
        return threading.Thread(target=_generar_voz, args=(token, chat, mid, user, sid, eid), daemon=True).start()
    if cual == "coloir":
        if not _archivo(s):
            return avisa("Esa sección no tiene audio.", True)
        avisa("Te lo mando…")
        return threading.Thread(target=_mandar_audio, args=(token, chat, s), daemon=True).start()
    if cual == "colanty":
        from . import app as webapp
        try:
            webapp._restaurar_anterior(sid)
        except ValueError as e:
            return avisa(str(e), True)
        webapp._aviso_colaborador(user, sid, "regresó la versión anterior de", "telegram")
        avisa("Listo")
        return pantalla("cols", arg, "↩ Listo: regresé a la versión anterior.\n\n")
    avisa("Botón desconocido")


def _texto_recibido(token, m, user, texto, esp):
    """Un texto mientras el bot espera algo: el nombre de una sección nueva, el texto de la voz
    o el número de nodo al que conectar."""
    chat, mid, tg = m["chat"]["id"], m.get("message_id"), (m.get("from") or {}).get("id")
    if esp["modo"] == "nodo":
        return _nodo_recibido(token, chat, mid, user, texto, tg)
    cancelar = [[("Cancelar", "m:colx:{}:{}".format(esp.get("sid") or 0, esp.get("eid") or 0))]]
    if esp["modo"] == "audio":
        return _responder(token, chat, "📤 Estoy esperando un <b>audio</b> (MP3 o nota de voz). Mándamelo o toca Cancelar.",
                          botones=cancelar, a=mid)
    if esp["modo"] == "tipo":
        return _responder(token, chat, "Elige con los botones si la sección <b>{}</b> es de audio o de texto a voz.".format(
            notify.esc(esp["nombre"])), botones=_botones_tipo(esp["eid"]), a=mid)
    if esp["modo"] == "nombre":
        nombre = " ".join(texto.split())[:80]
        if not nombre:
            return _responder(token, chat, "Escríbeme el nombre de la sección.", botones=cancelar, a=mid)
        _espera_poner(tg, modo="tipo", eid=esp["eid"], nombre=nombre)
        return _responder(token, chat, "➕ <b>{}</b>\n¿Qué tipo de sección es?".format(notify.esc(nombre)),
                          botones=_botones_tipo(esp["eid"]), a=mid)
    # modo «texto»: el texto a voz de una sección (o de una nueva)
    if not esp.get("nueva"):
        s = db.get_seccion(esp["sid"])
        if not s or s["tipo"] != "TTS" or not _puede_editar(user, s["id"]):
            _espera_quitar(tg)
            return _responder(token, chat, "Esa sección ya no está disponible.", a=mid)
    elif not _gestor(user):
        _espera_quitar(tg)
        return _responder(token, chat, "Solo un operador o el administrador pueden agregar secciones.", a=mid)
    _espera_quitar(tg)
    _responder(token, chat, "⏳ Generando la voz…", a=mid)
    nueva = (esp["eid"], esp["nombre"]) if esp.get("nueva") else None
    threading.Thread(target=_generar_voz, args=(token, chat, None, user, esp.get("sid"), esp.get("eid"), texto.strip(), nueva),
                     daemon=True).start()


def _botones_tipo(eid):
    return [[("🎙 Audio (me lo mandas)", "m:colnt:{}:A".format(eid)), ("🗣 Texto a voz", "m:colnt:{}:T".format(eid))],
            [("Cancelar", "m:colx:0:{}".format(eid))]]


def _crear_seccion(eid, nombre, tipo, texto=None):
    if not db.get_evento(eid):
        raise ValueError("Ese evento ya no existe")
    sid = db.insert_seccion(nombre, tipo, texto_tts=texto)
    db.add_seccion_to_evento(eid, sid)
    log.info("Sección nueva «%s» (%s) en el evento #%s, desde Telegram", nombre, tipo, eid)
    return sid


def _borrar_seccion(sid):
    try:
        s = db.get_seccion(sid) or {}
        if s.get("ruta_archivo"):
            paths.rm(paths.audios_dir() / s["ruta_archivo"])
        db.execute("DELETE FROM evento_secciones WHERE seccion_id=?", (sid,))
        db.delete_seccion(sid)
    except Exception:
        log.exception("No pude quitar la sección #%s", sid)


def _generar_voz(token, chat, mid, user, sid, eid, texto=None, nueva=None):
    """Genera la voz (con texto nuevo, o el mismo otra vez si texto=None). mid: editar ese
    mensaje con el resultado; si no, mandar uno nuevo. Si falla, todo queda como estaba."""
    from . import app as webapp
    previo, creada = None, None
    try:
        if nueva:
            sid = creada = _crear_seccion(nueva[0], nueva[1], "TTS", texto)
        elif texto is not None:
            previo = (db.get_seccion(sid) or {}).get("texto_tts") or ""
            db.update_seccion(sid, texto_tts=texto)
        webapp._generate_tts(sid)
        if not _archivo(db.get_seccion(sid)):
            raise ValueError("no quedó audio (¿el texto está vacío?)")
        creada = previo = None
        webapp._aviso_colaborador(user, sid, "agregó la sección" if nueva else
                                  "cambió el texto de" if texto is not None else "generó de nuevo la voz de", "telegram")
        pre = ("✅ Listo: agregué la sección al final del evento. ¿La dejas ahí o la mueves? "
               "Para cambiarla de lugar toca «↕ Mover de lugar».\n\n") if nueva else "✅ Listo: voz generada.\n\n"
        cuerpo, botones = _pantalla("cols", user, "{}:{}".format(sid, eid or 0))
        if mid:
            _editar(token, chat, mid, pre + cuerpo, botones)
        else:
            _responder(token, chat, pre + cuerpo, botones=botones)
    except Exception as e:
        if not isinstance(e, ValueError):
            log.exception("No pude generar la voz de la sección #%s", sid)
        if previo is not None:
            db.update_seccion(sid, texto_tts=previo)
        if creada:
            _borrar_seccion(creada)
        volver = [[("« Secciones", "m:cole:{}".format(eid or 0))]] if nueva else \
            [[("« Sección", "m:cols:{}:{}".format(sid, eid or 0))]]
        _responder(token, chat, "❌ No pude generar la voz: {}{}".format(
            notify.esc(e), "\nEl texto quedó como estaba." if previo is not None else ""), botones=volver)


def _mandar_audio(token, chat, s):
    """Manda al chat el audio actual de la sección para escucharlo."""
    try:
        p = _archivo(s)
        ext = p.suffix.lower()
        if ext not in (".mp3", ".m4a", ".ogg", ".wav"):
            p, ext = audio.prepare(p, None), ".wav"
        if p.stat().st_size > 49 * 1024 * 1024:
            return _responder(token, chat, "Ese audio pesa más de 50 MB y Telegram no deja mandarlo; escúchalo en la página.")
        nombre = "".join(c for c in s["nombre"] if c not in '\\/:*?"<>|\r\n\t').strip() or "seccion"
        tipo = {".mp3": "audio/mpeg", ".m4a": "audio/mp4", ".ogg": "audio/ogg", ".wav": "audio/wav"}[ext]
        como_audio = ext in (".mp3", ".m4a")
        notify.send_document(token, chat, str(p), nombre + ext,
                             caption="🎧 <b>{}</b> · {}".format(notify.esc(s["nombre"]), _hm(s.get("duracion"))),
                             metodo="sendAudio" if como_audio else "sendDocument",
                             campo="audio" if como_audio else "document", tipo=tipo)
    except Exception as e:
        log.exception("No pude mandar el audio de la sección #%s", s.get("id"))
        _responder(token, chat, "❌ No pude mandarte el audio: {}".format(notify.esc(e)))


# ── Conexiones del nodo (Nodos → 🔗 Conexiones) ─────────────────────────────
#   ASL   enlaces directos con su modo; conectar como transceptor, monitor o
#         monitor local (ilink 3 / 2 / 8), cambiar el modo, desconectar uno o todos.
#   IRLP  el reflector o nodo activo; conectar (decode) o desconectar (end).
#   Ver: lectura en adelante · conectar y desconectar: operador o admin.
CON_ACCIONES = ("conn", "conm", "condx", "conx", "conf")
FAV_PAG = 8
# Dónde busca AllScan su favorites.ini (CfgModel.php: favsIniLoc), en ASL3 y en HamVOIP
FAV_ARCHIVOS = ("/var/www/html/allscan/favorites.ini", "/var/www/html/supermon/favorites.ini",
                "/srv/http/allscan/favorites.ini", "/srv/http/supermon/favorites.ini", "/etc/allscan/favorites.ini")


def _favoritos(node):
    """[(etiqueta, nodo)] de los favoritos de AllScan: la sección [general] y la del nodo."""
    import re
    for ruta in FAV_ARCHIVOS:
        try:
            with open(ruta, encoding="utf-8", errors="replace") as f:
                lineas = f.read().splitlines()
        except OSError:
            continue
        out, seccion, etiqueta = [], "", None
        for ln in lineas:
            ln = ln.strip()
            if not ln or ln.startswith(";"):
                continue
            m = re.match(r"^\[(.+)\]$", ln)
            if m:
                seccion = m.group(1).strip()
                continue
            if seccion not in ("general", str(node)):
                continue
            m = re.match(r'^(label|cmd)\[\]\s*=\s*"?(.*?)"?\s*$', ln)
            if not m:
                continue
            if m.group(1) == "label":
                etiqueta = m.group(2).strip()
                continue
            n = re.search(r"\bilink\s+\d+\s+(\d{3,7})\b", m.group(2))
            if n and etiqueta and n.group(1) not in {x[1] for x in out}:
                out.append((etiqueta, n.group(1)))
            etiqueta = None
        return out
    return []
CON_MODOS = [("transceptor", "🔁 Transceptor"), ("monitor", "👂 Monitor"), ("monitor_local", "🏠 Monitor local")]
MODO_ICO = {"transceptor": "🔁", "monitor": "👂", "conectando": "⏳"}
MODOS_AYUDA = ("🔁 <b>Transceptor</b>: se oyen y se hablan los dos nodos.\n"
               "👂 <b>Monitor</b>: este nodo oye al otro, pero no le manda audio.\n"
               "🏠 <b>Monitor local</b>: como monitor, pero lo que llega solo sale por el radio de este nodo "
               "(no pasa a los demás nodos conectados).")


def _sistema():
    from . import backends
    cfg = settings.load()
    kind = cfg.get("backend") or "auto"
    if kind == "auto":
        kind = backends.detect()
    return kind, cfg


def _nombre_nodo(d):
    return " · ".join(x for x in ((d or {}).get("indicativo"), (d or {}).get("descripcion"),
                                  (d or {}).get("ubicacion")) if x)[:70]


def _pantalla_con(cual, user, arg):
    from . import sessions
    op = _gestor(user)
    abajo = [("🔄 Actualizar", "m:con"), ("« Nodos", "m:nodos"), VOLVER]
    kind, cfg = _sistema()
    if kind not in ("asl", "irlp"):
        return "Este nodo no es ASL ni IRLP: no hay conexiones que manejar.", [[("« Nodos", "m:nodos"), VOLVER]]
    try:
        st = sessions.status(cfg)
    except Exception as e:
        return "❌ No pude leer las conexiones: {}".format(notify.esc(e)), [abajo]
    if kind == "irlp":
        return _pantalla_irlp(cual, st, op, abajo)

    enlaces = sorted(st.get("enlaces") or [], key=lambda e: e["nodo"])
    por_nodo = {e["nodo"]: e for e in enlaces}
    if cual == "condq":
        if arg == "all":
            return ("⛔ <b>¿Desconectar todos los enlaces del nodo {}?</b>\nSon {}: {}.".format(
                notify.esc(st["nodo"]), len(enlaces), ", ".join(e["nodo"] for e in enlaces)),
                [[("✅ Sí, desconectar todos", "m:condx:all")], [("Cancelar", "m:con")]])
        e = por_nodo.get(arg)
        if not e:
            return "El nodo {} ya no está conectado.".format(notify.esc(arg)), [abajo]
        return ("✖ <b>¿Desconectar el nodo {}?</b>{}".format(
            notify.esc(arg), "\n" + notify.esc(_nombre_nodo(e)) if _nombre_nodo(e) else ""),
            [[("✅ Sí, desconectar", "m:condx:" + arg)], [("Cancelar", "m:conl:" + arg)]])
    if cual == "conl":
        e = por_nodo.get(arg)
        if not e:
            return "El nodo {} ya no está conectado.".format(notify.esc(arg)), [[("« Conexiones", "m:con"), VOLVER]]
        t = ["🔗 <b>Nodo {}</b>".format(notify.esc(arg))]
        if _nombre_nodo(e):
            t.append(notify.esc(_nombre_nodo(e)))
        t += ["", "Modo: {} {}".format(MODO_ICO.get(e.get("modo"), "•"), notify.esc(e.get("modo") or "?")),
              "Conectado hace {} · {}".format(_hm(e.get("segundos")), "lo conectamos nosotros" if e.get("direccion") == "OUT"
                                               else "él se conectó a nosotros")]
        if e.get("transmitiendo"):
            t.append("🔊 Está transmitiendo ahora")
        filas = []
        if op:
            t += ["", "Puedes cambiarle el modo:", MODOS_AYUDA]
            filas = [[(lbl + (" ✓" if m == e.get("modo") else ""), "m:conm:{}:{}".format(arg, m)) for m, lbl in CON_MODOS[:2]],
                     [("{}".format(CON_MODOS[2][1]), "m:conm:{}:monitor_local".format(arg)), ("✖ Desconectar", "m:condq:" + arg)]]
        filas.append([("« Conexiones", "m:con"), VOLVER])
        return "\n".join(t), filas

    # con: la lista
    loc = _nombre_nodo(st.get("local"))
    t = ["🔗 <b>Conexiones del nodo {}</b>{}".format(notify.esc(st["nodo"]), "\n" + notify.esc(loc) if loc else "")]
    estado = [x for x, si in (("📥 recibiendo", st.get("rx")), ("📤 transmitiendo", st.get("tx"))) if si]
    if estado:
        t.append(" · ".join(estado))
    t.append("")
    if not enlaces:
        t.append("Sin conexiones en este momento.")
    for e in enlaces:
        nom = e.get("indicativo") or ""
        t.append("{} <b>{}</b>{} · {} · {}{}".format(
            MODO_ICO.get(e.get("modo"), "•"), notify.esc(e["nodo"]), " " + notify.esc(nom) if nom else "",
            notify.esc(e.get("modo") or "?"), _hm(e.get("segundos")), " · 🔊" if e.get("transmitiendo") else ""))
    if st.get("total_red"):
        t += ["", "🌐 {} nodos en total en la red conectada.".format(st["total_red"])]
    filas = []
    if op:
        botones = [("{} {}{}".format(MODO_ICO.get(e.get("modo"), "•"), e["nodo"], " " + e["indicativo"] if e.get("indicativo") else ""),
                    "m:conl:" + e["nodo"]) for e in enlaces[:20]]
        filas += [botones[i:i + 2] for i in range(0, len(botones), 2)]
        fila = [("➕ Conectar nodo", "m:conn")]
        if enlaces:
            fila.append(("⛔ Desconectar todos", "m:condq:all"))
        filas.append(fila)
        if enlaces:
            t += ["", "Toca un nodo para cambiarle el modo o desconectarlo."]
    filas.append(abajo)
    return "\n".join(t), filas


def _pantalla_irlp(cual, st, op, abajo):
    activo = st.get("activo") or ""
    if cual == "condq":
        if not activo:
            return "El nodo no está conectado a nada.", [abajo]
        return "✖ <b>¿Desconectar de {}?</b>".format(notify.esc(activo)), \
            [[("✅ Sí, desconectar", "m:condx:end")], [("Cancelar", "m:con")]]
    t = ["🔗 <b>Conexión IRLP</b>{}".format(" · nodo " + notify.esc(st["nodo"]) if st.get("nodo") else ""), ""]
    if activo:
        t.append("Conectado a <b>{}</b>".format(notify.esc(activo)))
        if st.get("red"):
            t.append("👥 {} nodos más en ese reflector".format(len(st["red"])))
    else:
        t.append("Sin conexión en este momento.")
    estado = [x for x, si in (("📥 recibiendo (COS)", st.get("cos")), ("📤 transmitiendo (PTT)", st.get("ptt"))) if si]
    if estado:
        t.append(" · ".join(estado))
    filas = []
    if op:
        fila = [("➕ Conectar", "m:conn")]
        if activo:
            fila.append(("✖ Desconectar", "m:condq:end"))
        filas.append(fila)
    filas.append(abajo)
    return "\n".join(t), filas


def _boton_con(token, chat, mid, user, cual, arg, avisa, tg):
    if not _gestor(user):
        return avisa("Solo un operador o el administrador pueden conectar o desconectar.", True)
    kind, _cfg = _sistema()
    if cual == "conx":
        _espera_quitar(tg)
        avisa("Cancelado")
        texto, botones = _pantalla("con", user)
        return _editar(token, chat, mid, texto, botones)
    if cual == "conn":
        _espera_poner(tg, modo="nodo")
        avisa("")
        pide = "✍ Escríbeme el número del {}.".format(
            "nodo o reflector IRLP (por ejemplo 9990)" if kind == "irlp" else "nodo ASL (por ejemplo 59624)")
        favs = _favoritos(_cfg.get("node") or "") if kind == "asl" else []
        if not favs:
            return _editar(token, chat, mid, "➕ <b>Conectar</b>\n\n" + pide, [[("Cancelar", "m:conx")]])
        from . import sessions
        try:
            conectados = {e["nodo"] for e in sessions.status(_cfg).get("enlaces") or []}
        except Exception:
            conectados = set()
        npag = (len(favs) + FAV_PAG - 1) // FAV_PAG
        pag = max(0, min(_ints(arg)[0], npag - 1))
        def boton(et, n):                           # el número primero: las etiquetas largas se cortan
            base = et[:-len(n)].rstrip(" ,") if et.endswith(n) else et
            return ("{} {} · {}".format("✅" if n in conectados else "⭐", n, base))[:56]
        filas = [[(boton(et, n), "m:conf:" + n)] for et, n in favs[pag * FAV_PAG:(pag + 1) * FAV_PAG]]
        nav = []
        if pag > 0:
            nav.append(("◀ Anteriores", "m:conn:{}".format(pag - 1)))
        if pag < npag - 1:
            nav.append(("Siguientes ▶", "m:conn:{}".format(pag + 1)))
        if nav:
            filas.append(nav)
        filas.append([("Cancelar", "m:conx")])
        return _editar(token, chat, mid, "➕ <b>Conectar</b>\n\n⭐ Elige uno de tus favoritos de AllScan{}, o {}\n"
                                         "✅ = ya está conectado (tócalo para cambiarle el modo).".format(
                                             " (página {} de {})".format(pag + 1, npag) if npag > 1 else "",
                                             pide[2].lower() + pide[3:]), filas)
    if cual == "conf":                              # eligió un favorito
        if not arg.isdigit():
            return avisa("Nodo inválido.", True)
        _espera_quitar(tg)
        avisa("")
        texto, botones = _pantalla_modo(arg, user)
        return _editar(token, chat, mid, texto, botones)
    if cual == "conm":
        destino, _, modo = arg.partition(":")
        avisa("Conectando {}…".format(destino))
        _editar(token, chat, mid, "⏳ Conectando {}…".format(notify.esc(destino)), None)
        return threading.Thread(target=_con_hacer, args=(token, chat, mid, user, "conectar", destino, modo or "transceptor"),
                                daemon=True).start()
    if cual == "condx":
        avisa("Desconectando…")
        _editar(token, chat, mid, "⏳ Desconectando…", None)
        return threading.Thread(target=_con_hacer, args=(token, chat, mid, user, "desconectar", arg), daemon=True).start()
    avisa("Botón desconocido")


def _con_hacer(token, chat, mid, user, accion, destino, modo="transceptor"):
    """Conecta o desconecta (en un hilo: Asterisk o IRLP tardan unos segundos) y vuelve a la lista."""
    from . import links, sessions
    kind, cfg = _sistema()
    try:
        if accion == "conectar":
            cmd = sessions.action(cfg, "conectar", destino, modo if kind == "asl" else "transceptor")
            que = "🔗 Conecté el nodo {} como {}".format(destino, links.ASL_MODO_NOMBRE.get(modo, modo)) if kind == "asl" \
                else "🔗 Conecté a {}".format(destino)
        elif destino in ("all", "end", ""):
            cmd = sessions.action(cfg, "desconectar_todo")
            que = "⛔ Desconecté todos los enlaces" if kind == "asl" else "✖ Desconecté IRLP"
        else:
            cmd = sessions.action(cfg, "desconectar", destino)
            que = "✖ Desconecté el nodo {}".format(destino)
        log.info("%s desde Telegram: %s", user["usuario"], cmd)
        time.sleep(4 if accion == "conectar" else 2)    # que la lista ya muestre el cambio
        pre = notify.esc(que) + ".\n\n"
        if kind == "asl" and destino not in ("all", "end", ""):
            with sessions._cache_lock:
                sessions._cache["key"] = None
            sigue = destino in {e["nodo"] for e in sessions.status(cfg).get("enlaces") or []}
            if accion == "desconectar" and sigue:
                pre = "⚠ Mandé desconectar el nodo {} pero sigue conectado (¿se reconecta desde el otro lado?).\n\n".format(
                    notify.esc(destino))
            elif accion == "conectar" and not sigue:
                pre = "⏳ Mandé conectar el nodo {}; todavía no aparece. Toca 🔄 Actualizar en unos segundos.\n\n".format(
                    notify.esc(destino))
    except Exception as e:
        log.warning("Conexiones desde Telegram (%s): %s", user["usuario"], e)
        pre = "❌ No pude: {}\n\n".format(notify.esc(e))
    try:
        texto, botones = _pantalla("con", user)
        _editar(token, chat, mid, pre + texto, botones)
    except Exception:
        log.exception("Conexiones desde Telegram")


def _nodo_recibido(token, chat, mid, user, texto, tg):
    from . import sessions
    kind, cfg = _sistema()
    n = "".join(c for c in texto if c.isdigit())
    cancelar = [("Cancelar", "m:conx")]
    if not (4 <= len(n) <= 6 if kind == "irlp" else 3 <= len(n) <= 7) or len(n) != len(texto.strip()):
        return _responder(token, chat, "Escríbeme solo el número del {} ({} dígitos).".format(
            "nodo o reflector" if kind == "irlp" else "nodo", "4 a 6" if kind == "irlp" else "3 a 7"),
            botones=[cancelar], a=mid)
    _espera_quitar(tg)
    texto, botones = _pantalla_modo(n, user)
    return _responder(token, chat, texto, botones=botones, a=mid)


def _pantalla_modo(n, user):
    """¿Cómo lo conecto? (después de escribir el número o de elegir un favorito)."""
    from . import sessions
    kind, cfg = _sistema()
    cancelar = [("« Favoritos", "m:conn:0"), ("Cancelar", "m:conx")]
    if kind == "irlp":
        return "🔗 ¿Conectar a <b>{}</b>?".format(notify.esc(n)), \
            [[("✅ Sí, conectar", "m:conm:{}:x".format(n))], [("Cancelar", "m:conx")]]
    nom = _nombre_nodo(sessions.lookup([n]).get(n))
    fav = next((et for et, x in _favoritos(cfg.get("node") or "") if x == n), "")
    ya = ""
    try:
        e = {x["nodo"]: x for x in sessions.status(cfg).get("enlaces") or []}.get(n)
        if e:
            ya = "\nYa está conectado como <b>{}</b>; elige otro modo para cambiarlo.".format(notify.esc(e.get("modo") or "?"))
    except Exception:
        pass
    return ("🔗 <b>Nodo {}</b>{}{}\n\n¿Cómo lo conecto?\n\n{}".format(
        notify.esc(n), "\n" + notify.esc(nom or fav) if (nom or fav) else "\n(no está en la lista de nodos de este equipo)",
        ya, MODOS_AYUDA),
        [[(lbl, "m:conm:{}:{}".format(n, m))] for m, lbl in CON_MODOS] + [cancelar])
