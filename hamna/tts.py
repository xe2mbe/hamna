"""
HAMNA Web — síntesis de voz.

Motores:
  azure       Azure Speech por REST (voces neuronales; requiere internet y clave)
  google      Google Cloud Text-to-Speech (Neural2 / Chirp HD; clave de API)
  elevenlabs  ElevenLabs (voces muy naturales; clave de API)
  piper       asl-tts de AllStarLink (Piper, voz neuronal local) si está instalado
  espeak      espeak-ng local (sin internet; voz sintética)

Respaldo automático (tts_fallback): si el motor elegido falla, se prueban los
demás que estén configurados, en el orden de RESPALDO, y se avisa por Telegram.
"""
import base64
import datetime
import html
import json
import logging
import os
import re
import shutil
import subprocess
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import wave
from pathlib import Path

from . import horas, paths, pronuncia

log = logging.getLogger("hamna.tts")

DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]

VARIABLES = [
    ("{fecha}", "Fecha actual (dd/mm/aaaa)"),
    ("{fecha_larga}", "Fecha en palabras (2 de noviembre de 2026)"),
    ("{hora}", "Hora actual (HH:MM)"),
    ("{dia}", "Día de la semana"),
    ("{saludo}", "Buenos días / buenas tardes / buenas noches, según la hora"),
    ("{despedida}", "Buen día / buena tarde / buena noche, según la hora"),
    ("{pausa_cada}", "Intervalo de pausa configurado"),
    ("{pausa_duracion}", "Duración de la pausa"),
    ("{pausa_alerta}", "Aviso antes de la pausa"),
    ("{evento}", "Nombre del evento"),
    ("{numero}", "Número de edición del evento (la emisión global si es automática)"),
    ("{emision}", "Número de emisión global (numeración automática)"),
    ("{emision_anio}", "Número de emisión del año: se reinicia cada 1 de enero"),
    ("{anio}", "Año de la emisión"),
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


def saludo(now):
    """(saludo, despedida) según la hora: mañana hasta las 12, tarde hasta las 19, luego noche."""
    if 5 <= now.hour < 12:
        return "buenos días", "buen día"
    if 12 <= now.hour < 19:
        return "buenas tardes", "buena tarde"
    return "buenas noches", "buena noche"


def resolve_variables(text, cfg, ctx=None):
    now = datetime.datetime.now()
    text = horas.resolver(text, cfg, now)        # {hora 21:00 America/Chicago}, {hora_evento …}
    ctx = ctx or {}
    rep = {
        "{fecha}": now.strftime("%d/%m/%Y"),
        "{fecha_larga}": "{} de {} de {}".format(now.day, MESES[now.month - 1], now.year),
        "{hora}": now.strftime("%H:%M"),
        "{dia}": DIAS[now.weekday()],
        "{saludo}": saludo(now)[0],
        "{despedida}": saludo(now)[1],
        "{pausa_cada}": fmt_seg(cfg.get("pause_tx_time", 160)),
        "{pausa_duracion}": fmt_seg(cfg.get("pause_duration", 10)),
        "{pausa_alerta}": fmt_seg(cfg.get("pause_alert_before", 10)),
        "{nodo}": " ".join(str(cfg.get("node", ""))),
        "{anio}": str(ctx.get("anio") or now.year),
    }
    for k in ("titulo", "descripcion", "evento", "numero", "emision", "emision_anio", "num_secciones",
              "duracion_total", "dur_contabilizable"):
        rep["{" + k + "}"] = str(ctx.get(k, "") or "")
    for token, value in rep.items():
        text = text.replace(token, value)
    return text


def event_context(evento, secs):
    if not evento:
        return {}
    from . import numeracion
    if evento.get("num_auto") and "num" not in evento:
        evento = numeracion.aplicar(evento)
    dur_t = sum(float(s.get("duracion") or 0) for s in secs)
    cont = [s for s in secs if s.get("contabilizable", 1)]
    return {
        "evento": evento.get("nombre", ""),
        "numero": evento.get("numero") or "",
        "emision": evento.get("numero") or "",
        "emision_anio": evento.get("emision_anio") or "",
        "anio": evento.get("anio") or "",
        "num_secciones": str(len(cont)),
        "duracion_total": fmt_seg(dur_t),
        "dur_contabilizable": fmt_seg(sum(float(s.get("duracion") or 0) for s in cont)),
    }


# ── Motores ───────────────────────────────────────────────────────────────────
NOMBRES = {"azure": "Azure", "google": "Google", "elevenlabs": "ElevenLabs", "piper": "Piper", "espeak": "eSpeak"}
RESPALDO = ["azure", "google", "elevenlabs", "piper", "espeak"]   # orden en que se prueban los de respaldo


def _trozos(text, limite, medida=len):
    """Parte un texto largo en trozos de frases completas que quepan en *limite*."""
    if medida(text) <= limite:
        return [text]
    frases = re.split(r"(?<=[.!?;:])\s+|\n+", text)
    out, cur = [], ""
    for f in frases:
        f = f.strip()
        if not f:
            continue
        while medida(f) > limite:              # una "frase" enorme: cortar por palabras
            corte = f[:limite]
            i = corte.rfind(" ")
            i = i if i > limite // 2 else len(corte)
            while medida(f[:i]) > limite:
                i -= 1
            if cur:
                out.append(cur)
                cur = ""
            out.append(f[:i].strip())
            f = f[i:].strip()
        cand = (cur + " " + f).strip()
        if medida(cand) <= limite:
            cur = cand
        else:
            out.append(cur)
            cur = f
    if cur:
        out.append(cur)
    return [t for t in out if t]


def _wav_pcm(out, pcm, rate):
    out = out.with_suffix(".wav")
    w = wave.open(str(out), "wb")
    try:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm)
    finally:
        w.close()
    return out


