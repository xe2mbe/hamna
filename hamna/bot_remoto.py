"""
HAMNA Web — pantallas del bot para controlar OTROS nodos (las órdenes viajan con control.py).

Botones («r:» + qué + nodo + …, máx. 64 bytes):
  r:n:N               menú del nodo N
  r:q:N:<acc>         pedirle datos al nodo (estado, con, an, cl, ev) → «⏳ Preguntando…»
  r:v:N:<pantalla>    otra vista con los datos que ya llegaron (favoritos, confirmar…)
  r:x:N:<acc>:…       una acción en el nodo (conectar, desconectar, transmitir…)
Cuando el nodo contesta, control.py llama a resultado() y se edita el mismo mensaje.
"""
import datetime as dt
import logging
import threading

from . import auth, control, db, notify, settings

log = logging.getLogger("hamna.bot.remoto")

FAV_PAG = 8
_vista = {}                      # (chat, mensaje) → {"nodo", "acc", "datos"} lo último que mostró ese mensaje
_lock = threading.Lock()
MODOS = {"t": ("transceptor", "🔁 Transceptor"), "m": ("monitor", "👂 Monitor"), "l": ("monitor_local", "🏠 Monitor local")}
MODO_ICO = {"transceptor": "🔁", "monitor": "👂", "conectando": "⏳"}
PANTALLA = {"estado": "estado", "con": "con", "cn": "con", "cd": "con", "an": "an", "aa": "an", "ap": "an",
            "cl": "cl", "ev": "ev", "et": "ev", "ed": "ev", "gr": "ev"}
PREGUNTA = {"estado": "la salud", "con": "las conexiones", "an": "los anuncios", "cl": "el clima y las alertas", "ev": "las emisiones"}


def _bot():
    from . import bot
    return bot


def _esc(x):
    return notify.esc(x if x is not None else "")


def _hm(s):
    return _bot()._hm(s)


def _volver_nodo(n):
    return ("« Nodo " + n, "r:n:" + n)


def _cuando(s):
    try:
        t = dt.datetime.strptime(s, "%Y-%m-%d %H:%M")
    except (TypeError, ValueError):
        return s or ""
    return _bot()._cuando(t)


# ── Lista de nodos (en «🗺 Nodos») ────────────────────────────────────────────
def botones_nodos(user):
    info = control.nodos()
    filas = []
    for n, nv in control.visibles(user):
        i = info.get(n) or {}
        filas.append([("{} 🎛 {}{}".format("🟢" if i.get("en_linea") else "⚪", n,
                                          " · " + i["estacion"][:22] if i.get("estacion") else ""), "r:n:" + n)])
    return filas


# ── Pantallas ────────────────────────────────────────────────────────────────
def _menu_nodo(n, user):
    i = control.nodos().get(n)
    nv = control.nivel(user, n)
    if not i or nv < control.VER:
        return "No tienes acceso al nodo {}.".format(_esc(n)), [[("« Nodos", "m:nodos")]]
    t = ["🎛 <b>Nodo {}</b>{}".format(_esc(n), " · " + _esc(i["estacion"]) if i.get("estacion") else ""),
         "{} {} v{}".format("🟢 Escuchando órdenes ·" if i["en_linea"] else "⚪ No está escuchando ahora ·", _esc(i["app"]), _esc(i["version"]))]
    if not i["en_linea"]:
        t.append("La última vez fue hace {}. Si sigue así, revisa en ese nodo: Ajustes → Panel de nodos → «Permitir que el hub controle este nodo».".format(
            _bot()._falta(i["edad"])))
    t.append("Puedes: " + ("ver y controlar" if nv >= control.CONTROLAR else "solo ver"))
    caps = i.get("caps") or []
    botones = [("🩺 Estado y salud", "r:q:{}:estado".format(n))]
    if "conexiones" in caps:
        botones.append(("🔗 Conexiones", "r:q:{}:con".format(n)))
    if "anuncios" in caps:
        botones.append(("📢 Anuncios", "r:q:{}:an".format(n)))
    if "clima" in caps:
        botones.append(("🌤 Clima y alertas", "r:q:{}:cl".format(n)))
    if "emisiones" in caps:
        botones.append(("📡 Emisiones", "r:q:{}:ev".format(n)))
    filas = [botones[k:k + 2] for k in range(0, len(botones), 2)]
    filas.append([("« Nodos", "m:nodos"), _bot().VOLVER])
    return "\n".join(t), filas


