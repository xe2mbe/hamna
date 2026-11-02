"""
HAMNA Web — síntesis de voz.

Motores:
  azure   Azure Speech por REST (voces neuronales; requiere internet y clave)
  espeak  espeak-ng local (sin internet; voz robótica)
  piper   asl-tts de AllStarLink (Piper, voz neuronal local) si está instalado
"""
from __future__ import annotations

import datetime
import html
import logging
import shutil
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

log = logging.getLogger("hamna.tts")

DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]

VARIABLES = [
    ("{fecha}", "Fecha actual (dd/mm/aaaa)"),
    ("{fecha_larga}", "Fecha en palabras (2 de noviembre de 2026)"),
    ("{hora}", "Hora actual (HH:MM)"),
    ("{dia}", "Día de la semana"),
    ("{pausa_cada}", "Intervalo de pausa configurado"),
    ("{pausa_duracion}", "Duración de la pausa"),
    ("{pausa_alerta}", "Aviso antes de la pausa"),
    ("{evento}", "Nombre del evento"),
    ("{numero}", "Número de edición del evento"),
    ("{num_secciones}", "Secciones contabilizables del evento"),
    ("{duracion_total}", "Duración total del evento"),
    ("{dur_contabilizable}", "Duración de las secciones contabilizables"),
    ("{titulo}", "Título de la sección"),
    ("{descripcion}", "Descripción de la sección"),
    ("{nodo}", "Número de nodo"),
]


def fmt_seg(s) -> str:
    s = int(float(s or 0))
    if s < 60:
        return f"{s} segundo{'s' if s != 1 else ''}"
    m, r = divmod(s, 60)
    mins = f"{m} minuto{'s' if m != 1 else ''}"
    return mins if r == 0 else f"{mins} con {r} segundo{'s' if r != 1 else ''}"


def resolve_variables(text: str, cfg: dict, ctx: dict | None = None) -> str:
    now = datetime.datetime.now()
    ctx = ctx or {}
    rep = {
        "{fecha}": now.strftime("%d/%m/%Y"),
        "{fecha_larga}": f"{now.day} de {MESES[now.month - 1]} de {now.year}",
        "{hora}": now.strftime("%H:%M"),
        "{dia}": DIAS[now.weekday()],
        "{pausa_cada}": fmt_seg(cfg.get("pause_tx_time", 160)),
        "{pausa_duracion}": fmt_seg(cfg.get("pause_duration", 10)),
        "{pausa_alerta}": fmt_seg(cfg.get("pause_alert_before", 10)),
        "{nodo}": " ".join(str(cfg.get("node", ""))),
    }
    for k in ("titulo", "descripcion", "evento", "numero", "num_secciones",
              "duracion_total", "dur_contabilizable"):
        rep["{" + k + "}"] = str(ctx.get(k, "") or "")
    for token, value in rep.items():
        text = text.replace(token, value)
    return text


def event_context(evento: dict | None, secs: list[dict]) -> dict:
    if not evento:
        return {}
    dur_t = sum(float(s.get("duracion") or 0) for s in secs)
    cont = [s for s in secs if s.get("contabilizable", 1)]
    return {
        "evento": evento.get("nombre", ""),
        "numero": evento.get("numero") or "",
        "num_secciones": str(len(cont)),
        "duracion_total": fmt_seg(dur_t),
        "dur_contabilizable": fmt_seg(sum(float(s.get("duracion") or 0) for s in cont)),
    }


