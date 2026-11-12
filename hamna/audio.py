"""
HAMNA Web — audio.

Todo lo que sale al aire se convierte a WAV 8 kHz, 16 bits, mono: es el
formato nativo de Asterisk (rpt localplay) y sirve para aplay en IRLP. Con un
solo formato, cortar, pegar y mezclar se hace en Python con el módulo wave.

Herramientas, en orden de preferencia:
  ffmpeg            convierte todo y mide LUFS de verdad (ASL3, IRLP con Debian)
  sox + mpg123      HamVOIP: sox convierte; mpg123 decodifica MP3; el nivel se
                    mide con sox tras un filtro que imita la ponderación K
"""
import array
import hashlib
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import uuid
import wave
from pathlib import Path

from . import paths

log = logging.getLogger("hamna.audio")

RATE = 8000
CACHE_VERSION = "v3"
PEAK_LIMIT_DB = -2.0
_locks = {}
_locks_guard = threading.Lock()


def _lock_for(key):
    with _locks_guard:
        return _locks.setdefault(key, threading.Lock())


def _run(cmd, timeout=900):
    cmd = [str(c) for c in cmd]
    # Convertir audio es lo único pesado de HAMNA: prioridad baja para que
    # Asterisk (el audio al aire) nunca espere por la CPU
    if cmd and cmd[0] in ("ffmpeg", "sox", "mpg123") and shutil.which("nice"):
        cmd = ["nice", "-n", "10"] + cmd
    return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)


_WORKS = {}


def have(tool):
    """¿Está el programa y además arranca? Un ffmpeg al que le faltan librerías
    (pasó en un nodo IRLP con libraspberrypi0 de buster) cuenta como ausente,
    y entonces se usa sox."""
    path = shutil.which(tool)
    if not path:
        return False
    if tool != "ffmpeg":
        return True
    try:
        mt = os.path.getmtime(path)
    except OSError:
        mt = 0
    if _WORKS.get(path, (None, None))[0] != mt:
        try:
            ok = subprocess.run([path, "-version"], stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL, timeout=15).returncode == 0
        except Exception:
            ok = False
        if not ok:
            log.warning("ffmpeg está instalado pero no arranca (¿faltan librerías?); uso sox")
        _WORKS[path] = (mt, ok)
    return _WORKS[path][1]


def tools():
    return {t: have(t) for t in ("ffmpeg", "sox", "mpg123")}


def formats():
    """Extensiones que este nodo puede leer."""
    if have("ffmpeg"):
        return [".mp3", ".wav", ".m4a", ".ogg", ".flac", ".aac", ".opus", ".wma", ".gsm", ".ul"]
    f = [".wav", ".ogg", ".flac", ".gsm", ".ul", ".aiff"] if have("sox") else [".wav"]
    if have("mpg123"):
        f.insert(0, ".mp3")
    return f


def can_play_in_browser(path):
    return Path(path).suffix.lower() in (".mp3", ".wav", ".ogg", ".m4a", ".opus", ".flac", ".aac")


# ── Lectura de duración ──────────────────────────────────────────────────────
def wav_duration(path):
    try:
        with wave.open(str(path), "rb") as w:
            return w.getnframes() / float(w.getframerate())
    except Exception:
        return 0.0


def duration(path):
    """Duración en segundos de cualquier archivo de audio."""
    p = Path(path)
    if not p.is_file():
        return 0.0
    if p.suffix.lower() == ".wav":
        d = wav_duration(p)
        if d > 0:
            return d
    if have("ffprobe"):
        try:
            r = _run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                      "-of", "default=nw=1:nk=1", p], 60)
            return float(r.stdout.decode().strip() or 0)
        except Exception:
            pass
    try:   # sin ffprobe: convertir (queda en caché para cuando salga al aire)
        return wav_duration(prepare(p, None))
    except Exception as e:
        log.warning("No pude leer la duración de %s: %s", p.name, e)
        return 0.0


# ── Conversión y nivel ───────────────────────────────────────────────────────
def _to_8k_ffmpeg(src, out, gain_db=None, rate=RATE):
    af = "aformat=channel_layouts=mono"
    if gain_db is not None:
        limit = 10 ** (PEAK_LIMIT_DB / 20)
        af += (",volume={:.2f}dB,alimiter=limit={:.4f}:attack=5:release=50:level=disabled"
               .format(gain_db, limit))
    r = _run(["ffmpeg", "-hide_banner", "-nostats", "-y", "-i", src, "-af", af,
              "-ar", str(rate), "-ac", "1", "-sample_fmt", "s16", "-f", "wav", out])
    if r.returncode != 0:
        raise RuntimeError("ffmpeg no pudo convertir {}: {}".format(
            Path(src).name, r.stderr.decode(errors="ignore")[-300:]))


