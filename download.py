import os
from yt_dlp import YoutubeDL
from imageio_ffmpeg import get_ffmpeg_exe

def descargar_audio(url, nombre_archivo="audio", dest_dir=None):
    if dest_dir is None:
        script_path = os.path.dirname(os.path.abspath(__file__))
        dest_dir = os.path.join(script_path, "media", "audios")
    os.makedirs(dest_dir, exist_ok=True)

    opciones = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': os.path.join(dest_dir, f"{nombre_archivo}.%(ext)s"),
        'quiet': False,
        'ffmpeg_location': get_ffmpeg_exe(),  # Usar FFmpeg de imageio
    }

    with YoutubeDL(opciones) as ydl:
        ydl.download([url])

def get_metadata(url):
    # Configuración de yt-dlp
    ydl_opts = {
        'quiet': True,  # Silencia los mensajes innecesarios
        'skip_download': True,  # No descarga el video
        'format': 'best'  # Usa el mejor formato disponible (solo para metadatos)
    }

    # Extrae información del video
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        title = info.get('title')  # Título del video
        channel = info.get('uploader') 
        # Nombre del canal o autor

    # Imprime los resultados
    print(info)
    print(f"Título del video: {title}")
    print(f"Canal o autor: {channel}")


# URL del video de Facebook
url_video = "https://www.youtube.com/watch?v=WuY86jOIzfk"
#media_path = '\\src\\media\\'
nombre_archivo = "lora"
#archivo = media_path + nombre_archivo

# Descargar el audio
descargar_audio(url_video, nombre_archivo)
#get_metadata(url_video)
script_path = os.path.dirname(os.path.abspath(__file__))
dest_dir_main = os.path.join(script_path, "media", "audios")
print(f"Audio descargado como {os.path.join(dest_dir_main, nombre_archivo + '.mp3')}")
