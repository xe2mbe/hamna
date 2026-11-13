"""
HAMNA Web — diagnóstico del nodo («Revisar este nodo»).

Cada revisión devuelve qué encontró en palabras simples y, si algo falta,
cómo arreglarlo (con el comando para copiar cuando aplica). Nada de aquí
cambia el nodo: solo lee y prueba.
"""
import concurrent.futures
import datetime as dt
import json
import logging
import re
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

from . import VERSION, audio, backends, db, health, paths, settings, tts

log = logging.getLogger("hamna.diagnostico")

AZURE_REGIONS = [
    "eastus", "eastus2", "westus", "westus2", "westus3", "centralus", "northcentralus", "southcentralus",
    "westcentralus", "canadacentral", "canadaeast", "brazilsouth", "mexicocentral", "northeurope",
    "westeurope", "uksouth", "ukwest", "francecentral", "germanywestcentral", "switzerlandnorth",
    "switzerlandwest", "norwayeast", "swedencentral", "italynorth", "polandcentral", "spaincentral",
    "eastasia", "southeastasia", "japaneast", "japanwest", "koreacentral", "australiaeast", "centralindia",
    "southafricanorth", "uaenorth", "qatarcentral",
]


def _r(grupo, nombre, nivel, detalle, arreglo="", cmd="", accion=None):
    return {"grupo": grupo, "nombre": nombre, "nivel": nivel, "detalle": detalle,
            "arreglo": arreglo, "cmd": cmd, "accion": accion}


def _kind(cfg):
    k = cfg.get("backend") or "auto"
    return backends.detect() if k == "auto" else k


# ── Nodo ─────────────────────────────────────────────────────────────────────
def _nodo(cfg, kind, sabor):
    out = []
    det = backends.detect()
    if (cfg.get("backend") or "auto") not in ("auto", det) and det != "simulado":
        out.append(_r("Nodo", "Tipo de nodo", "aviso",
                      "En Ajustes está como {} pero en este equipo se detecta {}".format(
                          (cfg.get("backend") or "").upper(), det.upper()),
                      "Si no es a propósito, pon «Detectar automáticamente» en Ajustes → Nodo."))
    if kind == "simulado":
        out.append(_r("Nodo", "Salida al aire", "aviso", "El nodo está en modo SIMULADO: nada sale por el radio",
                      "Elige AllStarLink o IRLP en Ajustes → Nodo."))
        return out
    try:
        good, msg = backends.make(cfg).test()
    except Exception as e:
        good, msg = False, str(e)
    if good:
        out.append(_r("Nodo", "El nodo responde", "ok", msg))
    elif kind == "asl":
        out.append(_r("Nodo", "El nodo responde", "grave", msg,
                      "Revisa que Asterisk esté corriendo y que el número de nodo de Ajustes → Nodo sea el de rpt.conf.",
                      "sudo systemctl status asterisk" if sabor != "hamvoip" else "asterisk -rx 'rpt stats {}'".format(cfg.get("node") or "")))
    else:
        out.append(_r("Nodo", "El nodo responde", "grave", msg,
                      "Revisa la ruta del archivo environment de IRLP en Ajustes → Nodo."))
    return out


def _rpt_stanza(node):
    try:
        txt = Path("/etc/asterisk/rpt.conf").read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None
    m = re.search(r"^\[{}\][^\n]*\n(.*?)(?=^\[|\Z)".format(re.escape(node)), txt, re.M | re.S)
    return m.group(1) if m else ""


