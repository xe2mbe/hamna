import os
from yt_dlp import YoutubeDL
from imageio_ffmpeg import get_ffmpeg_exe

def descargar_audio_facebook(url, nombre_archivo="audio.mp3"):
    opciones = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': f"{nombre_archivo}",
        'quiet': False,
        'ffmpeg_location': get_ffmpeg_exe(),  # Usar FFmpeg de imageio
    }

    with YoutubeDL(opciones) as ydl:
        ydl.download([url])

# URL del video de Facebook
url_video = "https://www.youtube.com/watch?v=vzfECgHjXTI"
nombre_archivo = "radioaficion"

# Descargar el audio
descargar_audio_facebook(url_video, nombre_archivo)
print(f"Audio descargado como {nombre_archivo}")
