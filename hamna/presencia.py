"""
HAMNA Web — ¿el nodo AllStar está en línea?

Tres estados por nodo:
  responde    registrado en AllStar y contesta un POKE de IAX (se le puede conectar)
  registrado  registrado (prendido y reportándose) pero no contesta: casi siempre
              falta reenviar el puerto UDP de IAX en su router
  fuera       no está registrado: apagado o sin internet
  (sin dato)  nodos privados (1000-1999), EchoLink (3xxxxxx) o si falló el DNS

El registro se lee del DNS de AllStar: <nodo>.nodes.allstarlink.org TXT
"NN=… IP=… PT=…". El DNS se consulta con un cliente mínimo (la biblioteca
estándar no lee TXT); si no hay servidor DNS utilizable se usa el registro A
con el puerto 4569. El POKE es un solo paquete de 12 bytes; el nodo contesta
PONG y se le manda ACK para que no lo repita. Todo con la biblioteca estándar
(Python 3.5+). Los resultados se guardan unos minutos.
"""
import logging
import random
import re
import socket
import struct
import threading
import time
from concurrent.futures import ThreadPoolExecutor

log = logging.getLogger("hamna.presencia")

DOMINIO = "nodes.allstarlink.org"
TTL = 150                 # segundos que vale un resultado
MAX_NODOS = 200
_cache = {}
_lock = threading.Lock()
_pool = ThreadPoolExecutor(max_workers=24)


def _nameservers():
    try:
        with open("/etc/resolv.conf") as f:
            ns = [l.split()[1] for l in f if l.startswith("nameserver") and len(l.split()) > 1]
    except OSError:
        ns = []
    return [n for n in ns if re.match(r"^\d{1,3}(\.\d{1,3}){3}$", n)]


def _skip_name(d, i):
    while True:
        b = d[i]
        if b == 0:
            return i + 1
        if b & 0xC0 == 0xC0:
            return i + 2
        i += b + 1


def _txt(nombre, ns, timeout=2.0):
    """Registros TXT de 'nombre'. None si no existe; lanza excepción si el DNS falló."""
    qid = random.randint(0, 0xFFFF)
    q = struct.pack(">HHHHHH", qid, 0x0100, 1, 0, 0, 0)
    for p in nombre.split("."):
        q += struct.pack("B", len(p)) + p.encode("ascii")
    q += b"\0" + struct.pack(">HH", 16, 1)
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.settimeout(timeout)
        for _ in range(2):
            s.sendto(q, (ns, 53))
            try:
                while True:
                    d, _a = s.recvfrom(4096)
                    if len(d) >= 12 and struct.unpack(">H", d[:2])[0] == qid:
                        break
                break
            except socket.timeout:
                d = None
        if d is None:
            raise OSError("el DNS no contestó")
    finally:
        s.close()
    fl, qd, an = struct.unpack(">HHH", d[2:8])
    rcode = fl & 0xF
    if rcode == 3:
        return None
    if rcode != 0:
        raise OSError("DNS rcode %d" % rcode)
    i = 12
    for _ in range(qd):
        i = _skip_name(d, i) + 4
    out = []
    for _ in range(an):
        i = _skip_name(d, i)
        t, _c, _ttl, rl = struct.unpack(">HHIH", d[i:i + 10])
        i += 10
        if t == 16:
            j = i
            while j < i + rl:
                L = d[j]
                out.append(d[j + 1:j + 1 + L].decode("ascii", "replace"))
                j += L + 1
        i += rl
    return out or None


