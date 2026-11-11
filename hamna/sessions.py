"""
HAMNA Web — sesiones: nodos conectados en este momento.

ASL   una sola llamada a  asterisk -rx "rpt xnode <nodo>"  da los enlaces
      directos (IP, dirección, tiempo), la red completa y quién transmite.
      Funciona igual en ASL3, ASL2 y HamVOIP.
IRLP  el archivo $LOCAL/active dice a qué nodo o reflector está conectado.

Los indicativos y ciudades salen del directorio de AllStar (astdb.txt). No se
carga entero (son ~40 000 líneas): solo se buscan los nodos que aparecen, y
lo encontrado se guarda hasta que el archivo cambie.
"""
import logging
import os
import re
import subprocess
import threading
import time

from . import backends, links

log = logging.getLogger("hamna.sesiones")

ASTDB_PATHS = ("/var/lib/asterisk/astdb.txt", "/var/log/asterisk/astdb.txt",
               "/tmp/astdb.txt")
MODOS = {"T": "transceptor", "R": "monitor", "C": "conectando", "M": "monitor"}

_dir_lock = threading.Lock()
_dir = {"path": None, "mtime": None, "info": {}, "missing": set()}
_cache = {"key": None, "t": 0, "data": None}
_cache_lock = threading.Lock()
CACHE_SECS = 2.0          # varias pestañas abiertas comparten la misma consulta


def _astdb_path():
    for p in ASTDB_PATHS:
        if os.path.isfile(p):
            return p
    return None


def lookup(nodes):
    """{nodo: {indicativo, descripcion, ubicacion}} solo para los nodos pedidos."""
    nodes = {str(n) for n in nodes if str(n).isdigit()}
    p = _astdb_path()
    if not p or not nodes:
        return {}
    with _dir_lock:
        try:
            mt = os.stat(p).st_mtime
        except OSError:
            return {}
        if _dir["path"] != p or _dir["mtime"] != mt:
            _dir.update(path=p, mtime=mt, info={}, missing=set())
        info, missing = _dir["info"], _dir["missing"]
        want = nodes - set(info) - missing
        if want:
            found = set()
            try:
                with open(p, encoding="utf-8", errors="replace") as f:
                    for line in f:
                        n, _, rest = line.partition("|")
                        if n in want:
                            parts = (rest.rstrip("\n").split("|") + ["", "", ""])[:3]
                            info[n] = {"indicativo": parts[0].strip(),
                                       "descripcion": parts[1].strip(),
                                       "ubicacion": parts[2].strip()}
                            found.add(n)
                            if len(found) == len(want):
                                break
            except OSError as e:
                log.warning("No pude leer %s: %s", p, e)
            missing.update(want - found)
        return {n: info[n] for n in nodes if n in info}


def local_nodes():
    """Nodos ASL definidos en rpt.conf (un mismo Asterisk puede tener varios)."""
    try:
        with open("/etc/asterisk/rpt.conf", encoding="utf-8", errors="ignore") as f:
            txt = f.read()
    except OSError:
        return []
    return re.findall(r"^\[(\d{3,7})\]", txt, re.M)


def _rx(cmd, timeout=8):
    r = subprocess.run([backends.asterisk_bin(), "-rx", cmd], stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, timeout=timeout)
    return r.stdout.decode(errors="ignore")


LINK_RX = re.compile(r"^\s*(\S+)\s+(\d{1,3}(?:\.\d{1,3}){3}|\S+)\s+(\d+)\s+(IN|OUT)\s+(\S+)\s+([A-Z]+)\s*$")


def parse_xnode(txt):
    """Interpreta la salida de 'rpt xnode'. Devuelve enlaces, red y variables."""
    enlaces, red, vars_ = [], [], {}
    for raw in re.split(r"[~\n]", txt):
        line = raw.strip()
        if not line:
            continue
        m = LINK_RX.match(line)
        if m:
            enlaces.append({"nodo": m.group(1), "ip": m.group(2), "reconexiones": int(m.group(3)),
                            "direccion": m.group(4), "tiempo": m.group(5), "estado": m.group(6)})
            continue
        if "=" in line and re.match(r"^[A-Za-z_]+=", line):
            k, _, v = line.partition("=")
            vars_[k.strip()] = v.strip()
            continue
        if re.match(r"^[TRCM]\w+(,\s*[TRCM]\w+)*,?$", line):
            red.extend(x.strip() for x in line.split(",") if x.strip())
    # Modo y si transmite (RPT_ALINKS=4,61734TU,59624TK,...)
    alinks = {}
    for item in (vars_.get("RPT_ALINKS") or "").split(",")[1:]:
        m = re.match(r"^(\w+?)([TRCM])([KU])$", item.strip())
        if m:
            alinks[m.group(1)] = (m.group(2), m.group(3) == "K")
    for e in enlaces:
        modo, rx = alinks.get(e["nodo"], ("", False))
        e["modo"] = MODOS.get(modo, "")
        e["transmitiendo"] = rx
    red_nodos = []
    seen = set()
    for x in red:
        n = x[1:]
        if n not in seen:
            seen.add(n)
            red_nodos.append({"nodo": n, "modo": MODOS.get(x[0], "")})
    return enlaces, red_nodos, vars_


def _secs(t):
    """'00:12:58' o '00:12:58:317' (d:h:m:s o h:m:s[:ms]) → segundos."""
    parts = [int(p) for p in re.findall(r"\d+", t)]
    if len(parts) == 4:              # ASL3 lstats: hh:mm:ss:ms
        h, m, s, _ = parts
        return h * 3600 + m * 60 + s
    s = 0
    for p in parts[-3:]:
        s = s * 60 + p
    return s


