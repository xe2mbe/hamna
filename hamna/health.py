"""
HAMNA Web — salud del equipo del nodo y avisos por Telegram.

Cada minuto revisa, sin necesitar permisos de root:
  • Tarjeta SD / almacenamiento: errores del kernel (dmesg: mmc, I/O error,
    "blocked for more than", EXT4-fs error), errores de ext4 en
    /sys/fs/ext4/*/errors_count y si el sistema de archivos quedó en solo lectura.
  • Escritura: cada 10 min escribe y sincroniza un archivo pequeño y mide
    cuánto tarda. Una SD que se está muriendo tarda segundos o no responde
    (es lo que le pasó al stn8798: escrituras colgadas más de 2 minutos).
  • Alimentación: alarma de bajo voltaje de la Raspberry (hwmon rpi_volt) y
    avisos de "Under-voltage" en dmesg.
  • Temperatura, espacio en disco y memoria.

Avisa por Telegram cuando algo empeora, recuerda cada 12 h si sigue mal y
avisa cuando se recupera.
"""
import glob
import json
import logging
import os
import re
import shutil
import subprocess
import threading
import time

from . import notify, paths, sysmon

log = logging.getLogger("hamna.salud")

INTERVAL = 60
WRITE_EVERY = 600
REMIND = 12 * 3600
ORDER = ["sd", "escritura", "voltaje", "temperatura", "disco", "memoria"]
NOMBRE = {"sd": "Tarjeta SD", "escritura": "Escritura en la SD", "voltaje": "Alimentación",
          "temperatura": "Temperatura", "disco": "Espacio en disco", "memoria": "Memoria"}
NIVEL = {"ok": 0, "nd": 0, "aviso": 1, "grave": 2}
ICONO = {"ok": "✅", "nd": "➖", "aviso": "⚠️", "grave": "❌"}

SD_ERR = re.compile(r"(mmc\d+:.*(error|timeout|timed out)|I/O error|blocked for more than \d+ seconds"
                    r"|EXT4-fs error|EXT4-fs.*read-only|Buffer I/O error|end_request: I/O error"
                    r"|mmcblk\d+: error)", re.I)
UNCLEAN = re.compile(r"(FAT-fs|EXT4-fs).*(not properly unmounted|recovery complete|orphan)", re.I)
UNDERV = re.compile(r"under-?voltage detected", re.I)
TS = re.compile(r"^\[\s*(\d+\.\d+)\]")

CONSEJO = {
    "sd": "La tarjeta SD puede estar fallando. Descarga un respaldo cuanto antes (Ajustes → Respaldo) y cámbiala por una nueva, de preferencia «High Endurance». Revisa también la fuente de alimentación.",
    "escritura": "La tarjeta SD tarda mucho en guardar o no responde: es la señal típica de una SD que se está muriendo. Saca un respaldo ya y prepara una SD nueva.",
    "voltaje": "La fuente no da suficiente voltaje. Usa una fuente de 5.1 V y al menos 2.5 A (Pi 3) con un cable corto y grueso; el bajo voltaje también daña las tarjetas SD.",
    "temperatura": "La Raspberry está muy caliente y puede frenarse. Mejora la ventilación, agrega disipador o ventilador y revisa que no esté encerrada.",
    "disco": "Queda poco espacio. Borra audios que ya no uses, compacta las secciones (Ajustes → Nivel de audio) o revisa la bitácora del sistema.",
    "memoria": "Queda muy poca memoria libre. Revisa qué programas están corriendo en el nodo.",
}

_lock = threading.Lock()
_state = {"checks": {}, "actualizado": None}
_alerted = {}          # id -> (nivel, cuándo se avisó)
_dmesg = {"ok": None, "sd": [], "unclean": [], "underv": 0, "last": ""}
_write = {"t": 0.0, "nivel": "nd", "detalle": "Aún no se mide", "segundos": None}
_started = False


# ── Lecturas ─────────────────────────────────────────────────────────────────
def _read(path):
    try:
        with open(path) as f:
            return f.read().strip()
    except (OSError, ValueError):
        return None


def _scan_dmesg():
    """Lee el registro del kernel completo (desde el arranque)."""
    try:
        p = subprocess.run(["dmesg"], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           universal_newlines=True, timeout=15)
    except (OSError, subprocess.SubprocessError):
        _dmesg["ok"] = False
        return
    if p.returncode != 0 or not p.stdout:
        _dmesg["ok"] = False
        return
    sd, unclean, underv = [], [], 0
    for line in p.stdout.splitlines():
        if SD_ERR.search(line):
            sd.append(line.strip())
        elif UNCLEAN.search(line):
            unclean.append(line.strip())
        if UNDERV.search(line):
            underv += 1
    _dmesg.update(ok=True, sd=sd, unclean=unclean, underv=underv)