def registro(nodo):
    """(ip, puerto) si el nodo está registrado, None si no. Excepción si no se pudo saber."""
    nombre = "{}.{}".format(nodo, DOMINIO)
    err = None
    for ns in _nameservers()[:2]:
        try:
            txt = _txt(nombre, ns)
        except (OSError, IndexError, struct.error) as e:
            err = e
            continue
        if not txt:
            return None
        kv = dict(x.split("=", 1) for x in txt if "=" in x)
        if kv.get("IP"):
            try:
                return kv["IP"], int(kv.get("PT") or 4569)
            except ValueError:
                return kv["IP"], 4569
        return None
    # Sin DNS propio utilizable: el resolvedor del sistema (registro A)
    try:
        return socket.gethostbyname(nombre), 4569
    except socket.gaierror as e:
        if e.errno in (socket.EAI_NONAME, getattr(socket, "EAI_NODATA", -5)):
            return None
        raise OSError(err or e)


def poke(ip, puerto, timeout=1.2, intentos=2):
    """Milisegundos que tardó el PONG, o None si no contestó."""
    cn = random.randint(1, 0x7FFF)
    pkt = struct.pack(">HHIBBBB", 0x8000 | cn, 0, 3, 0, 0, 6, 0x1E)      # IAX POKE
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.settimeout(timeout)
        for _ in range(intentos):
            t0 = time.time()
            s.sendto(pkt, (ip, puerto))
            fin = t0 + timeout
            while True:
                restante = fin - time.time()
                if restante <= 0:
                    break
                s.settimeout(restante)
                try:
                    r, _a = s.recvfrom(1500)
                except socket.timeout:
                    break
                if len(r) >= 12 and r[0] & 0x80:                  # trama completa de IAX
                    dst = struct.unpack(">H", r[2:4])[0] & 0x7FFF
                    if dst != cn:
                        continue
                    ms = int((time.time() - t0) * 1000)
                    if r[10] == 6 and r[11] == 3:                    # PONG → ACK
                        src = struct.unpack(">H", r[0:2])[0] & 0x7FFF
                        ack = struct.pack(">HH", 0x8000 | cn, src) + r[4:8] + \
                            struct.pack("BBBB", 1, (r[8] + 1) & 0xFF, 6, 4)
                        try:
                            s.sendto(ack, (ip, puerto))
                        except OSError:
                            pass
                    return ms
        return None
    finally:
        s.close()


def sin_dato(nodo):
    """Nodos que no están en el DNS de AllStar aunque existan."""
    n = str(nodo)
    if not n.isdigit() or len(n) < 4:
        return True
    if len(n) == 7 and n.startswith("3"):        # EchoLink
        return True
    return 1000 <= int(n) <= 1999                 # privados


def _revisar(nodo):
    try:
        reg = registro(nodo)
    except Exception as e:      # DNS caído: mejor no decir nada que decir algo falso
        log.debug("Presencia de %s: %s", nodo, e)
        return {"estado": ""}
    if not reg:
        return {"estado": "fuera"}
    try:
        ms = poke(reg[0], reg[1])
    except OSError as e:
        log.debug("POKE a %s (%s:%s): %s", nodo, reg[0], reg[1], e)
        ms = None
    if ms is None:
        return {"estado": "registrado", "ip": reg[0], "puerto": reg[1]}
    return {"estado": "responde", "ms": ms}


def estado(nodos):
    """{nodo: {estado, ms?}} para los nodos pedidos (hasta MAX_NODOS)."""
    pedidos = []
    for n in nodos:
        n = str(n).strip()
        if re.match(r"^\d{3,7}$", n) and n not in pedidos:
            pedidos.append(n)
    pedidos = pedidos[:MAX_NODOS]
    ahora = time.time()
    out, faltan = {}, []
    with _lock:
        for n in pedidos:
            if sin_dato(n):
                out[n] = {"estado": ""}
                continue
            c = _cache.get(n)
            if c and ahora - c[0] < TTL:
                out[n] = c[1]
            else:
                faltan.append(n)
    if faltan:
        for n, r in zip(faltan, _pool.map(_revisar, faltan)):
            out[n] = r
            if r.get("estado"):
                with _lock:
                    _cache[n] = (time.time(), r)
        with _lock:
            if len(_cache) > 5000:
                viejo = time.time() - TTL
                for k in [k for k, v in _cache.items() if v[0] < viejo]:
                    del _cache[k]
    return out
