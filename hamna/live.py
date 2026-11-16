"""
HAMNA Web — escuchar el nodo en vivo desde la página.

app_rpt entrega el audio del nodo (lo que recibe y lo que transmite: HAMNA,
reportes, nodos enlazados) a `bin/hamna-live` con la línea `outstreamcmd`
de rpt.conf. Ese programa lo manda en paquetes UDP a 127.0.0.1:8091 y aquí
se reparte a quien esté escuchando.

En nodos IRLP no hay app_rpt. Al encenderlo en Ajustes → Sistema (o con
`bin/hamna-irlp-envivo on`) se agrega un bloque en /home/irlp/.asoundrc. Lo que IRLP reproduce (reflector, mensajes, HAMNA) pasa
por un derivador de ALSA a `bin/hamna-live-irlp`, que lo manda al mismo puerto;
lo que entra del radio lo lee este módulo con arecord (dsnoop, compartido con
imike). Mientras llega audio del derivador, el del radio se ignora (el nodo
está transmitiendo, así que el receptor no tiene nada útil).

El audio va en µ-law (8 kHz, 64 kbps): se convierte con una tabla, sin
ffmpeg, y solo mientras alguien escucha. El navegador lo reproduce con
Web Audio.
"""
import array
import collections
import logging
import os
import shutil
import socket
import subprocess
import threading
import time
from pathlib import Path

log = logging.getLogger("hamna.envivo")

PORT = 8091
MAX_LISTENERS = 8
CHUNK_RX = 1600                   # 100 ms del receptor (IRLP)
SILENCE = b"\xff" * 80            # 10 ms de silencio µ-law (para mantener viva la conexión)
ASOUNDRC = "/home/irlp/.asoundrc"
MARCA = ">>> HAMNA Web: escuchar en vivo"
TAP_HOLD = 0.4                     # s sin audio del derivador para volver a oír el receptor
HELPER = Path(__file__).resolve().parent.parent / "bin" / "hamna-irlp-envivo"


def es_irlp():
    return os.path.isdir("/home/irlp/scripts")


def irlp_activado():
    """¿Tiene /home/irlp/.asoundrc el bloque de HAMNA?"""
    try:
        with open(ASOUNDRC, encoding="utf-8", errors="ignore") as f:
            return MARCA in f.read()
    except OSError:
        return False


def _mulaw_table():
    """Tabla de 65536 entradas: muestra de 16 bits (sin signo) → byte µ-law."""
    out = bytearray(65536)
    for i in range(65536):
        s = i - 65536 if i >= 32768 else i
        sign = 0x80 if s < 0 else 0
        s = min(abs(s), 32635) + 0x84
        exp, mask = 7, 0x4000
        while not (s & mask) and exp > 0:
            exp -= 1
            mask >>= 1
        out[i] = ~(sign | (exp << 4) | ((s >> (exp + 3)) & 0x0F)) & 0xFF
    return bytes(out)


class _Listener:
    def __init__(self, ip, user):
        self.ip = ip
        self.user = user
        self.since = time.time()
        self.q = collections.deque(maxlen=50)     # 5 s como máximo; si se atrasa, se tira lo viejo
        self.ev = threading.Event()