def _http(req, nombre, timeout=90):
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        cuerpo = e.read().decode("utf-8", "ignore")
        detalle = cuerpo[:300]
        try:
            j = json.loads(cuerpo)
            d = j.get("error") or j.get("detail") or j
            if isinstance(d, dict):
                detalle = d.get("message") or d.get("status") or json.dumps(d)[:300]
            else:
                detalle = str(d)[:300]
        except ValueError:
            pass
        bajo = (detalle + " " + cuerpo[:500]).lower()
        if e.code == 429 or "quota" in bajo:
            raise RuntimeError("{}: se acabó la cuota o hay demasiadas peticiones (HTTP {}): {}".format(nombre, e.code, detalle))
        if "has not been used" in bajo or "is disabled" in bajo or "service_disabled" in bajo:
            raise RuntimeError("{}: la API Cloud Text-to-Speech no está habilitada en tu proyecto de Google Cloud "
                               "(HTTP {}). Habilítala en APIs y servicios → Biblioteca.".format(nombre, e.code))
        if e.code in (401, 403) or "api key not valid" in bajo or "invalid_api_key" in bajo:
            raise RuntimeError("{} rechazó la clave (HTTP {}): {}".format(nombre, e.code, detalle))
        raise RuntimeError("{} HTTP {}: {}".format(nombre, e.code, detalle))
    except urllib.error.URLError as e:
        raise RuntimeError("No pude conectar con {}: {}".format(nombre, e.reason))


# Google: máximo 5000 bytes de texto por petición; LINEAR16 a 16 kHz trae su encabezado WAV
GOOGLE_URL = os.environ.get("HAMNA_GOOGLE_API", "https://texttospeech.googleapis.com") + "/v1/"   # env: solo pruebas


def _google(text, cfg, out):
    key = (cfg.get("google_key") or "").strip()
    if not key:
        raise RuntimeError("Falta la clave de Google (Ajustes → Voz)")
    voice = (cfg.get("google_voice") or "es-US-Neural2-A").strip()
    lang = "-".join(voice.split("-")[:2]) if voice.count("-") >= 2 else "es-US"
    rate = max(25, min(400, int(cfg.get("google_rate", 100)))) / 100.0
    pitch = max(-20.0, min(20.0, float(cfg.get("google_pitch", 0))))
    pcm = b""
    for t in _trozos(text, 4500, lambda s: len(s.encode("utf-8"))):
        ac = {"audioEncoding": "LINEAR16", "sampleRateHertz": 16000}
        if rate != 1.0:
            ac["speakingRate"] = rate
        if pitch and "Chirp" not in voice:        # las voces Chirp HD no aceptan tono
            ac["pitch"] = pitch
        body = {"input": {"text": t}, "voice": {"languageCode": lang, "name": voice}, "audioConfig": ac}
        req = urllib.request.Request(GOOGLE_URL + "text:synthesize?key=" + urllib.parse.quote(key),
                                     data=json.dumps(body).encode("utf-8"), method="POST",
                                     headers={"Content-Type": "application/json", "User-Agent": "HAMNA-Web/1.0"})
        data = json.loads(_http(req, "Google").decode("utf-8"))
        wav = base64.b64decode(data.get("audioContent") or "")
        if wav[:4] == b"RIFF":
            i = wav.find(b"data")
            wav = wav[i + 8:] if i >= 0 else wav[44:]
        if not wav:
            raise RuntimeError("Google no devolvió audio")
        pcm += wav
    return _wav_pcm(out, pcm, 16000)


