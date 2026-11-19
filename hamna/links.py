"""
HAMNA Web — conexiones y desconexiones automáticas de un evento.

Cada evento puede llevar una lista de acciones que corren antes de empezar
(N minutos antes si está programado) o al terminar (N minutos después):

  ASL   asterisk -rx "rpt cmd <nodo> ilink <n> [destino]"
          conectar      ilink 3 (transceptor), 2 (solo monitor), 8 (monitor local), 13 (permanente)
          desconectar   ilink 1 <destino>; si sigue (enlace permanente) ilink 11 <destino>
          todo          ilink 6 y luego ilink 11 a los que sigan conectados
  IRLP  $SCRIPT/decode <nodo|reflector>  y  $SCRIPT/end
        siempre como el usuario repeater, con el ayudante bin/hamna-irlp

Un nodo puede tener los dos sistemas; se detectan por separado.
"""
import logging
import os
import re
import subprocess
from pathlib import Path

from . import backends

log = logging.getLogger("hamna.links")

APP_DIR = Path(__file__).resolve().parent.parent
IRLP_HELPER = APP_DIR / "bin" / "hamna-irlp"

ASL_MODES = {"transceptor": 3, "monitor": 2, "monitor_local": 8, "permanente": 13}
ASL_MODO_NOMBRE = {"transceptor": "transceptor", "monitor": "monitor", "monitor_local": "monitor local",
                   "permanente": "permanente"}
ACCIONES = ("conectar", "desconectar", "desconectar_todo")
MOMENTOS = ("antes", "despues")


def detect_systems():
    """Qué sistemas hay en este equipo (pueden ser los dos)."""
    asl = os.path.isfile("/etc/asterisk/rpt.conf") and os.path.exists(backends.asterisk_bin())
    irlp = os.path.isdir("/home/irlp/scripts")
    return {"asl": asl, "irlp": irlp,
            "asl_nodo": backends.detect_asl_node() if asl else "",
            "irlp_helper": IRLP_HELPER.is_file()}


def validate(a):
    """Normaliza y valida una acción. Lanza ValueError si algo no cuadra."""
    sistema = (a.get("sistema") or "").lower()
    accion = (a.get("accion") or "").lower()
    momento = (a.get("momento") or "antes").lower()
    destino = str(a.get("destino") or "").strip()
    modo = (a.get("modo") or "transceptor").lower()
    try:
        minutos = float(a.get("minutos") or 0)
    except (TypeError, ValueError):
        raise ValueError("Minutos inválidos")
    if sistema not in ("asl", "irlp"):
        raise ValueError("Sistema inválido: usa ASL o IRLP")
    if accion not in ACCIONES:
        raise ValueError("Acción inválida")
    if momento not in MOMENTOS:
        raise ValueError("Momento inválido")
    if not 0 <= minutos <= 120:
        raise ValueError("Los minutos van de 0 a 120")
    if sistema == "asl":
        if modo not in ASL_MODES:
            raise ValueError("Modo de conexión inválido")
        if accion != "desconectar_todo" and not re.match(r"^\d{3,7}$", destino):
            raise ValueError("El nodo ASL debe ser un número de 3 a 7 dígitos")
    else:
        modo = ""
        if accion == "conectar" and not re.match(r"^\d{4,6}$", destino):
            raise ValueError("El nodo o reflector IRLP debe ser un número de 4 a 6 dígitos")
        if accion != "conectar":
            accion, destino = "desconectar_todo", ""   # IRLP solo tiene un enlace: 'end'
    if accion == "desconectar_todo":
        destino = ""
    return {"sistema": sistema, "accion": accion, "destino": destino, "modo": modo,
            "momento": momento, "minutos": minutos}


def describe(a):
    if a["accion"] == "desconectar_todo":
        txt = "desconectar todo" if a["sistema"] == "asl" else "desconectar (end)"
    elif a["accion"] == "desconectar":
        txt = "desconectar {}".format(a["destino"])
    else:
        txt = "conectar {}".format(a["destino"])
        if a["sistema"] == "asl" and a.get("modo") and a["modo"] != "transceptor":
            txt += " ({})".format(ASL_MODO_NOMBRE.get(a["modo"], a["modo"]))
    return "{} {}".format(a["sistema"].upper(), txt)