def _lufs_ffmpeg(src):
    """Sonoridad integrada (EBU R128) en mono. Se usa el filtro ebur128: da el
    mismo valor que loudnorm pero sin el cálculo de picos reales a 192 kHz,
    unas 7 veces más rápido (17 min de audio: ~1 min en una Pi 3 en vez de 7)."""
    r = _run(["ffmpeg", "-hide_banner", "-nostats", "-i", src, "-af",
              "aformat=channel_layouts=mono,ebur128=framelog=quiet", "-f", "null", "-"])
    txt = r.stderr.decode(errors="ignore")
    i = txt.rfind("Integrated loudness:")
    m = re.search(r"I:\s*(-?[\d.]+)\s*LUFS", txt[i:] if i >= 0 else txt)
    if m:
        v = float(m.group(1))
        return v if v > -70 else None
    # Respaldo: ffmpeg muy viejo sin ebur128
    r = _run(["ffmpeg", "-hide_banner", "-nostats", "-i", src, "-af",
              "aformat=channel_layouts=mono,loudnorm=print_format=json", "-f", "null", "-"])
    txt = r.stderr.decode(errors="ignore")
    a, b = txt.rfind("{"), txt.rfind("}")
    try:
        v = float(json.loads(txt[a:b + 1])["input_i"])
        return v if v > -70 else None
    except Exception:
        return None


def _to_8k_sox(src, out, gain_db=None, rate=RATE):
    src = Path(src)
    tmp = None
    if src.suffix.lower() == ".mp3":
        if not have("mpg123"):
            raise RuntimeError("No hay con qué leer MP3 en este nodo (falta mpg123 o ffmpeg)")
        tmp = paths.tmp_dir() / ("dec_" + uuid.uuid4().hex + ".wav")
        r = _run(["mpg123", "-q", "-w", tmp, src])
        if r.returncode != 0 or not tmp.is_file():
            paths.rm(tmp)
            raise RuntimeError("mpg123 no pudo leer {}: {}".format(
                src.name, r.stderr.decode(errors="ignore")[-200:]))
        src = tmp
    elif src.suffix.lower() == ".ul":
        src = ["-t", "ul", "-r", "8000", "-c", "1", src]
    try:
        cmd = ["sox", "-V1"] + (src if isinstance(src, list) else [src]) + \
              ["-r", str(rate), "-c", "1", "-b", "16", "-e", "signed-integer", out]
        if gain_db is not None:
            # limitador de sox a 0 dBFS y luego bajar 2 dB = ganancia exacta con techo en -2 dB
            cmd += ["gain", "-l", "{:.2f}".format(gain_db - PEAK_LIMIT_DB),
                    "gain", "{:.1f}".format(PEAK_LIMIT_DB)]
        r = _run(cmd)
        if r.returncode != 0:
            raise RuntimeError("sox no pudo convertir: " + r.stderr.decode(errors="ignore")[-300:])
    finally:
        if tmp:
            paths.rm(tmp)


def _lufs_sox(wav8k):
    """Aproximación de LUFS: filtro de ponderación K (paso alto 38 Hz + realce
    de agudos) y RMS sin compuertas. Para voz da unos 1-2 dB de diferencia."""
    r = _run(["sox", "-V1", wav8k, "-n", "highpass", "38", "treble", "4", "1681", "0.707q", "stats"])
    m = re.search(r"RMS lev dB\s+(-?[\d.]+)", r.stderr.decode(errors="ignore"))
    if not m:
        return None
    v = float(m.group(1)) - 0.691
    return v if v > -70 else None


AIRE_SUFFIX = ".aire.wav"


def is_aire(p):
    """Archivo ya convertido para el aire (cuando no se guardan los originales)."""
    return Path(p).name.endswith(AIRE_SUFFIX)


def _cache_path(src, tag):
    st = src.stat()
    key = hashlib.sha1("{}|{}|{}|{}|{}".format(src.resolve(), st.st_size, st.st_mtime, tag,
                                               CACHE_VERSION).encode()).hexdigest()[:16]
    return paths.cache_dir() / "{}_{}.wav".format(re.sub(r"[^\w-]", "_", src.stem)[:40], key)


def compact(src, target_lufs):
    """Convierte src al formato del aire, lo deja junto al original con
    terminación .aire.wav y borra el original y sus copias en caché.
    Devuelve (ruta nueva, bytes liberados)."""
    src = Path(src)
    if is_aire(src):
        return src, 0
    prep = prepare(src, target_lufs)
    raw = _cache_path(src, "raw")
    dest = src.with_name(src.stem[:60] + AIRE_SUFFIX)
    shutil.copyfile(str(prep), str(dest))
    freed = -dest.stat().st_size
    for f in {prep, raw, src}:
        if f.is_file():
            freed += f.stat().st_size
            paths.rm(f)
    log.info("Original %s reemplazado por %s", src.name, dest.name)
    return dest, freed


