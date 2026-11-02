"""
HAMNA Web — salida al aire.

Cada backend recibe un WAV 8 kHz mono y lo transmite completo, con el
transmisor activado de principio a fin. play() bloquea hasta que termina o
hasta que abort() devuelve True.

  ASL    asterisk -rx "rpt localplay|playback <nodo> <archivo>"
         app_rpt activa y suelta el PTT solo.
  IRLP   $BIN/key → aplay → $BIN/unkey (con el entorno de IRLP)
  simulado  solo espera; sirve para probar la interfaz sin radio.
"""
from __future__ import annotations

import logging
import os
import re
import shlex
import shutil
import subprocess
import time
from pathlib import Path
from typing import Callable

log = logging.getLogger("hamna.backend")

FINISH_BUFFER = 0.8


def _sleep_until(seconds: float, abort: Callable[[], bool]) -> bool:
    """Espera *seconds*. Devuelve False si se abortó antes."""
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if abort():
            return False
        time.sleep(0.1)
    return True


class Backend:
    name = "base"

    def play(self, wav: Path, dur: float, abort: Callable[[], bool]) -> bool:
        raise NotImplementedError

    def info(self) -> dict:
        return {"backend": self.name}

    def test(self) -> tuple[bool, str]:
        return True, "OK"


class SimulatedBackend(Backend):
    name = "simulado"

    def play(self, wav, dur, abort):
        log.info("[simulado] TX %.1f s  %s", dur, Path(wav).name)
        return _sleep_until(dur, abort)

    def info(self):
        return {"backend": self.name, "detalle": "Sin radio: solo simula los tiempos"}


# ── AllStarLink ───────────────────────────────────────────────────────────────
class ASLBackend(Backend):
    name = "asl"

    def __init__(self, node: str, mode: str = "localplay"):
        self.node = str(node).strip()
        self.mode = mode if mode in ("localplay", "playback") else "localplay"
        self.asterisk = (shutil.which("asterisk") or
                         next((p for p in ("/usr/sbin/asterisk", "/usr/bin/asterisk")
                               if os.path.exists(p)), "asterisk"))

    def rx(self, cmd: str, timeout=20) -> tuple[int, str]:
        r = subprocess.run([self.asterisk, "-rx", cmd], stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, timeout=timeout)
        return r.returncode, r.stdout.decode(errors="ignore").strip()

    def flush(self) -> None:
        """Corta lo que se esté reproduciendo (COP 24: vaciar la cola de telemetría)."""
        try:
            code, out = self.rx(f"rpt cmd {self.node} cop 24 0")
            log.info("[ASL] flush telemetría → %s %s", code, out[:100])
        except Exception as e:
            log.warning("[ASL] no se pudo cortar el audio: %s", e)

    def play(self, wav, dur, abort):
        if not self.node:
            raise RuntimeError("Falta el número de nodo (Ajustes → Nodo)")
        target = str(Path(wav).with_suffix(""))
        code, out = self.rx(f"rpt {self.mode} {self.node} {target}")
        if code != 0 or re.search(r"(?i)no such|not found|unable|error|usage", out):
            raise RuntimeError(f"Asterisk rechazó el comando: {out[:200] or code}")
        log.info("[ASL] %s %s (%.1f s)", self.mode, Path(wav).name, dur)
        ok = _sleep_until(dur + FINISH_BUFFER, abort)
        if not ok:
            self.flush()
        return ok

    def info(self):
        d = {"backend": self.name, "node": self.node, "mode": self.mode}
        try:
            code, out = self.rx("core show version", 8)
            d["asterisk"] = out.splitlines()[0] if out else ""
            code, out = self.rx(f"rpt stats {self.node}", 8)
            d["nodo_ok"] = "TX time today" in out or "Selected system state" in out
            code, out = self.rx(f"rpt nodes {self.node}", 8)
            d["enlaces"] = ", ".join(x for x in re.split(r"[\s,]+", out)
                                     if x and not x.startswith("*") and "CONNECTED" not in x
                                     and "NODES" not in x and "<NONE>" not in x)[:200]
        except Exception as e:
            d["error"] = str(e)
        return d

    def test(self):
        try:
            code, out = self.rx(f"rpt stats {self.node}", 8)
        except Exception as e:
            return False, f"No se pudo hablar con Asterisk: {e}"
        if "TX time today" in out or "Selected system state" in out:
            return True, f"Asterisk responde y el nodo {self.node} está activo"
        return False, f"El nodo {self.node} no respondió a 'rpt stats': {out[:150]}"


