import azure.cognitiveservices.speech as speechsdk
import ssl
import os
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

# 🔊 Configuración del servicio
speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=service_region)
speech_config.speech_synthesis_voice_name = "es-MX-DaliaNeural"

# 🎧 Usar bocina local (no archivo)
audio_config = speechsdk.audio.AudioOutputConfig(use_default_speaker=True)

synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)

# 🗣️ Texto de prueba
text = "Hola Eliud, esta es una prueba del servicio de voz de Azure."

print("🟢 Iniciando síntesis de voz...")
result = synthesizer.speak_text_async(text).get()

if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
    print("✅ Voz generada correctamente.")
elif result.reason == speechsdk.ResultReason.Canceled:
    cancellation = result.cancellation_details
    print("❌ Error:", cancellation.reason)
    if cancellation.reason == speechsdk.CancellationReason.Error:
        print("Detalles:", cancellation.error_details)
        print("Revisa también el archivo: speechsdk.log")
