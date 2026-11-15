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

A quien no está vinculado solo se le explica cómo vincularse.
"""
import datetime as dt
import json
import logging
import random
import threading
import time

from . import auth, db, health, notify, numeracion, paths, settings, sysmon

log = logging.getLogger("hamna.bot")

CODE_SECS = 10 * 60
_rand = random.SystemRandom()
_lock = threading.Lock()
_codes = {}                     # código → (usuario_id, vence)
_estado = {"activo": False, "error": "", "bot": "", "chats": {}, "token": ""}
_COMANDOS = [
    ("estado", "Qué está al aire ahora"),
    ("proximo", "Los siguientes eventos"),
    ("salud", "Temperatura, voltaje, disco y memoria del nodo"),
    ("historial", "Las últimas emisiones"),
    ("ayuda", "Qué puedo hacer"),
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
def _responder(token, chat, texto, botones=None, a=None):
    p = {"chat_id": chat, "text": texto, "parse_mode": "HTML", "disable_web_page_preview": "true"}
    if a:
        p["reply_to_message_id"] = a
    if botones:
        p["reply_markup"] = teclado(botones)
    notify._call(token, "sendMessage", p)


def teclado(filas):
    return json.dumps({"inline_keyboard": [[{"text": t, "callback_data": d} for t, d in fila] for fila in filas]})


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
    if not texto:
        return
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
        cmd, arg = "ayuda", ""
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
    resp = _comando(cmd, user)
    if resp:
        _responder(token, chat, resp, a=None if privado else m.get("message_id"))


def _vincular(token, chat, quien, code, msg_id):
    uid = _usar_codigo(code.strip())
    if not uid:
        return _responder(token, chat, "❌ Ese código no existe o ya venció. Pide uno nuevo en HAMNA → Mi perfil.")
    tg_nombre = "@" + quien["username"] if quien.get("username") else \
        " ".join(x for x in (quien.get("first_name"), quien.get("last_name")) if x)
    auth.set_tg(uid, str(quien.get("id")), tg_nombre)
    u = auth.user_by_tg(quien.get("id")) or {}
    log.info("Telegram %s vinculado con el usuario %s", tg_nombre, u.get("usuario"))
    _responder(token, chat, "✅ Listo, <b>{}</b>. Tu Telegram quedó vinculado con tu usuario de HAMNA ({}).\n\n{}".format(
        notify.esc(u.get("nombre") or u.get("usuario")), notify.esc(u.get("rol_nombre")), _ayuda(u)))


def _ayuda(user):
    n = _nivel(user)
    t = ["<b>Lo que puedo hacer</b>",
         "/estado · qué está al aire ahora",
         "/proximo · los siguientes eventos"]
    if n >= auth.ROLES["lectura"]:
        t += ["/salud · temperatura, voltaje, disco y memoria", "/historial · las últimas emisiones"]
    if n >= auth.ROLES["operador"]:
        t += ["", "En los avisos te pongo botones para <b>detener</b>, pasar a la <b>siguiente sección</b>, "
                  "<b>transmitir ya</b> o <b>saltar</b> una emisión (siempre te pido confirmar)."]
    return "\n".join(t)


def _comando(cmd, user):
    n = _nivel(user)
    if cmd in ("ayuda", "help", "start"):
        return _ayuda(user)
    if cmd == "estado":
        return _txt_estado()
    if cmd in ("proximo", "próximo", "proximos"):
        return _txt_proximo(user)
    if cmd in ("salud", "historial"):
        if n < auth.ROLES["lectura"]:
            return "Ese comando no está disponible para tu usuario."
        return _txt_salud() if cmd == "salud" else _txt_historial()
    return "No conozco ese comando.\n\n" + _ayuda(user)


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
             "skip": "✅ Sí, saltar esta vez"}


def _original(data):
    p = data.split(":")
    if p[0] in ("sig", "det"):
        return [[("⏭ Siguiente sección", "sig:" + p[1]), ("⏹ Detener", "det:" + p[1])]]
    return [[("▶ Transmitir ya", "tx:{}:{}".format(p[1], p[2])), ("⏸ Saltar esta vez", "skip:{}:{}".format(p[1], p[2]))]]


def _boton(token, q):
    data = q.get("data") or ""
    msg = q.get("message") or {}
    chat = (msg.get("chat") or {}).get("id")
    mid = msg.get("message_id")

    def avisa(texto, alerta=False):
        notify._call(token, "answerCallbackQuery", {"callback_query_id": q["id"], "text": texto[:190],
                                                    "show_alert": "true" if alerta else "false"})

    def teclas(filas):
        notify._call(token, "editMessageReplyMarkup", {"chat_id": chat, "message_id": mid,
                                                       "reply_markup": teclado(filas) if filas else
                                                       json.dumps({"inline_keyboard": []})})
    user = auth.user_by_tg((q.get("from") or {}).get("id"))
    if not user:
        return avisa("Primero vincula tu Telegram en HAMNA → Mi perfil.", True)
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
    accion, quien = p[1], notify.esc(user.get("nombre") or user["usuario"])
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
