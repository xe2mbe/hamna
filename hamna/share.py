"""
HAMNA Web — compartir un evento con otros nodos (lado del que comparte).

Un administrador crea un código de acceso para un evento. Con ese código,
otro HAMNA puede leer la lista de secciones del evento y descargar sus
audios: nada más (no entra a la página ni ve otros eventos). En la base solo
se guarda la huella (sha256) del código.
"""
import hashlib
import os
import threading
import time

from . import db, paths

_hash_lock = threading.Lock()
_hash_cache = {}          # (ruta, mtime, tamaño) -> sha256


def init():
    with db.conn() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS compartidos (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            evento_id  INTEGER NOT NULL REFERENCES eventos(id) ON DELETE CASCADE,
            token_hash TEXT NOT NULL UNIQUE,
            etiqueta   TEXT DEFAULT '',
            creado     REAL NOT NULL,
            ultimo_uso REAL,
            ultima_ip  TEXT DEFAULT '',
            usos       INTEGER DEFAULT 0)""")


def _th(token):
    return hashlib.sha256(token.encode()).hexdigest()


def create(evento_id, etiqueta=""):
    token = "hs_" + os.urandom(24).hex()
    db.execute("INSERT INTO compartidos (evento_id, token_hash, etiqueta, creado) VALUES (?,?,?,?)",
               (evento_id, _th(token), (etiqueta or "").strip()[:60], time.time()))
    return token


def codes(evento_id):
    return db.rows("SELECT id, etiqueta, creado, ultimo_uso, ultima_ip, usos FROM compartidos"
                   " WHERE evento_id=? ORDER BY id", (evento_id,))


def revoke(code_id):
    db.execute("DELETE FROM compartidos WHERE id=?", (code_id,))


def event_for(token, ip=""):
    """Evento al que da acceso el código, o None."""
    if not token or not token.startswith("hs_") or len(token) > 80:
        return None
    r = db.row("SELECT id, evento_id, ultimo_uso FROM compartidos WHERE token_hash=?", (_th(token),))
    if not r:
        return None
    db.execute("UPDATE compartidos SET ultimo_uso=?, ultima_ip=?, usos=usos+1 WHERE id=?",
               (time.time(), ip or "", r["id"]))
    return r["evento_id"]


def _file(sec):
    name = sec.get("ruta_archivo") or ""
    if not name:
        return None
    p = paths.audios_dir() / name
    return p if p.is_file() else None


def file_sha(p):
    st = p.stat()
    key = (str(p), st.st_mtime, st.st_size)
    with _hash_lock:
        if key in _hash_cache:
            return _hash_cache[key]
    h = hashlib.sha256()
    with open(str(p), "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    with _hash_lock:
        _hash_cache[key] = h.hexdigest()
    return _hash_cache[key]


def payload(evento_id):
    ev = db.get_evento(evento_id)
    if not ev:
        return None
    out = []
    for s in db.get_secciones_by_evento(evento_id):
        p = _file(s)
        out.append({
            "uid": "s{}".format(s["id"]), "id": s["id"], "nombre": s["nombre"], "tipo": s.get("tipo"),
            "titulo": s.get("titulo"), "descripcion": s.get("descripcion"), "texto_tts": s.get("texto_tts"),
            "regenerar_antes": bool(s.get("regenerar_antes")), "contabilizable": bool(s.get("contabilizable")),
            "duracion": s.get("duracion") or 0,
            "archivo": {"sha256": file_sha(p), "tam": p.stat().st_size, "ext": p.suffix.lower()} if p else None,
        })
    return {"evento": {"nombre": ev["nombre"], "numero": ev.get("numero")}, "secciones": out}


def file_for(evento_id, seccion_id):
    for s in db.get_secciones_by_evento(evento_id):
        if s["id"] == seccion_id:
            return _file(s)
    return None
