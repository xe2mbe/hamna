"""
HAMNA Web — grabar lo que se escucha en el nodo (p. ej. la toma de reportes).

El audio sale del mismo canal que «🔊 En vivo» (outstreamcmd de rpt.conf →
live.py): lo que el nodo recibe y lo que transmite. app_rpt solo manda audio
mientras hay sonido, así que los silencios largos no se graban (se dejan
pausas de hasta 1 s) y la grabación queda corrida, sin aire muerto.

Termina sola tras N minutos sin actividad (el ruido de fondo no cuenta), o al
llegar al tope de duración, o a mano. Al cerrar se recorta el final sin audio,
se pasa a MP3 si el nodo puede (si no, queda en WAV) y, si se pidió, se manda
al grupo de avisos de Telegram.
"""
import array
import datetime as dt
import json
import logging
import math
import os
import re
import threading
import time
import unicodedata
import wave

from . import export, notify, paths, settings

log = logging.getLogger("hamna.grabar")

RATE = 8000
UMBRAL_RMS = 400            # ~ −38 dBFS: por debajo es ruido o silencio
HUECO_MAX = 1.0             # silencio que se conserva entre pedazos de audio (s)
MIN_AUDIO = 3.0             # menos que esto de audio con actividad: no se guarda
TG_MAX = 49 * 1024 * 1024
NOMBRE_RX = re.compile(r"^\d{8}_\d{6}_[A-Za-z0-9_-]{0,60}\.(mp3|wav)$")


def carpeta():
    d = paths.data_dir() / "grabaciones"
    if not d.is_dir():
        os.makedirs(str(d), exist_ok=True)
    return d


def _slug(t):
    t = unicodedata.normalize("NFKD", t or "").encode("ascii", "ignore").decode("ascii")   # «Boletín» → «Boletin»
    return re.sub(r"[^A-Za-z0-9]+", "_", t).strip("_")[:50] or "grabacion"


def _rms(data):
    a = array.array("h")
    a.frombytes(data[:len(data) - len(data) % 2])
    if not a:
        return 0.0
    return math.sqrt(sum(x * x for x in a[::4]) / max(1, len(a[::4])))