def asl_status(node):
    with _cache_lock:
        if _cache["key"] == node and time.time() - _cache["t"] < CACHE_SECS:
            return _cache["data"]
    out = _rx("rpt xnode {}".format(node))
    if re.search(r"(?i)no such|not found|unable to connect|usage", out) and "RPT_" not in out:
        raise RuntimeError("Asterisk no respondió para el nodo {}: {}".format(node, out.strip()[:120]))
    enlaces, red, v = parse_xnode(out)
    info = lookup([e["nodo"] for e in enlaces] + [r["nodo"] for r in red] + [node])
    for e in enlaces:
        e["segundos"] = _secs(e["tiempo"])
        e.update(info.get(e["nodo"], {}))
    for r in red:
        r.update(info.get(r["nodo"], {}))
    directos = {e["nodo"] for e in enlaces}
    data = {
        "sistema": "asl", "nodo": node, "local": info.get(node, {}),
        "nodos_locales": local_nodes(),
        "rx": v.get("RPT_RXKEYED") == "1", "tx": v.get("RPT_TXKEYED") == "1",
        "enlaces": sorted(enlaces, key=lambda e: e["nodo"]),
        "red": [r for r in red if r["nodo"] not in directos and r["nodo"] != node],
        "total_red": len(red),
    }
    with _cache_lock:
        _cache.update(key=node, t=time.time(), data=data)
    return data


def _irlp_local(env):
    """$LOCAL de IRLP. El archivo de entorno lo define con otras variables
    (export LOCAL=${IRLPDIR}/local), así que se resuelven las asignaciones
    simples del propio archivo; si no se puede, /home/irlp/local."""
    default = "/home/irlp/local"
    try:
        with open(env, encoding="utf-8", errors="ignore") as f:
            txt = f.read()
    except OSError:
        return default
    vals = {}
    for m in re.finditer(r"^\s*(?:export\s+)?([A-Z_][A-Z0-9_]*)=([^\s#;]*)", txt, re.M):
        v = m.group(2).strip("\"'")
        v = re.sub(r"\$\{?([A-Z_][A-Z0-9_]*)\}?", lambda x: vals.get(x.group(1), os.environ.get(x.group(1), "")), v)
        vals[m.group(1)] = v
    local = vals.get("LOCAL", "")
    return local if local.startswith("/") and os.path.isdir(local) else default


def _irlp_lines(env):
    """COS y PTT con cosstate/pttstate de IRLP (sirven con puerto paralelo o
    GPIO; salen con 1 si la línea está activa). None = no se pudo leer."""
    script = ('[ -f "$1" ] && . "$1" >/dev/null 2>&1; '
              '"$BIN/cosstate" >/dev/null 2>&1; echo "c=$?"; '
              '"$BIN/pttstate" >/dev/null 2>&1; echo "p=$?"')
    try:
        r = subprocess.run(["bash", "-c", script, "irlp", env], stdout=subprocess.PIPE,
                           stderr=subprocess.DEVNULL, timeout=5)
        out = r.stdout.decode(errors="ignore")
    except Exception:
        return None, None
    c = re.search(r"c=(\d+)", out)
    p = re.search(r"p=(\d+)", out)
    val = lambda m: None if not m or m.group(1) not in ("0", "1") else m.group(1) == "1"
    return val(c), val(p)


def irlp_status(cfg):
    env = cfg.get("irlp_env") or "/home/irlp/custom/environment"
    local = _irlp_local(env)
    activo = ""
    try:
        with open(os.path.join(local, "active"), encoding="utf-8", errors="ignore") as f:
            activo = f.read().strip()
    except OSError:
        pass
    detalle = ""
    if activo:
        from . import irlpnet
        t = irlpnet.target(local)
        if t and t["ip"]:
            detalle = "{}:{} · {}".format(t["ip"], t["port"], t["codec"])
    cos, ptt = _irlp_lines(env)
    return {"sistema": "irlp", "nodo": cfg.get("node") or "", "activo": activo, "detalle": detalle,
            "cos": cos, "ptt": ptt, "rx": bool(cos), "tx": bool(ptt),
            "enlaces": [{"nodo": activo, "modo": "transceptor"}] if activo else [], "red": []}


def status(cfg, node=None):
    kind = cfg.get("backend") or "auto"
    if kind == "auto":
        kind = backends.detect()
    if kind == "irlp":
        return irlp_status(cfg)
    if kind != "asl":
        return {"sistema": kind, "enlaces": [], "red": [], "nodo": cfg.get("node") or ""}
    node = str(node or cfg.get("node") or backends.detect_asl_node())
    if not re.match(r"^\d{3,7}$", node):
        raise ValueError("Número de nodo inválido")
    return asl_status(node)


def action(cfg, accion, destino="", modo="transceptor", node=None):
    """Conectar o desconectar desde la página. Reutiliza las reglas de links."""
    kind = cfg.get("backend") or "auto"
    if kind == "auto":
        kind = backends.detect()
    sistema = "irlp" if kind == "irlp" else "asl"
    a = links.validate({"sistema": sistema, "accion": accion, "destino": destino,
                        "modo": modo, "momento": "antes", "minutos": 0})
    with _cache_lock:
        _cache["key"] = None
    if sistema == "irlp":
        return links._irlp(a)
    node = str(node or cfg.get("node") or backends.detect_asl_node())
    if node not in local_nodes():
        raise ValueError("El nodo {} no está en rpt.conf".format(node))
    return links._asl(a, node)