def _envivo(cfg, kind, sabor):
    if kind == "irlp":
        return [_r("Nodo", "Audio en vivo", "nd", "Escuchar en vivo todavía no funciona en nodos IRLP")]
    if kind != "asl":
        return []
    from .live import live
    node = str(cfg.get("node") or backends.detect_asl_node())
    st = _rpt_stanza(node)
    restart = "astres.sh" if sabor == "hamvoip" else "sudo systemctl restart asterisk"
    linea = "outstreamcmd = /opt/hamna-web/bin/hamna-live"
    if st is None:
        return [_r("Nodo", "Audio en vivo", "nd", "No pude leer /etc/asterisk/rpt.conf para revisarlo")]
    tiene = re.search(r"^\s*outstreamcmd\s*=", st, re.M) is not None
    s = live.status()
    if tiene and s["recibiendo"]:
        return [_r("Nodo", "Audio en vivo", "ok", "Asterisk está mandando el audio del nodo; el botón 🔊 En vivo está disponible")]
    if tiene and s["configurado"]:
        return [_r("Nodo", "Audio en vivo", "ok", "Configurado (sin audio en los últimos segundos, normal si el nodo está en silencio)")]
    if tiene:
        return [_r("Nodo", "Audio en vivo", "aviso", "rpt.conf ya tiene outstreamcmd, pero Asterisk no ha mandado audio desde que arrancó HAMNA",
                   "Reinicia Asterisk cuando no haya nada al aire (no uses «rpt restart»).", restart)]
    cp = "sudo " if sabor != "hamvoip" else ""
    cmd = ("{cp}cp /etc/asterisk/rpt.conf /etc/asterisk/rpt.conf.bak-$(date +%Y%m%d_%H%M%S)\n"
           "{cp}sed -i '/^\\[{n}\\]/a {l}' /etc/asterisk/rpt.conf\n"
           "grep -n -A2 '^\\[{n}\\]' /etc/asterisk/rpt.conf\n{r}").format(cp=cp, n=node, l=linea, r=restart)
    return [_r("Nodo", "Audio en vivo", "aviso",
               "Falta la línea outstreamcmd en la sección [{}] de rpt.conf: por eso no aparece el botón 🔊 En vivo".format(node),
               "Agrégala y reinicia Asterisk cuando no haya nada al aire (los enlaces se caen al reiniciar).", cmd)]


# ── Audio ────────────────────────────────────────────────────────────────────
def _install_cmd(sabor, kind, pkg):
    if sabor == "hamvoip":
        return ""
    return "sudo apt-get update && sudo apt-get install -y " + pkg


