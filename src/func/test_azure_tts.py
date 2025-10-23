import azure.cognitiveservices.speech as speechsdk
import ssl
import os
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

# Ajuste de SSL (soluciona fallos de handshake)
ssl._create_default_https_context = ssl._create_unverified_context

# Obtener credenciales de variables de entorno
speech_key = os.getenv("AZURE_SPEECH_KEY")
service_region = os.getenv("AZURE_SPEECH_REGION")

if not speech_key or not service_region:
    raise ValueError("Por favor configura las variables de entorno AZURE_SPEECH_KEY y AZURE_SPEECH_REGION en el archivo .env")

speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=service_region)
speech_config.speech_synthesis_voice_name = "es-MX-DaliaNeural"

# Ruta absoluta garantizada (usa tu carpeta de proyecto)
output_path = os.path.join(os.getcwd(), "voz_generada.mp3")
print("📁 Guardando en:", output_path)

audio_config = speechsdk.audio.AudioOutputConfig(filename=output_path)

synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
texto = "Hola, esta es una prueba de guardado en archivo de voz."

result = synthesizer.speak_text_async(texto).get()

if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
    print("✅ Archivo generado correctamente:", output_path)
else:
    print("❌ Error:", result.cancellation_details.reason)
    print("Detalles:", result.cancellation_details.error_details)