def _p_estado(n, d, user, pre=""):
    t = [pre + "🩺 <b>Nodo {}</b>{} · {} v{}".format(_esc(n), " · " + _esc(d.get("estacion")) if d.get("estacion") else "",
                                                   _esc(d.get("app")), _esc(d.get("version")))]
    if d.get("emision"):
        t += ["", d["emision"]]          # ya viene en HTML del nodo
    t += ["", d.get("salud") or ""]
    return "\n".join(t), [[("🔄 Actualizar", "r:q:{}:estado".format(n)), _volver_nodo(n)]]


def _p_con(n, d, user, pre=""):
    ctl = control.nivel(user, n) >= control.CONTROLAR
    abajo = [("🔄 Actualizar", "r:q:{}:con".format(n)), _volver_nodo(n)]
    if d.get("sistema") == "irlp":
        t = [pre + "🔗 <b>IRLP · nodo {}</b>".format(_esc(n)), ""]
        t.append("Conectado a <b>{}</b>".format(_esc(d["activo"])) if d.get("activo") else "Sin conexión en este momento.")
        if not d.get("habilitado", True):
            t.append("⛔ Nodo deshabilitado.")
        filas = []
        if ctl:
            fila = [("➕ Conectar", "r:v:{}:fc".format(n))]
            if d.get("activo"):
                fila.append(("✖ Desconectar", "r:v:{}:dq:end".format(n)))
            filas.append(fila)
        return "\n".join(t), filas + [abajo]
    enl = d.get("enlaces") or []
    t = [pre + "🔗 <b>Conexiones del nodo {}</b>{}".format(_esc(n), "\n" + _esc(d["local"]) if d.get("local") else "")]
    est = [x for x, si in (("📥 recibiendo", d.get("rx")), ("📤 transmitiendo", d.get("tx"))) if si]
    if est:
        t.append(" · ".join(est))
    t.append("")
    if not enl:
        t.append("Sin conexiones en este momento.")
    for e in enl:
        t.append("{} <b>{}</b>{} · {} · {}{}".format(MODO_ICO.get(e.get("modo"), "•"), _esc(e["nodo"]),
                                                    " " + _esc(e["indicativo"]) if e.get("indicativo") else "", _esc(e.get("modo") or "?"),
                                                    _hm(e.get("segundos")), " · 🔊" if e.get("transmitiendo") else ""))
    if d.get("total_red"):
        t += ["", "🌐 {} nodos en total en la red conectada.".format(d["total_red"])]
    filas = []
    if ctl:
        b = [("{} {}{}".format(MODO_ICO.get(e.get("modo"), "•"), e["nodo"], " " + e["indicativo"] if e.get("indicativo") else "")[:40],
              "r:v:{}:l:{}".format(n, e["nodo"])) for e in enl[:16]]
        filas += [b[k:k + 2] for k in range(0, len(b), 2)]
        fila = [("➕ Conectar nodo", "r:v:{}:fc".format(n))]
        if enl:
            fila.append(("⛔ Desconectar todos", "r:v:{}:dq:all".format(n)))
        filas.append(fila)
    return "\n".join(t), filas + [abajo]


def _p_an(n, d, user, pre=""):
    ctl = control.nivel(user, n) >= control.CONTROLAR
    lst = d.get("anuncios") or []
    t = [pre + "📢 <b>Anuncios del nodo {}</b>".format(_esc(n))]
    if d.get("al_aire"):
        t.append("📡 Al aire ahora: <b>{}</b>".format(_esc(d["al_aire"])))
    t.append("")
    if not lst:
        t.append("Este nodo no tiene anuncios.")
    for a in lst:
        t.append("{} <b>{}</b>{}".format("▶" if a["activo"] else "⏸", _esc(a["nombre"]),
                                         " · {} · {}".format(_cuando(a["proximo"]), "RF + Net" if a.get("red") else "RF")
                                         if a["activo"] and a.get("proximo") else " · pausado" if not a["activo"] else ""))
    filas = []
    if ctl and lst:
        b = [("📢 " + a["nombre"][:30], "r:v:{}:ad:{}".format(n, a["id"])) for a in lst[:20]]
        filas += [b[k:k + 2] for k in range(0, len(b), 2)]
        t += ["", "Toca un anuncio para transmitirlo ahora o pausarlo."]
    return "\n".join(t), filas + [[("🔄 Actualizar", "r:q:{}:an".format(n)), _volver_nodo(n)]]


