"""
HAMNA Web — usuarios, roles, sesiones y bloqueo por intentos.

Roles (cada uno incluye lo del anterior):
  lectura    ver todo (estado, programación, eventos, conexiones)
  operador   transmitir, programar, editar eventos y secciones, conectar nodos
  admin      además Ajustes, Cron, logo y usuarios

Sesiones: la cookie lleva un código aleatorio; en la base solo se guarda su
huella (sha256), así que leer la base no permite entrar. Cerrar una sesión,
cambiar la contraseña o desactivar al usuario la invalida al instante.

Bloqueo: 5 contraseñas malas para un usuario desde una IP, o 20 desde una IP
para cualquier usuario, bloquean 15 minutos. Vive en memoria: reiniciar el
servicio lo limpia (sirve como "desbloqueo" de emergencia).
"""
import hashlib
import os
import re
import threading
import time

from . import db, settings
from .web import check_password, hash_password

ROLES = {"lectura": 1, "operador": 2, "admin": 3}
ROL_NOMBRE = {"lectura": "Solo lectura", "operador": "Operador", "admin": "Administrador"}
SESSION_DAYS = 30
TOUCH_SECS = 60                 # actualizar "última actividad" a lo mucho cada minuto
MAX_USER_IP, MAX_IP, LOCK_SECS = 5, 20, 15 * 60
USER_RX = re.compile(r"^[A-Za-z0-9._-]{2,32}$")


class AuthError(ValueError):
    pass


