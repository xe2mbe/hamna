"""
HAMNA Web — tablas de cron del nodo, a través del ayudante bin/hamna-cron.

El servicio corre como asterisk (ASL3) o repeater (IRLP) y no puede leer ni
escribir el cron de root; el instalador le permite ejecutar ese único
ayudante con sudo. En HamVOIP el servicio ya es root y lo llama directo.
"""
import json
import os
import subprocess
from pathlib import Path

HELPER = Path(__file__).resolve().parent.parent / "bin" / "hamna-cron"


def available():
    return HELPER.is_file()


def _call(args, stdin=None):
    if not available():
        raise RuntimeError("Este equipo no tiene el ayudante de cron (vuelve a ejecutar install.sh)")
    cmd = [str(HELPER)] + args
    if os.geteuid() != 0:
        cmd = ["sudo", "-n"] + cmd
    r = subprocess.run(cmd, input=stdin, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
    out = r.stdout.decode("utf-8", "replace").strip()
    try:
        data = json.loads(out.splitlines()[-1]) if out else {}
    except ValueError:
        data = {}
    if not data:
        err = r.stderr.decode("utf-8", "replace").strip()
        if "password is required" in err or "not allowed" in err or "a password" in err:
            raise RuntimeError("El servicio no tiene permiso para el cron. "
                               "Vuelve a ejecutar install.sh para crear la regla de sudo.")
        raise RuntimeError(err[-300:] or "El ayudante de cron no respondió")
    if not data.get("ok"):
        e = RuntimeError(data.get("error") or "Error del ayudante de cron")
        e.conflicto = bool(data.get("conflicto"))
        raise e
    return data


def list_tables():
    return _call(["list"])["tablas"]


def save_table(tid, expected_hash, text):
    return _call(["set", tid, expected_hash], stdin=text.encode("utf-8", "surrogateescape"))
