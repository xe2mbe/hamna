import sqlite3
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
import time
import logging
import wave
import io
import base64
import tempfile
import shutil
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Union, Any, Callable
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

# Configurar el sistema de registro
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuración de reintentos para solicitudes HTTP
MAX_RETRIES = 3
RETRY_DELAY = 1  # segundos

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
        print("\n[DEBUG] === Iniciando búsqueda de configuración de Azure ===")
        
        # 1. Primero intentar cargar desde .env usando python-dotenv
        try:
            from dotenv import load_dotenv
            import os.path
            
            # Buscar el archivo .env en el directorio raíz del proyecto
            env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), '.env')
            if os.path.exists(env_path):
                print(f"[DEBUG] Cargando configuración desde: {env_path}")
                load_dotenv(dotenv_path=env_path, override=True)
            else:
                print(f"[ADVERTENCIA] No se encontró el archivo .env en: {env_path}")
        except Exception as e:
            print(f"[ADVERTENCIA] No se pudo cargar el archivo .env: {str(e)}")
        
        # 2. Obtener las variables de entorno (ya sea del sistema o cargadas desde .env)
        key = os.getenv('AZURE_SPEECH_KEY') or os.getenv('AZURE_TTS_KEY')
        region = os.getenv('AZURE_SPEECH_REGION') or os.getenv('AZURE_TTS_REGION')
        
        # Depuración detallada
        print("\n[DEBUG] Revisando variables de entorno:")
        print(f"[DEBUG] AZURE_SPEECH_KEY: {'PRESENTE' if os.getenv('AZURE_SPEECH_KEY') else 'NO ENCONTRADO'}")
        print(f"[DEBUG] AZURE_TTS_KEY: {'PRESENTE' if os.getenv('AZURE_TTS_KEY') else 'NO ENCONTRADO'}")
        print(f"[DEBUG] AZURE_SPEECH_REGION: {'PRESENTE' if os.getenv('AZURE_SPEECH_REGION') else 'NO ENCONTRADO'}")
        print(f"[DEBUG] AZURE_TTS_REGION: {'PRESENTE' if os.getenv('AZURE_TTS_REGION') else 'NO ENCONTRADO'}")
        
        # Verificar si las variables tienen contenido
        if key and region:
            key = key.strip()
            region = region.strip()
            key_debug = f"{key[:5]}...{key[-5:]}" if len(key) > 10 else "[clave muy corta]"
            
            print(f"\n[DEBUG] Configuración encontrada en variables de entorno:")
            print(f"[DEBUG] Clave: {key_debug}")
            print(f"[DEBUG] Región: {region}")
            print(f"[DEBUG] Longitud de la clave: {len(key)} caracteres")
            
            # Verificar formato de la clave (debería ser un GUID de 32 caracteres)
            if not (len(key) == 32 and all(c in '0123456789abcdefABCDEF' for c in key)):
                print("[ADVERTENCIA] El formato de la clave no parece ser válido (debería ser un GUID de 32 caracteres hexadecimales)")
            
            return key, region
        else:
            print("\n[DEBUG] No se encontró configuración completa en las variables de entorno")
    
    except Exception as e:
        print(f"[ERROR] Error al leer la configuración de Azure: {str(e)}")
    
    # 3. Si no se encontró en las variables de entorno, buscar en el archivo de configuración
    if callable(read_cfg):
        try:
            print("\n[DEBUG] Buscando configuración en el archivo de configuración...")
            data, _ = read_cfg()
            tcfg = (data or {}).get('tts', {}) or {}
            key = tcfg.get('azure_key') or (tcfg.get('azure', {}) or {}).get('key')
            region = tcfg.get('azure_region') or (tcfg.get('azure', {}) or {}).get('region')
            
            if key and region:
                key = str(key).strip()
                region = str(region).strip()
                key_debug = f"{key[:5]}...{key[-5:]}" if len(key) > 10 else "[clave muy corta]"
                
                print(f"\n[DEBUG] Configuración encontrada en archivo de configuración:")
                print(f"[DEBUG] Clave: {key_debug}")
                print(f"[DEBUG] Región: {region}")
                print(f"[DEBUG] Longitud de la clave: {len(key)} caracteres")
                
                # Verificar formato de la clave
                if not (len(key) == 32 and all(c in '0123456789abcdefABCDEF' for c in key)):
                    print("[ADVERTENCIA] El formato de la clave no parece ser válido (debería ser un GUID de 32 caracteres hexadecimales)")
                
                return key, region
            else:
                print("[DEBUG] No se encontró configuración completa en el archivo de configuración")
                
        except Exception as e:
            print(f"[ERROR] Error al leer la configuración del archivo: {str(e)}")
    
    print("\n[ERROR] No se pudo encontrar una configuración válida de Azure")
    print("[SOLUCIÓN] Por favor, asegúrate de tener configuradas las siguientes variables de entorno:")
    print("  - AZURE_SPEECH_KEY o AZURE_TTS_KEY: Tu clave de suscripción de Azure")
    print("  - AZURE_SPEECH_REGION o AZURE_TTS_REGION: La región de tu recurso de Azure (ej: 'eastus', 'westeurope')")
    print("\nO configura estas opciones en el archivo de configuración de la aplicación.")
    
    return None, None