def _ext4_errors():
    total = 0
    for f in glob.glob("/sys/fs/ext4/*/errors_count"):
        v = _read(f)
        if v and v.isdigit():
            total += int(v)
    return total


def _readonly():
    txt = _read("/proc/mounts") or ""
    data = str(paths.data_dir())
    best, ro = "", False
    for line in txt.splitlines():
        f = line.split()
        if len(f) < 4:
            continue
        mp = f[1].replace("\\040", " ")
        if (data == mp or data.startswith(mp.rstrip("/") + "/") or mp == "/") and len(mp) >= len(best):
            best, ro = mp, "ro" in f[3].split(",")
    return ro


def _undervolt_now():
    for d in glob.glob("/sys/class/hwmon/hwmon*"):
        if _read(os.path.join(d, "name")) == "rpi_volt":
            v = _read(os.path.join(d, "in0_lcrit_alarm"))
            return None if v is None else v == "1"
    return None


def _write_probe():
    """Escribe 64 KB, fsync y borra; mide el tiempo en un hilo con límite."""
    f = paths.data_dir() / ".prueba-escritura"
    res = {}

    def work():
        t0 = time.time()
        try:
            with open(str(f), "wb") as fh:
                fh.write(os.urandom(65536))
                fh.flush()
                os.fsync(fh.fileno())
            paths.rm(f)
            res["s"] = time.time() - t0
        except OSError as e:
            res["err"] = e
    th = threading.Thread(target=work, daemon=True)
    th.start()
    th.join(90)
    if th.is_alive():
        return "grave", "La SD no terminó de guardar un archivo de 64 KB en 90 s (no responde)", None
    if "err" in res:
        return "grave", "No se pudo escribir en la SD: {}".format(res["err"]), None
    s = res["s"]
    if s > 20:
        return "grave", "Guardar 64 KB tardó {:.0f} s (lo normal es menos de 1 s)".format(s), s
    if s > 5:
        return "aviso", "Guardar 64 KB tardó {:.1f} s (lo normal es menos de 1 s)".format(s), s
    return "ok", "Guardar 64 KB tardó {:.2f} s".format(s), s


