try:
    import pyttsx3
except Exception:
    pyttsx3 = None
try:
    from .functions import read_cfg
except Exception:
    read_cfg = None
import asyncio
import os
import subprocess
import json
import sys
import html
import requests
try:
    import edge_tts
except Exception:
    edge_tts = None
try:
    from gtts import gTTS
    from gtts.lang import tts_langs as gtts_langs
except Exception:
    gTTS = None
    gtts_langs = None

try:
    import azure.cognitiveservices.speech as speechsdk
except Exception:
    speechsdk = None

# Fallback list of common Spanish Edge TTS voices when online listing is unavailable
EDGE_FALLBACK_VOICES = [
    {'id': 'es-MX-DaliaNeural', 'name': 'Dalia (es-MX)', 'languages': ['es-MX']},
    {'id': 'es-MX-JorgeNeural', 'name': 'Jorge (es-MX)', 'languages': ['es-MX']},
    {'id': 'es-ES-ElviraNeural', 'name': 'Elvira (es-ES)', 'languages': ['es-ES']},
    {'id': 'es-ES-AlvaroNeural', 'name': 'Alvaro (es-ES)', 'languages': ['es-ES']},
    {'id': 'es-US-PalomaNeural', 'name': 'Paloma (es-US)', 'languages': ['es-US']},
    {'id': 'es-US-AlonsoNeural', 'name': 'Alonso (es-US)', 'languages': ['es-US']},
]

 

def _run_async(coro):
    try:
        return asyncio.run(coro)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

async def _edge_list_voices_async():
    if edge_tts is None:
        return []
    try:
        # New API (VoicesManager)
        try:
            vm = await edge_tts.VoicesManager.create()
            raw = vm.voices
        except Exception:
            # Fallback older API
            try:
                raw = await edge_tts.list_voices()
            except Exception:
                raw = []
        res = []
        for v in raw or []:
            try:
                vid = v.get('ShortName') or v.get('shortName') or v.get('Shortname') or ''
                name = v.get('Name') or v.get('name') or vid
                loc = v.get('Locale') or v.get('locale') or ''
                res.append({'id': vid, 'name': name, 'languages': [loc] if loc else []})
            except Exception:
                continue
        return res or EDGE_FALLBACK_VOICES
    except Exception:
        return EDGE_FALLBACK_VOICES

def _get_tts_proxy_from_cfg():
    try:
        env_proxy = os.environ.get('EDGE_TTS_PROXY')
        if env_proxy and env_proxy.strip():
            return env_proxy.strip()
    except Exception:
        pass
    if callable(read_cfg):
        try:
            data, _ = read_cfg()
            tcfg = (data or {}).get('tts', {}) or {}
            proxy = tcfg.get('proxy')
            if proxy:
                return str(proxy).strip()
        except Exception:
            return None

def _get_azure_cfg():
    try:
        key = os.environ.get('AZURE_SPEECH_KEY') or os.environ.get('AZURE_TTS_KEY')
        region = os.environ.get('AZURE_SPEECH_REGION') or os.environ.get('AZURE_TTS_REGION')
        if key and region:
            return str(key).strip(), str(region).strip()
    except Exception:
        pass
    if callable(read_cfg):
        try:
            data, _ = read_cfg()
            tcfg = (data or {}).get('tts', {}) or {}
            key = tcfg.get('azure_key') or (tcfg.get('azure', {}) or {}).get('key')
            region = tcfg.get('azure_region') or (tcfg.get('azure', {}) or {}).get('region')
            if key and region:
                return str(key).strip(), str(region).strip()
        except Exception:
            return None, None
    return None, None

def _azure_list_voices_http(region: str, key: str):
    try:
        url = f"https://{region}.tts.speech.microsoft.com/cognitiveservices/voices/list"
        hdr = {"Ocp-Apim-Subscription-Key": key}
        r = requests.get(url, headers=hdr, timeout=10)
        if r.status_code != 200:
            return []
        arr = r.json() if r.content else []
        res = []
        for v in arr or []:
            try:
                vid = v.get('ShortName') or v.get('Shortname') or v.get('shortName') or v.get('Name') or ''
                name = v.get('DisplayName') or v.get('LocalName') or v.get('Name') or vid
                loc = v.get('Locale') or ''
                res.append({'id': vid, 'name': name, 'languages': [loc] if loc else []})
            except Exception:
                continue
        return res
    except Exception:
        return []
    return None

