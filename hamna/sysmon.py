"""
HAMNA Web — datos del equipo (CPU, memoria, disco, temperatura, red).

Todo sale de leer archivos de /proc y /sys que Linux ya tiene en memoria:
menos de un milisegundo y sin correr programas. Las velocidades (CPU, red)
se calculan con la diferencia contra la lectura anterior; si dos páginas
piden datos casi al mismo tiempo, comparten la misma lectura.
"""
import os
import shutil
import threading
import time

from . import paths

_lock = threading.Lock()
_prev = {"t": 0.0, "cpu": None, "net": None}
_last = {"t": 0.0, "data": None}
MIN_SECS = 0.8


def _read(path):
    try:
        with open(path) as f:
            return f.read()
    except (OSError, ValueError):
        return None


def _cpu_times():
    txt = _read("/proc/stat")
    if not txt:
        return None
    v = [int(x) for x in txt.split("\n", 1)[0].split()[1:]]
    idle = v[3] + (v[4] if len(v) > 4 else 0)          # idle + iowait
    return sum(v[:8]), idle


def _net_bytes():
    txt = _read("/proc/net/dev")
    if not txt:
        return None
    rx = tx = 0
    for line in txt.splitlines()[2:]:
        name, _, rest = line.partition(":")
        name = name.strip()
        if not rest or name == "lo":
            continue
        f = rest.split()
        rx += int(f[0])
        tx += int(f[8])
    return rx, tx


def _mem():
    txt = _read("/proc/meminfo")
    if not txt:
        return None
    m = {}
    for line in txt.splitlines():
        k, _, v = line.partition(":")
        parts = v.split()
        if parts:
            m[k] = int(parts[0]) * 1024
    total = m.get("MemTotal", 0)
    avail = m.get("MemAvailable", m.get("MemFree", 0) + m.get("Cached", 0) + m.get("Buffers", 0))
    return {"total": total, "usada": max(0, total - avail)}


def _temp():
    for z in range(4):
        txt = _read("/sys/class/thermal/thermal_zone{}/temp".format(z))
        if txt and txt.strip().lstrip("-").isdigit():
            v = int(txt.strip())
            return round(v / 1000.0, 1) if v > 1000 else float(v)
    return None


def snapshot():
    now = time.time()
    with _lock:
        if _last["data"] is not None and now - _last["t"] < MIN_SECS:
            return _last["data"]
        cpu, net = _cpu_times(), _net_bytes()
        d = {"cpu": None, "rx_bps": None, "tx_bps": None}
        dt = now - _prev["t"]
        if cpu and _prev["cpu"]:
            tot, idle = cpu[0] - _prev["cpu"][0], cpu[1] - _prev["cpu"][1]
            if tot > 0:
                d["cpu"] = round(100.0 * (1 - idle / float(tot)), 1)
        if net and _prev["net"] and dt > 0:
            d["rx_bps"] = max(0, int((net[0] - _prev["net"][0]) / dt))
            d["tx_bps"] = max(0, int((net[1] - _prev["net"][1]) / dt))
        _prev.update(t=now, cpu=cpu, net=net)
        d["mem"] = _mem()
        try:
            du = shutil.disk_usage(str(paths.data_dir()))
            d["disco"] = {"total": du.total, "usada": du.used}
        except OSError:
            d["disco"] = None
        d["temp"] = _temp()
        try:
            d["carga"] = round(os.getloadavg()[0], 2)
        except (OSError, AttributeError):
            d["carga"] = None
        up = _read("/proc/uptime")
        d["encendido_s"] = int(float(up.split()[0])) if up else None
        d["nucleos"] = os.cpu_count() or 1
        _last.update(t=now, data=d)
        return d
