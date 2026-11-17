"""
HAMNA Web — panel de nodos.

  Nodo que reporta  cada minuto manda un «latido» al hub (POST api/remoto/latido)
                    con su estado: al aire, próximo evento, salud, versión,
                    último respaldo. Usa la dirección y el código de acceso del
                    hub (si se dejan vacíos, los del respaldo a otro nodo). Así
                    el hub no necesita poder entrar a los nodos: basta con que
                    cada nodo llegue al hub.
  Hub               guarda el último latido de cada nodo, los muestra en la
                    pestaña «Nodos» y avisa por Telegram si uno deja de reportar
                    (y cuando vuelve).
"""
import datetime as dt
import json
import logging
import re
import threading
import time

from . import VERSION, autobackup, db, health, notify, numeracion, settings, sysmon

log = logging.getLogger("hamna.hub")

INTERVALO = 60
NODO_RX = re.compile(r"^[A-Za-z0-9]{1,12}$")
_estado = {"ok": 0.0, "error": "", "hub": "", "intento": 0.0}


def init():
    with db.conn() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS nodos_latido (
                         nodo      TEXT PRIMARY KEY,
                         estacion  TEXT DEFAULT '',
                         version   TEXT DEFAULT '',
                         ip        TEXT DEFAULT '',
                         datos     TEXT DEFAULT '{}',
                         ultimo    REAL DEFAULT 0,
                         alertado  INTEGER DEFAULT 0)""")
        # Direcciones del dashboard de cada nodo (las escribe el admin del hub; no se
        # borran al quitar el nodo del panel)
        c.execute("""CREATE TABLE IF NOT EXISTS nodos_urls (
                         nodo     TEXT PRIMARY KEY,
                         url_int  TEXT DEFAULT '',
                         url_ext  TEXT DEFAULT '')""")


URL_RX = re.compile(r"^https?://[^\s\"'<>]{1,300}$", re.I)


def urls():
    try:
        return {r["nodo"]: {"url_int": r["url_int"] or "", "url_ext": r["url_ext"] or ""}
                for r in db.rows("SELECT * FROM nodos_urls")}
    except Exception:
        return {}


def guardar_urls(nodo, url_int, url_ext):
    nodo = str(nodo or "").strip()
    if not (NODO_RX.match(nodo) or nodo == "_este"):
        raise ValueError("Nodo inválido")
    limpio = []
    for nombre, u in (("interna", url_int), ("de internet", url_ext)):
        u = (u or "").strip()
        if u and "://" not in u:
            u = "http://" + u
        if u and not URL_RX.match(u):
            raise ValueError("La dirección {} no es válida: debe empezar con http:// o https:// y no llevar espacios ni comillas".format(nombre))
        limpio.append(u)
    if db.row("SELECT nodo FROM nodos_urls WHERE nodo=?", (nodo,)):
        db.execute("UPDATE nodos_urls SET url_int=?, url_ext=? WHERE nodo=?", (limpio[0], limpio[1], nodo))
    else:
        db.execute("INSERT INTO nodos_urls (nodo, url_int, url_ext) VALUES (?,?,?)", (nodo, limpio[0], limpio[1]))
    return {"url_int": limpio[0], "url_ext": limpio[1]}


# ── Lo que reporta un nodo ──────────────────────────────────────────────────
def _sistemas():
    try:
        from . import backends
        return backends.etiquetas()
    except Exception:
        return []


def datos_locales():
    from .engine import engine
    from . import bot
    cfg = settings.load()
    s = engine.status()
    al_aire = None
    if s.get("on_air"):
        secs, i = s.get("secciones") or [], s.get("cur_sec", -1)
        al_aire = {"evento": s.get("evento") or "prueba", "origen": s.get("origen") or "",
                   "seccion": secs[i]["nombre"] if 0 <= i < len(secs) else "", "i": i + 1, "n": len(secs),
                   "falta": max(0, int((s.get("total") or 0) - (s.get("elapsed") or 0)))}
    prox = None
    try:
        p = bot._proximos(1)
        if p:
            t, row = p[0]
            ev = numeracion.aplicar(db.get_evento(row["evento_id"]) or {})
            prox = {"evento": row.get("evento_nombre") or ev.get("nombre"), "fecha": t.strftime("%Y-%m-%d %H:%M"),
                    "num": numeracion.etiqueta(ev) if (ev.get("num") or ev.get("numero")) else ""}
    except Exception:
        log.exception("No pude calcular el próximo evento")
    h = health.status()
    sm = sysmon.snapshot()
    mem, dis = sm.get("mem") or {}, sm.get("disco") or {}
    st = autobackup.load_state()
    return {
        "nodo": str(cfg.get("node") or ""), "estacion": cfg.get("station_name") or "", "version": VERSION,
        "tipo": cfg.get("backend") or "", "sistemas": _sistemas(), "hora": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "al_aire": al_aire, "proximo": prox,
        "salud": {"peor": h.get("peor"), "checks": [{"id": c.get("id"), "nombre": c["nombre"], "nivel": c["nivel"],
                                                      "detalle": c["detalle"]} for c in h.get("checks") or []]},
        "equipo": {"cpu": sm.get("cpu"), "temp": sm.get("temp"),
                   "mem": int(round(100.0 * mem["usada"] / mem["total"])) if mem.get("total") else None,
                   "disco": int(round(100.0 * dis["usada"] / dis["total"])) if dis.get("total") else None,
                   "encendido_s": sm.get("encendido_s")},
        "respaldo": {"ultimo_ok": st.get("ultimo_ok"), "ok": (st.get("ultimo") or {}).get("ok"),
                     "fecha": (st.get("ultimo") or {}).get("fecha")},
        "bot": bot.activo(),
        "grabando": _grabando(),
    }


def _grabando():
    try:
        from . import grabar
        e = grabar.grabadora.estado()
        return {"titulo": e["titulo"], "dur": e["dur"]} if e.get("grabando") else None
    except Exception:
        return None


def destino(cfg=None):
    """(url, código, huella) del hub; vacíos → los del respaldo a otro nodo."""
    cfg = cfg or settings.load()
    url = (cfg.get("hub_url") or "").strip() or (cfg.get("ab_node_url") or "").strip()
    tok = (cfg.get("hub_token") or "").strip() or (cfg.get("ab_node_token") or "").strip()
    pin = (cfg.get("hub_pin") or "").strip() if (cfg.get("hub_url") or "").strip() else (cfg.get("ab_node_pin") or "")
    return url, tok, pin


def enviar(cfg=None):
    cfg = cfg or settings.load()
    url, tok, pin = destino(cfg)
    if not url or not tok:
        raise RuntimeError("Falta la dirección o el código de acceso del hub")
    body = json.dumps(datos_locales()).encode("utf-8")
    conn, base, _fp = autobackup._connect(url, pin, timeout=20)
    try:
        conn.request("POST", base + "api/remoto/latido", body=body, headers={
            "X-HAMNA-Backup": tok, "Content-Type": "application/json",
            "User-Agent": "HAMNA-Web/" + VERSION})
        data = autobackup._answer(conn.getresponse())
    finally:
        conn.close()
    return data


def estado_envio():
    cfg = settings.load()
    url, tok, _pin = destino(cfg)
    return {"activo": bool(cfg.get("hub_on")), "url": url, "usa_respaldo": not (cfg.get("hub_url") or "").strip(),
            "ultimo_ok": _estado["ok"], "error": _estado["error"], "hub": _estado["hub"]}


# ── Hilo: mandar latidos (nodo) y vigilar a los demás (hub) ─────────────────
def start():
    threading.Thread(target=_loop, name="hamna-hub", daemon=True).start()


def _loop():
    time.sleep(15)
    error_previo = ""
    while True:
        cfg = settings.load()
        if cfg.get("hub_on"):
            try:
                r = enviar(cfg)
                _estado.update(ok=time.time(), error="", hub=r.get("estacion") or r.get("nodo") or "")
                if error_previo:
                    log.info("Panel de nodos: el hub volvió a recibir los latidos")
                error_previo = ""
            except Exception as e:
                _estado["error"] = str(e)
                if str(e) != error_previo:
                    log.warning("Panel de nodos: no pude reportar al hub: %s", e)
                error_previo = str(e)
        try:
            vigilar(cfg)
        except Exception:
            log.exception("Panel de nodos: error al revisar los nodos")
        time.sleep(INTERVALO)


def vigilar(cfg=None):
    """Hub: avisar de los nodos que dejaron de reportar."""
    cfg = cfg or settings.load()
    mins = int(cfg.get("hub_alerta_min", 10) or 0)
    if mins <= 0:
        return
    now = time.time()
    for r in db.rows("SELECT * FROM nodos_latido WHERE alertado=0 AND ultimo < ?", (now - mins * 60,)):
        db.execute("UPDATE nodos_latido SET alertado=1 WHERE nodo=?", (r["nodo"],))
        notify.send("nodos", "🔴 El nodo <b>{}</b>{} no reporta desde las {} (hace {} min).".format(
            notify.esc(r["nodo"]), " · " + notify.esc(r["estacion"]) if r["estacion"] else "",
            dt.datetime.fromtimestamp(r["ultimo"]).strftime("%H:%M"), int((now - r["ultimo"]) // 60)),
            dedupe="nodo-caido:{}:{}".format(r["nodo"], int(r["ultimo"])))


# ── Lado hub: recibir y mostrar ─────────────────────────────────────────────
def recibir(datos, ip):
    nodo = str(datos.get("nodo") or "").strip()
    if not NODO_RX.match(nodo):
        raise ValueError("El nodo no tiene número configurado (Ajustes → Nodo)")
    prev = db.row("SELECT ultimo, alertado FROM nodos_latido WHERE nodo=?", (nodo,))
    now = time.time()
    vals = (str(datos.get("estacion") or "")[:80], str(datos.get("version") or "")[:20], ip or "",
            json.dumps(datos)[:20000], now, nodo)
    if prev:        # sin «ON CONFLICT»: el SQLite de HamVOIP es anterior a 3.24
        db.execute("UPDATE nodos_latido SET estacion=?, version=?, ip=?, datos=?, ultimo=?, alertado=0 WHERE nodo=?", vals)
    else:
        db.execute("INSERT INTO nodos_latido (estacion, version, ip, datos, ultimo, nodo) VALUES (?,?,?,?,?,?)", vals)
    if prev and prev["alertado"]:
        notify.send("nodos", "🟢 El nodo <b>{}</b>{} volvió a reportar (estuvo {} min sin reportar).".format(
            notify.esc(nodo), " · " + notify.esc(datos.get("estacion")) if datos.get("estacion") else "",
            int((now - prev["ultimo"]) // 60)), dedupe="nodo-vuelve:{}:{}".format(nodo, int(now // 60)))


def quitar(nodo):
    db.execute("DELETE FROM nodos_latido WHERE nodo=?", (nodo,))


def panel():
    cfg = settings.load()
    now = time.time()
    recibidos = {}
    try:
        for m in autobackup.received():
            if m.get("archivos"):
                recibidos[str(m.get("nodo"))] = m["archivos"][0]
    except Exception:
        pass
    nodos = []
    dirs = urls()
    for r in db.rows("SELECT * FROM nodos_latido ORDER BY nodo"):
        try:
            d = json.loads(r["datos"] or "{}")
        except ValueError:
            d = {}
        d.update(nodo=r["nodo"], ip=r["ip"], edad=int(now - r["ultimo"]), ultimo=r["ultimo"],
                 recibido=recibidos.get(r["nodo"]), **dirs.get(r["nodo"], {}))
        nodos.append(d)
    este = datos_locales()
    este.update(edad=0, propio=True, recibido=None, clave=este.get("nodo") or "_este")
    este.update(dirs.get(este["clave"], {}))
    ultima = None
    try:
        from . import updates
        ultima = (updates._cache.get("data") or {}).get("ultima")
    except Exception:
        pass
    return {"este": este, "nodos": nodos, "alerta_min": int(cfg.get("hub_alerta_min", 10) or 0),
            "ultima_version": ultima or VERSION}
