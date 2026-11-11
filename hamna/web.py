"""
HAMNA Web — servidor HTTP mínimo con la librería estándar.

Sin Flask a propósito: HamVOIP trae Python 3.5 y no se le deben instalar
paquetes, y Debian 13 ya no trae el módulo cgi. Esto corre igual en
Python 3.5 a 3.13.

  - Rutas con expresiones regulares
  - JSON, formularios multipart (las subidas grandes van a disco, no a RAM)
  - Sesión en cookie firmada con HMAC
  - Archivos con soporte de Range (para adelantar en el reproductor)
"""
import base64
import hashlib
import hmac
import json
import logging
import mimetypes
import mmap
import os
import re
import socketserver
import time
import traceback
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, unquote, urlparse

from . import paths

log = logging.getLogger("hamna.http")

COOKIE = "hamna_s"
SESSION_DAYS = 30
mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("text/css", ".css")
mimetypes.add_type("audio/mpeg", ".mp3")
mimetypes.add_type("audio/wav", ".wav")
mimetypes.add_type("audio/ogg", ".ogg")


class HTTPError(Exception):
    def __init__(self, code, msg=""):
        Exception.__init__(self, msg or str(code))
        self.code = code
        self.msg = msg


# ── Contraseñas ───────────────────────────────────────────────────────────────
def hash_password(pw, iterations=120000):
    salt = base64.b16encode(os.urandom(8)).decode().lower()
    dk = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt.encode(), iterations)
    return "pbkdf2:sha256:{}${}${}".format(iterations, salt, base64.b16encode(dk).decode().lower())


def check_password(stored, pw):
    try:
        method, salt, hexd = stored.split("$", 2)
        _, algo, iters = method.split(":")
        dk = hashlib.pbkdf2_hmac(algo, pw.encode(), salt.encode(), int(iters))
        return hmac.compare_digest(base64.b16encode(dk).decode().lower(), hexd.lower())
    except Exception:
        return False


# ── Petición y respuesta ─────────────────────────────────────────────────────
class UploadedFile:
    def __init__(self, filename, path):
        self.filename = filename
        self.path = path            # archivo temporal; el handler lo mueve o se borra


class Request:
    def __init__(self, handler, secret):
        self.h = handler
        self.secret = secret
        u = urlparse(handler.path)
        self.path = unquote(u.path)
        self.query = {k: v[0] for k, v in parse_qs(u.query).items()}
        self.method = handler.command
        self.headers = handler.headers
        self.form = {}
        self.files = {}
        self._json = None
        self.session = self._read_session()
        self.new_session = None
        self.user = None            # lo llena App.user_loader
        self.ip = ""

    # Sesión
    def _sign(self, data):
        return base64.urlsafe_b64encode(
            hmac.new(self.secret.encode(), data, hashlib.sha256).digest()).decode().rstrip("=")

    def _read_session(self):
        raw = self.headers.get("Cookie", "")
        m = re.search(r"(?:^|;\s*)" + COOKIE + r"=([^;]+)", raw)
        if not m:
            return {}
        try:
            payload, sig = m.group(1).rsplit(".", 1)
            if not hmac.compare_digest(self._sign(payload.encode()), sig):
                return {}
            data = json.loads(base64.urlsafe_b64decode(payload + "==").decode())
            return data if data.get("exp", 0) > time.time() else {}
        except Exception:
            return {}

    def login(self, token):
        self.new_session = {"t": token, "exp": int(time.time()) + SESSION_DAYS * 86400}

    @property
    def token(self):
        return self.session.get("t") or ""

    def logout(self):
        self.new_session = {}

    def cookie_header(self):
        if self.new_session is None:
            return None
        if not self.new_session:
            return "{}=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax".format(COOKIE)
        payload = base64.urlsafe_b64encode(json.dumps(self.new_session).encode()).decode().rstrip("=")
        return "{}={}.{}; Path=/; Max-Age={}; HttpOnly; SameSite=Lax".format(
            COOKIE, payload, self._sign(payload.encode()), SESSION_DAYS * 86400)

    @property
    def authed(self):
        return bool(self.user)

    # Cuerpo
    def json(self):
        if self._json is None:
            self._json = {}
            if self.form:
                self._json = dict(self.form)
            else:
                raw = getattr(self, "_raw", b"")
                if raw:
                    try:
                        self._json = json.loads(raw.decode("utf-8")) or {}
                    except ValueError:
                        raise HTTPError(400, "JSON inválido")
        return self._json

    def cleanup(self):
        for f in self.files.values():
            if f.path:
                paths.rm(f.path)


