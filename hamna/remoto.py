"""
Control desde el hub (lado del nodo) — el mismo archivo en HAMNA Web y en ASLSCAN.

Si en Ajustes están marcados «Reportar a un hub» y «Permitir que el hub controle
este nodo», el nodo le pregunta al hub, todo el tiempo, si hay órdenes para él
(POST api/remoto/control con su código de acceso). El hub contesta en cuanto
hay una o a los 25 s con nada; así funciona detrás de cualquier router: el
nodo es quien llama, nunca al revés.

Las órdenes son pocas y concretas (ver ACCIONES): leer las conexiones, conectar
o desconectar, ver y transmitir anuncios, ver el clima y las alertas (ASLSCAN),
ver y controlar las emisiones (HAMNA), ver la salud. El resultado viaja en la
siguiente pregunta al hub, que se lo muestra a quien la pidió por Telegram.
Quién puede pedir qué lo decide el hub (permisos por nodo).
"""
import json
import logging
import threading
import time

from . import VERSION, settings

APP = "ASLSCAN" if __name__.split(".")[0] == "aslscan" else "HAMNA"
log = logging.getLogger(__name__.split(".")[0] + ".remoto")
ESPERA_HUB = 45            # s que se espera la respuesta del hub (él contesta a los 25 s)
FAVS_MAX = 60
_estado = {"ok": 0.0, "error": "", "ordenes": 0, "hilo": None}


# ── Qué sabe hacer este nodo ─────────────────────────────────────────────────
def _hay(modulo):
    try:
        __import__(__name__.rsplit(".", 1)[0] + "." + modulo)
        return True
    except ImportError:
        return False


def capacidades():
    from . import backends
    cfg = settings.load()
    kind = cfg.get("backend") or "auto"
    if kind == "auto":
        kind = backends.detect()
    caps = ["estado"]
    if kind in ("asl", "irlp"):
        caps.append("conexiones")
    if _hay("anuncios"):
        caps.append("anuncios")
    if _hay("clima"):
        caps.append("clima")
    if _hay("engine"):
        caps.append("emisiones")
    return kind, caps


# ── Acciones ─────────────────────────────────────────────────────────────────
def _cfg_kind():
    from . import backends
    cfg = settings.load()
    kind = cfg.get("backend") or "auto"
    if kind == "auto":
        kind = backends.detect()
    return cfg, kind


def _estado_nodo(a):
    from . import bot
    cfg = settings.load()
    kind, caps = capacidades()
    d = {"app": APP, "version": VERSION, "nodo": str(cfg.get("node") or ""), "estacion": cfg.get("station_name") or "",
         "sistema": kind, "caps": caps, "salud": bot._txt_salud()}
    if "emisiones" in caps:
        d["emision"] = bot._txt_estado()
    return {"ok": True, "datos": d}


def _conexiones(a=None, aviso=""):
    from . import favoritos, sessions
    cfg, kind = _cfg_kind()
    if kind not in ("asl", "irlp"):
        return {"ok": False, "texto": "Este nodo no es ASL ni IRLP"}
    with sessions._cache_lock:
        sessions._cache["key"] = None
    st = sessions.status(cfg)
    if kind == "irlp":
        from . import irlpctl
        favs, cats = irlpctl.favoritos_todo()
    else:
        favs, cats = favoritos.asl_todo(cfg.get("node") or "")
    grupos, n = [], 0
    for c, fs in favoritos.agrupar(favs, cats):
        lst = [{"nodo": f["nodo"], "nombre": f.get("nombre") or ""} for f in fs][:max(0, FAVS_MAX - n)]
        n += len(lst)
        if lst:
            grupos.append({"categoria": c, "favoritos": lst})
    loc = st.get("local") or {}
    d = {"sistema": kind, "nodo": st.get("nodo") or cfg.get("node") or "", "rx": bool(st.get("rx") or st.get("cos")),
         "tx": bool(st.get("tx") or st.get("ptt")), "total_red": st.get("total_red") or 0,
         "local": " · ".join(x for x in (loc.get("indicativo"), loc.get("descripcion"), loc.get("ubicacion")) if x)[:70],
         "enlaces": [{k: e.get(k) for k in ("nodo", "indicativo", "descripcion", "modo", "segundos", "direccion", "transmitiendo")}
                     for e in sorted(st.get("enlaces") or [], key=lambda e: e["nodo"])][:30],
         "activo": st.get("activo") or "", "habilitado": st.get("habilitado") is not False, "favoritos": grupos}
    return {"ok": True, "texto": aviso, "datos": d}