def prepare(src, target_lufs):
    """Devuelve un WAV 8 kHz mono listo para el aire (cacheado).
    target_lufs=None → solo convierte, sin normalizar."""
    src = Path(src)
    if not src.is_file():
        raise FileNotFoundError("No existe el audio " + src.name)
    if is_aire(src):
        return src                            # ya convertido al subirlo
    tag = "raw" if target_lufs is None else "{:.1f}".format(target_lufs)
    out = _cache_path(src, tag)
    with _lock_for(str(out)):
        if out.is_file() and out.stat().st_size > 44:
            os.utime(str(out), None)          # marca de uso para la limpieza
            return out
        t0 = time.time()
        tmp = out.with_name(out.stem + ".part.wav")
        try:
            if have("ffmpeg"):
                gain = None
                if target_lufs is not None:
                    cur = _lufs_ffmpeg(src)
                    if cur is None:
                        log.warning("No pude medir el nivel de %s; solo se convierte", src.name)
                    else:
                        gain = min(target_lufs - cur, 20.0)
                _to_8k_ffmpeg(src, tmp, gain)
            elif have("sox"):
                if target_lufs is None:
                    _to_8k_sox(src, tmp)
                else:
                    raw = prepare(src, None)
                    cur = _lufs_sox(raw)
                    if cur is None:
                        shutil.copyfile(str(raw), str(tmp))
                    else:
                        gain = min(target_lufs - cur, 20.0)
                        _to_8k_sox(raw, tmp, gain)
                        # El limitador le quita nivel a la voz con picos altos:
                        # medir otra vez y compensar lo que falte
                        got = _lufs_sox(tmp)
                        if got is not None and abs(target_lufs - got) > 0.5:
                            gain = min(gain + (target_lufs - got) * 1.2, 24.0)
                            _to_8k_sox(raw, tmp, gain)
            else:
                raise RuntimeError("Este nodo no tiene ffmpeg ni sox para convertir audio")
            if not tmp.is_file() or tmp.stat().st_size <= 44:
                raise RuntimeError("La conversión de {} no produjo audio".format(src.name))
            os.replace(str(tmp), str(out))
        finally:
            paths.rm(tmp)
        log.info("Audio preparado %s → %s (%.1f s, objetivo %s)",
                 src.name, out.name, time.time() - t0, tag)
        return out


# ── Operaciones sobre WAV 8 kHz mono ─────────────────────────────────────────
def read_samples(path):
    with wave.open(str(path), "rb") as w:
        if w.getframerate() != RATE or w.getnchannels() != 1 or w.getsampwidth() != 2:
            raise ValueError("{} no es WAV 8 kHz mono 16 bits".format(Path(path).name))
        data = w.readframes(w.getnframes())
    a = array.array("h")
    a.frombytes(data)
    if sys.byteorder == "big":
        a.byteswap()
    return a


def write_samples(path, a):
    if sys.byteorder == "big":
        a = array.array("h", a)
        a.byteswap()
    path = Path(path)
    tmp = path.with_name(path.stem + ".part.wav")
    w = wave.open(str(tmp), "wb")
    try:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(a.tobytes())
    finally:
        w.close()
    os.replace(str(tmp), str(path))


def silence(seconds):
    return array.array("h", bytes(2 * max(0, int(seconds * RATE))))


def mix_into(base, over, at_sample):
    """Suma *over* sobre *base* desde at_sample, con recorte."""
    at_sample = max(0, at_sample)
    n = min(len(over), len(base) - at_sample)
    for i in range(n):
        v = base[at_sample + i] + over[i]
        base[at_sample + i] = 32767 if v > 32767 else (-32768 if v < -32768 else v)


def build_segment(body, start, end, out, lead=0.0, pre=(), post=(),
                  alert=None, alert_before=0.0):
    """Arma el archivo de un tramo al aire:
        [silencio PTT] + [anuncio de regreso] + cuerpo[start:end] + [anuncio de pausa]
    con la alerta mezclada *alert_before* segundos antes del final del cuerpo.
    Devuelve los tiempos (s) para mostrar el avance en la interfaz."""
    src = read_samples(body)
    a = silence(lead)
    pre_len = 0.0
    for p in pre:
        s = read_samples(p)
        a.extend(s)
        pre_len += len(s) / float(RATE)
    body_start = len(a)
    chunk = src[int(start * RATE):int(end * RATE)]
    a.extend(chunk)
    body_len = len(chunk) / float(RATE)
    if alert is not None and alert_before > 0:
        al = read_samples(alert)
        at = body_start + len(chunk) - int(alert_before * RATE)
        mix_into(a, al, max(body_start, at))
    for p in post:
        a.extend(read_samples(p))
    write_samples(out, a)
    return {"total": len(a) / float(RATE), "body_offset": lead + pre_len, "body_len": body_len}


def cleanup(max_age_days=21):
    """Borra tramos viejos y caché sin uso."""
    now = time.time()
    for f in paths.tmp_dir().glob("*"):
        try:
            if f.is_file() and now - f.stat().st_mtime > 6 * 3600:
                paths.rm(f)
        except OSError:
            pass
    for f in paths.cache_dir().glob("*.wav"):
        try:
            if now - f.stat().st_mtime > max_age_days * 86400:
                paths.rm(f)
        except OSError:
            pass
