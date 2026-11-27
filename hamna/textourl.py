"""
HAMNA Web — texto desde una dirección (anuncios de tipo «url»).

El nodo baja un texto de una dirección https justo antes de transmitirlo (ya
con el canal libre), para que salga al minuto: un pronóstico, un aviso del día…

Contrato con el servidor que publica el texto (propuesta de XE1E):

  200 text/plain; charset=utf-8   se lee (sin HTML ni marcas)
  204 No Content                  hoy no hay nada: no se transmite y no es error
  X-HAMNA-Vence: <ISO 8601 UTC>   si ya pasó, igual que un 204 (un texto de ayer nunca sale)
  otro código, tiempo agotado,
  TLS inválido, HTML…             error → texto de respaldo o se salta
  Párrafos separados por un renglón en blanco: si el texto no cabe en un tramo
  se corta solo entre párrafos (anuncios.tramos).

Límites: 10 s, 16 KB, hasta 3 redirecciones (todas https), User-Agent
HAMNA/<versión>, certificado verificado. Como es una petición que sale del
nodo hacia donde diga un campo, solo un administrador pone la dirección y no se
aceptan direcciones de la red local ni del propio equipo (127.x, 10.x,
192.168.x…). En Ajustes puede limitarse a ciertos dominios y darse un archivo
de certificados propio (para equipos viejos cuyo almacén ya no reconoce al
servidor).
"""
import datetime as dt
import ipaddress
import logging
import os
import re
import socket
import ssl
import urllib.error
import urllib.parse
import urllib.request

from . import VERSION

log = logging.getLogger("hamna.textourl")

TIMEOUT = 10
MAX_BYTES = 16 * 1024
MAX_REDIR = 3
URL_MAX = 500


class SinContenido(Exception):
    """204, o el texto ya venció: hoy no hay nada que decir (no es un error)."""


def validar(url):
    """Normaliza y revisa la forma de la dirección. Lanza ValueError."""
    url = str(url or "").strip()
    if not url:
        raise ValueError("Escribe la dirección del texto")
    if len(url) > URL_MAX or re.search(r"\s", url):
        raise ValueError("Dirección inválida")
    p = urllib.parse.urlsplit(url)
    if p.scheme != "https" or not p.hostname:
        raise ValueError("La dirección debe empezar con https://")
    if p.username or p.password:
        raise ValueError("La dirección no puede llevar usuario ni contraseña")
    return url


def _dominio_ok(host, cfg):
    lista = [x.strip().lower().lstrip(".") for x in re.split(r"[,\s]+", cfg.get("url_dominios") or "") if x.strip()]
    if not lista:
        return True
    host = host.lower().rstrip(".")
    return any(host == d or host.endswith("." + d) for d in lista)


def _ip_publica(host, port):
    """Todas las direcciones del nombre deben ser públicas (nada de la red local ni del equipo)."""
    try:
        infos = socket.getaddrinfo(host, port or 443, proto=socket.IPPROTO_TCP)
    except socket.gaierror as e:
        raise RuntimeError("No encontré el servidor «{}»: {}".format(host, e))
    for info in infos:
        ip = ipaddress.ip_address(info[4][0].split("%")[0])
        if getattr(ip, "ipv4_mapped", None):
            ip = ip.ipv4_mapped
        if not ip.is_global or ip.is_multicast:
            raise RuntimeError("«{}» apunta a una dirección privada o del propio equipo ({}); no se permite".format(host, ip))


def _revisar_destino(url, cfg):
    p = urllib.parse.urlsplit(url)
    if p.scheme != "https" or not p.hostname:
        raise RuntimeError("Una redirección llevó a una dirección que no es https")
    if not _dominio_ok(p.hostname, cfg):
        raise RuntimeError("El dominio «{}» no está en la lista permitida (Ajustes → Voz)".format(p.hostname))
    _ip_publica(p.hostname, p.port)


class _Redir(urllib.request.HTTPRedirectHandler):
    max_redirections = MAX_REDIR

    def __init__(self, cfg):
        self.cfg = cfg

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        _revisar_destino(newurl, self.cfg)
        return urllib.request.HTTPRedirectHandler.redirect_request(self, req, fp, code, msg, headers, newurl)


def _contexto(cfg):
    ca = (cfg.get("url_cafile") or "").strip()
    if ca:
        if not os.path.isfile(ca):
            raise RuntimeError("No existe el archivo de certificados {} (Ajustes → Voz)".format(ca))
        return ssl.create_default_context(cafile=ca)
    return ssl.create_default_context()