def _azure_list_voices_http(region: str, key: str):
    try:
        print(f"[DEBUG] Intentando obtener voces de Azure. Región: {region}")
        
        # Asegurarse de que la región no tenga espacios ni caracteres extraños
        region = region.strip().lower()
        
        # Construir la URL del endpoint
        endpoint = f"https://{region}.tts.speech.microsoft.com/cognitiveservices/voices/list"
        print(f"[DEBUG] Endpoint: {endpoint}")
        
        # Configurar los encabezados de la solicitud
        headers = {
            "Ocp-Apim-Subscription-Key": key.strip(),
            "Content-Type": "application/ssml+xml",
            "X-Microsoft-OutputFormat": "audio-24khz-48kbitrate-mono-mp3",
            "User-Agent": "hamna-tts-client/1.0"
        }
        
        # Imprimir información de depuración (sin mostrar la clave completa)
        key_preview = f"{key[:5]}...{key[-5:]}" if key and len(key) > 10 else "[clave no válida]"
        print(f"[DEBUG] Usando clave: {key_preview}")
        print(f"[DEBUG] Headers: {headers}")
        
        # Realizar la solicitud con un tiempo de espera mayor
        print("[DEBUG] Realizando solicitud a la API de Azure TTS...")
        response = requests.get(endpoint, headers=headers, timeout=30)
        
        # Verificar el código de estado
        print(f"[DEBUG] Código de estado HTTP: {response.status_code}")
        
        # Si hay un error 401, proporcionar más detalles
        if response.status_code == 401:
            print("[ERROR] Error 401 - No autorizado. Posibles causas:")
            print("1. La clave de suscripción es incorrecta o ha expirado")
            print("2. La región no coincide con la región de la clave")
            print("3. La clave no tiene permisos para acceder al servicio de voz")
            print(f"4. URL utilizada: {endpoint}")
            print("5. Asegúrate de que el recurso de Azure esté en la región correcta")
            print("6. Verifica que el recurso de Azure tenga habilitado el servicio de voz")
            
            # Intentar obtener más detalles del error
            try:
                error_details = response.json()
                print(f"[ERROR] Detalles del error: {error_details}")
            except:
                print("[ERROR] No se pudieron obtener detalles adicionales del error")
                print(f"[ERROR] Respuesta cruda: {response.text[:500]}")
            
            return []
        
        # Si la respuesta no es exitosa, devolver lista vacía
        if response.status_code != 200:
            print(f"[ERROR] Error al obtener voces. Código: {response.status_code}, Respuesta: {response.text[:200]}")
            return []
        
        # Procesar la respuesta exitosa
        try:
            arr = response.json() if response.content else []
            print(f"[DEBUG] Se recibieron {len(arr)} voces de Azure TTS")
            
            # Verificar si la respuesta tiene el formato esperado
            if not isinstance(arr, list):
                print(f"[ERROR] La respuesta no tiene el formato esperado. Se esperaba una lista, se obtuvo: {type(arr)}")
                return []
                
            # Procesar las voces
            res = []
            for v in arr:
                try:
                    vid = v.get('ShortName') or v.get('Shortname') or v.get('shortName') or v.get('Name') or ''
                    name = v.get('DisplayName') or v.get('LocalName') or v.get('Name') or vid
                    loc = v.get('Locale') or ''
                    res.append({'id': vid, 'name': name, 'languages': [loc] if loc else []})
                except Exception as e:
                    print(f"[ADVERTENCIA] Error al procesar voz: {str(e)}")
                    continue
                    
            return res
            
        except Exception as e:
            print(f"[ERROR] Error al procesar la respuesta de Azure TTS: {str(e)}")
            import traceback
            traceback.print_exc()
            return []
            
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Error de conexión al obtener voces de Azure: {str(e)}")
        return []
    except json.JSONDecodeError as e:
        print(f"[ERROR] Error al decodificar la respuesta JSON: {str(e)}")
        print(f"Respuesta recibida: {response.text[:500] if 'response' in locals() else 'No hay respuesta'}")
        return []
    except Exception as e:
        print(f"[ERROR] Error inesperado al obtener voces de Azure: {str(e)}")
        import traceback
        traceback.print_exc()
        return []

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
    print(f"\n[DEBUG] list_voices - Procesando proveedor: {provider}")
    
    if provider == 'edge':
        print("[DEBUG] Usando proveedor Edge TTS")
        proxy = _get_tts_proxy_from_cfg()
        voices = []
        if proxy:
            print("[DEBUG] Usando proxy para Edge TTS")
            voices = _edge_list_voices_cli(proxy)
        else:
            print("[DEBUG] Intentando obtener voces de Edge TTS de forma asíncrona")
            voices = _run_async(_edge_list_voices_async())
            if not voices:
                print("[DEBUG] Falló la obtención asíncrona, intentando con CLI")
                voices = _edge_list_voices_cli()
        return voices or EDGE_FALLBACK_VOICES
        
    if provider == 'gtts':
        print("[DEBUG] Usando proveedor gTTS")
        res = []
        try:
            langs = gtts_langs() if callable(gtts_langs) else {}
            for code, name in (langs or {}).items():
                res.append({'id': code, 'name': f"{name} ({code})", 'languages': [code]})
        except Exception as e:
            print(f"[ERROR] Error al obtener idiomas de gTTS: {str(e)}")
            res = []
        # Asegurar que existan opciones en español incluso si falla langs
        if not res:
            print("[DEBUG] Usando lista de respaldo para gTTS")
            res = [
                {'id': 'es', 'name': 'Spanish (es)', 'languages': ['es']},
                {'id': 'es-us', 'name': 'Spanish (US) (es-us)', 'languages': ['es-us']},
            ]
        return res
        
    if provider == 'azure':
        print("[DEBUG] Usando proveedor Azure TTS")
        key, region = _get_azure_cfg()
        
        if not key or not region:
            print("[ERROR] No se pudo obtener la configuración de Azure (falta clave o región)")
            print("[DEBUG] Variables de entorno AZURE_TTS_KEY:", 'PRESENTE' if os.environ.get('AZURE_TTS_KEY') else 'FALTANTE')
            print("[DEBUG] Variables de entorno AZURE_TTS_REGION:", 'PRESENTE' if os.environ.get('AZURE_TTS_REGION') else 'FALTANTE')
            return []
            
        print(f"[DEBUG] Solicitando voces a Azure TTS...")
        voices = _azure_list_voices_http(region, key)
        print(f"[DEBUG] Se obtuvieron {len(voices)} voces de Azure TTS")
        if not voices:
            print("[ADVERTENCIA] No se pudieron cargar las voces de Azure. Verifica tu conexión y credenciales.")
        return voices
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

