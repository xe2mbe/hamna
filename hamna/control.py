"""
HAMNA Web — control de otros nodos desde el bot (lado del hub).

  Bot del hub        un usuario pide algo de otro nodo («conexiones del 59624»,
                     «conecta el 2000»…). Aquí se guarda como orden pendiente.
  Nodo (remoto.py)   pregunta todo el tiempo si hay órdenes (POST api/remoto/control,
                     con su código de acceso); la pregunta se queda abierta hasta
                     25 s y se contesta en cuanto llega una orden.
  Resultado          viaja en la siguiente pregunta del nodo; el bot edita el
                     mensaje de Telegram con lo que pasó.

Cada nodo queda ligado al código de acceso con que se presentó la primera vez
(otro código no puede hacerse pasar por él). Permisos por nodo: el
administrador del hub puede todo; a los demás se les da «ver» o «controlar»
nodo por nodo (Nodos → 🎛 Bot).
"""
import json
import logging
import re
import threading
import time

from . import db

log = logging.getLogger("hamna.control")

ESPERA = 25                 # s que el hub retiene la pregunta del nodo
VENCE = 75                  # s que una orden espera a que el nodo la recoja
EN_LINEA = 70               # s desde la última pregunta para decir que el nodo está escuchando
NODO_RX = re.compile(r"^[A-Za-z0-9]{1,12}$")
VER, CONTROLAR = 1, 2
LECTURA = ("estado", "con", "an", "cl", "ev")     # órdenes que solo leen

_cond = threading.Condition()
_hilo = {"t": None}