def _p_cl(n, d, user, pre=""):
    t = [pre + "🌤 <b>Clima y alertas · nodo {}</b>{}".format(_esc(n), " · " + _esc(d["lugar"]) if d.get("lugar") else "")]
    if not d.get("configurado"):
        t.append("Ese nodo no tiene ubicación (Ajustes → Clima).")
    elif d.get("error"):
        t.append("⚠ " + _esc(d["error"]))
    elif d.get("clima"):
        c = d["clima"]
        t += ["", "{}, {} (sensación {}).".format(_esc(c.get("condicion", "")).capitalize(), _esc(c.get("temperatura", "")), _esc(c.get("sensacion", ""))),
              "Humedad {} · viento {}{}".format(_esc(c.get("humedad", "")), _esc(c.get("viento", "")),
                                                " · rachas " + _esc(c["racha"]) if c.get("racha") else ""),
              _esc(c.get("pronostico", "")), "<i>Fuente: {}</i>".format(_esc(d.get("fuente", "")))]
    al = d.get("alertas") or {}
    act = al.get("activas") or {}
    t += ["", "⚠ <b>Alertas</b>: " + (" · ".join(x for x, si in (("clima", act.get("clima")), ("pronóstico", act.get("pronostico")),
                                                             ("sismos", act.get("sismos"))) if si) or "apagadas")]
    if al.get("fuera"):
        t.append("Pasaron el límite ahora: " + _esc(", ".join(al["fuera"])))
    for p in al.get("pronostico") or []:
        t.append("⛈ {} desde {}".format(_esc(p["nombre"]), _cuando(p["desde"])))
    for s in al.get("sismos") or []:
        t.append("🌎 M{:.1f} {} · {}{}".format(s["mag"], _esc(s["lugar"]), dt.datetime.fromtimestamp(s["t"]).strftime("%d/%m %H:%M"),
                                              " ✓ avisado" if s.get("avisado") else ""))
    for h in al.get("historial") or []:
        t.append("📣 {} · {}".format(_esc(h.get("nombre")), _cuando(h.get("cuando"))))
    return "\n".join(t), [[("🔄 Actualizar", "r:q:{}:cl".format(n)), _volver_nodo(n)]]


def _p_ev(n, d, user, pre=""):
    ctl = control.nivel(user, n) >= control.CONTROLAR
    t = [pre + "📡 <b>Emisiones · nodo {}</b>".format(_esc(n)), "", d.get("estado") or ""]
    if d.get("grabando"):
        t.append("⏺ Grabando «{}»".format(_esc(d["grabando"])))
    filas = []
    if ctl:
        if d.get("al_aire"):
            filas.append([("⏹ Detener", "r:v:{}:eq".format(n))])
        else:
            for e in (d.get("eventos") or [])[:8]:
                filas.append([("▶ {}{}".format(e["nombre"][:28], " · " + _cuando(e["proximo"]) if e.get("proximo") else "")[:56],
                               "r:v:{}:ec:{}".format(n, e["id"]))])
            if d.get("eventos"):
                t += ["", "Toca un evento para transmitirlo ahora."]
        filas.append([("⏹ Detener grabación", "r:x:{}:gs".format(n)) if d.get("grabando") else ("⏺ Grabar", "r:x:{}:gr".format(n))])
    return "\n".join(t), filas + [[("🔄 Actualizar", "r:q:{}:ev".format(n)), _volver_nodo(n)]]


PANTALLAS = {"estado": _p_estado, "con": _p_con, "an": _p_an, "cl": _p_cl, "ev": _p_ev}