def _azure_synthesize_rest(text: str, output_file: str, voice_id: str | None, region: str, key: str, rate=None, volume=None):
    url = f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1"
    headers = {
        "Ocp-Apim-Subscription-Key": key,
        "Content-Type": "application/ssml+xml",
        "X-Microsoft-OutputFormat": "audio-24khz-48kbitrate-mono-mp3",
        "User-Agent": "hamna",
    }
    # Infer locale from voice id like es-MX-DaliaNeural
    lang = "en-US"
    vname = voice_id or "es-MX-DaliaNeural"
    try:
        parts = (vname or "").split("-")
        if len(parts) >= 2:
            lang = f"{parts[0]}-{parts[1]}"
    except Exception:
        pass
    # Map rate/volume to Azure SSML prosody if provided
    rate_attr = None
    vol_attr = None
    try:
        if isinstance(rate, str) and rate.strip():
            rate_attr = rate.strip()
        elif rate is not None:
            rate_attr = f"{int(rate):+d}%"
    except Exception:
        rate_attr = None
    try:
        if isinstance(volume, str) and volume.strip():
            vol_attr = volume.strip()
        elif volume is not None:
            vol_attr = f"{int(round((float(volume) * 100) - 100)):+d}%"
    except Exception:
        vol_attr = None
    inner = html.escape(text or "")
    if rate_attr or vol_attr:
        attrs = []
        if rate_attr:
            attrs.append(f"rate=\"{rate_attr}\"")
        if vol_attr:
            attrs.append(f"volume=\"{vol_attr}\"")
        inner = f"<prosody {' '.join(attrs)}>{inner}</prosody>"
    ssml = f"<?xml version='1.0' encoding='utf-8'?><speak version='1.0' xml:lang='{lang}'><voice name='{vname}'>{inner}</voice></speak>"
    r = requests.post(url, headers=headers, data=ssml.encode("utf-8"), timeout=60)
    if r.status_code != 200 or not r.content:
        raise RuntimeError(f"Azure REST synthesis failed: HTTP {r.status_code}")
    with open(output_file, "wb") as f:
        f.write(r.content)

def _edge_list_voices_cli(proxy: str | None = None):
    try:
        exe = sys.executable or "python"
        # Use CLI to fetch voices; expected JSON output
        cmd = [exe, "-m", "edge_tts", "--list-voices"]
        if proxy:
            cmd.extend(["--proxy", proxy])
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        out = (proc.stdout or "").strip()
        if not out:
            return []
        voices = []
        try:
            data = json.loads(out)
            for v in data or []:
                try:
                    vid = v.get('ShortName') or v.get('shortName') or ''
                    name = v.get('Name') or v.get('name') or vid
                    loc = v.get('Locale') or v.get('locale') or ''
                    voices.append({'id': vid, 'name': name, 'languages': [loc] if loc else []})
                except Exception:
                    continue
            return voices
        except Exception:
            # Try to parse tabular/text output rudimentarily
            res = []
            for line in out.splitlines():
                # Attempt to find ShortName and Locale markers
                if 'ShortName' in line or 'shortname' in line.lower():
                    vid = line.split(':', 1)[-1].strip()
                    if vid:
                        res.append({'id': vid, 'name': vid, 'languages': []})
            return res
    except Exception:
        return []