def _conectar(a):
    from . import sessions
    cfg, kind = _cfg_kind()
    dest = "".join(c for c in str(a.get("destino") or "") if c.isdigit())
    modo = a.get("modo") if a.get("modo") in ("transceptor", "monitor", "monitor_local") else "transceptor"
    if not dest:
        return {"ok": False, "texto": "Falta el número del nodo"}
    sessions.action(cfg, "conectar", dest, modo if kind == "asl" else "transceptor")
    log.info("Hub (%s): conectar %s como %s", a.get("quien"), dest, modo)
    time.sleep(4)
    r = _conexiones()
    conectado = any(e["nodo"] == dest for e in r.get("datos", {}).get("enlaces", [])) or kind == "irlp"
    r["texto"] = ("🔗 Conecté el nodo {} ({}).".format(dest, modo) if conectado
                  else "⏳ Mandé conectar el nodo {}; todavía no aparece.".format(dest))
    return r


def _desconectar(a):
    from . import sessions
    cfg, kind = _cfg_kind()
    dest = str(a.get("destino") or "")
    if dest in ("all", ""):
        sessions.action(cfg, "desconectar_todo")
        aviso = "⛔ Desconecté todos los enlaces." if kind == "asl" else "✖ Desconecté IRLP."
    else:
        dest = "".join(c for c in dest if c.isdigit())
        sessions.action(cfg, "desconectar", dest)
        aviso = "✖ Desconecté el nodo {}.".format(dest)
    log.info("Hub (%s): desconectar %s", a.get("quien"), dest or "todo")
    time.sleep(2)
    r = _conexiones()
    r["texto"] = aviso
    return r


def _anuncios(a=None, aviso=""):
    from . import anuncios
    r = anuncios.resumen()
    act = (r.get("emisor") or {}).get("actual") or {}
    d = {"anuncios": [{"id": x["id"], "nombre": x["nombre"], "activo": x["activo"], "proximo": x.get("proximo") or "",
                       "red": bool(x.get("proximo_red")), "destino": x.get("destino"), "duracion": x.get("duracion"),
                       "tipo": x.get("tipo"), "dtmf": x.get("dtmf") or ""} for x in r.get("anuncios") or []][:40],
         "al_aire": act.get("nombre") if act else "", "asl": r.get("asl")}
    return {"ok": True, "texto": aviso, "datos": d}


def _anuncio_ahora(a):
    from . import anuncios
    aid = int(a.get("id") or 0)
    x = anuncios.uno(aid)
    destino = "red" if a.get("destino") == "red" else "local"
    anuncios.emisor.start()
    anuncios.emisor.encolar(aid, "telegram", destino)
    log.info("Hub (%s): transmitir el anuncio «%s» (%s)", a.get("quien"), x["nombre"], destino)
    return _anuncios(aviso="📡 «{}» va al aire ({}); espera canal libre.".format(
        x["nombre"], "RF + Net" if destino == "red" else "solo RF"))


def _anuncio_activo(a):
    from . import anuncios
    aid, on = int(a.get("id") or 0), bool(a.get("on"))
    x = anuncios.activar(aid, on, "hub · {}".format(a.get("quien") or ""))
    return _anuncios(aviso="{} «{}».".format("▶ Activé" if on else "⏸ Pausé", x["nombre"]))