def google_voices(key):
    req = urllib.request.Request(GOOGLE_URL + "voices?languageCode=es&key=" + urllib.parse.quote(key.strip()),
                                 headers={"User-Agent": "HAMNA-Web/1.0"})
    data = json.loads(_http(req, "Google", 20).decode("utf-8"))
    out = []
    for v in data.get("voices", []):
        locs = [l for l in v.get("languageCodes", []) if l.startswith("es")]
        if not locs:
            continue
        nombre = v.get("name", "")
        tipo = next((k for k in ("Chirp3-HD", "Chirp-HD", "Neural2", "Studio", "Wavenet", "Polyglot", "News", "Standard")
                     if k in nombre), "")
        g = {"FEMALE": "Femenina", "MALE": "Masculina"}.get(v.get("ssmlGender"), "")
        out.append({"name": nombre, "display": tipo or nombre, "locale": locs[0], "gender": g})
    orden = {"Chirp3-HD": 0, "Chirp-HD": 1, "Neural2": 2, "Studio": 3, "Wavenet": 4}
    out.sort(key=lambda v: (v["locale"] != "es-US", orden.get(v["display"], 9), v["locale"], v["name"]))
    return out


# ElevenLabs: hasta ~10 000 caracteres por petición; pcm_16000 = PCM crudo 16 bits 16 kHz
ELEVEN_URL = os.environ.get("HAMNA_ELEVEN_API", "https://api.elevenlabs.io") + "/v1/"   # env: solo pruebas


def _elevenlabs(text, cfg, out):
    key = (cfg.get("eleven_key") or "").strip()
    voice = (cfg.get("eleven_voice") or "").strip()
    if not key:
        raise RuntimeError("Falta la clave de ElevenLabs (Ajustes → Voz)")
    if not voice:
        raise RuntimeError("Elige una voz de ElevenLabs (Ajustes → Voz → Cargar)")
    ajustes = {"stability": max(0, min(100, int(cfg.get("eleven_stability", 50)))) / 100.0,
               "similarity_boost": max(0, min(100, int(cfg.get("eleven_similarity", 75)))) / 100.0}
    vel = int(cfg.get("eleven_speed", 100))
    if vel != 100:
        ajustes["speed"] = max(70, min(120, vel)) / 100.0
    pcm = b""
    for t in _trozos(text, 4800):
        body = {"text": t, "model_id": cfg.get("eleven_model") or "eleven_multilingual_v2", "voice_settings": ajustes}
        req = urllib.request.Request(
            ELEVEN_URL + "text-to-speech/{}?output_format=pcm_16000".format(urllib.parse.quote(voice)),
            data=json.dumps(body).encode("utf-8"), method="POST",
            headers={"xi-api-key": key, "Content-Type": "application/json", "Accept": "audio/pcm",
                     "User-Agent": "HAMNA-Web/1.0"})
        data = _http(req, "ElevenLabs", 120)
        if not data:
            raise RuntimeError("ElevenLabs no devolvió audio")
        pcm += data[:len(data) - len(data) % 2]
    return _wav_pcm(out, pcm, 16000)


def eleven_voices(key):
    req = urllib.request.Request(ELEVEN_URL + "voices", headers={"xi-api-key": key.strip(), "User-Agent": "HAMNA-Web/1.0"})
    data = json.loads(_http(req, "ElevenLabs", 20).decode("utf-8"))
    out = []
    for v in data.get("voices", []):
        lb = v.get("labels") or {}
        g = {"female": "Femenina", "male": "Masculina"}.get((lb.get("gender") or "").lower(), "")
        extra = " · ".join(x for x in (lb.get("accent"), lb.get("description") or lb.get("descriptive"),
                                       v.get("category")) if x)
        out.append({"name": v.get("voice_id", ""), "display": v.get("name", ""), "locale": extra, "gender": g})
    out.sort(key=lambda v: v["display"].lower())
    return out


def eleven_cuota(key):
    """(caracteres usados, límite) del mes en ElevenLabs, o None si la clave no deja verlo."""
    req = urllib.request.Request(ELEVEN_URL + "user/subscription",
                                 headers={"xi-api-key": key.strip(), "User-Agent": "HAMNA-Web/1.0"})
    try:
        d = json.loads(_http(req, "ElevenLabs", 15).decode("utf-8"))
    except RuntimeError:
        return None
    if "character_count" in d and "character_limit" in d:
        return int(d["character_count"]), int(d["character_limit"])
    return None


