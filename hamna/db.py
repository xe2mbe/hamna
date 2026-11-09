"""
HAMNA Web — base de datos SQLite.
Mismo esquema que HAMNA Desktop (eventos, secciones, evento_secciones,
programacion), para que ambos se entiendan.
"""
import sqlite3
import threading
from contextlib import contextmanager

from . import paths

_lock = threading.RLock()


def _connect():
    conn = sqlite3.connect(str(paths.db_file()), timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def conn():
    with _lock:
        c = _connect()
        try:
            yield c
            c.commit()
        finally:
            c.close()


def rows(sql, args=()):
    with conn() as c:
        return [dict(r) for r in c.execute(sql, args).fetchall()]


def row(sql, args=()):
    with conn() as c:
        r = c.execute(sql, args).fetchone()
        return dict(r) if r else None


def execute(sql, args=()):
    with conn() as c:
        cur = c.execute(sql, args)
        return cur.lastrowid


def init_db():
    with conn() as c:
        c.execute("PRAGMA journal_mode = WAL")
        c.executescript("""
            CREATE TABLE IF NOT EXISTS eventos_type (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre  TEXT NOT NULL UNIQUE
            );
            CREATE TABLE IF NOT EXISTS eventos (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre         TEXT NOT NULL,
                tipo_evento_id INTEGER REFERENCES eventos_type(id),
                numero         INTEGER,
                creado_en      DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS tipos_seccion (
                id     INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL UNIQUE
            );
            CREATE TABLE IF NOT EXISTS secciones (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre          TEXT NOT NULL,
                tipo_seccion_id INTEGER REFERENCES tipos_seccion(id),
                ruta_archivo    TEXT,
                texto_tts       TEXT,
                duracion        REAL DEFAULT 0,
                regenerar_antes INTEGER DEFAULT 0,
                titulo          TEXT,
                descripcion     TEXT,
                creado_en       DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS evento_secciones (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                evento_id      INTEGER NOT NULL REFERENCES eventos(id) ON DELETE CASCADE,
                seccion_id     INTEGER NOT NULL REFERENCES secciones(id) ON DELETE CASCADE,
                orden          INTEGER DEFAULT 0,
                contabilizable INTEGER DEFAULT 1,
                UNIQUE(evento_id, seccion_id)
            );
            CREATE TABLE IF NOT EXISTS programacion (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                evento_id   INTEGER NOT NULL REFERENCES eventos(id) ON DELETE CASCADE,
                fecha       TEXT NOT NULL,
                hora        TEXT NOT NULL,
                recurrencia TEXT DEFAULT 'ninguna',
                activo      INTEGER DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS evento_conexiones (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                evento_id  INTEGER NOT NULL REFERENCES eventos(id) ON DELETE CASCADE,
                orden      INTEGER DEFAULT 0,
                sistema    TEXT NOT NULL,
                accion     TEXT NOT NULL,
                destino    TEXT DEFAULT '',
                modo       TEXT DEFAULT '',
                momento    TEXT NOT NULL DEFAULT 'antes',
                minutos    REAL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS historial (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                evento_id  INTEGER,
                evento     TEXT,
                origen     TEXT,
                inicio     DATETIME,
                fin        DATETIME,
                resultado  TEXT
            );
        """)
        # Zona horaria de cada programación ('' = hora del nodo)
        cols = [r[1] for r in c.execute("PRAGMA table_info(programacion)")]
        if "zona" not in cols:
            c.execute("ALTER TABLE programacion ADD COLUMN zona TEXT DEFAULT ''")
        if c.execute("SELECT COUNT(*) FROM eventos_type").fetchone()[0] == 0:
            c.executemany("INSERT INTO eventos_type (nombre) VALUES (?)", [
                ("Transmisión en Vivo",), ("Grabación",),
                ("Programa Diferido",), ("Boletín",), ("Especial",),
            ])
        if c.execute("SELECT COUNT(*) FROM tipos_seccion").fetchone()[0] == 0:
            c.executemany("INSERT INTO tipos_seccion (nombre) VALUES (?)",
                          [("TTS",), ("Audio",), ("Sonido",)])


# ── Tipos ──────────────────────────────────────────────────────────────────────
def tipo_seccion_id(nombre):
    r = row("SELECT id FROM tipos_seccion WHERE nombre=?", (nombre,))
    if not r:
        raise ValueError("Tipo de sección desconocido: " + nombre)
    return r["id"]


def get_eventos_types():
    return rows("SELECT id, nombre FROM eventos_type ORDER BY nombre")


# ── Secciones ──────────────────────────────────────────────────────────────────
_SEC_SELECT = """
    SELECT s.id, s.nombre, ts.nombre AS tipo, s.ruta_archivo, s.texto_tts,
           s.duracion, s.regenerar_antes, s.titulo, s.descripcion, s.creado_en
    FROM secciones s LEFT JOIN tipos_seccion ts ON ts.id = s.tipo_seccion_id
"""


def get_secciones():
    out = rows(_SEC_SELECT + " ORDER BY s.nombre COLLATE NOCASE")
    usos = {r["seccion_id"]: r["n"] for r in rows(
        "SELECT seccion_id, COUNT(*) AS n FROM evento_secciones GROUP BY seccion_id")}
    for s in out:
        s["usos"] = usos.get(s["id"], 0)
    return out


def get_seccion(sid):
    return row(_SEC_SELECT + " WHERE s.id=?", (sid,))


def insert_seccion(nombre, tipo, texto_tts=None, regenerar_antes=False,
                   titulo=None, descripcion=None):
    return execute("""
        INSERT INTO secciones (nombre, tipo_seccion_id, texto_tts,
                               regenerar_antes, titulo, descripcion)
        VALUES (?,?,?,?,?,?)""",
        (nombre, tipo_seccion_id(tipo), texto_tts, int(bool(regenerar_antes)),
         titulo, descripcion))


def update_seccion(sid, **fields):
    allowed = {"nombre", "ruta_archivo", "texto_tts", "duracion",
               "regenerar_antes", "titulo", "descripcion"}
    sets, vals = [], []
    for k, v in fields.items():
        if k in allowed:
            sets.append(k + "=?")
            vals.append(int(bool(v)) if k == "regenerar_antes" else v)
    if not sets:
        return
    vals.append(sid)
    execute("UPDATE secciones SET " + ", ".join(sets) + " WHERE id=?", vals)


def delete_seccion(sid):
    execute("DELETE FROM secciones WHERE id=?", (sid,))


# ── Eventos ────────────────────────────────────────────────────────────────────
def get_eventos():
    return rows("""
        SELECT e.id, e.nombre, e.numero, e.tipo_evento_id, et.nombre AS tipo,
               e.creado_en,
               (SELECT COUNT(*) FROM evento_secciones es
                 WHERE es.evento_id = e.id) AS num_secciones,
               (SELECT COALESCE(SUM(s.duracion),0) FROM evento_secciones es
                 JOIN secciones s ON s.id = es.seccion_id
                 WHERE es.evento_id = e.id) AS duracion_total,
               (SELECT COUNT(*) FROM evento_conexiones ec
                 WHERE ec.evento_id = e.id) AS num_conexiones
        FROM eventos e LEFT JOIN eventos_type et ON et.id = e.tipo_evento_id
        ORDER BY e.nombre COLLATE NOCASE
    """)


def get_evento(eid):
    return row("""
        SELECT e.id, e.nombre, e.numero, e.tipo_evento_id, et.nombre AS tipo
        FROM eventos e LEFT JOIN eventos_type et ON et.id = e.tipo_evento_id
        WHERE e.id=?""", (eid,))


def insert_evento(nombre, tipo_evento_id=None, numero=None):
    return execute(
        "INSERT INTO eventos (nombre, tipo_evento_id, numero) VALUES (?,?,?)",
        (nombre, tipo_evento_id, numero))


def update_evento(eid, nombre, tipo_evento_id=None, numero=None):
    execute("UPDATE eventos SET nombre=?, tipo_evento_id=?, numero=? WHERE id=?",
            (nombre, tipo_evento_id, numero, eid))


def delete_evento(eid):
    execute("DELETE FROM eventos WHERE id=?", (eid,))


def get_secciones_by_evento(eid):
    return rows("""
        SELECT s.id, s.nombre, ts.nombre AS tipo, s.ruta_archivo, s.texto_tts,
               s.duracion, s.regenerar_antes, s.titulo, s.descripcion,
               es.orden, es.contabilizable
        FROM secciones s
        JOIN evento_secciones es ON es.seccion_id = s.id
        LEFT JOIN tipos_seccion ts ON ts.id = s.tipo_seccion_id
        WHERE es.evento_id = ?
        ORDER BY es.orden, s.id""", (eid,))


def add_seccion_to_evento(eid, sid):
    with conn() as c:
        orden = c.execute(
            "SELECT COALESCE(MAX(orden),0)+1 FROM evento_secciones WHERE evento_id=?",
            (eid,)).fetchone()[0]
        c.execute("INSERT OR IGNORE INTO evento_secciones (evento_id, seccion_id, orden)"
                  " VALUES (?,?,?)", (eid, sid, orden))


def remove_seccion_from_evento(eid, sid):
    execute("DELETE FROM evento_secciones WHERE evento_id=? AND seccion_id=?",
            (eid, sid))


def set_orden_evento(eid, ids):
    with conn() as c:
        for i, sid in enumerate(ids):
            c.execute("UPDATE evento_secciones SET orden=? "
                      "WHERE evento_id=? AND seccion_id=?", (i + 1, eid, sid))


def set_contabilizable(eid, sid, value):
    execute("UPDATE evento_secciones SET contabilizable=? "
            "WHERE evento_id=? AND seccion_id=?", (int(bool(value)), eid, sid))


# ── Programación ──────────────────────────────────────────────────────────────
def get_programacion(solo_activos=False):
    where = "WHERE p.activo = 1" if solo_activos else ""
    return rows("""
        SELECT p.id, p.evento_id, p.fecha, p.hora, p.recurrencia, p.activo, p.zona,
               e.nombre AS evento_nombre, et.nombre AS evento_tipo
        FROM programacion p
        JOIN eventos e ON e.id = p.evento_id
        LEFT JOIN eventos_type et ON et.id = e.tipo_evento_id
        """ + where + """
        ORDER BY p.hora, p.fecha""")


def insert_programacion(eid, fecha, hora, recurrencia="ninguna", activo=True, zona=""):
    return execute("INSERT INTO programacion (evento_id, fecha, hora, recurrencia, activo, zona)"
                   " VALUES (?,?,?,?,?,?)", (eid, fecha, hora, recurrencia, int(bool(activo)), zona or ""))


def update_programacion(pid, eid, fecha, hora, recurrencia, activo, zona=""):
    execute("UPDATE programacion SET evento_id=?, fecha=?, hora=?, recurrencia=?, activo=?, zona=?"
            " WHERE id=?", (eid, fecha, hora, recurrencia, int(bool(activo)), zona or "", pid))


def delete_programacion(pid):
    execute("DELETE FROM programacion WHERE id=?", (pid,))


# ── Conexiones automáticas de un evento ──────────────────────────────────────
def get_conexiones(eid):
    return rows("SELECT id, sistema, accion, destino, modo, momento, minutos"
                " FROM evento_conexiones WHERE evento_id=? ORDER BY orden, id", (eid,))


def set_conexiones(eid, items):
    """Reemplaza la lista completa (ya validada)."""
    with conn() as c:
        c.execute("DELETE FROM evento_conexiones WHERE evento_id=?", (eid,))
        for i, a in enumerate(items):
            c.execute("INSERT INTO evento_conexiones (evento_id, orden, sistema, accion, destino,"
                      " modo, momento, minutos) VALUES (?,?,?,?,?,?,?,?)",
                      (eid, i, a["sistema"], a["accion"], a["destino"], a["modo"],
                       a["momento"], a["minutos"]))


# ── Historial ─────────────────────────────────────────────────────────────────
def historial_inicio(eid, nombre, origen):
    return execute("INSERT INTO historial (evento_id, evento, origen, inicio)"
                   " VALUES (?,?,?,datetime('now','localtime'))", (eid, nombre, origen))


def historial_fin(hid, resultado):
    execute("UPDATE historial SET fin=datetime('now','localtime'), resultado=? WHERE id=?",
            (resultado, hid))


def get_historial(limit=30):
    return rows("SELECT * FROM historial ORDER BY id DESC LIMIT ?", (limit,))