class Grabadora:
    def __init__(self):
        self._lock = threading.Lock()
        self.g = None

    # ── Estado ────────────────────────────────────────────────────────────
    def estado(self):
        with self._lock:
            g = self.g
            if not g:
                return {"grabando": False}
            now = time.time()
            sil = now - g["ultimo_audio"]
            return {"grabando": True, "titulo": g["titulo"], "origen": g["origen"],
                    "desde": dt.datetime.fromtimestamp(g["inicio"]).strftime("%Y-%m-%d %H:%M:%S"),
                    "dur": int(now - g["inicio"]), "audio": round(g["frames"] / float(RATE)),
                    "silencio": int(sil), "limite": g["silencio_max"],
                    "faltan": max(0, int(g["silencio_max"] - sil))}

    # ── Empezar / parar ───────────────────────────────────────────────────
    def iniciar(self, titulo, origen, evento_id=None):
        from .live import live
        cfg = settings.load()
        with self._lock:
            if self.g:
                raise ValueError("Ya se está grabando «{}»".format(self.g["titulo"]))
            now = time.time()
            base = "{}_{}".format(dt.datetime.fromtimestamp(now).strftime("%Y%m%d_%H%M%S"), _slug(titulo))
            part = carpeta() / (base + ".wav.part")
            w = wave.open(str(part), "wb")
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(RATE)
            self.g = {"titulo": (titulo or "Grabación")[:120], "origen": origen, "evento_id": evento_id,
                      "base": base, "part": part, "w": w, "inicio": now, "ultimo_audio": now, "ultimo_rx": 0.0,
                      "frames": 0, "frames_activos": 0, "frames_ult_audio": 0,
                      "silencio_max": max(1, int(cfg.get("rec_silencio_min", 5) or 5)) * 60,
                      "tope": max(10, int(cfg.get("rec_max_min", 180) or 180)) * 60}
        if not live.started:
            live.start()
        live.add_tap(self._pcm)
        threading.Thread(target=self._vigilar, name="grabar", daemon=True).start()
        log.info("Grabación: empieza «%s» (%s)", titulo, origen)
        return self.estado()

    def _pcm(self, data):
        """Llega del hilo de live.py: audio de 16 bits a 8 kHz."""
        with self._lock:
            g = self.g
            if not g or len(data) < 2:
                return
            data = data[:len(data) - len(data) % 2]
            now = time.time()
            n = len(data) // 2
            if g["ultimo_rx"]:
                hueco = now - g["ultimo_rx"] - n / float(RATE)
                if hueco > 0.05:
                    relleno = int(min(hueco, HUECO_MAX) * RATE)
                    g["w"].writeframes(b"\0\0" * relleno)
                    g["frames"] += relleno
            g["w"].writeframes(data)
            g["frames"] += n
            g["ultimo_rx"] = now
            if _rms(data) > UMBRAL_RMS:
                g["ultimo_audio"] = now
                g["frames_activos"] += n
                g["frames_ult_audio"] = g["frames"]

    def _vigilar(self):
        while True:
            time.sleep(1)
            with self._lock:
                g = self.g
                if not g:
                    return
                now = time.time()
                motivo = ("silencio" if now - g["ultimo_audio"] >= g["silencio_max"] else
                          "tope" if now - g["inicio"] >= g["tope"] else None)
            if motivo:
                self.detener(motivo)
                return

    def detener(self, motivo="manual"):
        from .live import live
        with self._lock:
            g, self.g = self.g, None
        if not g:
            return None
        live.remove_tap(self._pcm)
        try:
            g["w"].close()
        except Exception:
            pass
        g["fin"] = time.time()
        threading.Thread(target=self._cerrar, args=(g, motivo), daemon=True).start()
        return {"titulo": g["titulo"], "motivo": motivo}

    # ── Cerrar: recortar, MP3, guardar y (si se pidió) mandar ───────────
    def _cerrar(self, g, motivo):
        part = g["part"]
        try:
            if g["frames_activos"] / float(RATE) < MIN_AUDIO:
                paths.rm(part)
                log.info("Grabación «%s»: no hubo audio; no se guardó", g["titulo"])
                return
            # quitar el final sin actividad (deja 2 s)
            hasta = min(g["frames"], g["frames_ult_audio"] + 2 * RATE)
            wav = carpeta() / (g["base"] + ".wav")
            with wave.open(str(part), "rb") as r, wave.open(str(wav), "wb") as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(RATE)
                quedan = hasta
                while quedan > 0:
                    b = r.readframes(min(quedan, 65536))
                    if not b:
                        break
                    w.writeframes(b)
                    quedan -= len(b) // 2
            paths.rm(part)
            final = wav
            if "mp3" in export.formats():
                mp3 = carpeta() / (g["base"] + ".mp3")
                try:
                    export._encode_mp3(str(wav), str(mp3), RATE)
                    paths.rm(wav)
                    final = mp3
                except Exception as e:
                    log.warning("Grabación: no pude pasar a MP3 (%s); queda en WAV", e)
            meta = {"archivo": final.name, "titulo": g["titulo"], "origen": g["origen"], "evento_id": g["evento_id"],
                    "inicio": dt.datetime.fromtimestamp(g["inicio"]).strftime("%Y-%m-%d %H:%M:%S"),
                    "fin": dt.datetime.fromtimestamp(g["fin"]).strftime("%Y-%m-%d %H:%M:%S"),
                    "dur": round(hasta / float(RATE)), "tam": final.stat().st_size, "motivo": motivo}
            (carpeta() / (g["base"] + ".json")).write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
            log.info("Grabación guardada: %s (%s, %s)", final.name, _hm(meta["dur"]), motivo)
            limpiar()
            _a_telegram(final, meta)
        except Exception:
            log.exception("No pude cerrar la grabación «%s»", g["titulo"])


