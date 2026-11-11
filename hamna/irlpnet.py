"""
HAMNA Web — el audio de HAMNA también a la red IRLP (reflector o nodo conectado).

IRLP solo manda a la red lo que entra por el receptor mientras hay COS, así que
`aplay` por sí solo suena en el radio local pero no en el reflector. Para que
llegue a la red, como `rpt playback` en AllStar, se usa el mismo imike de IRLP
en modo archivo, con la identidad del nodo:

    imike -n|-f|-t -Y/dev/null 127.0.0.1:R archivo.au
        → relevo en 127.0.0.1:R (audio) y R+1 (control)
        → reflector IP:PUERTO y PUERTO+1, desde un solo socket

imike comprime (UNCOMP, ADPCM o GSM, el que use el canal) y marca el ritmo. El
relevo solo reenvía, y descarta la despedida RTCP (BYE): con ella el reflector
olvida al emisor (probado con el reflector de eco 9990 en el stn8422).
"""
import array
import logging
import os
import random
import select
import shutil
import socket
import struct
import subprocess
import sys
import threading
import time
import wave

log = logging.getLogger("hamna.irlp")

CODEC_FLAGS = (("UNCOMP", "-n"), ("ADPCM", "-f"), ("GSM", "-t"))
DEFAULT_PORT = 2074
# IRLP escribe calledip unos segundos antes que active al conectar. Si calledip
# es mucho más viejo que active, es de una conexión anterior (p. ej. ahora es
# una llamada entrante) y no sirve.
STALE_SECS = 120
RTCP_BYE = 203


def _read(path):
    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            return f.read().strip()
    except OSError:
        return ""


def _mtime(path):
    try:
        return os.path.getmtime(path)
    except OSError:
        return 0.0


def target(local_dir):
    """A dónde mandar el audio: la conexión activa de IRLP.

    Devuelve None si el nodo no está conectado, o un dict con active, ip,
    port, codec y flag (ip vacía + error si no se puede saber la IP)."""
    f_active = os.path.join(local_dir, "active")
    active = _read(f_active)
    if not active:
        return None
    t = {"active": active, "ip": "", "port": DEFAULT_PORT, "codec": "", "flag": "-n", "error": ""}
    f_ip = os.path.join(local_dir, "calledip")
    ip = _read(f_ip)
    if not ip or _mtime(f_ip) < _mtime(f_active) - STALE_SECS:
        t["error"] = "IRLP no guardó la IP de esta conexión (¿llamada entrante?)"
        return t
    t["ip"] = ip.split()[0]
    port = _read(os.path.join(local_dir, "udp_port"))
    if port.isdigit():
        t["port"] = int(port)
    codec = _read(os.path.join(local_dir, "codec")).upper()
    t["codec"] = codec or "UNCOMP"
    t["flag"] = next((fl for name, fl in CODEC_FLAGS if codec.startswith(name)), "-n")
    return t


def describe(t):
    if not t:
        return "sin conexión: solo el radio local"
    if not t["ip"]:
        return "{} — {}".format(t["active"], t["error"])
    return "{} ({}:{}, {})".format(t["active"], t["ip"], t["port"], t["codec"])


# ── WAV → AU µ-law (lo que lee imike) ────────────────────────────────────────
_TABLE = None


def _table():
    global _TABLE
    if _TABLE is None:
        from .live import _mulaw_table
        _TABLE = _mulaw_table()
    return _TABLE


