"""
HAMNA Web — salida al aire.

Cada backend recibe un WAV 8 kHz mono y lo transmite completo, con el
transmisor activado de principio a fin. play() bloquea hasta que termina o
hasta que abort() devuelve True.

  ASL       asterisk -rx "rpt localplay|playback <nodo> <archivo>"
            (ASL3, ASL2 y HamVOIP). app_rpt activa y suelta el PTT solo.
  IRLP      $BIN/key → aplay → $BIN/unkey (con el entorno de IRLP)
  simulado  solo espera; sirve para probar la interfaz sin radio.
"""
import logging
import os
import re
import shlex
import shutil
import subprocess
import time
from pathlib import Path

log = logging.getLogger("hamna.backend")

FINISH_BUFFER = 0.8


def _sleep_until(seconds, abort):
    """Espera *seconds*. Devuelve False si se abortó antes."""
    end = time.time() + seconds
    while time.time() < end:
        if abort():
            return False
        time.sleep(0.1)
    return True


class Backend:
    name = "base"
    node = ""

    def play(self, wav, dur, abort):
        raise NotImplementedError

    def info(self):
        return {"backend": self.name}

    def test(self):
        return True, "OK"


class SimulatedBackend(Backend):
    name = "simulado"

    def play(self, wav, dur, abort):
        log.info("[simulado] TX %.1f s  %s", dur, Path(wav).name)
        return _sleep_until(dur, abort)

    def info(self):
        return {"backend": self.name, "detalle": "Sin radio: solo simula los tiempos"}

    def test(self):
        return True, "Modo simulado: no se transmite nada"


# ── AllStarLink / HamVOIP ─────────────────────────────────────────────────────
def asterisk_bin():
    return (shutil.which("asterisk") or
            next((p for p in ("/usr/sbin/asterisk", "/usr/bin/asterisk",
                              "/usr/local/sbin/asterisk") if os.path.exists(p)), "asterisk"))


class ASLBackend(Backend):
    name = "asl"

    def __init__(self, node, mode="localplay", flush_cmd=""):
        self.node = str(node).strip()
        self.mode = mode if mode in ("localplay", "playback") else "localplay"
        self.flush_cmd = flush_cmd
        self.asterisk = asterisk_bin()

    def rx(self, cmd, timeout=20):
        r = subprocess.run([self.asterisk, "-rx", cmd], stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, timeout=timeout)
        return r.returncode, r.stdout.decode(errors="ignore").strip()

    def flush(self):
        """Intenta cortar el audio que se está reproduciendo."""
        cmd = (self.flush_cmd or "").replace("{nodo}", self.node)
        if not cmd:
            log.info("[ASL] sin comando para cortar; el tramo actual termina solo")
            return
        try:
            code, out = self.rx(cmd)
            log.info("[ASL] cortar audio (%s) → %s %s", cmd, code, out[:100])
        except Exception as e:
            log.warning("[ASL] no se pudo cortar el audio: %s", e)

    def play(self, wav, dur, abort):
        if not self.node:
            raise RuntimeError("Falta el número de nodo (Ajustes → Nodo)")
        target = str(Path(wav).with_suffix(""))
        code, out = self.rx("rpt {} {} {}".format(self.mode, self.node, target))
        if code != 0 or re.search(r"(?i)no such|not found|unable|error|usage|invalid", out):
            raise RuntimeError("Asterisk rechazó el comando: {}".format(out[:200] or code))
        log.info("[ASL] %s %s (%.1f s)", self.mode, Path(wav).name, dur)
        ok = _sleep_until(dur + FINISH_BUFFER, abort)
        if not ok:
            self.flush()
        return ok

    def info(self):
        d = {"backend": self.name, "node": self.node, "mode": self.mode}
        try:
            code, out = self.rx("core show version", 8)
            d["asterisk"] = out.splitlines()[0][:120] if out else ""
            code, out = self.rx("rpt stats {}".format(self.node), 8)
            d["nodo_ok"] = "TX time today" in out or "Selected system state" in out
            code, out = self.rx("rpt nodes {}".format(self.node), 8)
            nodes = [x for x in re.split(r"[\s,]+", out)
                     if x and re.match(r"^[TRCL]?\d{3,7}$", x)]
            d["enlaces"] = ", ".join(nodes) or "ninguno"
        except Exception as e:
            d["error"] = str(e)
        return d

    def test(self):
        try:
            code, out = self.rx("rpt stats {}".format(self.node), 8)
        except Exception as e:
            return False, "No se pudo hablar con Asterisk: {}".format(e)
        if "TX time today" in out or "Selected system state" in out:
            return True, "Asterisk responde y el nodo {} está activo".format(self.node)
        return False, "El nodo {} no respondió a 'rpt stats': {}".format(self.node, out[:150])