def _audio(cfg, kind, sabor):
    out = []
    t = audio.tools()
    fm = audio.formats()
    lista = ", ".join(e[1:].upper() for e in fm)
    if ".mp3" in fm:
        out.append(_r("Audio", "Formatos que puede leer", "ok", lista + " (" + ", ".join(k for k, v in t.items() if v) + ")"))
    else:
        cmd = _install_cmd(sabor, kind, "mpg123")
        out.append(_r("Audio", "Formatos que puede leer", "aviso",
                      "Este nodo no puede leer MP3 (no tiene ffmpeg ni mpg123). Lee: " + lista,
                      ("Instala mpg123, o sube los audios en WAV. " if cmd else "Sube los audios en WAV. ")
                      + "Desde esta versión, la página convierte los MP3 a WAV en tu navegador al subirlos.", cmd))

    def legible(name):
        return Path(name).suffix.lower() in fm

    # Audios de pausa
    if cfg.get("pause_enabled"):
        for key, nombre in (("pause_alert_file", "Alerta de pausa"), ("pause_announcement_file", "Anuncio de pausa"),
                            ("pause_resume_file", "Continuamos")):
            f = cfg.get(key) or ""
            if not f:
                out.append(_r("Audio", nombre, "aviso", "Las pausas están activadas pero no hay audio de «{}»".format(nombre),
                              "Súbelo en Ajustes → Tiempos y pausas."))
            elif not (paths.sonidos_dir() / f).is_file():
                out.append(_r("Audio", nombre, "grave", "El archivo {} ya no existe".format(f),
                              "Vuelve a subirlo en Ajustes → Tiempos y pausas."))
            elif not legible(f):
                out.append(_r("Audio", nombre, "grave",
                              "{} es {} y este nodo no puede leer ese formato: la pausa fallará al transmitir".format(
                                  f, Path(f).suffix[1:].upper()),
                              "Vuelve a subirlo desde Ajustes → Tiempos y pausas: la página lo convertirá a WAV."))
            else:
                out.append(_r("Audio", nombre, "ok", f))
    else:
        out.append(_r("Audio", "Pausas", "ok", "Las pausas automáticas están apagadas"))

    # Secciones
    faltan, ilegibles = [], []
    for s in db.rows("SELECT nombre, ruta_archivo, texto_tts FROM secciones"):
        name = s.get("ruta_archivo") or ""
        if not name:
            continue
        p = Path(name) if Path(name).is_absolute() else paths.audios_dir() / name
        if not p.is_file():
            if not (s.get("texto_tts") or "").strip():
                faltan.append(s["nombre"])
        elif not legible(p.name):
            ilegibles.append(s["nombre"])
    if faltan:
        out.append(_r("Audio", "Secciones sin archivo", "aviso",
                      "{} secciones apuntan a un audio que ya no existe: {}".format(len(faltan), ", ".join(faltan[:6])
                                                                                   + ("…" if len(faltan) > 6 else "")),
                      "Vuelve a subir su audio en la pestaña Secciones (o restaura un respaldo con audios)."))
    if ilegibles:
        out.append(_r("Audio", "Secciones en formato no soportado", "grave",
                      "{} secciones tienen un audio que este nodo no puede leer: {}".format(
                          len(ilegibles), ", ".join(ilegibles[:6]) + ("…" if len(ilegibles) > 6 else "")),
                      "Vuelve a subir esos audios: la página los convertirá a WAV."))
    if not faltan and not ilegibles:
        n = db.row("SELECT COUNT(*) AS n FROM secciones")["n"]
        out.append(_r("Audio", "Audios de las secciones", "ok", "{} secciones, todas con audio legible".format(n)))
    return out


# ── Voz ──────────────────────────────────────────────────────────────────────
_last_err = {}


def _azure_token(key, region, timeout=8):
    req = urllib.request.Request("https://{}.api.cognitive.microsoft.com/sts/v1.0/issueToken".format(region),
                                 data=b"", method="POST",
                                 headers={"Ocp-Apim-Subscription-Key": key, "User-Agent": "HAMNA-Web/" + VERSION})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception as e:
        _last_err[region] = str(getattr(e, "reason", e))
        return 0