class Response:
    def __init__(self, body=b"", status=200, ctype="application/json; charset=utf-8",
                 headers=None, file=None, cache=False, stream=None):
        self.stream = stream            # generador de bytes (audio en vivo)
        self.body = body
        self.status = status
        self.ctype = ctype
        self.headers = headers or {}
        self.file = file
        self.cache = cache


def jsonr(obj, status=200):
    return Response(json.dumps(obj, ensure_ascii=False, default=str).encode("utf-8"), status)


def send_file(path, ctype=None, cache=False):
    path = str(path)
    if not os.path.isfile(path):
        raise HTTPError(404, "No existe")
    return Response(file=path, ctype=ctype or mimetypes.guess_type(path)[0]
                    or "application/octet-stream", cache=cache)


# ── Multipart a disco ────────────────────────────────────────────────────────
def _parse_multipart(rfile, length, boundary, max_bytes):
    """Copia el cuerpo a un archivo temporal y lo parte con mmap; así una
    subida de 200 MB no ocupa 200 MB de RAM en la Raspberry."""
    if length > max_bytes:
        raise HTTPError(413, "El archivo es demasiado grande (máximo {} MB)".format(max_bytes // 2**20))
    spool = paths.tmp_dir() / ("up_" + uuid.uuid4().hex)
    form, files = {}, {}
    try:
        with open(str(spool), "wb") as f:
            left = length
            while left > 0:
                chunk = rfile.read(min(65536, left))
                if not chunk:
                    raise HTTPError(400, "Subida incompleta")
                f.write(chunk)
                left -= len(chunk)
        if length == 0:
            return form, files
        delim = b"--" + boundary
        with open(str(spool), "rb") as f:
            mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
            try:
                pos = mm.find(delim)
                while pos >= 0:
                    pos += len(delim)
                    if mm[pos:pos + 2] == b"--":
                        break
                    pos += 2                                   # \r\n
                    hend = mm.find(b"\r\n\r\n", pos)
                    if hend < 0:
                        break
                    head = mm[pos:hend].decode("utf-8", "replace")
                    start = hend + 4
                    nxt = mm.find(b"\r\n" + delim, start)
                    if nxt < 0:
                        break
                    name = re.search(r'name="([^"]*)"', head)
                    fname = re.search(r'filename="([^"]*)"', head)
                    if name:
                        if fname is not None:
                            if fname.group(1):
                                dest = paths.tmp_dir() / ("upf_" + uuid.uuid4().hex)
                                with open(str(dest), "wb") as out:
                                    p = start
                                    while p < nxt:
                                        q = min(nxt, p + 1048576)
                                        out.write(mm[p:q])
                                        p = q
                                files[name.group(1)] = UploadedFile(fname.group(1), str(dest))
                        else:
                            form[name.group(1)] = mm[start:nxt].decode("utf-8", "replace")
                    pos = nxt + 2
            finally:
                mm.close()
    finally:
        paths.rm(spool)
    return form, files


# ── Aplicación ───────────────────────────────────────────────────────────────
class App:
    def __init__(self, static_dir):
        self.routes = []
        self.static_dir = str(static_dir)
        self.secret = "x"
        self.max_upload = 300 * 2**20
        self.user_loader = None     # función(request) -> usuario o None
        self.roles = {}             # rol -> nivel

    def route(self, pattern, methods=("GET",), auth=True, rol=None):
        """auth=False: pública. rol: mínimo necesario; si no se da, leer (GET)
        pide 'lectura' y cambiar algo pide 'operador'."""
        rx = re.compile("^" + re.sub(r"<int:(\w+)>", r"(?P<\1>\\d+)",
                                     re.sub(r"<(\w+)>", r"(?P<\1>[^/]+)", pattern)) + "$")

        def deco(fn):
            self.routes.append((rx, tuple(methods), fn, auth, rol))
            return fn
        return deco

    def dispatch(self, req):
        if req.path.startswith("/static/"):
            name = req.path[len("/static/"):]
            if not re.match(r"^[A-Za-z0-9_.-]+$", name):
                raise HTTPError(404)
            return send_file(os.path.join(self.static_dir, name), cache=True)
        allowed = False
        for rx, methods, fn, auth, rol in self.routes:
            m = rx.match(req.path)
            if not m:
                continue
            allowed = True
            if req.method not in methods:
                continue
            if auth:
                if not req.authed:
                    return jsonr({"ok": False, "error": "Inicia sesión"}, 401)
                # Defensa CSRF: otro sitio no puede mandar esta cabecera sin permiso
                if req.method not in ("GET", "HEAD") and req.headers.get("X-HAMNA") != "1":
                    return jsonr({"ok": False, "error": "Petición rechazada"}, 403)
                need = rol or ("lectura" if req.method in ("GET", "HEAD") else "operador")
                if self.roles.get(req.user.get("rol"), 0) < self.roles.get(need, 99):
                    return jsonr({"ok": False, "error": "Tu usuario no tiene permiso para esto"}, 403)
            kw = {k: (int(v) if v.isdigit() else v) for k, v in m.groupdict().items()}
            return fn(req, **kw)
        raise HTTPError(405 if allowed else 404)

    def serve(self, host, port):
        app = self

        class Server(socketserver.ThreadingMixIn, HTTPServer):
            daemon_threads = True
            allow_reuse_address = True
            request_queue_size = 32

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"
            server_version = "HAMNA"
            sys_version = ""

            def log_message(self, fmt, *args):
                pass

            def _client_ip(self):
                """IP de quien usa la página. Detrás de Apache (/hamna/) la
                conexión llega de 127.0.0.1 y la IP real viene en X-Forwarded-For."""
                ip = self.client_address[0]
                fwd = self.headers.get("X-Forwarded-For", "")
                if fwd and ip in ("127.0.0.1", "::1", "::ffff:127.0.0.1"):
                    return fwd.split(",")[-1].strip() or ip
                return ip

            def _handle(self):
                req = None
                try:
                    req = Request(self, app.secret)
                    req.ip = self._client_ip()
                    if app.user_loader:
                        req.user = app.user_loader(req)
                    length = int(self.headers.get("Content-Length") or 0)
                    ctype = self.headers.get("Content-Type", "")
                    if ctype.startswith("multipart/form-data"):
                        m = re.search(r'boundary="?([^";]+)"?', ctype)
                        if not m:
                            raise HTTPError(400, "Falta boundary")
                        if not req.authed and req.path != "/api/login":
                            self.rfile.read(length) if length < 65536 else None
                            raise HTTPError(401, "Inicia sesión")
                        req.form, req.files = _parse_multipart(
                            self.rfile, length, m.group(1).encode(), app.max_upload)
                    elif length:
                        if length > 2**20:
                            raise HTTPError(413, "Petición demasiado grande")
                        req._raw = self.rfile.read(length)
                    if ctype.startswith("application/x-www-form-urlencoded") and getattr(req, "_raw", b""):
                        req.form = {k: v[0] for k, v in parse_qs(req._raw.decode()).items()}
                    resp = app.dispatch(req)
                    if req.method in ("POST", "PUT", "DELETE") and req.path != "/api/login":
                        who = req.user["usuario"] if req.user else "-"
                        log.info("%s %s por %s desde %s → %s", req.method, req.path,
                                 who, req.ip, resp.status)
                except HTTPError as e:
                    msg = e.msg or {401: "Inicia sesión", 404: "No encontrado",
                                    405: "Método no permitido"}.get(e.code, "Error")
                    resp = jsonr({"ok": False, "error": msg}, e.code)
                    if e.code in (400, 401, 413):
                        self.close_connection = True
                except (ValueError, FileNotFoundError, RuntimeError, KeyError) as e:
                    resp = jsonr({"ok": False, "error": str(e)}, 400)
                except Exception as e:
                    log.error("Error en %s %s\n%s", self.command, self.path, traceback.format_exc())
                    resp = jsonr({"ok": False, "error": "Error interno: {}".format(e)}, 500)
                finally:
                    if req is not None:
                        req.cleanup()
                try:
                    self._send(resp, req)
                except (BrokenPipeError, ConnectionResetError):
                    self.close_connection = True

            def _send(self, resp, req):
                head_only = self.command == "HEAD"
                hdrs = dict(resp.headers)
                cookie = req.cookie_header() if req else None
                if resp.stream is not None:
                    self.close_connection = True
                    self.send_response(resp.status)
                    self.send_header("Content-Type", resp.ctype)
                    self.send_header("Cache-Control", "no-store")
                    self.send_header("X-Accel-Buffering", "no")
                    self.send_header("Connection", "close")
                    for k, v in hdrs.items():
                        self.send_header(k, v)
                    if cookie:
                        self.send_header("Set-Cookie", cookie)
                    self.end_headers()
                    try:
                        if not head_only:
                            for chunk in resp.stream:
                                self.wfile.write(chunk)
                    finally:
                        resp.stream.close()
                    return
                if resp.file:
                    size = os.path.getsize(resp.file)
                    start, end, status = 0, size - 1, 200
                    rng = self.headers.get("Range", "")
                    m = re.match(r"bytes=(\d*)-(\d*)$", rng.strip())
                    if m and size:
                        if m.group(1):
                            start = int(m.group(1))
                            end = int(m.group(2)) if m.group(2) else size - 1
                        else:
                            start = max(0, size - int(m.group(2) or 0))
                        end = min(end, size - 1)
                        if start <= end:
                            status = 206
                            hdrs["Content-Range"] = "bytes {}-{}/{}".format(start, end, size)
                    self.send_response(status)
                    self.send_header("Content-Type", resp.ctype)
                    self.send_header("Content-Length", str(end - start + 1 if size else 0))
                    self.send_header("Accept-Ranges", "bytes")
                    self.send_header("Cache-Control", "max-age=300" if resp.cache else "no-store")
                    for k, v in hdrs.items():
                        self.send_header(k, v)
                    if cookie:
                        self.send_header("Set-Cookie", cookie)
                    self.end_headers()
                    if head_only or not size:
                        return
                    with open(resp.file, "rb") as f:
                        f.seek(start)
                        left = end - start + 1
                        while left > 0:
                            chunk = f.read(min(65536, left))
                            if not chunk:
                                break
                            self.wfile.write(chunk)
                            left -= len(chunk)
                    return
                body = resp.body if isinstance(resp.body, bytes) else str(resp.body).encode()
                self.send_response(resp.status)
                self.send_header("Content-Type", resp.ctype)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                if self.close_connection:
                    self.send_header("Connection", "close")
                for k, v in hdrs.items():
                    self.send_header(k, v)
                if cookie:
                    self.send_header("Set-Cookie", cookie)
                self.end_headers()
                if not head_only:
                    self.wfile.write(body)

            do_GET = do_POST = do_PUT = do_DELETE = do_HEAD = _handle

        srv = Server((host, port), Handler)
        log.info("Escuchando en http://%s:%d", host, port)
        srv.serve_forever(poll_interval=0.5)