def configurado(eng, cfg):
    """¿Se puede usar este motor con los ajustes actuales?"""
    if eng == "azure":
        return bool((cfg.get("azure_key") or "").strip() and (cfg.get("azure_region") or "").strip())
    if eng == "google":
        return bool((cfg.get("google_key") or "").strip())
    if eng == "elevenlabs":
        return bool((cfg.get("eleven_key") or "").strip() and (cfg.get("eleven_voice") or "").strip())
    if eng == "piper":
        return piper_available()
    if eng == "espeak":
        return espeak_available()
    return False


def cadena(cfg):
    """Motores en el orden en que se intentan: el elegido y, si hay respaldo, los demás configurados."""
    principal = cfg.get("tts_engine") or "azure"
    out = [principal]
    if cfg.get("tts_fallback"):
        out += [e for e in RESPALDO if e != principal and configurado(e, cfg)]
    return out


_aviso_lock = threading.Lock()
_ultimo_aviso = {}


def _avisar_respaldo(principal, usado, error):
    log.warning("TTS: %s falló (%s); se usó %s", NOMBRES.get(principal, principal), error, NOMBRES.get(usado, usado))
    with _aviso_lock:                          # un aviso por motor cada 30 min, no uno por sección
        if time.time() - _ultimo_aviso.get(principal, 0) < 1800:
            return
        _ultimo_aviso[principal] = time.time()
    try:
        from . import notify
        notify.send("error", "⚠️ <b>La voz {} falló</b> y se usó {} de respaldo.\n{}\n"
                    "Revisa Ajustes → Voz (o «Revisar este nodo»).".format(
                        NOMBRES.get(principal, principal), NOMBRES.get(usado, usado), html.escape(str(error)[:300])),
                    dedupe="tts-respaldo:" + principal)
    except Exception:
        log.exception("No pude avisar del respaldo de voz")


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
    out = ["azure", "google", "elevenlabs"]
    if piper_available():
        out.append("piper")
    if espeak_available():
        out.append("espeak")
    return out


_MOTORES = {"azure": _azure, "google": _google, "elevenlabs": _elevenlabs, "piper": _piper, "espeak": _espeak}


def synthesize(text, cfg, out, ctx=None, respaldo=True):
    """Sintetiza *text* (con variables resueltas). Devuelve la ruta creada;
    la extensión depende del motor. Con el respaldo automático activado, si el
    motor elegido falla se prueban los demás configurados (respaldo=False para
    la prueba de voz de Ajustes, que debe oír exactamente el motor elegido)."""
    # Variables y después el diccionario de pronunciación (Ajustes → Voz)
    resolved = pronuncia.para_voz(resolve_variables(text, cfg, ctx), cfg)
    out = Path(out)
    orden = cadena(cfg) if respaldo else [cfg.get("tts_engine") or "azure"]
    errores = []
    for i, eng in enumerate(orden):
        fn = _MOTORES.get(eng, _espeak)
        log.info("TTS %s: %s", eng, resolved[:80].replace("\n", " "))
        try:
            src = fn(resolved, cfg, out)
        except Exception as e:
            errores.append((eng, e))
            if len(orden) > 1:
                log.warning("TTS %s falló: %s", eng, e)
            continue
        if i:
            _avisar_respaldo(orden[0], eng, errores[0][1])
        return src
    if len(errores) == 1:
        raise errores[0][1]
    def uno(e, x):
        m = str(x)[:200]
        return m if m.startswith(NOMBRES.get(e, e)) else "{}: {}".format(NOMBRES.get(e, e), m)
    raise RuntimeError("Ningún motor de voz funcionó — " + " · ".join(uno(e, x) for e, x in errores))


def azure_voices(key, region):
    req = urllib.request.Request(
        "https://{}.tts.speech.microsoft.com/cognitiveservices/voices/list".format(region),
        headers={"Ocp-Apim-Subscription-Key": key})
    data = json.loads(urllib.request.urlopen(req, timeout=15).read().decode("utf-8"))
    return [{"name": v["ShortName"], "display": v.get("LocalName", v["ShortName"]),
             "locale": v["Locale"], "gender": v.get("Gender", ""),
             "styles": v.get("StyleList", [])}
            for v in data if v.get("Locale", "").startswith("es")]