def find_azure_region(key):
    """Prueba la clave en todas las regiones a la vez; devuelve las que la aceptan."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as ex:
        res = dict(zip(AZURE_REGIONS, ex.map(lambda r: _azure_token(key, r), AZURE_REGIONS)))
    return [r for r, c in res.items() if c == 200]


def _voz(cfg):
    eng = cfg.get("tts_engine") or "azure"
    disp = tts.engines()
    if eng != "azure":
        if eng in disp:
            return [_r("Voz", "Motor de voz", "ok", "{} instalado en este nodo".format(eng))]
        return [_r("Voz", "Motor de voz", "grave", "El motor {} no está instalado en este nodo".format(eng),
                   "Elige otro en Ajustes → Voz (disponibles: {}).".format(", ".join(disp) or "ninguno"))]
    key = (cfg.get("azure_key") or "").strip()
    region = (cfg.get("azure_region") or "").strip()
    if not key:
        return [_r("Voz", "Azure", "grave", "Falta la clave de Azure: no se pueden generar secciones de voz",
                   "Pégala en Ajustes → Voz.")]
    code = _azure_token(key, region, 10)
    if code == 0:                          # a veces el primer intento es lento: otra vez con más tiempo
        code = _azure_token(key, region, 25)
    if code == 200:
        return [_r("Voz", "Azure", "ok", "La clave funciona en la región {}".format(region))]
    if code == 0:
        return [_r("Voz", "Azure", "aviso", "No pude conectar con Azure en {} ({}): ¿tiene internet el nodo?".format(
            region, _last_err.get(region, "sin respuesta")),
                   "Revisa la conexión a internet y el DNS del nodo.")]
    if code in (401, 403):
        buenas = find_azure_region(key)
        if buenas:
            return [_r("Voz", "Azure", "grave",
                       "Azure rechaza la clave en la región «{}» (HTTP {}), pero la clave sí funciona en «{}»".format(
                           region, code, buenas[0]),
                       "La clave de Azure solo sirve en la región donde se creó. Cambia la región a «{}».".format(buenas[0]),
                       accion={"tipo": "ajuste", "clave": "azure_region", "valor": buenas[0],
                               "texto": "Usar la región {}".format(buenas[0])})]
        return [_r("Voz", "Azure", "grave",
                   "Azure rechaza la clave (HTTP {}) en todas las regiones: la clave está mal copiada o ya no es válida".format(code),
                   "Copia de nuevo la clave desde el portal de Azure (recurso de Voz → Claves y punto de conexión) sin espacios.")]
    return [_r("Voz", "Azure", "aviso", "Azure respondió HTTP {} en {}".format(code, region))]


# ── Avisos, respaldo, salud, hora, versión ───────────────────────────────────
def _telegram(cfg):
    if not cfg.get("tg_enabled"):
        return [_r("Avisos", "Telegram", "aviso", "Los avisos por Telegram están apagados: no te enterarás si algo falla",
                   "Configúralos en Ajustes → Avisos.")]
    if not cfg.get("tg_token") or not cfg.get("tg_chat"):
        return [_r("Avisos", "Telegram", "grave", "Telegram está activado pero falta el token del bot o el chat",
                   "Complétalo en Ajustes → Avisos.")]
    try:
        from . import notify
        me = notify._call(cfg["tg_token"], "getMe", {}, timeout=10)
        nombre = (me or {}).get("username", "")
        return [_r("Avisos", "Telegram", "ok", "El bot @{} responde".format(nombre) if nombre else "El bot responde")]
    except Exception as e:
        return [_r("Avisos", "Telegram", "grave", "Telegram no aceptó el token del bot: {}".format(e),
                   "Revisa el token en Ajustes → Avisos (lo da @BotFather).")]


def _respaldo(cfg):
    from . import autobackup
    if not cfg.get("ab_enabled"):
        return [_r("Respaldo", "Respaldo automático", "aviso",
                   "No hay respaldo automático: si la tarjeta SD se daña, se pierde todo lo de HAMNA",
                   "Actívalo en Ajustes → Respaldo (a otro nodo o a Google Drive / OneDrive).")]
    if not autobackup.destinations(cfg):
        return [_r("Respaldo", "Respaldo automático", "grave", "Está activado pero no tiene ningún destino que funcione",
                   "Configura otro nodo o la nube en Ajustes → Respaldo.")]
    u = autobackup.load_state().get("ultimo") or {}
    ok_fecha = autobackup.load_state().get("ultimo_ok")
    if u and not u.get("ok"):
        fallas = "; ".join("{}: {}".format(k, v.get("detalle")) for k, v in (u.get("resultados") or {}).items() if not v.get("ok"))
        return [_r("Respaldo", "Respaldo automático", "grave", "El último respaldo ({}) falló: {}".format(
            u.get("fecha"), fallas or u.get("nota") or "?"), "Revisa el destino en Ajustes → Respaldo y usa «Respaldar ahora».")]
    if not ok_fecha:
        return [_r("Respaldo", "Respaldo automático", "aviso", "Todavía no se ha hecho ningún respaldo",
                   "Usa «Respaldar ahora» en Ajustes → Respaldo para comprobar que funciona.")]
    edad = (dt.datetime.now() - dt.datetime.strptime(ok_fecha, "%Y-%m-%d %H:%M:%S")).total_seconds() / 3600
    if edad > 50:
        return [_r("Respaldo", "Respaldo automático", "aviso", "El último respaldo bueno es de hace {:.0f} horas ({})".format(edad, ok_fecha),
                   "Revisa que el nodo esté encendido a la hora del respaldo.")]
    return [_r("Respaldo", "Respaldo automático", "ok", "Último respaldo bueno: {}".format(ok_fecha))]


def _salud():
    st = health.status()
    if not st["checks"]:
        return [_r("Equipo", "Salud del equipo", "nd", "Todavía no se revisa (empieza un minuto después de arrancar)")]
    malas = [c for c in st["checks"] if c["nivel"] in ("aviso", "grave")]
    if not malas:
        return [_r("Equipo", "Salud del equipo", "ok", "Tarjeta SD, alimentación, temperatura, disco y memoria bien")]
    return [_r("Equipo", c["nombre"], c["nivel"], c["detalle"], c["consejo"]) for c in malas]


def _hora():
    exe = shutil.which("timedatectl")
    if not exe:
        return [_r("Equipo", "Hora del nodo", "nd", "No se puede comprobar la sincronización de la hora en este sistema "
                   "(hora actual: {})".format(time.strftime("%Y-%m-%d %H:%M")))]
    try:
        p = subprocess.run([exe, "show", "-p", "NTPSynchronized", "--value"], stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, universal_newlines=True, timeout=10)
        v = p.stdout.strip()
    except Exception:
        v = ""
    if v == "yes":
        return [_r("Equipo", "Hora del nodo", "ok", "Sincronizada por internet ({})".format(time.strftime("%Y-%m-%d %H:%M")))]
    if v == "no":
        return [_r("Equipo", "Hora del nodo", "aviso",
                   "La hora no está sincronizada por internet ({}): los eventos podrían salir a destiempo".format(time.strftime("%Y-%m-%d %H:%M")),
                   "Activa la sincronización de hora.", "sudo timedatectl set-ntp true")]
    return [_r("Equipo", "Hora del nodo", "nd", "No se pudo saber si la hora está sincronizada")]


def _version(sabor):
    try:
        from . import updates
        d = updates.check()
    except Exception as e:
        return [_r("Equipo", "Versión de HAMNA", "nd", "No pude consultar GitHub: {}".format(e))]
    if d.get("hay_actualizacion"):
        return [_r("Equipo", "Versión de HAMNA", "aviso", "Instalada v{}, hay una nueva: v{}".format(VERSION, d.get("ultima")),
                   "Actualiza cuando no haya nada al aire.",
                   "/opt/hamna-web/update.sh" if sabor == "hamvoip" else "sudo /opt/hamna-web/update.sh")]
    return [_r("Equipo", "Versión de HAMNA", "ok", "v{} (al día)".format(VERSION))]


# ── Todo ─────────────────────────────────────────────────────────────────────
def run():
    cfg = settings.load()
    kind = _kind(cfg)
    sabor = backends.detect_flavor()
    t0 = time.time()
    out = []
    for fn in (lambda: _nodo(cfg, kind, sabor), lambda: _envivo(cfg, kind, sabor), lambda: _audio(cfg, kind, sabor),
               lambda: _voz(cfg), lambda: _telegram(cfg), lambda: _respaldo(cfg), _salud, _hora, lambda: _version(sabor)):
        try:
            out.extend(fn())
        except Exception as e:
            log.exception("Error en el diagnóstico")
            out.append(_r("Diagnóstico", "Revisión interna", "aviso", "Una revisión falló: {}".format(e)))
    peor = max((c["nivel"] for c in out), key=lambda n: {"grave": 2, "aviso": 1}.get(n, 0), default="ok")
    return {"revisiones": out, "peor": peor, "segundos": round(time.time() - t0, 1),
            "fecha": time.strftime("%Y-%m-%d %H:%M:%S"), "tipo": kind, "sabor": sabor}