def _clima(a=None, aviso=""):
    from . import alertas, clima
    cfg = settings.load()
    d = {"configurado": clima.configurado(cfg), "lugar": cfg.get("wx_lugar") or ""}
    if d["configurado"]:
        try:
            dd = clima.datos(cfg)
            t = clima.textos(dd, cfg)
            d["clima"] = {k.strip("{}"): v for k, v in t.items()}
            d["fuente"] = dd.get("fuente", "")
        except Exception as e:
            d["error"] = str(e)
    r = alertas.resumen()
    d["alertas"] = {"activas": r["activas"], "horario": r["horario"],
                    "fuera": [x["nombre"] for x in (r["clima"].get("evaluacion") or []) if x.get("alerta")],
                    "pronostico": [{"nombre": p["nombre"], "desde": p["desde"]} for p in r["pronostico"]][:6],
                    "sismos": [{"mag": s["mag"], "lugar": s.get("lugar_es") or s["lugar"], "t": s["t"], "avisado": s.get("avisado")}
                               for s in (r["sismos"].get("lista") or [])][:5],
                    "historial": r["historial"][:5]}
    return {"ok": True, "texto": aviso, "datos": d}


def _emisiones(a=None, aviso=""):
    from . import bot, db, grabar
    evs = [e for e in db.get_eventos() if e.get("num_secciones")]
    prox = {}
    for t, row in bot._proximos(50):
        prox.setdefault(row["evento_id"], t)
    evs.sort(key=lambda e: (e["id"] not in prox, prox.get(e["id"]) or 0, e["nombre"].lower()))
    g = grabar.grabadora.estado()
    from .engine import engine
    s = engine.status()
    d = {"estado": bot._txt_estado(), "al_aire": bool(s.get("on_air")), "evento_id": s.get("evento_id"),
         "grabando": g.get("titulo") if g.get("grabando") else "",
         "eventos": [{"id": e["id"], "nombre": e["nombre"], "proximo": prox[e["id"]].strftime("%Y-%m-%d %H:%M") if e["id"] in prox else "",
                      "duracion": e.get("duracion_total")} for e in evs[:12]]}
    return {"ok": True, "texto": aviso, "datos": d}


def _transmitir(a):
    from . import db
    from .engine import engine
    ev = db.get_evento(int(a.get("id") or 0))
    if not ev:
        return {"ok": False, "texto": "Ese evento ya no existe"}
    engine.start_event(ev["id"], origen="Telegram (hub) · {}".format(a.get("quien") or ""))
    engine.note("«{}» iniciado desde el bot del hub por {}".format(ev["nombre"], a.get("quien") or "?"))
    time.sleep(2)
    return _emisiones(aviso="▶ Inició «{}».".format(ev["nombre"]))


def _detener(a):
    from .engine import engine
    s = engine.status()
    if not s.get("on_air"):
        return _emisiones(aviso="No había nada al aire.")
    engine.note("Detenido desde el bot del hub por {}".format(a.get("quien") or "?"), "warn")
    engine.command("stop")
    time.sleep(2)
    return _emisiones(aviso="⏹ Detuve «{}».".format(s.get("evento") or ""))


def _grabar(a):
    from . import grabar
    if a.get("parar"):
        e = grabar.grabadora.estado()
        if e.get("grabando"):
            grabar.grabadora.detener("manual")
        return _emisiones(aviso="⏹ Detuve la grabación." if e.get("grabando") else "No se estaba grabando.")
    titulo = "Grabación de {}".format((a.get("quien") or "").upper() or "Telegram")
    grabar.grabadora.iniciar(titulo, "Telegram (hub) · {}".format(a.get("quien") or ""))
    return _emisiones(aviso="⏺ Grabando «{}».".format(titulo))


