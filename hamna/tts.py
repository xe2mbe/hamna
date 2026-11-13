"""
HAMNA Web — síntesis de voz.

Motores:
  azure   Azure Speech por REST (voces neuronales; requiere internet y clave)
  piper   asl-tts de AllStarLink (Piper, voz neuronal local) si está instalado
  espeak  espeak-ng local (sin internet; voz sintética)
"""
import datetime
import html
import json
import logging
import shutil
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

from . import paths

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


def fmt_seg(s):
    s = int(float(s or 0))
    if s < 60:
        return "{} segundo{}".format(s, "" if s == 1 else "s")
    m, r = divmod(s, 60)
    mins = "{} minuto{}".format(m, "" if m == 1 else "s")
    return mins if r == 0 else "{} con {} segundo{}".format(mins, r, "" if r == 1 else "s")


def resolve_variables(text, cfg, ctx=None):
    now = datetime.datetime.now()
    ctx = ctx or {}
    rep = {
        "{fecha}": now.strftime("%d/%m/%Y"),
        "{fecha_larga}": "{} de {} de {}".format(now.day, MESES[now.month - 1], now.year),
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


def event_context(evento, secs):
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
def _azure(text, cfg, out):
    key = (cfg.get("azure_key") or "").strip()
    region = (cfg.get("azure_region") or "").strip()
    if not key or not region:
        raise RuntimeError("Falta la clave o la región de Azure (Ajustes → Voz)")
    voice = cfg.get("azure_voice") or "es-MX-DaliaNeural"
    style = cfg.get("azure_style") or "general"
    rate = int(cfg.get("azure_rate", 100))
    pitch = int(cfg.get("azure_pitch", 0))
    locale = voice[:5] if len(voice) >= 5 else "es-MX"
    rate_str = "+{}%".format(rate - 100) if rate >= 100 else "-{}%".format(100 - rate)
    pitch_str = "+{}Hz".format(pitch) if pitch >= 0 else "{}Hz".format(pitch)
    body = '<prosody rate="{}" pitch="{}">{}</prosody>'.format(rate_str, pitch_str, html.escape(text))
    if style and style != "general":
        body = '<mstts:express-as style="{}">{}</mstts:express-as>'.format(style, body)
    ssml = ('<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" '
            'xmlns:mstts="http://www.w3.org/2001/mstts" xml:lang="{}">'
            '<voice name="{}">{}</voice></speak>').format(locale, voice, body)
    # Pedir WAV 16 kHz: así no hace falta decodificar MP3 en nodos sin ffmpeg
    req = urllib.request.Request(
        "https://{}.tts.speech.microsoft.com/cognitiveservices/v1".format(region),
        data=ssml.encode("utf-8"), method="POST",
        headers={"Ocp-Apim-Subscription-Key": key,
                 "Content-Type": "application/ssml+xml",
                 "X-Microsoft-OutputFormat": "riff-16khz-16bit-mono-pcm",
                 "User-Agent": "HAMNA-Web/1.0"})
    try:
        r = urllib.request.urlopen(req, timeout=60)
        data = r.read()
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            raise RuntimeError("Azure rechazó la clave (HTTP {}). La clave solo sirve en la región donde se creó: "
                               "revisa que la región de Ajustes → Voz («{}») sea la de tu recurso y que la clave esté "
                               "completa. Ajustes → Sistema → Revisar este nodo busca la región correcta.".format(e.code, region))
        raise RuntimeError("Azure HTTP {}: {}".format(e.code, e.read().decode(errors="ignore")[:200]))
    except urllib.error.URLError as e:
        raise RuntimeError("No pude conectar con Azure: {}".format(e.reason))
    out = out.with_suffix(".wav")
    out.write_bytes(data)
    return out


def _espeak(text, cfg, out):
    exe = shutil.which("espeak-ng") or shutil.which("espeak")
    if not exe:
        raise RuntimeError("eSpeak no está instalado en este nodo")
    out = out.with_suffix(".wav")
    # El texto va en un archivo UTF-8: como argumento falla si el sistema está en LANG=C
    txt = out.with_suffix(".txt")
    txt.write_text(text, encoding="utf-8")
    try:
        r = subprocess.run([exe, "-b", "1", "-v", str(cfg.get("espeak_voice") or "es-419"),
                            "-s", str(int(cfg.get("espeak_speed", 150))),
                            "-p", str(int(cfg.get("espeak_pitch", 50))),
                            "-w", str(out), "-f", str(txt)],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=180)
    finally:
        paths.rm(txt)
    if r.returncode != 0 or not out.is_file():
        raise RuntimeError("eSpeak falló: " + r.stderr.decode(errors="ignore")[:200])
    return out


def piper_available():
    return bool(shutil.which("asl-tts"))


def espeak_available():
    return bool(shutil.which("espeak-ng") or shutil.which("espeak"))


def _piper(text, cfg, out):
    exe = shutil.which("asl-tts")
    if not exe:
        raise RuntimeError("asl-tts (Piper) no está instalado: apt install asl3-tts")
    base = out.with_suffix("")
    r = subprocess.run([exe, "-n", str(cfg.get("node") or "0"), "-t", text, "-f", str(base)],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=300)
    for ext in (".ul", ".ulaw", ".wav", ".gsm", ""):
        cand = Path(str(base) + ext)
        if cand.is_file() and cand.stat().st_size > 0:
            if ext == ".ulaw":
                fixed = cand.with_suffix(".ul")
                cand.rename(fixed)
                return fixed
            return cand
    raise RuntimeError("asl-tts no generó audio: " + r.stderr.decode(errors="ignore")[:200])


def engines():
    out = ["azure"]
    if piper_available():
        out.append("piper")
    if espeak_available():
        out.append("espeak")
    return out


def synthesize(text, cfg, out, ctx=None):
    """Sintetiza *text* (con variables resueltas). Devuelve la ruta creada;
    la extensión depende del motor."""
    resolved = resolve_variables(text, cfg, ctx)
    engine = cfg.get("tts_engine", "azure")
    log.info("TTS %s: %s", engine, resolved[:80].replace("\n", " "))
    out = Path(out)
    if engine == "azure":
        return _azure(resolved, cfg, out)
    if engine == "piper":
        return _piper(resolved, cfg, out)
    return _espeak(resolved, cfg, out)


def azure_voices(key, region):
    req = urllib.request.Request(
        "https://{}.tts.speech.microsoft.com/cognitiveservices/voices/list".format(region),
        headers={"Ocp-Apim-Subscription-Key": key})
    data = json.loads(urllib.request.urlopen(req, timeout=15).read().decode("utf-8"))
    return [{"name": v["ShortName"], "display": v.get("LocalName", v["ShortName"]),
             "locale": v["Locale"], "gender": v.get("Gender", ""),
             "styles": v.get("StyleList", [])}
            for v in data if v.get("Locale", "").startswith("es")]