def _asl(a, node):
    if not node:
        raise RuntimeError("Falta el número de nodo ASL (Ajustes → Nodo)")
    # Probado en ASL3 (app_rpt 3.9.3) con el 299081 → 58788:
    #   enlace normal       ilink 1 lo desconecta (ilink 11 lo suelta, pero puede reconectarse solo)
    #   enlace permanente   ilink 1 se IGNORA; ilink 11 lo desconecta y se queda así
    #                       (los del startup_macro quedan permanentes)
    # Por eso: ilink 1 y, si el nodo sigue enlazado a los pocos segundos, ilink 11.
    if a["accion"] == "conectar":
        return _asl_rx(node, "rpt cmd {} ilink {} {}".format(node, ASL_MODES[a["modo"] or "transceptor"], a["destino"]))
    if a["accion"] == "desconectar":
        cmd = _asl_rx(node, "rpt cmd {} ilink 1 {}".format(node, a["destino"]))
        if _sigue(node, {a["destino"]}):
            cmd = _asl_rx(node, "rpt cmd {} ilink 11 {}".format(node, a["destino"])) + " (era permanente)"
        return cmd
    cmd = _asl_rx(node, "rpt cmd {} ilink 6".format(node))
    quedan = _sigue(node, None)
    for n in quedan:
        _asl_rx(node, "rpt cmd {} ilink 11 {}".format(node, n))
    return cmd + (" (+ ilink 11 a los permanentes: {})".format(", ".join(sorted(quedan))) if quedan else "")


def _sigue(node, nodos, espera=4):
    """Nodos (de `nodos`, o cualquiera si es None) que siguen enlazados tras `espera` segundos."""
    import time
    fin = time.time() + espera
    while True:
        time.sleep(1)
        ahora = set(_asl_enlaces(node))
        quedan = ahora if nodos is None else (ahora & nodos)
        if not quedan or time.time() >= fin:
            return quedan


def _asl_enlaces(node):
    """Nodos enlazados directamente ahora (rpt lstats)."""
    try:
        out = _asl_rx(node, "rpt lstats {}".format(node), salida=True)
    except RuntimeError:
        return []
    return re.findall(r"^\s*(\d{3,7})\s+\S+\s+\d+\s+(?:IN|OUT)\b", out, re.M)


def _asl_rx(node, cmd, salida=False):
    ast = [backends.asterisk_bin(), "-rx", cmd]
    r = subprocess.run(ast, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=20)
    out = r.stdout.decode(errors="ignore").strip()
    if "unable to connect" in out.lower() and os.geteuid() != 0:
        # Nodo con IRLP y ASL: el servicio es repeater y habla con Asterisk por sudo
        owner = _ctl_owner()
        if owner:
            r = subprocess.run(["sudo", "-n", "-u", owner] + ast, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, timeout=20)
            out = r.stdout.decode(errors="ignore").strip()
    if r.returncode != 0 or re.search(r"(?i)no such|not found|unable|usage|invalid|unknown", out):
        raise RuntimeError("Asterisk rechazó «{}»: {}".format(cmd, out[:150] or r.returncode))
    return out if salida else cmd


def _ctl_owner():
    for p in ("/var/run/asterisk/asterisk.ctl", "/run/asterisk/asterisk.ctl"):
        try:
            import pwd
            return pwd.getpwuid(os.stat(p).st_uid).pw_name
        except (ImportError, OSError, KeyError):
            continue
    return ""


def _irlp(a):
    if not IRLP_HELPER.is_file():
        raise RuntimeError("Falta el ayudante de IRLP; vuelve a ejecutar install.sh")
    arg = a["destino"] if a["accion"] == "conectar" else "end"
    try:
        import pwd                       # no existe en Windows
        me = pwd.getpwuid(os.geteuid()).pw_name
    except (ImportError, KeyError):
        me = ""
    if me == "repeater":
        cmd = [str(IRLP_HELPER), arg]
    elif os.geteuid() == 0:
        cmd = ["runuser", "-u", "repeater", "--", str(IRLP_HELPER), arg]
    else:
        cmd = ["sudo", "-n", "-u", "repeater", str(IRLP_HELPER), arg]
    r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60)
    out = r.stdout.decode(errors="ignore").strip()
    if r.returncode != 0:
        raise RuntimeError("IRLP no aceptó «{}»: {}".format(arg, out[-200:] or r.returncode))
    return "decode {}".format(arg) if arg != "end" else "end"


def run(a, cfg):
    """Ejecuta una acción ya validada. Devuelve el comando usado."""
    a = validate(a)
    if a["sistema"] == "asl":
        node = cfg.get("node") or backends.detect_asl_node()
        return _asl(a, node)
    return _irlp(a)
