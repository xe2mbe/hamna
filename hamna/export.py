"""
HAMNA Web — exportar secciones de un evento a un solo archivo.

Igual que en HAMNA Desktop: se eligen y ordenan las secciones, se pone un
silencio entre ellas, opcionalmente se nivelan y sale un MP3 o un WAV para
descargar. Corre en segundo plano (en una Pi 3 un boletín largo tarda unos
minutos) y la página consulta el avance.

Calidad: si hay audios originales se exporta a 44.1 kHz mono; si todas las
secciones están solo en la versión del aire (8 kHz) se exporta a 8 kHz, porque
subirle la frecuencia no le devuelve calidad y solo hace el archivo más grande.
"""
import datetime as dt
import logging
import re
import shutil
import subprocess
import threading
import time
import uuid
import wave
from pathlib import Path

from . import audio, db, paths

log = logging.getLogger("hamna.exportar")

HI_RATE = 44100
JOB_TTL = 6 * 3600          # el archivo se queda 6 h (audio.cleanup borra tmp/ igual)
_jobs = {}
_lock = threading.Lock()
_busy = threading.Lock()    # una exportación a la vez: es trabajo pesado para una Pi


def _sox_mp3():
    if not audio.have("sox"):
        return False
    try:
        r = subprocess.run(["sox", "-h"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=10)
        m = re.search(r"AUDIO FILE FORMATS:(.*)", r.stdout.decode(errors="ignore"))
        return bool(m and re.search(r"\bmp3\b", m.group(1)))
    except Exception:
        return False


def formats():
    """Formatos que este nodo puede escribir."""
    out = []
    if audio.have("ffmpeg") or shutil.which("lame") or _sox_mp3():
        out.append("mp3")
    out.append("wav")
    return out


def _file_of(sec):
    name = sec.get("ruta_archivo") or ""
    if not name:
        return None
    p = Path(name)
    if not p.is_absolute():
        p = paths.audios_dir() / name
    return p if p.is_file() else None


def _prune():
    now = time.time()
    with _lock:
        for k in [k for k, j in _jobs.items() if now - j["t"] > JOB_TTL]:
            j = _jobs.pop(k)
            if j.get("archivo"):
                paths.rm(j["archivo"])


def safe_filename(name):
    name = re.sub(r'[\\/:*?"<>|\x00-\x1f]+', "_", name or "").strip(" .")
    return name[:80] or "evento"


def start(evento_id, sec_ids, silencio=5.0, formato="mp3", normalizar=False,
          objetivo=-18.0, usuario="-"):
    ev = db.get_evento(evento_id)
    if not ev:
        raise ValueError("El evento no existe")
    if formato not in formats():
        raise ValueError("Este nodo no puede crear archivos {}; elige WAV".format(formato.upper())
                         if formato == "mp3" else "Formato inválido")
    del_evento = {s["id"]: dict(s) for s in db.get_secciones_by_evento(evento_id)}
    secs = []
    for sid in sec_ids:
        s = del_evento.get(int(sid))
        if s is None:
            raise ValueError("Una de las secciones ya no está en el evento; recarga la página")
        secs.append(s)
    if not secs:
        raise ValueError("Selecciona al menos una sección")
    silencio = max(0.0, min(float(silencio), 60.0))
    objetivo = max(-40.0, min(float(objetivo), -6.0))
    if _busy.locked():
        raise ValueError("Ya hay una exportación en curso; espera a que termine")
    _prune()
    jid = "x" + uuid.uuid4().hex[:16]     # con letra: el enrutador convierte a int lo que es solo dígitos
    fecha = dt.datetime.now().strftime("%Y-%m-%d")
    job = {"id": jid, "estado": "trabajando", "paso": 0, "total": len(secs) + 1,
           "mensaje": "Preparando…", "error": "", "archivo": None, "omitidas": [],
           "nombre": "{} {}.{}".format(safe_filename(ev["nombre"]), fecha, formato),
           "duracion": 0.0, "tamano": 0, "usuario": usuario, "t": time.time()}
    with _lock:
        _jobs[jid] = job
    threading.Thread(target=_work, args=(job, secs, silencio, formato, normalizar, objetivo),
                     daemon=True).start()
    log.info("%s exporta «%s» (%d secciones, %s)", usuario, ev["nombre"], len(secs), formato)
    return jid


def get(jid):
    with _lock:
        j = _jobs.get(jid)
        if not j:
            return None
        out = {k: v for k, v in j.items() if k not in ("archivo", "t")}
    return out


def file_of(jid):
    with _lock:
        j = _jobs.get(jid)
    if not j or j["estado"] != "listo" or not j.get("archivo") or not Path(j["archivo"]).is_file():
        return None, None
    return j["archivo"], j["nombre"]


def _upd(job, **kw):
    with _lock:
        job.update(kw)


def _convert(src, out, rate, objetivo):
    """Una sección → WAV mono 16 bits a *rate*, nivelada si objetivo no es None."""
    if audio.have("ffmpeg"):
        gain = None
        if objetivo is not None:
            cur = audio._lufs_ffmpeg(src)
            if cur is not None:
                gain = min(objetivo - cur, 20.0)
        audio._to_8k_ffmpeg(src, out, gain, rate)
    elif audio.have("sox"):
        if objetivo is None:
            audio._to_8k_sox(src, out, None, rate)
        else:
            raw = out.with_name(out.stem + ".raw.wav")
            try:
                audio._to_8k_sox(src, raw, None, rate)
                cur = audio._lufs_sox(raw)
                if cur is None:
                    shutil.move(str(raw), str(out))
                else:
                    audio._to_8k_sox(raw, out, min(objetivo - cur, 20.0), rate)
            finally:
                paths.rm(raw)
    elif Path(src).suffix.lower() == ".wav" and rate == audio.RATE and audio.is_aire(src):
        shutil.copyfile(str(src), str(out))
    else:
        raise RuntimeError("Este nodo no tiene ffmpeg ni sox para convertir audio")


def _append(w, path, rate):
    with wave.open(str(path), "rb") as r:
        if r.getframerate() != rate or r.getnchannels() != 1 or r.getsampwidth() != 2:
            raise RuntimeError("Formato inesperado al unir {}".format(Path(path).name))
        n = r.getnframes()
        while n > 0:
            data = r.readframes(min(n, 65536))
            if not data:
                break
            w.writeframes(data)
            n -= len(data) // 2
        return r.getnframes() / float(rate)


def _encode_mp3(wav, out, rate):
    br = "32k" if rate <= 8000 else "128k"
    if audio.have("ffmpeg"):
        cmd = ["ffmpeg", "-hide_banner", "-nostats", "-y", "-i", wav,
               "-codec:a", "libmp3lame", "-b:a", br, "-f", "mp3", out]
    elif shutil.which("lame"):
        cmd = ["lame", "--quiet", "-b", br[:-1], wav, out]
    else:
        cmd = ["sox", "-V1", wav, "-C", br[:-1], out]
    r = audio._run(cmd, timeout=3600)
    if r.returncode != 0 or not Path(out).is_file():
        raise RuntimeError("No se pudo crear el MP3: " + r.stderr.decode(errors="ignore")[-300:])


def _work(job, secs, silencio, formato, normalizar, objetivo):
    with _busy:
        tmp = paths.tmp_dir()
        parts, wav, final = [], tmp / "export_{}.wav".format(job["id"]), None
        try:
            fuentes = []
            for s in secs:
                p = _file_of(s)
                if p:
                    fuentes.append((s, p))
                else:
                    job["omitidas"].append(s["nombre"])
            if not fuentes:
                raise RuntimeError("Ninguna de las secciones elegidas tiene audio")
            rate = audio.RATE if all(audio.is_aire(p) for _, p in fuentes) else HI_RATE
            total = len(fuentes) + 1
            _upd(job, total=total)
            for i, (s, p) in enumerate(fuentes):
                _upd(job, paso=i, mensaje="({}/{}) {}{}".format(
                    i + 1, len(fuentes), s["nombre"], " — nivelando…" if normalizar else ""))
                out = tmp / "export_{}_{:03d}.wav".format(job["id"], i)
                parts.append(out)
                _convert(p, out, rate, objetivo if normalizar else None)
            _upd(job, paso=len(fuentes), mensaje="Uniendo las secciones…")
            gap = bytes(2 * int(silencio * rate))
            dur = 0.0
            w = wave.open(str(wav), "wb")
            try:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(rate)
                for i, part in enumerate(parts):
                    if i:
                        w.writeframes(gap)
                        dur += silencio
                    dur += _append(w, part, rate)
                    paths.rm(part)
            finally:
                w.close()
            if formato == "mp3":
                _upd(job, mensaje="Creando el MP3…")
                final = tmp / "export_{}.mp3".format(job["id"])
                _encode_mp3(wav, final, rate)
                paths.rm(wav)
            else:
                final = wav
            _upd(job, estado="listo", paso=total, archivo=str(final), duracion=round(dur, 1),
                 tamano=Path(final).stat().st_size, mensaje="Listo", t=time.time())
            log.info("Exportación lista: %s (%.0f s, %.1f MB, %d Hz)", job["nombre"], dur,
                     job["tamano"] / 2.0**20, rate)
        except Exception as e:
            log.warning("La exportación falló: %s", e)
            _upd(job, estado="error", error=str(e), mensaje="Error")
            for f in parts + [wav] + ([final] if final else []):
                paths.rm(f)
        finally:
            for f in parts:
                paths.rm(f)