# ── IRLP ──────────────────────────────────────────────────────────────────────
class IRLPBackend(Backend):
    name = "irlp"

    def __init__(self, env_file: str, key_cmd="key", unkey_cmd="unkey",
                 player="aplay", node=""):
        self.env_file = env_file
        self.key_cmd = key_cmd
        self.unkey_cmd = unkey_cmd
        self.player = player
        self.node = node

    def _sh(self, script: str, timeout=20) -> tuple[int, str]:
        full = f"[ -f {shlex.quote(self.env_file)} ] && . {shlex.quote(self.env_file)}; {script}"
        r = subprocess.run(["bash", "-c", full], stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, timeout=timeout)
        return r.returncode, r.stdout.decode(errors="ignore").strip()

    def key(self):
        return self._sh(f'"$BIN"/{shlex.quote(self.key_cmd)}')

    def unkey(self):
        return self._sh(f'"$BIN"/{shlex.quote(self.unkey_cmd)}')

    def play(self, wav, dur, abort):
        code, out = self.key()
        if code != 0:
            raise RuntimeError(f"No se pudo activar el PTT (key): {out[:200]}")
        proc = None
        try:
            cmd = [self.player, "-q", str(wav)] if self.player == "aplay" else \
                  shlex.split(self.player) + [str(wav)]
            proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            while proc.poll() is None:
                if abort():
                    proc.terminate()
                    try:
                        proc.wait(3)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                    return False
                time.sleep(0.1)
            if proc.returncode != 0:
                err = proc.stderr.read().decode(errors="ignore")[:200] if proc.stderr else ""
                raise RuntimeError(f"{self.player} falló: {err}")
            return True
        finally:
            self.unkey()

    def info(self):
        d = {"backend": self.name, "node": self.node}
        try:
            code, out = self._sh('echo "$STATIONID|$( [ -f "$LOCAL/active" ] && cat "$LOCAL/active")"')
            sid, _, active = out.partition("|")
            d["stationid"] = sid
            d["conectado_a"] = active
        except Exception as e:
            d["error"] = str(e)
        return d

    def test(self):
        code, out = self._sh('[ -x "$BIN/key" ] && [ -x "$BIN/unkey" ] && echo "OK $STATIONID"')
        if out.startswith("OK"):
            return True, f"Scripts de IRLP encontrados ({out[3:]})"
        return False, f"No encontré $BIN/key / $BIN/unkey con {self.env_file}"


# ── Detección y fábrica ───────────────────────────────────────────────────────
def detect() -> str:
    if os.path.isdir("/home/irlp/scripts") or os.path.isfile("/home/irlp/custom/environment"):
        return "irlp"
    if shutil.which("asterisk") or os.path.exists("/usr/sbin/asterisk"):
        if os.path.isfile("/etc/asterisk/rpt.conf"):
            return "asl"
    return "simulado"


def detect_asl_node() -> str:
    try:
        txt = Path("/etc/asterisk/rpt.conf").read_text(errors="ignore")
    except Exception:
        return ""
    m = re.search(r"^\[(\d{3,7})\]\s*(\(.*\))?\s*$", txt, re.M)
    return m.group(1) if m else ""


def make(cfg: dict) -> Backend:
    kind = cfg.get("backend") or "auto"
    if kind == "auto":
        kind = detect()
    if kind == "asl":
        return ASLBackend(cfg.get("node") or detect_asl_node(), cfg.get("asl_mode", "localplay"))
    if kind == "irlp":
        return IRLPBackend(cfg.get("irlp_env", "/home/irlp/custom/environment"),
                           cfg.get("irlp_key_cmd", "key"), cfg.get("irlp_unkey_cmd", "unkey"),
                           cfg.get("irlp_player", "aplay"), cfg.get("node", ""))
    return SimulatedBackend()
