"""
HAMNA Web — zonas horarias de los eventos programados.

Un evento puede programarse "a las 20:00 de San Antonio" (America/Chicago).
Para cada fecha se convierte esa hora a la hora del nodo; así, cuando esa
zona cambia de horario (verano/invierno), el evento se recorre solo.

Usa zoneinfo (Python 3.9+). En Python más viejo (HamVOIP trae 3.5) lee
directamente los archivos de /usr/share/zoneinfo (formato TZif).
"""
import datetime as dt
import os
import struct
import time

ZONEINFO_DIR = "/usr/share/zoneinfo"

# Zonas sugeridas en la página (cualquier otra válida también se acepta)
ZONAS = [
    ("", "Hora del nodo (sin conversión)"),
    ("America/Mexico_City", "México centro (CDMX, Guadalajara, Monterrey) · sin cambio de horario"),
    ("America/Cancun", "Quintana Roo · sin cambio de horario"),
    ("America/Hermosillo", "Sonora · sin cambio de horario"),
    ("America/Mazatlan", "Sinaloa, Nayarit, BCS · sin cambio de horario"),
    ("America/Chihuahua", "Chihuahua · sin cambio de horario"),
    ("America/Ciudad_Juarez", "Ciudad Juárez · con horario de verano (como EE. UU.)"),
    ("America/Matamoros", "Frontera noreste (Matamoros, Reynosa, N. Laredo) · con horario de verano"),
    ("America/Tijuana", "Tijuana / Mexicali · con horario de verano"),
    ("America/Chicago", "EE. UU. centro (Texas, Chicago) · con horario de verano"),
    ("America/Denver", "EE. UU. montaña (Denver, El Paso) · con horario de verano"),
    ("America/Phoenix", "Arizona · sin cambio de horario"),
    ("America/Los_Angeles", "EE. UU. pacífico (California) · con horario de verano"),
    ("America/New_York", "EE. UU. este (Nueva York, Miami) · con horario de verano"),
    ("America/Guatemala", "Centroamérica (Guatemala, El Salvador, Honduras)"),
    ("America/Bogota", "Colombia, Perú, Ecuador"),
    ("America/Caracas", "Venezuela"),
    ("America/Santiago", "Chile · con horario de verano"),
    ("America/Argentina/Buenos_Aires", "Argentina"),
    ("Europe/Madrid", "España peninsular · con horario de verano"),
    ("Atlantic/Canary", "Islas Canarias · con horario de verano"),
    ("UTC", "UTC"),
]

try:                                    # Python 3.9+
    from zoneinfo import ZoneInfo
except ImportError:                     # HamVOIP (3.5)
    ZoneInfo = None

_cache = {}


def valid(zone):
    if not zone:
        return True
    if ".." in zone or zone.startswith("/"):
        return False
    return os.path.isfile(os.path.join(ZONEINFO_DIR, zone))


def node_zone():
    """Nombre de la zona del nodo (America/Mexico_City, America/Belize...).
    Manda /etc/localtime (lo que usa el reloj); /etc/timezone puede quedar
    viejo (en el hub decía Europe/London de la imagen original)."""
    real = os.path.realpath("/etc/localtime")
    if "zoneinfo/" in real:
        return real.split("zoneinfo/")[-1]
    try:
        with open("/etc/timezone") as f:
            return f.read().strip()
    except OSError:
        return ""


# ── Lector TZif para Python sin zoneinfo ─────────────────────────────────────
def _tzif(zone):
    """(transiciones, índices, tipos[(offset, dst)]) del archivo de la zona."""
    if zone in _cache:
        return _cache[zone]
    with open(os.path.join(ZONEINFO_DIR, zone), "rb") as f:
        data = f.read()
    if data[:4] != b"TZif":
        raise ValueError("Zona inválida: " + zone)
    isutc, isstd, leap, timecnt, typecnt, charcnt = struct.unpack(">6l", data[20:44])
    p = 44
    trans = list(struct.unpack(">%dl" % timecnt, data[p:p + 4 * timecnt])); p += 4 * timecnt
    idx = list(data[p:p + timecnt]); p += timecnt
    types = []
    for i in range(typecnt):
        off, dst, _ = struct.unpack(">lBB", data[p:p + 6]); p += 6
        types.append((off, dst))
    _cache[zone] = (trans, idx, types)
    return _cache[zone]


def _offset_at(zone, ts):
    """Diferencia con UTC (segundos) de la zona en el instante ts."""
    trans, idx, types = _tzif(zone)
    if not trans or ts < trans[0]:
        std = [t for t in types if not t[1]]
        return (std or types)[0][0]
    lo, hi = 0, len(trans) - 1
    while lo < hi:                          # última transición <= ts
        mid = (lo + hi + 1) // 2
        if trans[mid] <= ts:
            lo = mid
        else:
            hi = mid - 1
    return types[idx[lo]][0]


def _local_to_ts_tzif(zone, naive):
    base = (naive - dt.datetime(1970, 1, 1)).total_seconds()
    for off in sorted({t[0] for t in _tzif(zone)[2]}, reverse=True):
        ts = base - off
        if _offset_at(zone, ts) == off:
            return ts
    # Hora inexistente (salto de primavera): usar el offset de una hora después
    ts = base - _offset_at(zone, base + 3600 - _offset_at(zone, base))
    return ts


# ── Conversión ───────────────────────────────────────────────────────────────
def to_node(naive, zone):
    """Hora `naive` de la zona `zone` → hora local del nodo (naive)."""
    if not zone or zone == node_zone():
        return naive
    ts = None
    if ZoneInfo is not None:
        try:
            ts = naive.replace(tzinfo=ZoneInfo(zone)).timestamp()
        except Exception:
            ts = None                       # sin datos de zona en Python: usar el archivo del sistema
    if ts is None:
        ts = _local_to_ts_tzif(zone, naive)
    return dt.datetime.fromtimestamp(ts).replace(microsecond=0)


def node_to_zone(naive_local, zone):
    """Hora local del nodo → hora de la zona (para saber qué fecha es allá)."""
    if not zone or zone == node_zone():
        return naive_local
    ts = time.mktime(naive_local.timetuple())
    if ZoneInfo is not None:
        try:
            return dt.datetime.fromtimestamp(ts, ZoneInfo(zone)).replace(tzinfo=None)
        except Exception:
            pass
    return dt.datetime(1970, 1, 1) + dt.timedelta(seconds=ts + _offset_at(zone, ts))


def label(zone):
    for z, l in ZONAS:
        if z == zone:
            return l
    return zone