def to_au(wav_path, au_path):
    """Convierte el WAV 8 kHz 16 bits mono de HAMNA a .au µ-law."""
    sox = shutil.which("sox")
    if sox:
        r = subprocess.run([sox, "-q", str(wav_path), "-r", "8000", "-c", "1", "-t", "au",
                            "-e", "mu-law", str(au_path)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=300)
        if r.returncode == 0:
            return
        log.warning("[IRLP] sox no pudo convertir (%s); uso el conversor interno",
                    r.stderr.decode(errors="ignore")[:120])
    with wave.open(str(wav_path), "rb") as w:
        if w.getsampwidth() != 2 or w.getnchannels() != 1 or w.getframerate() != 8000:
            raise RuntimeError("se esperaba WAV 8 kHz 16 bits mono")
        frames = w.readframes(w.getnframes())
    samples = array.array("h")
    samples.frombytes(frames[:len(frames) // 2 * 2])
    if sys.byteorder == "big":
        samples.byteswap()
    tab = _table()
    data = bytes(tab[s & 0xFFFF] for s in samples)
    with open(str(au_path), "wb") as f:
        f.write(struct.pack(">4sIIIII", b".snd", 24, len(data), 1, 8000, 1))
        f.write(data)


# ── Envío ────────────────────────────────────────────────────────────────────
def _has_bye(pkt):
    """¿El paquete RTCP (compuesto) trae una despedida?"""
    off = 0
    while off + 4 <= len(pkt):
        if pkt[off + 1] == RTCP_BYE:
            return True
        off += (struct.unpack(">H", pkt[off + 2:off + 4])[0] + 1) * 4
    return False


class Sender:
    """Un imike en modo archivo + el relevo hacia el reflector."""

    def __init__(self, t, imike, callsign, stationid):
        self.t = t
        self.imike = imike
        self.callsign = callsign
        # IRLP agrega un 0 a los stationid viejos de 6 caracteres
        self.sid = stationid + "0" if len(stationid) == 6 else stationid
        self.proc = None
        self._stop = threading.Event()
        self._thread = None
        self._socks = []
        self.audio = self.control = self.byes = 0

    def _bind(self):
        for _ in range(30):
            r = random.randrange(40000, 60000, 2)
            a = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            c = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                a.bind(("127.0.0.1", r))
                c.bind(("127.0.0.1", r + 1))
                return r, a, c
            except OSError:
                a.close()
                c.close()
        raise RuntimeError("no encontré un par de puertos libres para el relevo")

    def start(self, au_path):
        r, a, c = self._bind()
        out = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._socks = [a, c, out]
        dst = self.t["ip"]
        port = self.t["port"]

        def relay():
            while not self._stop.is_set():
                try:
                    ready, _, _ = select.select([a, c], [], [], 0.2)
                    for s in ready:
                        pkt = s.recv(65535)
                        if s is a:
                            out.sendto(pkt, (dst, port))
                            self.audio += 1
                        elif _has_bye(pkt):
                            self.byes += 1
                        else:
                            out.sendto(pkt, (dst, port + 1))
                            self.control += 1
                except OSError as e:
                    if not self._stop.is_set():
                        log.warning("[IRLP] relevo: %s", e)
                    return

        self._thread = threading.Thread(target=relay, daemon=True, name="irlp-relevo")
        self._thread.start()
        env = dict(os.environ)
        env["SPEAKFREE_CNAME"] = self.callsign
        env["SPEAKFREE_ID"] = "{} IRLP::".format(self.sid)
        self.proc = subprocess.Popen([self.imike, self.t["flag"], "-Y/dev/null",
                                      "127.0.0.1:{}".format(r), str(au_path)],
                                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                     stderr=subprocess.DEVNULL, env=env)
        log.info("[IRLP] a la red: %s", describe(self.t))

    def running(self):
        return self.proc is not None and self.proc.poll() is None

    def finish(self, timeout=3.0):
        """Espera a que imike termine de mandar (va al ritmo del audio)."""
        end = time.time() + timeout
        while self.running() and time.time() < end:
            time.sleep(0.05)
        time.sleep(0.3)          # lo último que quedó en el relevo
        self.stop()

    def stop(self):
        if self.proc is not None and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(3)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        self._stop.set()
        if self._thread:
            self._thread.join(2)
        for s in self._socks:
            try:
                s.close()
            except OSError:
                pass
        self._socks = []
        if self.audio or self.control:
            log.info("[IRLP] red: %d paquetes de audio, %d de control", self.audio, self.control)
            self.audio = self.control = 0