def list_voices(provider: str = 'windows'):
    provider = (provider or 'windows').lower()
    if provider == 'edge':
        proxy = _get_tts_proxy_from_cfg()
        voices = []
        if proxy:
            voices = _edge_list_voices_cli(proxy)
        else:
            voices = _run_async(_edge_list_voices_async())
            if not voices:
                voices = _edge_list_voices_cli()
        return voices or EDGE_FALLBACK_VOICES
    if provider == 'gtts':
        res = []
        try:
            langs = gtts_langs() if callable(gtts_langs) else {}
            for code, name in (langs or {}).items():
                res.append({'id': code, 'name': f"{name} ({code})", 'languages': [code]})
        except Exception:
            res = []
        # Ensure Spanish options exist even if langs fails
        if not res:
            res = [
                {'id': 'es', 'name': 'Spanish (es)', 'languages': ['es']},
                {'id': 'es-us', 'name': 'Spanish (US) (es-us)', 'languages': ['es-us']},
            ]
        return res
    if provider == 'azure':
        key, region = _get_azure_cfg()
        if not key or not region:
            return []
        return _azure_list_voices_http(region, key)
    # Windows (pyttsx3)
    voices = []
    if pyttsx3 is None:
        return voices
    try:
        engine = pyttsx3.init(driverName='sapi5')
        for v in engine.getProperty('voices'):
            langs = []
            try:
                for l in getattr(v, 'languages', []) or []:
                    try:
                        langs.append(l.decode() if isinstance(l, (bytes, bytearray)) else str(l))
                    except Exception:
                        langs.append(str(l))
            except Exception:
                langs = []
            voices.append({
                'id': getattr(v, 'id', ''),
                'name': getattr(v, 'name', ''),
                'languages': langs,
            })
        try:
            engine.stop()
        except Exception:
            pass
    except Exception:
        voices = []
    return voices

async def _edge_synthesize_async(text: str, output_file: str, voice_id: str | None, rate, volume):
    if edge_tts is None:
        raise ImportError('edge-tts is not installed')
    # Convert generic rate/volume to Edge format
    rate_s = None
    vol_s = None
    try:
        if isinstance(rate, str):
            rate_s = rate
        elif rate is not None:
            rate_s = f"{int(rate):+d}%"
    except Exception:
        rate_s = None
    try:
        if isinstance(volume, str):
            vol_s = volume
        elif volume is not None:
            # Map 0.0..1.0 to -100%..0%
            vol_s = f"{int(round((float(volume) * 100) - 100)):+d}%"
    except Exception:
        vol_s = None
    voice = voice_id or "es-MX-DaliaNeural"
    kwargs = {}
    if isinstance(rate_s, str) and rate_s.strip():
        kwargs["rate"] = rate_s
    if isinstance(vol_s, str) and vol_s.strip():
        kwargs["volume"] = vol_s
    # Use the simple .save() path like the reference repo
    comm = edge_tts.Communicate(text, voice, **kwargs)
    await comm.save(output_file)

def _edge_synthesize_cli(text: str, output_file: str, voice_id: str | None, proxy: str | None = None):
    exe = sys.executable or "python"
    voice = voice_id or "es-MX-DaliaNeural"
    # Avoid passing rate/volume to minimize CLI incompatibilities across versions
    cmd = [exe, "-m", "edge_tts", "--voice", voice, "--text", text, "--write-media", output_file]
    if proxy:
        cmd.extend(["--proxy", proxy])
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or f"edge-tts CLI failed with code {proc.returncode}")
    except Exception as e:
        raise e