def _vence(valor):
    """«2026-11-23T12:00:00Z» (también con +00:00 o fracciones) → datetime UTC sin zona; None si no se entiende."""
    m = re.match(r"^\s*(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})(?::(\d{2}))?(?:\.\d+)?\s*(Z|[+-]\d{2}:?\d{2})?\s*$", valor or "")
    if not m:
        return None
    y, mo, d, h, mi, s = (int(x or 0) for x in m.groups()[:6])
    t = dt.datetime(y, mo, d, h, mi, s)
    z = m.group(7)
    if z and z != "Z":
        signo = 1 if z[0] == "+" else -1
        hh, mm = int(z[1:3]), int(z[-2:])
        t -= signo * dt.timedelta(hours=hh, minutes=mm)
    return t


def limpiar(texto):
    """Renglones parejos, sin caracteres de control; párrafos separados por un renglón en blanco."""
    t = texto.replace("﻿", "").replace("\r\n", "\n").replace("\r", "\n")
    t = re.sub(r"[\x00-\x08\x0b-\x1f\x7f]", " ", t)
    t = re.sub(r"[ \t]+\n", "\n", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def bajar(url, cfg):
    """Baja el texto. Devuelve (texto, info). Lanza SinContenido (204 o vencido) o RuntimeError."""
    url = validar(url)
    _revisar_destino(url, cfg)
    opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=_contexto(cfg)), _Redir(cfg))
    req = urllib.request.Request(url, headers={"User-Agent": "HAMNA/{}".format(VERSION),
                                               "Accept": "text/plain, */*;q=0.1"})
    try:
        r = opener.open(req, timeout=TIMEOUT)
    except urllib.error.HTTPError as e:
        raise RuntimeError("El servidor respondió HTTP {}".format(e.code))
    except urllib.error.URLError as e:
        motivo = e.reason
        if isinstance(motivo, ssl.SSLError) or "CERTIFICATE" in str(motivo).upper():
            raise RuntimeError("No pude verificar el certificado del servidor ({}). En equipos viejos puede faltar "
                               "su autoridad: pon un archivo de certificados en Ajustes → Voz.".format(motivo))
        raise RuntimeError("No pude conectar: {}".format(motivo))
    except RuntimeError:
        raise
    except (socket.timeout, OSError) as e:
        raise RuntimeError("No respondió a tiempo ({} s): {}".format(TIMEOUT, e))
    with r:
        if r.status == 204:
            raise SinContenido("El servidor dice que hoy no hay nada (204)")
        if r.status != 200:
            raise RuntimeError("El servidor respondió HTTP {}".format(r.status))
        vence = r.headers.get("X-HAMNA-Vence") or ""
        if vence:
            t = _vence(vence)
            if t is None:
                log.warning("X-HAMNA-Vence no se entiende: %s", vence[:60])
            elif t <= dt.datetime.utcnow():
                raise SinContenido("El texto ya venció ({} UTC)".format(t.strftime("%Y-%m-%d %H:%M")))
        ctype = (r.headers.get("Content-Type") or "").lower()
        if "html" in ctype or "xml" in ctype or "json" in ctype:
            raise RuntimeError("Llegó {} y se esperaba texto plano".format(ctype.split(";")[0] or "otro formato"))
        try:
            datos = r.read(MAX_BYTES + 1)
        except (socket.timeout, OSError) as e:
            raise RuntimeError("Se cortó al leer: {}".format(e))
        if len(datos) > MAX_BYTES:
            raise RuntimeError("El texto pesa más de {} KB".format(MAX_BYTES // 1024))
        m = re.search(r"charset=([\w.-]+)", ctype)
        try:
            texto = datos.decode(m.group(1) if m else "utf-8", errors="replace")
        except LookupError:
            texto = datos.decode("utf-8", errors="replace")
        final = r.geturl()
    texto = limpiar(texto)
    if re.search(r"(?i)<\s*(html|body|div|p|script)\b", texto):
        raise RuntimeError("Llegó HTML y se esperaba texto plano")
    if not texto:
        raise SinContenido("El servidor mandó un texto vacío")
    return texto, {"url": final, "bytes": len(datos), "vence": vence, "tipo": ctype.split(";")[0]}


def parrafos(texto):
    return [p.strip() for p in re.split(r"\n\s*\n", texto) if p.strip()]
