"""
Variables de hora que se ajustan solas al horario de otra zona:

  {hora 20:00 America/Chicago | palabras}   las 20:00 de Chicago en hora de aquí, hoy
  {hora_evento Red de los martes | 24h}     la hora de la próxima salida de un evento (solo HAMNA)

Formatos: palabras («9 de la noche», el de siempre), 24h («21:00») y 12h («9 pm»).
Se calculan al generar la voz: cuando Chicago cambia de horario, el texto
dice la hora nueva sin tocarlo. Un token que no se puede calcular no se lee
(queda vacío) y la página lo marca con ⚠.
"""
import datetime as dt
import re

from . import tz

FORMATOS = ("palabras", "24h", "12h")
RX = re.compile(r"\{hora(_evento)?\s+([^{}|]+?)\s*(?:\|\s*(palabras|24h|12h)\s*)?\}")
HHMM = re.compile(r"^([01]?\d|2[0-3]):([0-5]\d)$")


def tiene(texto):
    return bool(RX.search(texto or ""))


def decir(t, fmt="palabras"):
    h, m = t.hour, t.minute
    if fmt == "24h":
        return "{:02d}:{:02d}".format(h, m)
    h12 = h % 12 or 12
    if fmt == "12h":
        return "{}{} {}".format(h12, ":{:02d}".format(m) if m else "", "am" if h < 12 else "pm")
    if h == 0 or h >= 19:
        parte = "de la noche"
    elif h < 6:
        parte = "de la madrugada"
    elif h < 12:
        parte = "de la mañana"
    elif h == 12:
        parte = "del día"
    else:
        parte = "de la tarde"
    mm = "" if not m else " y cuarto" if m == 15 else " y media" if m == 30 else " y {}".format(m)
    return "{}{} {}".format(h12, mm, parte)


def _de_zona(arg, now):
    """«20:00 America/Chicago» → fecha-hora del nodo de hoy (en el día de esa zona)."""
    partes = arg.split(None, 1)
    if len(partes) != 2 or not HHMM.match(partes[0]):
        raise ValueError("Escribe la hora (HH:MM) y la zona, p. ej. 20:00 America/Chicago")
    zona = partes[1].strip()
    if not zona or not tz.valid(zona):
        raise ValueError("Zona horaria desconocida: {}".format(zona))
    h, m = map(int, partes[0].split(":"))
    dia = tz.node_to_zone(now, zona).date()
    return tz.to_node(dt.datetime.combine(dia, dt.time(h, m)), zona), "{} {}".format(partes[0], tz.short(zona))


def _de_evento(nombre, now):
    try:
        from . import db
        from .engine import Engine
    except ImportError:
        raise ValueError("Solo en HAMNA: aquí no hay eventos")
    nombre = re.sub(r"\s+", " ", nombre).strip().lower()
    ev = [e for e in db.get_eventos() if re.sub(r"\s+", " ", e["nombre"]).strip().lower() == nombre]
    if not ev:
        raise ValueError("No hay un evento llamado «{}»".format(nombre))
    occ = [Engine.next_run(r, now) for r in db.get_programacion(solo_activos=True) if r["evento_id"] == ev[0]["id"]]
    occ = [o for o in occ if o]
    if not occ:
        raise ValueError("«{}» no tiene programación activa".format(ev[0]["nombre"]))
    t = min(occ)
    return t, "{} · {}".format(ev[0]["nombre"], t.strftime("%d/%m %H:%M"))


def _uno(m, now):
    evento, arg, fmt = m.group(1), m.group(2).strip(), m.group(3) or "palabras"
    t, detalle = (_de_evento if evento else _de_zona)(arg, now)
    return decir(t, fmt), t, detalle


def resolver(texto, cfg=None, now=None):
    """Cambia cada token por la hora que corresponde hoy; los que fallan quedan vacíos."""
    if not texto or "{hora" not in texto:
        return texto
    now = (now or dt.datetime.now()).replace(second=0, microsecond=0)

    def cambia(m):
        try:
            return _uno(m, now)[0]
        except Exception:
            return ""
    return RX.sub(cambia, texto)


def revisar(texto, now=None):
    """Para la página: qué dice cada token hoy, o por qué no se puede calcular."""
    now = (now or dt.datetime.now()).replace(second=0, microsecond=0)
    out = []
    for m in RX.finditer(texto or ""):
        try:
            dice, t, detalle = _uno(m, now)
            out.append({"token": m.group(0), "ok": True, "dice": dice, "detalle": detalle,
                        "aqui": t.strftime("%Y-%m-%d %H:%M")})
        except Exception as e:
            out.append({"token": m.group(0), "ok": False, "error": str(e)})
    return out