class Live:
    def __init__(self):
        self._lock = threading.Lock()
        self._listeners = set()
        self._taps = []                 # funciones que reciben el audio crudo (grabar.py)
        self._table = None
        self.last_rx = 0.0
        self.last_tap = 0.0
        self.started = False
        self.error = ""
        self.irlp = False               # este nodo es IRLP
        self.irlp_rx = False            # arecord está leyendo el receptor
        self._wake = threading.Event()
        self._cambio = threading.Lock()

    # ── Recepción ─────────────────────────────────────────────────────────
    def start(self, port=PORT):
        if self.started:
            return
        self.started = True
        if es_irlp():
            self.irlp = True
            threading.Thread(target=self._irlp_loop, daemon=True, name="envivo-irlp").start()
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.bind(("127.0.0.1", port))
        except OSError as e:
            self.error = "No pude abrir 127.0.0.1:{} ({})".format(port, e)
            log.warning(self.error)
            return
        threading.Thread(target=self._rx, args=(sock,), daemon=True, name="envivo").start()

    def _rx(self, sock):
        while True:
            try:
                data = sock.recv(8192)
            except OSError:
                time.sleep(1)
                continue
            self.last_tap = time.time()
            self._feed(data)

    def _irlp_loop(self):
        """IRLP: lee lo que entra del radio mientras el bloque de .asoundrc esté puesto."""
        avisado = False
        while True:
            if not irlp_activado() or not shutil.which("arecord"):
                self.irlp_rx = False
                self._wake.wait(10)
                self._wake.clear()
                continue
            t0 = time.time()
            try:
                p = subprocess.Popen(["arecord", "-q", "-D", "default", "-f", "S16_LE", "-r", "8000",
                                      "-c", "1", "-t", "raw"],
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            except OSError as e:
                self.error = "No pude arrancar arecord: {}".format(e)
                time.sleep(30)
                continue
            self.irlp_rx = True
            if not avisado:
                log.info("En vivo (IRLP): escuchando el receptor con arecord")
                avisado = True
            revisado = time.time()
            try:
                while True:
                    data = p.stdout.read(CHUNK_RX)
                    if not data:
                        break
                    now = time.time()
                    if now - self.last_tap > TAP_HOLD:
                        self._feed(data)
                    if now - revisado > 10:
                        revisado = now
                        if not irlp_activado():
                            log.info("En vivo (IRLP): se desactivó; dejo de leer el receptor")
                            break
            finally:
                self.irlp_rx = False
                try:
                    p.kill()
                    err = p.communicate(timeout=5)[1].decode("utf-8", "replace").strip()
                except Exception:
                    err = ""
            if irlp_activado():
                self.error = "arecord se detuvo: {}".format(err[-200:] or "sin mensaje")
                log.warning("En vivo (IRLP): %s", self.error)
                time.sleep(5 if time.time() - t0 > 60 else 30)

    # ── IRLP: encender / apagar ───────────────────────────────────────────
    def _helper(self, accion):
        if not HELPER.is_file():
            return False, "Falta {}".format(HELPER)
        try:
            r = subprocess.run(["bash", str(HELPER), accion], stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, timeout=20)
        except (OSError, subprocess.SubprocessError) as e:
            return False, str(e)
        return r.returncode == 0, r.stdout.decode("utf-8", "replace").strip()

    def irlp_cambiar(self, on):
        """Enciende (con prueba; si falla, se revierte) o apaga escuchar en vivo en IRLP."""
        if not self.irlp:
            raise RuntimeError("Este nodo no es IRLP")
        if not self._cambio.acquire(False):
            raise RuntimeError("Ya se está cambiando; espera unos segundos")
        try:
            if not on:
                ok, msg = self._helper("off")
                self._wake.set()
                if not ok:
                    raise RuntimeError(msg or "No se pudo apagar")
                log.info("En vivo (IRLP): apagado desde la página")
                return {"ok": True, "activado": irlp_activado()}
            if irlp_activado():
                return {"ok": True, "activado": True}
            ok, msg = self._helper("on")
            if not ok:
                raise RuntimeError(msg or "No se pudo encender")
            falla = self._probar_irlp()
            if falla:
                self._helper("off")
                self._wake.set()
                log.warning("En vivo (IRLP): la prueba falló (%s); se dejó como estaba", falla)
                raise RuntimeError("La prueba falló y se dejó todo como estaba: " + falla)
            self._wake.set()
            log.info("En vivo (IRLP): encendido desde la página (prueba correcta)")
            return {"ok": True, "activado": True}
        finally:
            self._cambio.release()

    def _probar_irlp(self):
        """Medio segundo de silencio por la salida y un segundo del receptor. "" si todo bien."""
        if not shutil.which("aplay") or not shutil.which("arecord"):
            return "faltan aplay/arecord (paquete alsa-utils)"
        if self.error.startswith("No pude abrir"):
            return self.error
        t0 = time.time()
        try:
            r = subprocess.run(["aplay", "-q", "-t", "raw", "-f", "S16_LE", "-r", "8000", "-c", "1"],
                               input=b"\0\0" * 4000, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15)
        except (OSError, subprocess.SubprocessError) as e:
            return "no se pudo reproducir: {}".format(e)
        if r.returncode != 0:
            return "la salida de audio no abrió: " + r.stderr.decode("utf-8", "replace").strip()[-200:]
        fin = time.time() + 3
        while self.last_tap < t0 and time.time() < fin:
            time.sleep(0.1)
        if self.last_tap < t0:
            return "el audio de la salida no llegó a HAMNA"
        try:
            r = subprocess.run(["arecord", "-q", "-D", "default", "-f", "S16_LE", "-r", "8000", "-c", "1",
                                "-t", "raw", "-d", "1"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15)
        except (OSError, subprocess.SubprocessError) as e:
            return "no se pudo leer el receptor: {}".format(e)
        if r.returncode != 0 or len(r.stdout) < 8000:
            return "el receptor no entregó audio: " + r.stderr.decode("utf-8", "replace").strip()[-200:]
        return ""

    def _feed(self, data):
        """Audio de 16 bits a 8 kHz: a las grabaciones y a quien esté escuchando."""
        self.last_rx = time.time()
        if self.irlp_rx and self.error.startswith("arecord"):
            self.error = ""
        for t in list(self._taps):
            try:
                t(data)
            except Exception:
                log.exception("Error al pasar el audio a la grabación")
        if not self._listeners or len(data) < 2:
            return
        if len(data) % 2:
            data = data[:-1]
        if self._table is None:
            self._table = _mulaw_table()
        enc = bytes(map(self._table.__getitem__, array.array("H", data)))
        with self._lock:
            for l in self._listeners:
                l.q.append(enc)
                l.ev.set()

    def add_tap(self, fn):
        if fn not in self._taps:
            self._taps.append(fn)

    def remove_tap(self, fn):
        if fn in self._taps:
            self._taps.remove(fn)

    # ── Oyentes ───────────────────────────────────────────────────────────
    def stream(self, ip, user):
        """Generador con el audio µ-law para una respuesta HTTP."""
        with self._lock:
            if len(self._listeners) >= MAX_LISTENERS:
                raise RuntimeError("Ya hay {} personas escuchando; intenta más tarde".format(MAX_LISTENERS))
            l = _Listener(ip, user)
            self._listeners.add(l)
        log.info("En vivo: empieza a escuchar %s desde %s", user, ip)
        return self._gen(l)

    def _gen(self, l):
        try:
            yield SILENCE
            while True:
                if not l.ev.wait(5):
                    yield SILENCE          # nada que oír: un poco de silencio para que no se corte
                    continue
                l.ev.clear()
                chunks = []
                while l.q:
                    chunks.append(l.q.popleft())
                if chunks:
                    yield b"".join(chunks)
        finally:
            with self._lock:
                self._listeners.discard(l)
            log.info("En vivo: deja de escuchar %s (%d min)", l.user, int((time.time() - l.since) / 60))

    def status(self):
        now = time.time()
        with self._lock:
            oyentes = [{"usuario": l.user, "ip": l.ip, "desde": int(now - l.since)} for l in self._listeners]
        return {
            "configurado": self.last_rx > 0,
            "recibiendo": now - self.last_rx < 10,
            "oyentes": oyentes,
            "error": self.error,
            "puerto": PORT,
            "tipo": "irlp" if self.irlp else "asl",
            "irlp_activado": irlp_activado() if self.irlp else None,
        }


live = Live()