def init():
    with db.conn() as c:
        c.executescript("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario       TEXT NOT NULL UNIQUE COLLATE NOCASE,
                nombre        TEXT DEFAULT '',
                rol           TEXT NOT NULL DEFAULT 'operador',
                password_hash TEXT NOT NULL,
                activo        INTEGER DEFAULT 1,
                creado_en     DATETIME DEFAULT CURRENT_TIMESTAMP,
                ultimo_acceso DATETIME
            );
            CREATE TABLE IF NOT EXISTS sesiones_web (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                token_hash  TEXT NOT NULL UNIQUE,
                usuario_id  INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
                creada      REAL NOT NULL,
                ultima      REAL NOT NULL,
                expira      REAL NOT NULL,
                ip          TEXT DEFAULT '',
                agente      TEXT DEFAULT ''
            );
        """)
        # Migración: la contraseña única de antes pasa a ser el usuario "admin"
        if c.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0] == 0:
            old = settings.get("password_hash")
            if old:
                c.execute("INSERT INTO usuarios (usuario, nombre, rol, password_hash) VALUES (?,?,?,?)",
                          ("admin", "Administrador", "admin", old))
        c.execute("DELETE FROM sesiones_web WHERE expira < ?", (time.time(),))


def _th(token):
    return hashlib.sha256(token.encode()).hexdigest()


def _clean_user(u):
    if not u:
        return None
    u = dict(u)
    u.pop("password_hash", None)
    u["rol_nombre"] = ROL_NOMBRE.get(u.get("rol"), u.get("rol"))
    return u


# ── Bloqueo por intentos ─────────────────────────────────────────────────────
_fails = {}            # clave -> [marcas de tiempo de fallos]
_locked = {}           # clave -> hasta cuándo
_flock = threading.Lock()


def _keys(usuario, ip):
    return ("u:{}|{}".format(usuario.lower(), ip), MAX_USER_IP), ("ip:{}".format(ip), MAX_IP)


def locked_for(usuario, ip):
    now = time.time()
    with _flock:
        left = 0
        for k, _ in _keys(usuario, ip):
            until = _locked.get(k, 0)
            if until > now:
                left = max(left, until - now)
            elif k in _locked:
                del _locked[k]
        return int(left)


def _fail(usuario, ip):
    now = time.time()
    with _flock:
        for k, limit in _keys(usuario, ip):
            lst = [t for t in _fails.get(k, []) if now - t < LOCK_SECS] + [now]
            _fails[k] = lst
            if len(lst) >= limit:
                _locked[k] = now + LOCK_SECS
                _fails[k] = []
        if len(_fails) > 5000:           # no dejar crecer la memoria
            for k in [k for k, v in _fails.items() if not v or now - v[-1] > LOCK_SECS]:
                del _fails[k]


def _ok(usuario, ip):
    with _flock:
        _fails.pop(_keys(usuario, ip)[0][0], None)


def locked_list():
    now = time.time()
    with _flock:
        return [{"clave": k.split(":", 1)[1], "segundos": int(v - now)}
                for k, v in _locked.items() if v > now]


def unlock_all():
    with _flock:
        _locked.clear()
        _fails.clear()


# ── Inicio y cierre de sesión ────────────────────────────────────────────────
def login(usuario, password, ip, agente=""):
    usuario = (usuario or "").strip()
    left = locked_for(usuario, ip)
    if left:
        raise AuthError("Demasiados intentos. Espera {} min.".format(left // 60 + 1))
    u = db.row("SELECT * FROM usuarios WHERE usuario=? COLLATE NOCASE", (usuario,))
    if not u or not check_password(u["password_hash"], password or ""):
        if not u:   # mismo tiempo de respuesta que con usuario real
            check_password(hash_password("x", 1000), "y")
        _fail(usuario, ip)
        time.sleep(1.0)
        left = locked_for(usuario, ip)
        if left:
            raise AuthError("Demasiados intentos. Espera {} min.".format(left // 60 + 1))
        raise AuthError("Usuario o contraseña incorrectos")
    if not u["activo"]:
        raise AuthError("Este usuario está desactivado")
    _ok(usuario, ip)
    token = os.urandom(32).hex()
    now = time.time()
    with db.conn() as c:
        c.execute("""INSERT INTO sesiones_web (token_hash, usuario_id, creada, ultima, expira, ip, agente)
                     VALUES (?,?,?,?,?,?,?)""",
                  (_th(token), u["id"], now, now, now + SESSION_DAYS * 86400, ip, (agente or "")[:200]))
        c.execute("UPDATE usuarios SET ultimo_acceso=CURRENT_TIMESTAMP WHERE id=?", (u["id"],))
    return token, _clean_user(u)


def user_for(token, ip=""):
    """Usuario de una sesión válida, o None."""
    if not token or not re.match(r"^[0-9a-f]{64}$", token):
        return None
    now = time.time()
    r = db.row("""SELECT s.id AS sid, s.ultima, u.* FROM sesiones_web s
                  JOIN usuarios u ON u.id = s.usuario_id
                  WHERE s.token_hash=? AND s.expira > ? AND u.activo = 1""", (_th(token), now))
    if not r:
        return None
    if now - r["ultima"] > TOUCH_SECS:
        db.execute("UPDATE sesiones_web SET ultima=?, ip=? WHERE id=?", (now, ip or "", r["sid"]))
    sid = r.pop("sid")
    r.pop("ultima", None)
    u = _clean_user(r)
    u["sid"] = sid
    return u


def logout(token):
    if token:
        db.execute("DELETE FROM sesiones_web WHERE token_hash=?", (_th(token),))


def sessions(usuario_id=None):
    sql = """SELECT s.id, s.usuario_id, u.usuario, u.nombre, s.creada, s.ultima, s.ip, s.agente
             FROM sesiones_web s JOIN usuarios u ON u.id = s.usuario_id WHERE s.expira > ?"""
    args = [time.time()]
    if usuario_id is not None:
        sql += " AND s.usuario_id = ?"
        args.append(usuario_id)
    return db.rows(sql + " ORDER BY s.ultima DESC", args)


def revoke(sid, usuario_id=None):
    if usuario_id is None:
        db.execute("DELETE FROM sesiones_web WHERE id=?", (sid,))
    else:
        db.execute("DELETE FROM sesiones_web WHERE id=? AND usuario_id=?", (sid, usuario_id))


def revoke_user(usuario_id, except_sid=None):
    db.execute("DELETE FROM sesiones_web WHERE usuario_id=? AND id<>?", (usuario_id, except_sid or -1))


# ── Usuarios ─────────────────────────────────────────────────────────────────
def users():
    out = db.rows("""SELECT u.id, u.usuario, u.nombre, u.rol, u.activo, u.creado_en, u.ultimo_acceso,
                       (SELECT COUNT(*) FROM sesiones_web s WHERE s.usuario_id=u.id AND s.expira > ?) AS sesiones
                     FROM usuarios u ORDER BY u.usuario COLLATE NOCASE""", (time.time(),))
    return [_clean_user(u) for u in out]


def _check_pw(pw):
    if len(pw or "") < 8:
        raise ValueError("La contraseña debe tener al menos 8 caracteres")


def _active_admins(excluding=None):
    return db.row("SELECT COUNT(*) AS n FROM usuarios WHERE rol='admin' AND activo=1 AND id<>?",
                  (excluding or -1,))["n"]


def create_user(usuario, nombre, rol, password):
    usuario = (usuario or "").strip()
    if not USER_RX.match(usuario):
        raise ValueError("Usuario inválido: de 2 a 32 letras, números, punto, guion o guion bajo")
    if rol not in ROLES:
        raise ValueError("Rol inválido")
    _check_pw(password)
    if db.row("SELECT id FROM usuarios WHERE usuario=? COLLATE NOCASE", (usuario,)):
        raise ValueError("Ya existe el usuario «{}»".format(usuario))
    return db.execute("INSERT INTO usuarios (usuario, nombre, rol, password_hash) VALUES (?,?,?,?)",
                      (usuario, (nombre or "").strip()[:60], rol, hash_password(password)))


def update_user(uid, cur_sid=None, **f):
    u = db.row("SELECT * FROM usuarios WHERE id=?", (uid,))
    if not u:
        raise ValueError("No existe ese usuario")
    sets, vals, cerrar = [], [], False
    if "nombre" in f:
        sets.append("nombre=?"); vals.append((f["nombre"] or "").strip()[:60])
    if "rol" in f and f["rol"] != u["rol"]:
        if f["rol"] not in ROLES:
            raise ValueError("Rol inválido")
        if u["rol"] == "admin" and not _active_admins(excluding=uid):
            raise ValueError("Debe quedar al menos un administrador activo")
        sets.append("rol=?"); vals.append(f["rol"])
    if "activo" in f and bool(f["activo"]) != bool(u["activo"]):
        if not f["activo"] and u["rol"] == "admin" and not _active_admins(excluding=uid):
            raise ValueError("Debe quedar al menos un administrador activo")
        sets.append("activo=?"); vals.append(1 if f["activo"] else 0)
        cerrar = cerrar or not f["activo"]
    if f.get("password"):
        _check_pw(f["password"])
        sets.append("password_hash=?"); vals.append(hash_password(f["password"]))
        cerrar = True
    if sets:
        vals.append(uid)
        db.execute("UPDATE usuarios SET " + ", ".join(sets) + " WHERE id=?", vals)
    if cerrar:
        revoke_user(uid, except_sid=cur_sid)


def delete_user(uid, my_id):
    if uid == my_id:
        raise ValueError("No puedes borrar tu propio usuario")
    u = db.row("SELECT * FROM usuarios WHERE id=?", (uid,))
    if not u:
        raise ValueError("No existe ese usuario")
    if u["rol"] == "admin" and u["activo"] and not _active_admins(excluding=uid):
        raise ValueError("Debe quedar al menos un administrador activo")
    db.execute("DELETE FROM sesiones_web WHERE usuario_id=?", (uid,))
    db.execute("DELETE FROM usuarios WHERE id=?", (uid,))


def change_own_password(user, actual, nueva):
    u = db.row("SELECT * FROM usuarios WHERE id=?", (user["id"],))
    if not u or not check_password(u["password_hash"], actual or ""):
        raise ValueError("La contraseña actual no coincide")
    _check_pw(nueva)
    db.execute("UPDATE usuarios SET password_hash=? WHERE id=?", (hash_password(nueva), u["id"]))
    revoke_user(u["id"], except_sid=user.get("sid"))


def set_password_cli(usuario, password):
    """Desde la terminal del nodo (hamna-web-passwd): crea el usuario como
    administrador si no existe, lo activa y cierra sus sesiones."""
    init()
    usuario = (usuario or "admin").strip()
    if not USER_RX.match(usuario):
        raise ValueError("Usuario inválido")
    if len(password) < 6:
        raise ValueError("Debe tener al menos 6 caracteres")
    u = db.row("SELECT * FROM usuarios WHERE usuario=? COLLATE NOCASE", (usuario,))
    if u:
        db.execute("UPDATE usuarios SET password_hash=?, activo=1 WHERE id=?", (hash_password(password), u["id"]))
        revoke_user(u["id"])
        return "contraseña cambiada; sus sesiones abiertas se cerraron"
    db.execute("INSERT INTO usuarios (usuario, nombre, rol, password_hash) VALUES (?,?,?,?)",
               (usuario, "Administrador" if usuario == "admin" else usuario, "admin", hash_password(password)))
    return "creado como administrador"


def has_admin():
    init()
    return db.row("SELECT COUNT(*) AS n FROM usuarios WHERE rol='admin' AND activo=1")["n"] > 0
