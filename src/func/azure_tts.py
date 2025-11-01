import azure.cognitiveservices.speech as speechsdk
import ssl
import os
import json
from pathlib import Path
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

# ⚙️ Ajuste de SSL (soluciona fallos de handshake)
ssl._create_default_https_context = ssl._create_unverified_context

# 🧠 Obtener credenciales de variables de entorno
speech_key = os.getenv("AZURE_SPEECH_KEY")
service_region = os.getenv("AZURE_SPEECH_REGION")

if not speech_key or not service_region:
    raise ValueError("Por favor configura las variables de entorno AZURE_SPEECH_KEY y AZURE_SPEECH_REGION en el archivo .env")

# 📢 Habilitar logs para ver detalle del error
os.environ["SPEECHSDK_LOG_FILENAME"] = "speechsdk.log"
os.environ["SPEECHSDK_LOG_LEVEL"] = "1"

def get_available_voices():
    """Obtiene la lista de voces disponibles de Azure TTS"""
    try:
        # Configuración de Azure Speech
        speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=service_region)
        
        # Crear un sintetizador con configuración nula para evitar reproducción automática
        synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)
        
        # Obtener las voces disponibles
        result = synthesizer.get_voices_async().get()
        
        if result.reason == speechsdk.ResultReason.VoicesListRetrieved:
            voices = []
            for voice in result.voices:
                # Solo incluir voces neuronales
                if 'Neural' in voice.short_name:
                    # Extraer idioma y nombre
                    lang_code = voice.locale.split('-')[0]
                    voice_name = voice.short_name.split('-')[-1].replace('Neural', '')
                    display_name = f"{voice_name} ({voice.locale})"
                    
                    voices.append({
                        'name': voice.short_name,
                        'display_name': display_name,
                        'locale': voice.locale,
                        'gender': voice.gender.name,
                        'neural': 'Neural' in voice.short_name
                    })
            
            # Guardar en caché las voces
            cache_dir = os.path.join(Path.home(), '.hamna', 'cache')
            os.makedirs(cache_dir, exist_ok=True)
            cache_file = os.path.join(cache_dir, 'azure_voices.json')
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(voices, f, ensure_ascii=False, indent=2)
                
            return voices
        else:
            print(f"Error al obtener voces: {result.cancellation_details}")
            return []
            
    except Exception as e:
        print(f"Error al obtener voces de Azure: {str(e)}")
        # Intentar cargar desde caché si hay un error
        return load_voices_from_cache()

def refresh_voices_cache():
    """Actualiza la caché de voces de Azure"""
    try:
        voices = get_available_voices()
        if not voices:
            print("No se pudieron obtener las voces de Azure")
            return False
        return True
    except Exception as e:
        print(f"Error al actualizar la caché de voces: {str(e)}")
        return False

def load_voices_from_cache():
    """Carga las voces desde el caché local"""
    try:
        cache_file = os.path.join(Path.home(), '.hamna', 'cache', 'azure_voices.json')
        if os.path.exists(cache_file):
            with open(cache_file, 'r', encoding='utf-8') as f:
                voices = json.load(f)
                if voices:  # Verificar que la lista no esté vacía
                    return voices
                
        # Si no hay caché o está vacío, intentar actualizar
        if refresh_voices_cache():
            if os.path.exists(cache_file):
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
    except Exception as e:
        print(f"Error al cargar voces desde caché: {str(e)}")
    
    # Si todo falla, devolver una lista con una voz por defecto
    return [{
        'name': 'es-MX-DaliaNeural',
        'display_name': 'Dalia (es-MX)',
        'locale': 'es-MX',
        'gender': 'Female',
        'neural': True
    }]

def get_default_voice_config():
    """Obtiene la configuración de voz predeterminada"""
    return {
        'engine': 'azure',
        'voice': 'es-MX-DaliaNeural',
        'rate': '0%',
        'pitch': '0%',
        'volume': '100%'
    }

# Configuración predeterminada
speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=service_region)
speech_config.speech_synthesis_voice_name = get_default_voice_config()['voice']

def synthesize_text(text, voice_name=None, rate=None, pitch=None, volume=None, return_audio=False):
    """
    Sintetiza texto a voz usando Azure TTS
    
    Args:
        text (str): Texto a sintetizar
        voice_name (str, optional): Nombre de la voz a usar. Si no se especifica, usa la predeterminada.
        rate (str, optional): Velocidad de habla (ej: "+10%", "-10%").
        pitch (str, optional): Tono de voz (ej: "+10%", "-10%").
        volume (str, optional): Volumen (ej: "80%").
        return_audio (bool, optional): Si es True, retorna los datos de audio junto con el estado.
    """
    try:
        # Configurar voz si se especifica
        if voice_name:
            speech_config.speech_synthesis_voice_name = voice_name
            
        # Configurar SSML con opciones adicionales si se proporcionan
        ssml = (f"<speak version='1.0' xml:lang='{speech_config.speech_synthesis_voice_name[:5]}' "
                f"xmlns='http://www.w3.org/2001/10/synthesis'>"
                f"<voice name='{speech_config.speech_synthesis_voice_name}'>"
                f"<prosody rate='{rate or '0%'}' pitch='{pitch or '0%'}' volume='{volume or '100%'}'>"
                f"{text}"
                "</prosody></voice></speak>")
        
        # Configurar salida de audio
        if return_audio:
            # Usar un stream en memoria para capturar el audio
            audio_stream = speechsdk.audio.PullAudioOutputStream()
            audio_config = speechsdk.audio.AudioOutputConfig(stream=audio_stream)
        else:
            # Usar el altavoz por defecto
            audio_config = speechsdk.audio.AudioOutputConfig(use_default_speaker=True)
            
        synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
        
        # Sintetizar voz
        result = synthesizer.speak_ssml_async(ssml).get()
        
        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            if return_audio:
                # Obtener los datos de audio del stream
                audio_data = result.audio_data
                return True, audio_data
            return True, "Voz generada correctamente"
        else:
            error_msg = f"Error en la síntesis de voz: {result.cancellation_details.reason}"
            if result.cancellation_details.reason == speechsdk.CancellationReason.Error:
                error_msg += f"\nDetalles: {result.cancellation_details.error_details}"
            return False, error_msg
            
    except Exception as e:
        return False, f"Error al sintetizar voz: {str(e)}"
