"""
HAMNA Web — historial de conexiones del nodo (la línea de tiempo del Dashboard).

Un hilo revisa el nodo cada pocos segundos (la misma consulta que usa el
Dashboard: rpt xnode en ASL, $LOCAL/active en IRLP) y compara con la vuelta
anterior:

  aparece un enlace establecido     → conexión (hora, IP, dirección, modo)
  desaparece                        → desconexión (y cuánto duró)
  se ve «conectando» y desaparece   → intento fallido
  HAMNA pidió conectar y en 30 s  → intento fallido (no respondió)
  nunca apareció

Así se registran también las conexiones que no pasan por HAMNA (DTMF por
radio, otro nodo que se conecta a este, startup_macro…). Un intento que falla
tan rápido que no alcanza a verse solo se sabe si lo pidió HAMNA.

La hora de conexión sale del tiempo que reporta app_rpt para el enlace, así
que un enlace que ya existía al arrancar HAMNA queda con su hora real.
Si HAMNA estuvo detenido cuando se cayó un enlace, la hora de desconexión es
la última vez que se vio (se marca como aproximada).
"""
import logging
import threading
import time

from . import backends, db, settings

log = logging.getLogger("hamna.historial")

CADA = 3                  # s entre revisiones
ESPERA_INTENTO = 30       # s para que aparezca un enlace que pidió HAMNA
VISTO_CADA = 60           # s entre escrituras de «visto» en la base
GUARDAR_DIAS = 90
MAX_FILAS = 20000

_lock = threading.Lock()
_vivos = {}               # (local, remoto) → dict con id, establecida, seg, visto…
_intentos = {}            # (local, remoto) → (t, origen)
_cierres = {}             # (local, remoto | "*") → (t, origen)
_listo = False