# ── Revisión ─────────────────────────────────────────────────────────────────
def _check(prev):
    out = {}
    snap = sysmon.snapshot()

    # SD / almacenamiento
    _scan_dmesg()
    ext4 = _ext4_errors()
    ro = _readonly()
    if ro:
        out["sd"] = ("grave", "El sistema de archivos quedó en solo lectura: lo que se guarde se perderá al reiniciar")
    elif _dmesg["sd"] or ext4:
        partes = []
        if _dmesg["sd"]:
            partes.append("{} errores del kernel desde el arranque; el último: {}".format(
                len(_dmesg["sd"]), _dmesg["sd"][-1][:160]))
        if ext4:
            partes.append("{} errores de ext4 registrados".format(ext4))
        out["sd"] = ("grave", " · ".join(partes))
    elif _dmesg["ok"] is False:
        out["sd"] = ("nd", "No se puede leer el registro del kernel (dmesg) con los permisos de HAMNA; sin errores de ext4")
    else:
        # Un apagado sin cerrar (corte de luz) es común y Linux lo repara al
        # arrancar: se anota, pero no es una alarma
        out["sd"] = ("ok", "Sin errores de la tarjeta desde el arranque" + (
            ". Nota: el último arranque fue después de un apagado sin cerrar (corte de luz o desconexión)"
            if _dmesg["unclean"] else ""))

    # Escritura (cada 10 min, o al empezar)
    if time.time() - _write["t"] >= WRITE_EVERY:
        nivel, det, s = _write_probe()
        _write.update(t=time.time(), nivel=nivel, detalle=det, segundos=s)
    out["escritura"] = (_write["nivel"], _write["detalle"])

    # Voltaje
    now = _undervolt_now()
    if now:
        out["voltaje"] = ("grave", "Bajo voltaje en este momento")
    elif _dmesg["underv"]:
        out["voltaje"] = ("aviso", "Hubo bajo voltaje {} {} desde el arranque".format(
            _dmesg["underv"], "vez" if _dmesg["underv"] == 1 else "veces"))
    elif now is None and not _dmesg["ok"]:
        out["voltaje"] = ("nd", "Este equipo no informa el voltaje")
    else:
        out["voltaje"] = ("ok", "Sin bajo voltaje desde el arranque")

    # Temperatura (con margen de 3 °C para dar por resuelto)
    t = snap.get("temp")
    if t is None:
        out["temperatura"] = ("nd", "Este equipo no informa la temperatura")
    else:
        p = prev.get("temperatura", ("ok",))[0]
        if t >= 82 or (p == "grave" and t >= 79):
            out["temperatura"] = ("grave", "{:.0f} °C".format(t))
        elif t >= 75 or (p in ("aviso", "grave") and t >= 72):
            out["temperatura"] = ("aviso", "{:.0f} °C".format(t))
        else:
            out["temperatura"] = ("ok", "{:.0f} °C".format(t))

    # Disco
    try:
        du = shutil.disk_usage(str(paths.data_dir()))
        mbf = du.free // 2**20
        det = "{} MB libres de {} MB".format(mbf, du.total // 2**20)
        if mbf < 200:
            out["disco"] = ("grave", det)
        elif mbf < 500 or du.free < du.total * 0.05:
            out["disco"] = ("aviso", det)
        else:
            out["disco"] = ("ok", det)
    except OSError as e:
        out["disco"] = ("grave", "No se pudo leer el disco: {}".format(e))

    # Memoria
    m = snap.get("mem")
    if not m or not m.get("total"):
        out["memoria"] = ("nd", "Sin datos")
    else:
        libre = (m["total"] - m["usada"]) // 2**20
        det = "{} MB libres de {} MB".format(libre, m["total"] // 2**20)
        out["memoria"] = ("aviso" if libre < 40 else "ok", det)
    return out


def _load_alerted():
    """Lo ya avisado sobrevive a los reinicios de HAMNA (si no, cada
    actualización repetiría los avisos de cosas que siguen igual)."""
    try:
        data = json.loads((paths.data_dir() / "salud.json").read_text(encoding="utf-8"))
        boot = _read("/proc/sys/kernel/random/boot_id")
        if data.get("boot") == boot:
            _alerted.update({k: tuple(v) for k, v in data.get("avisado", {}).items()})
    except Exception:
        pass


def _save_alerted():
    try:
        f = paths.data_dir() / "salud.json"
        f.write_text(json.dumps({"boot": _read("/proc/sys/kernel/random/boot_id"),
                                 "avisado": {k: list(v) for k, v in _alerted.items()}}), encoding="utf-8")
    except OSError:
        pass


def _alert(results):
    now = time.time()
    antes = dict(_alerted)
    peor, mejor = [], []
    for k in ORDER:
        nivel, det = results[k]
        n = NIVEL[nivel]
        prev_n, prev_t = _alerted.get(k, ("ok", 0))
        if n > NIVEL[prev_n] or (n and n == NIVEL[prev_n] and now - prev_t > REMIND):
            peor.append(k)
            _alerted[k] = (nivel, now)
        elif n < NIVEL[prev_n]:
            if n == 0:
                mejor.append(k)
                _alerted.pop(k, None)
            else:
                _alerted[k] = (nivel, prev_t)
    lines = []
    for k in peor:
        nivel, det = results[k]
        lines.append("{} <b>{}</b>: {}\n   <i>{}</i>".format(ICONO[nivel], NOMBRE[k], notify.esc(det),
                                                          notify.esc(CONSEJO[k])))
    for k in mejor:
        lines.append("✅ <b>{}</b>: se normalizó ({})".format(NOMBRE[k], notify.esc(results[k][1])))
    if _alerted != antes:
        _save_alerted()
    if lines:
        titulo = "🩺 <b>Salud del nodo</b>" if peor else "🩺 <b>Salud del nodo: se normalizó</b>"
        notify.send("salud", titulo + "\n" + "\n".join(lines), dedupe="salud:{}".format(now))
        for k in peor:
            log.warning("Salud: %s → %s: %s", NOMBRE[k], results[k][0], results[k][1])


def check_now():
    with _lock:
        prev = {k: (v["nivel"],) for k, v in _state["checks"].items()}
        res = _check(prev)
        _state["checks"] = {k: {"id": k, "nombre": NOMBRE[k], "nivel": res[k][0], "detalle": res[k][1],
                                "consejo": CONSEJO[k] if NIVEL[res[k][0]] else ""} for k in ORDER}
        _state["actualizado"] = time.strftime("%Y-%m-%d %H:%M:%S")
        _alert(res)
        return status()


def status():
    checks = [_state["checks"][k] for k in ORDER if k in _state["checks"]]
    worst = max([c["nivel"] for c in checks], key=lambda n: NIVEL[n], default="ok") if checks else "nd"
    return {"checks": checks, "actualizado": _state["actualizado"], "peor": worst}


def worst():
    return status()["peor"]


def _loop():
    time.sleep(20)                       # dejar que arranque todo lo demás
    while True:
        try:
            check_now()
        except Exception:
            log.exception("Error al revisar la salud del nodo")
        time.sleep(INTERVAL)


def start():
    global _started
    if _started:
        return
    _started = True
    _load_alerted()
    threading.Thread(target=_loop, daemon=True, name="salud").start()
