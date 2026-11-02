"""
HAMNA Web — audio.

Todo lo que sale al aire se convierte a WAV 8 kHz, 16 bits, mono: es el
formato nativo de Asterisk (rpt localplay) y también sirve para aplay en
IRLP. Con un solo formato, cortar, pegar y mezclar se hace en Python con el
módulo wave, sin volver a llamar a ffmpeg.
"""
from __future__ import annotations

import array
import hashlib
import json
import logging
import os
import subprocess
import sys
import threading
import time
import wave
from pathlib import Path

from . import paths

log = logging.getLogger("hamna.audio")

RATE = 8000
CACHE_VERSION = "v1"
PEAK_LIMIT_DB = -2.0
_locks: dict[str, threading.Lock] = {}
_locks_guard = threading.Lock()


def _lock_for(key: str) -> threading.Lock:
    with _locks_guard:
        return _locks.setdefault(key, threading.Lock())


def _run(cmd: list[str], timeout=600) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          timeout=timeout)


def ffmpeg_ok() -> bool:
    try:
        return _run(["ffmpeg", "-version"], 15).returncode == 0
    except Exception:
        return False


def duration(path: str | Path) -> float:
    """Duración en segundos de cualquier archivo de audio."""
    p = Path(path)
    if not p.is_file():
        return 0.0
    if p.suffix.lower() == ".wav":
        try:
            with wave.open(str(p), "rb") as w:
                return w.getnframes() / float(w.getframerate())
        except Exception:
            pass
    try:
        r = _run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                  "-of", "default=nw=1:nk=1", str(p)], 60)
        return float(r.stdout.decode().strip() or 0)
    except Exception:
        return 0.0


def _measure_loudness(src: Path) -> dict | None:
    """Primera pasada de loudnorm: mide en mono, como sale al aire."""
    r = _run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(src),
              "-af", "aformat=channel_layouts=mono,loudnorm=print_format=json",
              "-f", "null", "-"])
    txt = r.stderr.decode(errors="ignore")
    start = txt.rfind("{")
    end = txt.rfind("}")
    if start < 0 or end < start:
        return None
    try:
        return json.loads(txt[start:end + 1])
    except Exception:
        return None


def prepare(src: str | Path, target_lufs: float | None) -> Path:
    """Devuelve un WAV 8 kHz mono listo para el aire (cacheado).
    target_lufs=None → solo convierte, sin normalizar."""
    src = Path(src)
    if not src.is_file():
        raise FileNotFoundError(str(src))
    st = src.stat()
    tag = "raw" if target_lufs is None else f"{target_lufs:.1f}"
    key = hashlib.sha1(f"{src.resolve()}|{st.st_size}|{st.st_mtime}|{tag}|{CACHE_VERSION}"
                       .encode()).hexdigest()[:16]
    out = paths.cache_dir() / f"{src.stem[:40]}_{key}.wav"
    with _lock_for(str(out)):
        if out.is_file() and out.stat().st_size > 44:
            os.utime(out, None)       # marca de uso para la limpieza
            return out
        t0 = time.time()
        tmp = out.with_suffix(".part.wav")
        afilter = "aformat=channel_layouts=mono"
        if target_lufs is not None:
            m = _measure_loudness(src)
            if m and m.get("input_i") not in (None, "-inf") and float(m["input_i"]) > -70:
                # Ganancia lineal (no cambia la dinámica) + limitador de picos
                gain = min(target_lufs - float(m["input_i"]), 20.0)
                limit = 10 ** (PEAK_LIMIT_DB / 20)
                afilter += (f",volume={gain:.2f}dB"
                            f",alimiter=limit={limit:.4f}:attack=5:release=50:level=disabled")
            else:
                log.warning("No se pudo medir el nivel de %s; solo se convierte", src.name)
        cmd = ["ffmpeg", "-hide_banner", "-nostats", "-y", "-i", str(src),
               "-af", afilter, "-ar", str(RATE), "-ac", "1",
               "-sample_fmt", "s16", "-f", "wav", str(tmp)]
        r = _run(cmd)
        if r.returncode != 0 or not tmp.is_file():
            err = r.stderr.decode(errors="ignore")[-400:]
            raise RuntimeError(f"ffmpeg no pudo convertir {src.name}: {err}")
        os.replace(tmp, out)
        log.info("Audio preparado %s → %s (%.1f s, objetivo %s)",
                 src.name, out.name, time.time() - t0, tag)
        return out


# ── Operaciones sobre WAV 8 kHz mono ─────────────────────────────────────────
def read_samples(path: Path) -> array.array:
    with wave.open(str(path), "rb") as w:
        if w.getframerate() != RATE or w.getnchannels() != 1 or w.getsampwidth() != 2:
            raise ValueError(f"{path.name} no es WAV 8 kHz mono 16 bits")
        data = w.readframes(w.getnframes())
    a = array.array("h")
    a.frombytes(data)
    if sys.byteorder == "big":
        a.byteswap()
    return a


def write_samples(path: Path, a: array.array) -> None:
    if sys.byteorder == "big":
        a = array.array("h", a)
        a.byteswap()
    tmp = path.with_suffix(".part.wav")
    with wave.open(str(tmp), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(a.tobytes())
    os.replace(tmp, path)


def silence(seconds: float) -> array.array:
    return array.array("h", bytes(2 * max(0, int(seconds * RATE))))


def mix_into(base: array.array, over: array.array, at_sample: int) -> None:
    """Suma *over* sobre *base* desde at_sample, con recorte."""
    at_sample = max(0, at_sample)
    n = min(len(over), len(base) - at_sample)
    for i in range(n):
        v = base[at_sample + i] + over[i]
        base[at_sample + i] = 32767 if v > 32767 else (-32768 if v < -32768 else v)


def build_segment(body: Path, start: float, end: float, out: Path,
                  lead: float = 0.0, pre: list[Path] = (), post: list[Path] = (),
                  alert: Path | None = None, alert_before: float = 0.0) -> dict:
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
        pre_len += len(s) / RATE
    body_start = len(a)
    chunk = src[int(start * RATE):int(end * RATE)]
    a.extend(chunk)
    body_len = len(chunk) / RATE
    if alert is not None and alert_before > 0:
        al = read_samples(alert)
        at = body_start + len(chunk) - int(alert_before * RATE)
        mix_into(a, al, max(body_start, at))
    for p in post:
        a.extend(read_samples(p))
    write_samples(out, a)
    return {"total": len(a) / RATE, "body_offset": lead + pre_len, "body_len": body_len}


def cleanup(max_age_days: int = 21) -> None:
    """Borra tramos viejos y caché sin uso."""
    now = time.time()
    for f in paths.tmp_dir().glob("*"):
        if f.is_file() and now - f.stat().st_mtime > 6 * 3600:
            f.unlink(missing_ok=True)
    for f in paths.cache_dir().glob("*.wav"):
        if now - f.stat().st_mtime > max_age_days * 86400:
            f.unlink(missing_ok=True)


def to_mp3_preview(src: Path) -> Path:
    """Versión ligera para escuchar en el navegador (no para el aire)."""
    out = paths.tmp_dir() / f"prev_{hashlib.sha1(str(src).encode()).hexdigest()[:10]}.mp3"
    r = _run(["ffmpeg", "-hide_banner", "-nostats", "-y", "-i", str(src),
              "-ac", "1", "-b:a", "64k", str(out)])
    if r.returncode != 0:
        raise RuntimeError("No se pudo convertir para escuchar")
    return out
