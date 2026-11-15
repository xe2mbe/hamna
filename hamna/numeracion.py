"""
HAMNA Web — numeración automática de emisiones.

Los números salen del calendario, no de un contador: una emisión de prueba,
un reinicio o restaurar un respaldo no los mueven.

  emision_anio  cuántas fechas de la programación del evento van en el año,
                contando la de la emisión (el domingo 46 del año es la #46).
                Se reinicia cada 1 de enero.
  emision       número global: el usuario indica «la emisión del día R es la
                #N» y desde ahí se suma 1 por cada fecha programada.

La fecha de la emisión es la de hoy si hoy toca y todavía no termina (hora +
duración + 30 min), o la próxima que toque (así una prueba del sábado ya dice
el número del domingo).
"""
import datetime as dt

from . import db, tz

MAX_DIAS = 366 * 100


def _pats(eid):
    out = []
    for r in db.rows("SELECT fecha, hora, recurrencia, zona FROM programacion WHERE evento_id=? ORDER BY id", (eid,)):
        try:
            f = dt.datetime.strptime(r["fecha"] or "", "%Y-%m-%d").date()
        except ValueError:
            continue
        out.append(((r["recurrencia"] or "ninguna").lower(), f, r.get("zona") or "", r.get("hora") or ""))
    return out


def _toca(pats, d):
    """¿Hay emisión ese día? Las repetidas cuentan todo el año aunque la
    programación se haya creado después (el domingo 46 es el 46 aunque HAMNA
    empezara a transmitirlo en noviembre)."""
    for rec, f, _z, _h in pats:
        if rec == "ninguna":
            if d == f:
                return True
        elif rec == "diaria":
            return True
        elif rec == "semanal":
            if d.weekday() == f.weekday():
                return True
        elif rec == "lun-vie":
            if d.weekday() < 5:
                return True
    return False


def _contar(pats, a, b):
    """Fechas con emisión en (a, b]."""
    n, d = 0, a + dt.timedelta(days=1)
    if (b - a).days > MAX_DIAS:
        raise ValueError("La fecha de referencia está demasiado lejos")
    while d <= b:
        if _toca(pats, d):
            n += 1
        d += dt.timedelta(days=1)
    return n


def _fecha(s):
    try:
        return dt.datetime.strptime(str(s or ""), "%Y-%m-%d").date()
    except ValueError:
        return None


def _ya_termino(ev, pats, hoy, ahora):
    """¿Ya pasó la emisión de hoy? Cuenta hasta su hora + duración + 30 min."""
    horas = []
    for p in pats:
        if _toca([p], hoy):
            try:
                h, m = map(int, p[3][:5].split(":"))
                horas.append(dt.datetime.combine(hoy, dt.time(h, m)))
            except ValueError:
                pass
    if not horas:
        return False
    r = db.row("""SELECT COALESCE(SUM(s.duracion),0) AS d FROM evento_secciones es
                  JOIN secciones s ON s.id=es.seccion_id WHERE es.evento_id=?""", (ev["id"],))
    fin = max(horas) + dt.timedelta(seconds=float((r or {}).get("d") or 0)) + dt.timedelta(minutes=30)
    return ahora > fin


def calcular(ev, hoy=None, ref_fecha=None, ref_global=None, ahora=None):
    """Números de la próxima emisión (o la de hoy). None si el evento no
    tiene programación. ref_* reemplazan a los guardados (vista previa)."""
    if not ev or not ev.get("id"):
        return None
    pats = _pats(ev["id"])
    if not pats:
        return None
    if hoy is None:
        ahora = ahora or tz.node_to_zone(dt.datetime.now(), pats[0][2])
        hoy = ahora.date()
        if _toca(pats, hoy) and _ya_termino(ev, pats, hoy, ahora):
            hoy += dt.timedelta(days=1)         # la de hoy ya salió: la que sigue
    d = hoy
    for _ in range(400):
        if _toca(pats, d):
            break
        d += dt.timedelta(days=1)
    else:
        return None
    out = {"fecha": d.isoformat(), "anio": d.year,
           "emision_anio": _contar(pats, dt.date(d.year, 1, 1) - dt.timedelta(days=1), d),
           "emision": None}
    rf = _fecha(ref_fecha if ref_fecha is not None else ev.get("num_ref_fecha"))
    rn = ref_global if ref_global is not None else ev.get("num_ref_global")
    if rf and rn is not None:
        rn = int(rn)
        out["emision"] = rn + _contar(pats, rf, d) if d >= rf else rn - _contar(pats, d, rf)
    return out


def aplicar(ev):
    """Copia del evento con los números automáticos puestos: «numero» pasa a
    ser la emisión global y se agregan emision_anio y anio."""
    ev = dict(ev or {})
    if not ev.get("num_auto"):
        return ev
    try:
        n = calcular(ev)
    except Exception:
        n = None
    if n:
        if n["emision"] is not None:
            ev["numero"] = n["emision"]
        ev["emision_anio"] = n["emision_anio"]
        ev["anio"] = n["anio"]
        ev["num"] = n
    return ev


def etiqueta(ev):
    """«#92 · 2027 #46» para títulos y el historial ('' si no aplica)."""
    partes = []
    if ev.get("numero") not in (None, ""):
        partes.append("#{}".format(ev["numero"]))
    if ev.get("emision_anio"):
        partes.append("{} #{}".format(ev.get("anio"), ev["emision_anio"]))
    return " · ".join(partes)