def _vistas(n, v, arg, datos, user):
    """Pantallas que salen de los datos que ya llegaron (sin preguntar otra vez al nodo)."""
    d = datos or {}
    if v == "c":
        return _p_con(n, d, user)
    if v == "a":
        return _p_an(n, d, user)
    if v == "fc":
        grupos = d.get("favoritos") or []
        if len(grupos) > 1:
            filas = [[("📁 {} ({})".format(g["categoria"], len(g["favoritos"]))[:50], "r:v:{}:fk:{}:0".format(n, k))] for k, g in enumerate(grupos)]
            filas.append([("✍ Escribir el número", "r:v:{}:num".format(n))])
            filas.append([("Cancelar", "r:v:{}:c".format(n))])
            return "➕ <b>Conectar al nodo {}</b>\n\n📁 Elige una categoría de favoritos o escribe el número.".format(_esc(n)), filas
        return _vistas(n, "fk", "0:0", d, user)
    if v == "fk":
        grupos = d.get("favoritos") or []
        p = (arg or "0:0").split(":")
        ci, pag = int(p[0] or 0), int(p[1] if len(p) > 1 else 0)
        if not grupos:
            return _vistas(n, "num", "", d, user)
        ci = max(0, min(ci, len(grupos) - 1))
        g = grupos[ci]
        favs = g["favoritos"]
        npag = max(1, (len(favs) + FAV_PAG - 1) // FAV_PAG)
        pag = max(0, min(pag, npag - 1))
        con = {e["nodo"] for e in d.get("enlaces") or []}
        irlp = d.get("sistema") == "irlp"
        filas = [[("{} {}{}".format("✅" if f["nodo"] in con else "⭐", f["nodo"], " · " + f["nombre"] if f.get("nombre") else "")[:56],
                   ("r:x:{}:cn:{}:t" if irlp else "r:v:{}:m:{}").format(n, f["nodo"]))] for f in favs[pag * FAV_PAG:(pag + 1) * FAV_PAG]]
        nav = []
        if pag > 0:
            nav.append(("◀", "r:v:{}:fk:{}:{}".format(n, ci, pag - 1)))
        if pag < npag - 1:
            nav.append(("▶", "r:v:{}:fk:{}:{}".format(n, ci, pag + 1)))
        if nav:
            filas.append(nav)
        filas.append([("✍ Escribir el número", "r:v:{}:num".format(n))] + ([("« Categorías", "r:v:{}:fc".format(n))] if len(grupos) > 1 else []))
        filas.append([("Cancelar", "r:v:{}:c".format(n))])
        return "➕ <b>Conectar al nodo {}</b>\n📁 {}{}\n✅ = ya está conectado.".format(
            _esc(n), _esc(g["categoria"]), " (página {} de {})".format(pag + 1, npag) if npag > 1 else ""), filas
    if v == "m":
        dest = arg
        return ("🔗 <b>¿Cómo conecto el {} al nodo {}?</b>\n{}".format(_esc(dest), _esc(n), _bot().MODOS_AYUDA),
                [[(MODOS["t"][1], "r:x:{}:cn:{}:t".format(n, dest)), (MODOS["m"][1], "r:x:{}:cn:{}:m".format(n, dest))],
                 [(MODOS["l"][1], "r:x:{}:cn:{}:l".format(n, dest))], [("Cancelar", "r:v:{}:c".format(n))]])
    if v == "l":
        e = next((x for x in d.get("enlaces") or [] if x["nodo"] == arg), None)
        if not e:
            return "El {} ya no estaba conectado.".format(_esc(arg)), [[("« Conexiones", "r:q:{}:con".format(n))]]
        t = "🔗 <b>{} en el nodo {}</b>{}\nModo: {} · conectado hace {}".format(
            _esc(arg), _esc(n), "\n" + _esc(" · ".join(x for x in (e.get("indicativo"), e.get("descripcion")) if x)) if e.get("indicativo") else "",
            _esc(e.get("modo")), _hm(e.get("segundos")))
        return t, [[(MODOS[k][1] + (" ✓" if MODOS[k][0] == e.get("modo") else ""), "r:x:{}:cn:{}:{}".format(n, arg, k)) for k in ("t", "m")],
                   [(MODOS["l"][1], "r:x:{}:cn:{}:l".format(n, arg)), ("✖ Desconectar", "r:v:{}:dq:{}".format(n, arg))],
                   [("« Conexiones", "r:v:{}:c".format(n))]]
    if v == "dq":
        que = "todos los enlaces" if arg == "all" else "IRLP" if arg == "end" else "el {}".format(arg)
        return "⛔ <b>¿Desconectar {} del nodo {}?</b>".format(_esc(que), _esc(n)), \
            [[("✅ Sí, desconectar", "r:x:{}:cd:{}".format(n, arg))], [("Cancelar", "r:v:{}:c".format(n))]]
    if v == "ad":
        a = next((x for x in d.get("anuncios") or [] if str(x["id"]) == arg), None)
        if not a:
            return "Ese anuncio ya no existe.", [[("« Anuncios", "r:q:{}:an".format(n))]]
        t = "📢 <b>{}</b> · nodo {}\n{}{}".format(_esc(a["nombre"]), _esc(n), "▶ Activo" if a["activo"] else "⏸ Pausado",
                                                " · próximo " + _cuando(a["proximo"]) if a.get("proximo") and a["activo"] else "")
        return t + "\n\n¿Transmitirlo ahora? Espera a que el canal esté libre.", [
            [("📡 Solo RF", "r:x:{}:aa:{}:l".format(n, a["id"])), ("📡 RF + Net", "r:x:{}:aa:{}:r".format(n, a["id"]))],
            [("⏸ Pausar" if a["activo"] else "▶ Activar", "r:x:{}:ap:{}:{}".format(n, a["id"], 0 if a["activo"] else 1))],
            [("« Anuncios", "r:v:{}:a".format(n))]]
    if v == "ec":
        e = next((x for x in d.get("eventos") or [] if str(x["id"]) == arg), None)
        if not e:
            return "Ese evento ya no existe.", [[("« Emisiones", "r:q:{}:ev".format(n))]]
        return "▶ <b>¿Transmitir «{}» ahora en el nodo {}?</b>\nDura {} aprox.".format(_esc(e["nombre"]), _esc(n), _hm(e.get("duracion"))), \
            [[("✅ Sí, transmitir", "r:x:{}:et:{}".format(n, e["id"]))], [("Cancelar", "r:q:{}:ev".format(n))]]
    if v == "eq":
        return "⏹ <b>¿Detener lo que está al aire en el nodo {}?</b>".format(_esc(n)), \
            [[("✅ Sí, detener", "r:x:{}:ed".format(n))], [("Cancelar", "r:q:{}:ev".format(n))]]
    return "No conozco esa opción.", [[_volver_nodo(n)]]


# ── Botones ──────────────────────────────────────────────────────────────────
def _acciones(acc, args):
    """Botón r:x → (orden, argumentos, texto de espera)."""
    if acc == "cn":
        dest, modo = args[0], MODOS.get(args[1] if len(args) > 1 else "t", MODOS["t"])[0]
        return "cn", {"destino": dest, "modo": modo}, "Conectando {}…".format(dest)
    if acc == "cd":
        return "cd", {"destino": args[0] if args else "all"}, "Desconectando…"
    if acc == "aa":
        return "aa", {"id": int(args[0]), "destino": "red" if (args[1:] or ["l"])[0] == "r" else "local"}, "Mandando el anuncio…"
    if acc == "ap":
        return "ap", {"id": int(args[0]), "on": (args[1:] or ["1"])[0] == "1"}, "Cambiando…"
    if acc == "et":
        return "et", {"id": int(args[0])}, "Iniciando…"
    if acc == "ed":
        return "ed", {}, "Deteniendo…"
    if acc == "gr":
        return "gr", {}, "Iniciando la grabación…"
    if acc == "gs":
        return "gr", {"parar": True}, "Deteniendo la grabación…"
    raise ValueError("Botón desconocido")


def boton(token, q, user, data, avisa):
    bot = _bot()
    msg = q.get("message") or {}
    chat, mid = (msg.get("chat") or {}).get("id"), msg.get("message_id")
    p = data.split(":")
    if len(p) < 3:
        return avisa("Botón desconocido")
    que, n = p[1], p[2]
    try:
        if que == "n":
            texto, filas = _menu_nodo(n, user)
            avisa("")
            return bot._editar(token, chat, mid, texto, filas)
        if control.nivel(user, n) < control.VER:
            return avisa("No tienes acceso al nodo {}.".format(n), True)
        if que == "q":
            acc = p[3] if len(p) > 3 else "estado"
            control.nueva(n, acc, {}, user, chat, mid)
            avisa("")
            return bot._editar(token, chat, mid, "⏳ Preguntándole {} al nodo {}…".format(PREGUNTA.get(acc, "eso"), _esc(n)),
                               [[("Cancelar", "r:n:" + n)]])
        if que == "v":
            v, arg = (p[3] if len(p) > 3 else ""), ":".join(p[4:])
            if v not in ("c", "a") and control.nivel(user, n) < control.CONTROLAR:
                return avisa("Solo puedes ver ese nodo.", True)
            if v == "num":
                bot._espera_poner((q.get("from") or {}).get("id"), modo="rnodo", nodo=n)
                avisa("")
                return bot._editar(token, chat, mid, "✍ Escríbeme el número del nodo al que conecto el {}.".format(_esc(n)),
                                   [[("Cancelar", "r:v:{}:c".format(n))]])
            with _lock:
                vista = dict(_vista.get((str(chat), mid)) or {})
            if vista.get("nodo") != n:
                return avisa("Esa pantalla ya es vieja: toca Actualizar.", True)
            texto, filas = _vistas(n, v, arg, vista.get("datos"), user)
            avisa("")
            return bot._editar(token, chat, mid, texto, filas)
        if que == "x":
            if control.nivel(user, n) < control.CONTROLAR:
                return avisa("Solo puedes ver ese nodo.", True)
            acc, args, espera = _acciones(p[3] if len(p) > 3 else "", p[4:])
            control.nueva(n, acc, args, user, chat, mid)
            avisa(espera)
            return bot._editar(token, chat, mid, "⏳ {} (nodo {})".format(espera, _esc(n)), None)
        avisa("Botón desconocido")
    except ValueError as e:
        avisa(str(e), True)
    except Exception as e:
        log.exception("Botón %s", data)
        avisa("No pude: {}".format(e), True)


def texto(token, m, user, txt, esp):
    """Escribió el número del nodo al que conectar (modo «rnodo»)."""
    bot = _bot()
    chat, mid, tg = m["chat"]["id"], m.get("message_id"), (m.get("from") or {}).get("id")
    n = esp.get("nodo") or ""
    dest = "".join(c for c in txt if c.isdigit())
    if not (3 <= len(dest) <= 7) or len(dest) != len(txt.strip()):
        return bot._responder(token, chat, "Escríbeme solo el número del nodo (3 a 7 dígitos).", a=mid)
    bot._espera_quitar(tg)
    info = control.nodos().get(n) or {}
    if info.get("sistema") == "irlp":
        return bot._responder(token, chat, "🔗 ¿Conecto el nodo {} a {}?".format(_esc(n), _esc(dest)),
                              botones=[[("✅ Sí, conectar", "r:x:{}:cn:{}:t".format(n, dest))], [("Cancelar", "r:n:" + n)]], a=mid)
    t, filas = _vistas(n, "m", dest, {}, user)
    return bot._responder(token, chat, t, botones=filas, a=mid)


# ── Llegó la respuesta del nodo ──────────────────────────────────────────────
def _usuario(nombre):
    r = db.row("SELECT * FROM usuarios WHERE usuario=? AND activo=1", (nombre,))
    return dict(r) if r else None


def resultado(o):
    if not o or not o.get("chat") or not o.get("mensaje"):
        return
    token = (settings.load().get("tg_token") or "").strip()
    if not token:
        return
    bot = _bot()
    n, chat, mid = o["nodo"], o["chat"], int(o["mensaje"])
    user = _usuario(o["usuario"])
    if not user:
        return
    if o["estado"] == "vencida":
        return bot._editar(token, chat, mid, "⚠ El nodo {} no contestó a tiempo. ¿Está encendido y con internet?".format(_esc(n)),
                           [[("🔄 Intentar otra vez", "r:q:{}:{}".format(n, o["accion"] if o["accion"] in PREGUNTA else "estado"))], [_volver_nodo(n)]])
    r = o.get("resultado") or {}
    pant = PANTALLA.get(o["accion"], "estado")
    if not r.get("ok") and not r.get("datos"):
        return bot._editar(token, chat, mid, "❌ Nodo {}: {}".format(_esc(n), _esc(r.get("texto") or "no pudo")),
                           [[("🔄 Actualizar", "r:q:{}:{}".format(n, pant)), _volver_nodo(n)]])
    datos = r.get("datos") or {}
    with _lock:
        _vista[(str(chat), mid)] = {"nodo": n, "acc": pant, "datos": datos}
        if len(_vista) > 300:
            for k in list(_vista)[:100]:
                del _vista[k]
    pre = (("❌ " if not r.get("ok") else "") + _esc(r["texto"]) + "\n\n") if r.get("texto") else ""
    texto, filas = PANTALLAS[pant](n, datos, user, pre)
    bot._editar(token, chat, mid, texto[:4000], filas)