# ── IRLP ──────────────────────────────────────────────────────────────────────
class IRLPBackend(Backend):
    name = "irlp"

    def __init__(self, env_file, key_cmd="key", unkey_cmd="unkey", player="aplay", node=""):
        self.env_file = env_file
        self.key_cmd = key_cmd
        self.unkey_cmd = unkey_cmd
        self.player = player
        self.node = node

    def _sh(self, script, timeout=20):
        q = shlex.quote(self.env_file)
        full = "[ -f {0} ] && . {0}; {1}".format(q, script)
        r = subprocess.run(["bash", "-c", full], stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, timeout=timeout)
        return r.returncode, r.stdout.decode(errors="ignore").strip()

    def key(self):
        return self._sh('"$BIN"/' + shlex.quote(self.key_cmd))

    def unkey(self):
        return self._sh('"$BIN"/' + shlex.quote(self.unkey_cmd))

    def play(self, wav, dur, abort):
        code, out = self.key()
        if code != 0:
            raise RuntimeError("No se pudo activar el PTT (key): {}".format(out[:200]))
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
                raise RuntimeError("{} falló: {}".format(self.player, err))
            return True
        finally:
            self.unkey()

    def info(self):
        d = {"backend": self.name, "node": self.node}
        try:
            code, out = self._sh('echo "$STATIONID|$( [ -f "$LOCAL/active" ] && cat "$LOCAL/active")"')
            sid, _, active = out.partition("|")
            d["stationid"] = sid
            d["enlaces"] = active or "ninguno"
        except Exception as e:
            d["error"] = str(e)
        return d

    def test(self):
        code, out = self._sh('[ -x "$BIN/key" ] && [ -x "$BIN/unkey" ] && echo "OK $STATIONID"')
        if out.startswith("OK"):
            return True, "Scripts de IRLP encontrados ({})".format(out[3:])
        return False, "No encontré $BIN/key y $BIN/unkey con {}".format(self.env_file)


# ── Detección y fábrica ───────────────────────────────────────────────────────
def detect():
    if os.path.isdir("/home/irlp/scripts") or os.path.isfile("/home/irlp/custom/environment"):
        return "irlp"
    if os.path.isfile("/etc/asterisk/rpt.conf") and os.path.exists(asterisk_bin()):
        return "asl"
    return "simulado"


def detect_flavor():
    """asl3, hamvoip o asl (ASL2/otros)."""
    if os.path.exists("/usr/local/etc/allstar.env") or os.path.exists("/usr/local/hamvoip-sbin"):
        return "hamvoip"
    if os.path.exists("/etc/asterisk/rpt.conf"):
        try:
            if "asl3" in subprocess.run(["dpkg", "-l", "asl3"], stdout=subprocess.PIPE,
                                        stderr=subprocess.DEVNULL).stdout.decode():
                return "asl3"
        except Exception:
            pass
        return "asl"
    return ""


def detect_asl_node():
    try:
        txt = Path("/etc/asterisk/rpt.conf").read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""
    m = re.search(r"^\[(\d{3,7})\]", txt, re.M)
    return m.group(1) if m else ""


def make(cfg):
    kind = cfg.get("backend") or "auto"
    if kind == "auto":
        kind = detect()
    if kind == "asl":
        return ASLBackend(cfg.get("node") or detect_asl_node(),
                          cfg.get("asl_mode", "localplay"), cfg.get("asl_flush_cmd", ""))
    if kind == "irlp":
        return IRLPBackend(cfg.get("irlp_env", "/home/irlp/custom/environment"),
                           cfg.get("irlp_key_cmd", "key"), cfg.get("irlp_unkey_cmd", "unkey"),
                           cfg.get("irlp_player", "aplay"), cfg.get("node", ""))
    return SimulatedBackend()