ACCIONES = {
    "estado": _estado_nodo,
    "con": _conexiones, "cn": _conectar, "cd": _desconectar,
    "an": _anuncios, "aa": _anuncio_ahora, "ap": _anuncio_activo,
    "cl": _clima,
    "ev": _emisiones, "et": _transmitir, "ed": _detener, "gr": _grabar,
}


NECESITA = {"con": "conexiones", "cn": "conexiones", "cd": "conexiones", "an": "anuncios", "aa": "anuncios", "ap": "anuncios",
            "cl": "clima", "ev": "emisiones", "et": "emisiones", "ed": "emisiones", "gr": "emisiones"}
NOMBRE_CAP = {"conexiones": "conexiones (no es ASL ni IRLP)", "anuncios": "anuncios", "clima": "clima (eso es de ASLSCAN)",
              "emisiones": "emisiones (eso es de HAMNA)"}


def ejecutar(orden):
    acc = orden.get("accion")
    f = ACCIONES.get(acc)
    try:
        if not f:
            raise ValueError("Este nodo no conoce la orden «{}» (¿versión vieja?)".format(acc))
        cap = NECESITA.get(acc)
        if cap and cap not in capacidades()[1]:
            raise ValueError("Este nodo ({}) no tiene {}".format(APP, NOMBRE_CAP[cap]))
        args = orden.get("args") or {}
        if not isinstance(args, dict):
            args = {}
        r = f(args)
    except Exception as e:
        log.warning("Orden del hub «%s»: %s", acc, e)
        r = {"ok": False, "texto": str(e)[:300]}
    r["id"] = orden.get("id")
    return r


# ── Hilo: preguntarle al hub ─────────────────────────────────────────────────
def _preguntar(cfg, resultados):
    from . import autobackup, hub
    url, tok, pin = hub.destino(cfg)
    if not url or not tok:
        raise RuntimeError("Falta la dirección o el código de acceso del hub")
    kind, caps = capacidades()
    body = json.dumps({"nodo": str(cfg.get("node") or ""), "app": APP, "version": VERSION, "sistema": kind, "caps": caps,
                       "estacion": cfg.get("station_name") or "", "resultados": resultados}).encode("utf-8")
    conn, base, _fp = autobackup._connect(url, pin, timeout=ESPERA_HUB)
    try:
        conn.request("POST", base + "api/remoto/control", body=body, headers={
            "X-HAMNA-Backup": tok, "Content-Type": "application/json", "User-Agent": "{}/{}".format(APP, VERSION)})
        return autobackup._answer(conn.getresponse())
    finally:
        conn.close()


def estado():
    cfg = settings.load()
    return {"activo": bool(cfg.get("rc_on") and cfg.get("hub_on")), "ultimo_ok": _estado["ok"], "error": _estado["error"],
            "ordenes": _estado["ordenes"]}


def _loop():
    time.sleep(20)
    pendientes, error_previo = [], ""
    while True:
        cfg = settings.load()
        if not (cfg.get("rc_on") and cfg.get("hub_on")):
            pendientes = []
            time.sleep(15)
            continue
        try:
            r = _preguntar(cfg, pendientes)
            pendientes = []
            _estado.update(ok=time.time(), error="")
            if error_previo:
                log.info("Control desde el hub: conectado otra vez")
            error_previo = ""
            for o in r.get("ordenes") or []:
                _estado["ordenes"] += 1
                pendientes.append(ejecutar(o))
        except Exception as e:
            msg = str(e)
            _estado["error"] = msg
            if msg != error_previo:
                log.warning("Control desde el hub: %s", msg)
            error_previo = msg
            # Un hub viejo (sin esta función) contesta 404: no insistir tan seguido
            time.sleep(300 if "404" in msg or "No encontrado" in msg else 30)


def start():
    if not _estado["hilo"]:
        _estado["hilo"] = threading.Thread(target=_loop, daemon=True, name="remoto")
        _estado["hilo"].start()