def synthesize(text: str, output_file: str, voice_id: str | None = None, rate = None, volume = None, provider: str = 'windows'):
    provider = (provider or 'windows').lower()
    if provider == 'edge':
        proxy = _get_tts_proxy_from_cfg()
        if proxy:
            _edge_synthesize_cli(text, output_file, voice_id, proxy)
            return
        else:
            try:
                _run_async(_edge_synthesize_async(text, output_file, voice_id, rate, volume))
                return
            except Exception as e:
                # Fallback to CLI synthesis as in the reference repo
                try:
                    _edge_synthesize_cli(text, output_file, voice_id)
                    return
                except Exception as e2:
                    raise RuntimeError(f"Edge synthesis failed (API/CLI). Last error: {e2}")
    if provider == 'gtts':
        if gTTS is None:
            raise ImportError('gTTS is not installed')
        lang = (voice_id or 'es')
        try:
            tts = gTTS(text=text, lang=lang)
            tts.save(output_file)
            return
        except Exception as e:
            raise e
    if provider == 'azure':
        import ssl
        # SSL fix (solves handshake failures)
        ssl._create_default_https_context = ssl._create_unverified_context
        
        # Enable detailed logs
        os.environ["SPEECHSDK_LOG_FILENAME"] = "speechsdk.log"
        os.environ["SPEECHSDK_LOG_LEVEL"] = "1"
        
        key, region = _get_azure_cfg()
        if not key or not region:
            raise RuntimeError('Azure Speech key/region not configured')
            
        if speechsdk is None:
            # REST fallback when SDK is not available
            _azure_synthesize_rest(text, output_file, voice_id, region, key, rate=rate, volume=volume)
            return
            
        try:
            # Service configuration
            speech_config = speechsdk.SpeechConfig(subscription=key, region=region)
            
            # Set voice if specified
            if voice_id:
                speech_config.speech_synthesis_voice_name = voice_id
                
            # Configure audio output
            if output_file.endswith('.wav'):
                audio_config = speechsdk.audio.AudioOutputConfig(filename=output_file)
            else:
                audio_config = speechsdk.audio.AudioOutputConfig(use_default_speaker=True)
                
            # Create synthesizer
            synthesizer = speechsdk.SpeechSynthesizer(
                speech_config=speech_config, 
                audio_config=audio_config
            )
            
            # Synthesize voice
            result = synthesizer.speak_text_async(text).get()
            
            # Check result
            if result.reason == speechsdk.ResultReason.Canceled:
                cancellation = result.cancellation_details
                error_msg = f"Voice synthesis canceled: {cancellation.reason}"
                if cancellation.reason == speechsdk.CancellationReason.Error:
                    error_msg += f"\nDetails: {cancellation.error_details}"
                    error_msg += "\nCheck the speechsdk.log file for more details"
                raise RuntimeError(error_msg)
                
        except Exception as e:
            # If there's an error, try the REST method as a fallback
            print(f"Error with Azure SDK: {str(e)}")
            print("Trying with REST method...")
            _azure_synthesize_rest(text, output_file, voice_id, region, key, rate=rate, volume=volume)
    if pyttsx3 is None:
        raise ImportError("pyttsx3 is not installed")
    engine = pyttsx3.init(driverName='sapi5')
    if rate is not None:
        try:
            engine.setProperty('rate', int(rate))
        except Exception:
            pass
    if volume is not None:
        try:
            engine.setProperty('volume', float(volume))
        except Exception:
            pass
    if voice_id:
        try:
            engine.setProperty('voice', voice_id)
        except Exception:
            pass
    engine.save_to_file(text, output_file)
    engine.runAndWait()

def synthesize_from_cfg(text: str, output_file: str):
    voice_id = None
    rate = None
    volume = None
    provider = 'windows'
    if callable(read_cfg):
        try:
            data, _ = read_cfg()
            tcfg = (data or {}).get('tts', {}) or {}
            provider = str(tcfg.get('provider') or 'windows').lower()
            vid = tcfg.get('voice_id')
            if vid:
                voice_id = str(vid)
            r = tcfg.get('rate')
            if r not in (None, ""):
                try:
                    rate = int(r)
                except Exception:
                    try:
                        rate = float(r)
                    except Exception:
                        rate = None
            v = tcfg.get('volume')
            if v not in (None, ""):
                try:
                    volume = float(v)
                except Exception:
                    volume = None
        except Exception:
            pass
    if voice_id is None and provider != 'edge':
        try:
            for vv in list_voices('windows'):
                if any('es' in (l or '').lower() or 'spanish' in (l or '').lower() for l in (vv.get('languages') or [])) or 'es' in (vv.get('id') or '').lower():
                    voice_id = vv.get('id')
                    break
        except Exception:
            voice_id = None
    synthesize(text, output_file, voice_id=voice_id, rate=rate, volume=volume, provider=provider)

def tts(text, output_file, velocidad):
    if pyttsx3 is None:
        raise ImportError("pyttsx3 is not installed")
    try:
        voices = list_voices()
        voice_id = None
        for v in voices:
            if any('es' in (l or '').lower() or 'spanish' in (l or '').lower() for l in (v.get('languages') or [])) or 'es' in (v.get('id') or '').lower():
                voice_id = v.get('id')
                break
        synthesize(text, output_file, voice_id=voice_id, rate=velocidad, provider='windows')
    except Exception:
        synthesize(text, output_file, voice_id=None, rate=velocidad, provider='windows')

# Ejemplo de uso
texto = "Bienvenidos al boletín dominical de la Federación Mexicana de Radio Experimentadores A.C."
#tts(texto, "test.mp3", 150)