def init():
    with db.conn() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS control_nodos (
                         nodo TEXT PRIMARY KEY, codigo_id INTEGER, app TEXT DEFAULT '', version TEXT DEFAULT '',
                         sistema TEXT DEFAULT '', caps TEXT DEFAULT '[]', estacion TEXT DEFAULT '', ultimo REAL DEFAULT 0)""")
        c.execute("""CREATE TABLE IF NOT EXISTS control_ordenes (
                         id INTEGER PRIMARY KEY AUTOINCREMENT, nodo TEXT, accion TEXT, args TEXT DEFAULT '{}',
                         usuario TEXT DEFAULT '', chat TEXT DEFAULT '', mensaje INTEGER DEFAULT 0,
                         creada REAL, estado TEXT DEFAULT 'pendiente', resultado TEXT DEFAULT '', terminada REAL DEFAULT 0)""")
        c.execute("""CREATE TABLE IF NOT EXISTS control_permisos (
                         usuario_id INTEGER, nodo TEXT, nivel INTEGER, PRIMARY KEY (usuario_id, nodo))""")
    if not _hilo["t"]:
        _hilo["t"] = threading.Thread(target=_vigilar, daemon=True, name="hamna-control")
        _hilo["t"].start()


# ── Nodos ────────────────────────────────────────────────────────────────────
def nodos():
    """{nodo: {app, version, sistema, caps, estacion, en_linea, edad}}"""
    now = time.time()
    out = {}
    for r in db.rows("SELECT * FROM control_nodos"):
        try:
            caps = json.loads(r["caps"] or "[]")
        except ValueError:
            caps = []
        out[r["nodo"]] = {"app": r["app"], "version": r["version"], "sistema": r["sistema"], "caps": caps,
                          "estacion": r["estacion"], "edad": int(now - (r["ultimo"] or 0)),
                          "en_linea": now - (r["ultimo"] or 0) < EN_LINEA}
    return out


def olvidar(nodo):
    """Suelta el nodo de su código (si se reinstaló con otro código)."""
    db.execute("DELETE FROM control_nodos WHERE nodo=?", (nodo,))


# ── Permisos ─────────────────────────────────────────────────────────────────
def nivel(user, nodo):
    if not user:
        return 0
    if user.get("rol") == "admin":
        return CONTROLAR
    r = db.row("SELECT nivel FROM control_permisos WHERE usuario_id=? AND nodo=?", (user["id"], str(nodo)))
    return int(r["nivel"]) if r else 0


def permisos(nodo):
    return {int(r["usuario_id"]): int(r["nivel"]) for r in db.rows("SELECT * FROM control_permisos WHERE nodo=?", (str(nodo),))}


def guardar_permisos(nodo, por_usuario):
    nodo = str(nodo)
    if not NODO_RX.match(nodo):
        raise ValueError("Nodo inválido")
    with db.conn() as c:
        c.execute("DELETE FROM control_permisos WHERE nodo=?", (nodo,))
        for uid, n in por_usuario.items():
            n = int(n or 0)
            if n in (VER, CONTROLAR):
                c.execute("INSERT INTO control_permisos (usuario_id, nodo, nivel) VALUES (?,?,?)", (int(uid), nodo, n))
    return permisos(nodo)


def visibles(user):
    """Nodos que este usuario puede ver o controlar: [(nodo, nivel)] (los que alguna vez se conectaron al control)."""
    return [(n, nivel(user, n)) for n in sorted(nodos()) if nivel(user, n) >= VER]


# ── Órdenes ──────────────────────────────────────────────────────────────────
def nueva(nodo, accion, args, user, chat="", mensaje=0):
    nv = nivel(user, nodo)
    if nv < (VER if accion in LECTURA else CONTROLAR):
        raise ValueError("No tienes permiso para eso en el nodo {}".format(nodo))
    info = nodos().get(nodo)
    if not info:
        raise ValueError("El nodo {} no tiene activado el control desde el hub".format(nodo))
    if not info["en_linea"]:
        raise ValueError("El nodo {} no está escuchando ahora (última vez hace {} s)".format(nodo, info["edad"]))
    args = dict(args or {}, quien=user.get("usuario") or "")
    oid = db.execute("INSERT INTO control_ordenes (nodo, accion, args, usuario, chat, mensaje, creada) VALUES (?,?,?,?,?,?,?)",
                     (nodo, accion, json.dumps(args), user.get("usuario") or "", str(chat or ""), int(mensaje or 0), time.time()))
    log.info("%s pide «%s» al nodo %s", user.get("usuario"), accion, nodo)
    with _cond:
        _cond.notify_all()
    return oid


def orden(oid):
    r = db.row("SELECT * FROM control_ordenes WHERE id=?", (oid,))
    if not r:
        return None
    r = dict(r)
    for k in ("args", "resultado"):
        try:
            r[k] = json.loads(r[k] or "{}")
        except ValueError:
            r[k] = {}
    return r


def _pendientes(nodo):
    return db.rows("SELECT * FROM control_ordenes WHERE nodo=? AND estado='pendiente' AND creada > ? ORDER BY id",
                   (nodo, time.time() - VENCE))


def atender(fila_codigo, datos, ip=""):
    """Pregunta de un nodo: guarda sus resultados y le entrega sus órdenes (espera hasta ESPERA s)."""
    nodo = str((datos or {}).get("nodo") or "").strip()
    if not NODO_RX.match(nodo):
        raise ValueError("El nodo no tiene número configurado (Ajustes → Nodo)")
    previo = db.row("SELECT codigo_id FROM control_nodos WHERE nodo=?", (nodo,))
    if previo and previo["codigo_id"] != fila_codigo["id"]:
        raise PermissionError("El nodo {} ya está ligado a otro código de acceso en este hub".format(nodo))
    vals = (fila_codigo["id"], str(datos.get("app") or "")[:20], str(datos.get("version") or "")[:20],
            str(datos.get("sistema") or "")[:10], json.dumps([str(c)[:20] for c in (datos.get("caps") or [])][:10]),
            str(datos.get("estacion") or "")[:80], time.time(), nodo)
    if previo:
        db.execute("UPDATE control_nodos SET codigo_id=?, app=?, version=?, sistema=?, caps=?, estacion=?, ultimo=? WHERE nodo=?", vals)
    else:
        db.execute("INSERT INTO control_nodos (codigo_id, app, version, sistema, caps, estacion, ultimo, nodo) VALUES (?,?,?,?,?,?,?,?)", vals)
        log.info("El nodo %s (%s) se conectó al control desde %s", nodo, datos.get("app"), ip)
    for res in (datos.get("resultados") or [])[:20]:
        try:
            oid = int(res.get("id"))
        except (TypeError, ValueError):
            continue
        o = db.row("SELECT id, nodo FROM control_ordenes WHERE id=?", (oid,))
        if not o or o["nodo"] != nodo:
            continue
        db.execute("UPDATE control_ordenes SET estado=?, resultado=?, terminada=? WHERE id=?",
                   ("hecha" if res.get("ok") else "error", json.dumps(res)[:60000], time.time(), oid))
        _avisar_bot(oid)
    fin = time.time() + (0 if datos.get("resultados") else ESPERA)
    while True:
        filas = _pendientes(nodo)
        if filas or time.time() >= fin:
            break
        with _cond:
            _cond.wait(min(5, max(0.1, fin - time.time())))
        db.execute("UPDATE control_nodos SET ultimo=? WHERE nodo=?", (time.time(), nodo))
    out = []
    for f in filas:
        db.execute("UPDATE control_ordenes SET estado='enviada' WHERE id=?", (f["id"],))
        try:
            args = json.loads(f["args"] or "{}")
        except ValueError:
            args = {}
        out.append({"id": f["id"], "accion": f["accion"], "args": args})
    return out


def _avisar_bot(oid):
    def hilo():
        try:
            from . import bot_remoto
            bot_remoto.resultado(orden(oid))
        except Exception:
            log.exception("Resultado de la orden %s", oid)
    threading.Thread(target=hilo, daemon=True, name="hamna-control-bot").start()


def _vigilar():
    """Órdenes que el nodo nunca recogió (o nunca contestó): avisar en Telegram y limpiar lo viejo."""
    while True:
        time.sleep(5)
        try:
            now = time.time()
            for r in db.rows("SELECT id FROM control_ordenes WHERE estado IN ('pendiente','enviada') AND creada < ?", (now - VENCE - 60,)):
                db.execute("UPDATE control_ordenes SET estado='vencida', terminada=? WHERE id=?", (now, r["id"]))
                _avisar_bot(r["id"])
            db.execute("DELETE FROM control_ordenes WHERE creada < ?", (now - 7 * 86400,))
        except Exception:
            log.exception("Vigilando las órdenes a los nodos")
