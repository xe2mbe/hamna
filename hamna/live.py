"""
HAMNA Web — escuchar el nodo en vivo desde la página.

app_rpt entrega el audio del nodo (lo que recibe y lo que transmite: HAMNA,
reportes, nodos enlazados) a `bin/hamna-live` con la línea `outstreamcmd`
de rpt.conf. Ese programa lo manda en paquetes UDP a 127.0.0.1:8091 y aquí
se reparte a quien esté escuchando.

El audio va en µ-law (8 kHz, 64 kbps): se convierte con una tabla, sin
ffmpeg, y solo mientras alguien escucha. El navegador lo reproduce con
Web Audio.
"""
import array
import collections
import logging
import socket
import threading
import time

log = logging.getLogger("hamna.envivo")

PORT = 8091
MAX_LISTENERS = 8
SILENCE = b"\xff" * 80            # 10 ms de silencio µ-law (para mantener viva la conexión)


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
        self._table = None
        self.last_rx = 0.0
        self.started = False
        self.error = ""

    # ── Recepción ─────────────────────────────────────────────────────────
    def start(self, port=PORT):
        if self.started:
            return
        self.started = True
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
            self.last_rx = time.time()
            if not self._listeners or len(data) < 2:
                continue
            if len(data) % 2:
                data = data[:-1]
            if self._table is None:
                self._table = _mulaw_table()
            enc = bytes(map(self._table.__getitem__, array.array("H", data)))
            with self._lock:
                for l in self._listeners:
                    l.q.append(enc)
                    l.ev.set()

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
        }


live = Live()