def init():
    with db.conn() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS conexiones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sistema TEXT NOT NULL DEFAULT 'asl',
            nodo_local TEXT NOT NULL DEFAULT '',
            remoto TEXT NOT NULL DEFAULT '',
            ip TEXT NOT NULL DEFAULT '',
            direccion TEXT NOT NULL DEFAULT '',      -- IN | OUT | ''
            modo TEXT NOT NULL DEFAULT '',
            inicio REAL NOT NULL,
            fin REAL,
            visto REAL,
            estado TEXT NOT NULL DEFAULT 'activa',   -- activa | cerrada | fallida
            origen TEXT NOT NULL DEFAULT '',         -- quién pidió conectar (si fue HAMNA)
            cerro TEXT NOT NULL DEFAULT '',          -- quién pidió desconectar (si fue HAMNA)
            nota TEXT NOT NULL DEFAULT '')""")
        c.execute("CREATE INDEX IF NOT EXISTS conexiones_inicio ON conexiones (inicio)")


# ── Avisos desde links.py (lo que pide HAMNA) ─────────────────────────────
def intento(local, remoto, origen="HAMNA"):
    with _lock:
        _intentos[(str(local), str(remoto))] = (time.time(), origen)


def cierre(local, remoto=None, origen="HAMNA"):
    with _lock:
        _cierres[(str(local), str(remoto) if remoto else "*")] = (time.time(), origen)


def _quien_cerro(key, ahora):
    for k in (key, (key[0], "*")):
        v = _cierres.get(k)
        if v and ahora - v[0] < 30:
            return v[1]
    return ""


# ── Base ────────────────────────────────────────────────────────────────────
def _insertar(c, sistema, local, e, inicio, estado="activa", fin=None, origen="", nota=""):
    cur = c.execute(
        "INSERT INTO conexiones (sistema, nodo_local, remoto, ip, direccion, modo, inicio, fin, visto,"
        " estado, origen, nota) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (sistema, local, e.get("nodo", ""), e.get("ip") or "", e.get("direccion") or "",
         e.get("modo") or "", inicio, fin, fin or time.time(), estado, origen, nota))
    return cur.lastrowid


def _cerrar(c, rid, fin, cerro="", nota=""):
    c.execute("UPDATE conexiones SET estado='cerrada', fin=?, visto=?, cerro=?,"
              " nota=CASE WHEN ?='' THEN nota ELSE ? END WHERE id=?",
              (fin, fin, cerro, nota, nota, rid))


def _cargar_abiertas():
    """Al arrancar: las conexiones que quedaron abiertas se revisan en la primera vuelta."""
    for r in db.rows("SELECT * FROM conexiones WHERE estado='activa'"):
        _vivos[(r["nodo_local"], r["remoto"])] = {
            "id": r["id"], "establecida": True, "seg": None, "inicio": r["inicio"],
            "visto": r["visto"] or r["inicio"], "escrito": r["visto"] or r["inicio"],
            "modo": r["modo"], "sistema": r["sistema"], "revisar": True}


# ── Una vuelta ──────────────────────────────────────────────────────────────
def _leer(cfg):
    """[(sistema, nodo_local, [enlaces])] de lo que hay ahora. Lanza si el nodo no responde."""
    from . import sessions
    kind = cfg.get("backend") or "auto"
    if kind == "auto":
        kind = backends.detect()
    if kind == "irlp":
        s = sessions.irlp_status(cfg)
        loc = str(s.get("nodo") or "irlp")
        en = [{"nodo": s["activo"], "ip": (s.get("detalle") or "").split(":")[0], "direccion": "",
               "modo": "", "estado": "ESTABLISHED", "segundos": None}] if s.get("activo") else []
        return [("irlp", loc, en)]
    if kind != "asl":
        return []
    nodos = sessions.local_nodes() or [str(cfg.get("node") or backends.detect_asl_node())]
    out = []
    for n in nodos:
        if n and n.isdigit():
            out.append(("asl", n, sessions.asl_status(n)["enlaces"]))
    return out


def _establecida(e):
    est = (e.get("estado") or "").upper()
    if est:
        return est == "ESTABLISHED"
    return e.get("modo") != "conectando"


def vuelta():
    cfg = settings.load()
    try:
        actuales = _leer(cfg)
    except Exception as e:                       # Asterisk no responde: no se cierra nada
        log.debug("Sin lectura del nodo: %s", e)
        return
    ahora = time.time()
    with _lock, db.conn() as c:
        vistos = set()
        revisados = {loc for _, loc, _ in actuales}
        for sistema, loc, enlaces in actuales:
            for e in enlaces:
                if not e.get("nodo"):
                    continue
                key = (loc, str(e["nodo"]))
                vistos.add(key)
                seg = e.get("segundos")
                est = _establecida(e)
                v = _vivos.get(key)
                intento_ = _intentos.pop(key, None) if est else _intentos.get(key)
                origen = intento_[1] if intento_ else ""
                if v and v.get("revisar"):
                    # Abierta antes de reiniciar HAMNA: ¿es el mismo enlace?
                    v.pop("revisar")
                    mismo = seg is None or abs((ahora - seg) - v["inicio"]) < 90
                    if not mismo:
                        _cerrar(c, v["id"], v["visto"], nota="aprox")
                        v = _vivos.pop(key)
                        v = None
                if v is None:
                    if est:
                        inicio = ahora - seg if seg else ahora
                        rid = _insertar(c, sistema, loc, e, inicio, origen=origen)
                        _vivos[key] = {"id": rid, "establecida": True, "seg": seg, "inicio": inicio,
                                       "visto": ahora, "escrito": ahora, "modo": e.get("modo") or "",
                                       "sistema": sistema}
                    else:
                        _vivos[key] = {"id": None, "establecida": False, "seg": seg, "inicio": ahora,
                                       "visto": ahora, "escrito": ahora, "e": dict(e), "sistema": sistema,
                                       "origen": origen}
                    continue
                if not v["establecida"]:
                    v["e"] = dict(e)
                    if est:                              # terminó de conectar
                        inicio = ahora - seg if seg else v["inicio"]
                        rid = _insertar(c, sistema, loc, e, inicio, origen=origen or v.get("origen", ""))
                        _vivos[key] = {"id": rid, "establecida": True, "seg": seg, "inicio": inicio,
                                       "visto": ahora, "escrito": ahora, "modo": e.get("modo") or "",
                                       "sistema": sistema}
                    v["visto"] = ahora
                    continue
                # Ya establecida: ¿se reinició el contador? (se cayó y volvió entre dos vueltas)
                if seg is not None and v["seg"] is not None and seg + 30 < v["seg"] + (ahora - v["visto"]):
                    _cerrar(c, v["id"], ahora - seg, nota="reconectó")
                    rid = _insertar(c, sistema, loc, e, ahora - seg)
                    v.update(id=rid, inicio=ahora - seg, escrito=ahora)
                if (e.get("modo") or "") and e.get("modo") != v.get("modo"):
                    c.execute("UPDATE conexiones SET modo=? WHERE id=?", (e["modo"], v["id"]))
                    v["modo"] = e["modo"]
                v["seg"], v["visto"] = seg, ahora
                if ahora - v["escrito"] > VISTO_CADA:
                    c.execute("UPDATE conexiones SET visto=? WHERE id=?", (ahora, v["id"]))
                    v["escrito"] = ahora
        # Lo que ya no está
        for key in list(_vivos):
            if key in vistos:
                continue
            v = _vivos[key]
            if key[0] not in revisados and not v.get("revisar"):
                continue                             # ese nodo local ya no se lee
            _vivos.pop(key)
            if v.get("revisar"):
                _cerrar(c, v["id"], v["visto"], nota="aprox")
            elif v["establecida"]:
                _cerrar(c, v["id"], ahora, cerro=_quien_cerro(key, ahora))
            else:
                e = v.get("e") or {"nodo": key[1]}
                _intentos.pop(key, None)
                _insertar(c, v["sistema"], key[0], e, v["inicio"], estado="fallida", fin=ahora,
                          origen=v.get("origen", ""), nota="no terminó de conectar")
        # Intentos de HAMNA que nunca aparecieron
        sistema0 = actuales[0][0] if actuales else "asl"
        for key, (t, origen) in list(_intentos.items()):
            if key in vistos or ahora - t < ESPERA_INTENTO:
                continue
            _intentos.pop(key)
            _insertar(c, sistema0, key[0], {"nodo": key[1]}, t, estado="fallida", fin=ahora,
                      origen=origen, nota="no respondió")
        for k, (t, _) in list(_cierres.items()):
            if ahora - t > 60:
                _cierres.pop(k)


def _limpiar():
    corte = time.time() - GUARDAR_DIAS * 86400
    db.execute("DELETE FROM conexiones WHERE estado!='activa' AND inicio < ?", (corte,))
    db.execute("DELETE FROM conexiones WHERE estado!='activa' AND id <= (SELECT MAX(id) FROM conexiones) - ?",
               (MAX_FILAS,))


def _loop():
    global _listo
    with _lock:
        _cargar_abiertas()
    _listo = True
    ultimo_limpio = 0.0
    while True:
        try:
            vuelta()
        except Exception:
            log.exception("Error al revisar las conexiones")
        if time.time() - ultimo_limpio > 6 * 3600:
            ultimo_limpio = time.time()
            try:
                _limpiar()
            except Exception:
                log.exception("No pude limpiar el historial de conexiones")
        time.sleep(CADA)


def start():
    threading.Thread(target=_loop, daemon=True, name="hamna-historial").start()


# ── Consulta para la página ─────────────────────────────────────────────────
def _hora(t):
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(t)) if t else ""


def listar(dias=1, nodo="", limite=500):
    from . import sessions
    desde = time.time() - max(1, min(GUARDAR_DIAS, dias)) * 86400
    sql = "SELECT * FROM conexiones WHERE (inicio >= ? OR fin >= ? OR estado='activa')"
    args = [desde, desde]
    if nodo:
        sql += " AND nodo_local=?"
        args.append(str(nodo))
    sql += " ORDER BY COALESCE(fin, inicio) DESC LIMIT ?"
    args.append(limite)
    filas = db.rows(sql, args)
    info = sessions.lookup({f["remoto"] for f in filas})
    ahora = time.time()
    for f in filas:
        f.update(info.get(f["remoto"], {}))
        f["hora_inicio"] = _hora(f["inicio"])
        f["hora_fin"] = _hora(f["fin"])
        f["duracion"] = int((f["fin"] or ahora) - f["inicio"])
        f["aprox"] = f["nota"] == "aprox"
        f.pop("visto", None)
    return {"conexiones": filas, "ahora": _hora(ahora), "dias": dias, "listo": _listo,
            "guardar_dias": GUARDAR_DIAS}