def _hm(s):
    s = int(s or 0)
    h, r = divmod(s, 3600)
    return "{}:{:02d}:{:02d}".format(h, r // 60, r % 60) if h else "{}:{:02d}".format(r // 60, r % 60)


MOTIVOS = {"silencio": "sin actividad", "tope": "llegó al tope de duración", "manual": "detenida a mano"}


def _a_telegram(path, meta):
    cfg = settings.load()
    if not (cfg.get("rec_tg") and cfg.get("tg_enabled") and cfg.get("tg_token") and cfg.get("tg_chat")):
        return
    cap = "🎙 <b>{}</b>\n{} · {} · {}".format(notify.esc(meta["titulo"]), meta["inicio"][:16], _hm(meta["dur"]),
                                              MOTIVOS.get(meta["motivo"], meta["motivo"]))
    try:
        if path.stat().st_size > TG_MAX:
            notify.send_now(notify.header(cfg) + "\n" + cap + "\n(pesa {:.0f} MB: Telegram acepta hasta 50; está en HAMNA → Grabaciones)".format(
                path.stat().st_size / 1048576.0))
            return
        audio_mp3 = path.suffix == ".mp3"
        notify.send_document(cfg["tg_token"].strip(), cfg["tg_chat"].strip(), str(path),
                             nombre_bonito(meta["titulo"], path.suffix),
                             notify.header(cfg) + "\n" + cap, timeout=900,
                             metodo="sendAudio" if audio_mp3 else "sendDocument",
                             campo="audio" if audio_mp3 else "document",
                             tipo="audio/mpeg" if audio_mp3 else "audio/wav")
    except Exception as e:
        log.warning("No pude mandar la grabación a Telegram: %s", e)


# ── Lista y limpieza ────────────────────────────────────────────────────────
def lista():
    out = []
    for j in sorted(carpeta().glob("*.json"), reverse=True):
        try:
            m = json.loads(j.read_text(encoding="utf-8"))
        except Exception:
            continue
        if (carpeta() / m.get("archivo", "")).is_file():
            out.append(m)
    return out


def archivo(nombre):
    if not NOMBRE_RX.match(nombre or ""):
        return None
    p = carpeta() / nombre
    return p if p.is_file() else None


def borrar(nombre):
    p = archivo(nombre)
    if not p:
        raise ValueError("No existe esa grabación")
    base = re.sub(r"\.(mp3|wav)$", "", nombre)
    for ext in (".mp3", ".wav", ".json"):
        paths.rm(carpeta() / (base + ext))


def limpiar():
    """Borrar las de más de N días y, si queda poco disco, las más viejas."""
    import shutil
    dias = int(settings.load().get("rec_dias", 30) or 0)
    items = sorted(carpeta().glob("*.json"))
    if dias > 0:
        lim = time.time() - dias * 86400
        for j in items:
            if j.stat().st_mtime < lim:
                try:
                    borrar(json.loads(j.read_text(encoding="utf-8"))["archivo"])
                except Exception:
                    paths.rm(j)
    items = sorted(carpeta().glob("*.json"))
    while len(items) > 1 and shutil.disk_usage(str(carpeta())).free < 300 * 2**20:
        j = items.pop(0)
        try:
            borrar(json.loads(j.read_text(encoding="utf-8"))["archivo"])
            log.warning("Poco disco: borré la grabación más vieja (%s)", j.name)
        except Exception:
            paths.rm(j)
    for p in carpeta().glob("*.wav.part"):           # restos de un apagón a media grabación
        if not grabadora.g or p != grabadora.g["part"]:
            if time.time() - p.stat().st_mtime > 3600:
                paths.rm(p)


# ── Automático alrededor de los eventos ────────────────────────────────────
TITULO_DEFAULT = "{evento} {numero} · Toma de reportes"


def titulo_de(ev, plantilla):
    """Título de la grabación automática a partir de la plantilla de Ajustes → Grabación."""
    from . import numeracion
    ev = ev or {}
    etq = numeracion.etiqueta(ev) if ev.get("num") or ev.get("numero") else ""
    now = dt.datetime.now()
    rep = {"{evento}": ev.get("nombre") or "Emisión", "{numero}": etq,
           "{emision}": str(ev.get("numero") or ""), "{emision_anio}": str(ev.get("emision_anio") or ""),
           "{anio}": str(ev.get("anio") or now.year), "{fecha}": now.strftime("%d/%m/%Y"), "{hora}": now.strftime("%H:%M")}
    t = plantilla or TITULO_DEFAULT
    for k, v in rep.items():
        t = t.replace(k, v)
    t = re.sub(r"\s{2,}", " ", t)
    t = re.sub(r"(\s*·\s*){2,}", " · ", t).strip(" ·")         # sin número: que no queden «·» de más
    return (t or "Grabación")[:120]


def nombre_bonito(titulo, ext):
    """Nombre para descargar o mandar: el título tal cual, sin los caracteres que Windows no acepta."""
    t = re.sub(r'[\\/:*?"<>|\r\n\t]+', " ", titulo or "Grabación")
    t = re.sub(r"\s{2,}", " ", t).strip(" .") or "Grabación"
    return t[:150] + ext


def al_evento(cuando, ev, backend=""):
    """El motor avisa: cuando = 'inicio' o 'fin' de una emisión."""
    cfg = settings.load()
    modo = cfg.get("rec_auto", "fin")
    if modo != cuando or backend == "irlp":         # IRLP no tiene el audio en vivo
        return
    if grabadora.g:
        return
    titulo = titulo_de(ev, cfg.get("rec_titulo") or TITULO_DEFAULT)
    try:
        grabadora.iniciar(titulo, "automático", ev.get("id"))
    except Exception as e:
        log.warning("No pude empezar la grabación automática: %s", e)


grabadora = Grabadora()