# Configuración de rutas para archivos de audio TTS
AUDIO_BASE_DIR = os.path.join('media', 'audios', 'TTS')

def get_db_connection():
    """Obtiene una conexión a la base de datos."""
    db_path = os.path.join('database', 'hamna.db')
    return sqlite3.connect(db_path)

def create_tts_section_table():
    """Crea la tabla section_tts si no existe."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS section_tts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            text TEXT NOT NULL,
            voice_id TEXT NOT NULL,
            language TEXT NOT NULL,
            audio_path TEXT NOT NULL,
            duration_seconds REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (event_id) REFERENCES events (id) ON DELETE CASCADE
        )
        ''')
        conn.commit()
    finally:
        conn.close()

def save_tts_section(
    event_id: int,
    name: str,
    text: str,
    voice_id: str,
    language: str,
    audio_path: str,
    duration_seconds: float
) -> int:
    """
    Guarda una nueva sección TTS en la base de datos.
    
    Args:
        event_id: ID del evento al que pertenece la sección
        name: Nombre de la sección
        text: Texto a convertir a voz
        voice_id: ID de la voz seleccionada
        language: Idioma de la voz (ej: 'es-ES', 'en-US')
        audio_path: Ruta relativa al archivo de audio generado
        duration_seconds: Duración del audio en segundos
        
    Returns:
        int: ID de la sección creada
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('''
        INSERT INTO section_tts 
        (event_id, name, text, voice_id, language, audio_path, duration_seconds)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (event_id, name, text, voice_id, language, audio_path, duration_seconds))
        
        section_id = cursor.lastrowid
        conn.commit()
        return section_id
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def update_tts_section(
    id: int,
    name: Optional[str] = None,
    text: Optional[str] = None,
    voice_id: Optional[str] = None,
    language: Optional[str] = None,
    audio_path: Optional[str] = None,
    duration_seconds: Optional[float] = None
) -> bool:
    """
    Actualiza una sección TTS existente.
    
    Args:
        id: ID de la sección a actualizar
        name: Nuevo nombre (opcional)
        text: Nuevo texto (opcional)
        voice_id: Nueva voz (opcional)
        language: Nuevo idioma (opcional)
        audio_path: Nueva ruta de audio (opcional)
        duration_seconds: Nueva duración (opcional)
        
    Returns:
        bool: True si la actualización fue exitosa, False en caso contrario
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Construir la consulta dinámicamente basada en los parámetros proporcionados
        update_fields = []
        params = []
        
        if name is not None:
            update_fields.append("name = ?")
            params.append(name)
        if text is not None:
            update_fields.append("text = ?")
            params.append(text)
        if voice_id is not None:
            update_fields.append("voice_id = ?")
            params.append(voice_id)
        if language is not None:
            update_fields.append("language = ?")
            params.append(language)
        if audio_path is not None:
            update_fields.append("audio_path = ?")
            params.append(audio_path)
        if duration_seconds is not None:
            update_fields.append("duration_seconds = ?")
            params.append(duration_seconds)
            
        # Si no hay campos para actualizar, retornar False
        if not update_fields:
            return False
            
        # Agregar la actualización de updated_at
        update_fields.append("updated_at = ?")
        params.append(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        
        # Construir la consulta final
        query = f"""
        UPDATE section_tts 
        SET {', '.join(update_fields)}
        WHERE id = ?"""
        
        # Agregar el ID al final de los parámetros
        params.append(id)
        
        cursor.execute(query, params)
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def delete_tts_section(section_id: int) -> bool:
    """
    Elimina una sección TTS de la base de datos.
    
    Args:
        section_id: ID de la sección a eliminar
        
    Returns:
        bool: True si la eliminación fue exitosa, False en caso contrario
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM section_tts WHERE id = ?', (section_id,))
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def get_tts_section(section_id: int) -> Optional[Dict[str, Any]]:
    """
    Obtiene los detalles de una sección TTS por su ID.
    
    Args:
        section_id: ID de la sección a obtener
        
    Returns:
        Optional[Dict]: Diccionario con los detalles de la sección o None si no se encuentra
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM section_tts WHERE id = ?', (section_id,))
        row = cursor.fetchone()
        
        if not row:
            return None
            
        # Convertir la fila a un diccionario
        columns = [column[0] for column in cursor.description]
        return dict(zip(columns, row))
    finally:
        conn.close()

def get_tts_sections_by_event(event_id: int) -> List[Dict[str, Any]]:
    """
    Obtiene todas las secciones TTS de un evento específico.
    
    Args:
        event_id: ID del evento
        
    Returns:
        List[Dict]: Lista de diccionarios con los detalles de las secciones
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM section_tts WHERE event_id = ? ORDER BY name', (event_id,))
        
        # Convertir las filas a una lista de diccionarios
        columns = [column[0] for column in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
    finally:
        conn.close()

def get_audio_duration(audio_path: str) -> float:
    """
    Obtiene la duración de un archivo de audio en segundos.
    
    Args:
        audio_path: Ruta al archivo de audio
        
    Returns:
        float: Duración en segundos
    """
    try:
        with contextlib.closing(wave.open(audio_path, 'r')) as f:
            frames = f.getnframes()
            rate = f.getframerate()
            return frames / float(rate)
    except Exception as e:
        logger.error(f"Error al obtener la duración del audio {audio_path}: {str(e)}")
        return 0.0

def generate_audio_filename(event_id: int, section_name: str) -> str:
    """
    Genera un nombre de archivo único para el audio de una sección.
    
    Args:
        event_id: ID del evento
        section_name: Nombre de la sección
        
    Returns:
        str: Ruta relativa del archivo de audio
    """
    # Crear directorio si no existe
    event_dir = os.path.join(AUDIO_BASE_DIR, str(event_id))
    os.makedirs(event_dir, exist_ok=True)
    
    # Generar nombre de archivo seguro
    safe_name = "".join(c if c.isalnum() else "_" for c in section_name)
    base_name = f"{safe_name}.mp3"
    
    # Si el archivo ya existe, agregar un sufijo numérico
    counter = 1
    output_file = os.path.join(event_dir, base_name)
    while os.path.exists(output_file):
        name, ext = os.path.splitext(base_name)
        output_file = os.path.join(event_dir, f"{name}_{counter}{ext}")
        counter += 1
    
    return output_file

# Crear la tabla al importar el módulo
create_tts_section_table()

# Ejemplo de uso
texto = "Bienvenidos al boletín dominical de la Federación Mexicana de Radio Experimentadores A.C."
#tts(texto, "test.mp3", 150)