# ── Motores ───────────────────────────────────────────────────────────────────
def _azure(text: str, cfg: dict, out: Path) -> Path:
    key = (cfg.get("azure_key") or "").strip()
    region = (cfg.get("azure_region") or "").strip()
    if not key or not region:
        raise RuntimeError("Falta la clave o la región de Azure (Ajustes → Voz)")
    voice = cfg.get("azure_voice") or "es-MX-DaliaNeural"
    style = cfg.get("azure_style") or "general"
    rate = int(cfg.get("azure_rate", 100))
    pitch = int(cfg.get("azure_pitch", 0))
    locale = voice[:5] if len(voice) >= 5 else "es-MX"
    rate_str = f"+{rate - 100}%" if rate >= 100 else f"-{100 - rate}%"
    pitch_str = f"+{pitch}Hz" if pitch >= 0 else f"{pitch}Hz"
    body = (f'<prosody rate="{rate_str}" pitch="{pitch_str}">'
            f'{html.escape(text)}</prosody>')
    if style and style != "general":
        body = f'<mstts:express-as style="{style}">{body}</mstts:express-as>'
    ssml = (f'<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" '
            f'xmlns:mstts="http://www.w3.org/2001/mstts" xml:lang="{locale}">'
            f'<voice name="{voice}">{body}</voice></speak>')
    req = urllib.request.Request(
        f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1",
        data=ssml.encode("utf-8"), method="POST",
        headers={"Ocp-Apim-Subscription-Key": key,
                 "Content-Type": "application/ssml+xml",
                 "X-Microsoft-OutputFormat": "audio-24khz-160kbitrate-mono-mp3",
                 "User-Agent": "HAMNA-Web/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = r.read()
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Azure HTTP {e.code}: {e.read().decode(errors='ignore')[:200]}")
    out = out.with_suffix(".mp3")
    out.write_bytes(data)
    return out


def _espeak(text: str, cfg: dict, out: Path) -> Path:
    exe = shutil.which("espeak-ng") or shutil.which("espeak")
    if not exe:
        raise RuntimeError("espeak-ng no está instalado (apt install espeak-ng)")
    out = out.with_suffix(".wav")
    r = subprocess.run([exe, "-v", str(cfg.get("espeak_voice") or "es-419"),
                        "-s", str(int(cfg.get("espeak_speed", 150))),
                        "-p", str(int(cfg.get("espeak_pitch", 50))),
                        "-w", str(out), text],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=180)
    if r.returncode != 0 or not out.is_file():
        raise RuntimeError("espeak-ng falló: " + r.stderr.decode(errors="ignore")[:200])
    return out


def piper_available() -> bool:
    return bool(shutil.which("asl-tts"))


def _piper(text: str, cfg: dict, out: Path) -> Path:
    exe = shutil.which("asl-tts")
    if not exe:
        raise RuntimeError("asl-tts (Piper) no está instalado: apt install asl3-tts")
    # asl-tts -f guarda el archivo en vez de reproducirlo; agrega la extensión .ul
    base = out.with_suffix("")
    r = subprocess.run([exe, "-n", str(cfg.get("node") or "0"), "-t", text,
                        "-f", str(base)],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=300)
    for ext in (".ul", ".ulaw", ".wav", ".gsm", ""):
        cand = Path(str(base) + ext)
        if cand.is_file() and cand.stat().st_size > 0:
            if ext in (".ul", ".ulaw"):
                # μ-law crudo a 8 kHz: convertir a WAV para que ffmpeg lo lea
                wav = out.with_suffix(".wav")
                subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                                "-f", "mulaw", "-ar", "8000", "-ac", "1", "-i", str(cand),
                                str(wav)], timeout=120)
                cand.unlink(missing_ok=True)
                return wav
            return cand
    raise RuntimeError("asl-tts no generó audio: " + r.stderr.decode(errors="ignore")[:200])


def synthesize(text: str, cfg: dict, out: Path, ctx: dict | None = None) -> Path:
    """Sintetiza *text* (con variables resueltas). Devuelve la ruta creada;
    la extensión depende del motor."""
    resolved = resolve_variables(text, cfg, ctx)
    engine = cfg.get("tts_engine", "espeak")
    log.info("TTS %s: %s", engine, resolved[:80].replace("\n", " "))
    out.parent.mkdir(parents=True, exist_ok=True)
    if engine == "azure":
        return _azure(resolved, cfg, out)
    if engine == "piper":
        return _piper(resolved, cfg, out)
    return _espeak(resolved, cfg, out)


def azure_voices(key: str, region: str) -> list[dict]:
    import json
    req = urllib.request.Request(
        f"https://{region}.tts.speech.microsoft.com/cognitiveservices/voices/list",
        headers={"Ocp-Apim-Subscription-Key": key})
    with urllib.request.urlopen(req, timeout=15) as r:
        data = json.loads(r.read())
    return [{"name": v["ShortName"], "display": v.get("LocalName", v["ShortName"]),
             "locale": v["Locale"], "gender": v.get("Gender", ""),
             "styles": v.get("StyleList", [])}
            for v in data if v.get("Locale", "").startswith("es")]
