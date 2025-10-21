from mutagen.mp3 import MP3
from mutagen import MutagenError
import subprocess
import os
os.environ["PATH"] = r"C:\Python\ffmpeg\bin;" + os.environ["PATH"]

def file_duration(file):
    try:
        # Asegúrate de que sea un archivo MP3 válido
        audio_info = MP3(file)
        total_duration = audio_info.info.length
        return total_duration
    except MutagenError as e:
        print(f"Error al procesar el archivo: {file}. Detalles: {e}")
        return 0  # Retorna 0 o lanza una excepción personalizada
    except Exception as e:
        print(f"Ocurrió un error inesperado: {e}")
        return 0

def convert_to_valid_mp3(file):
    output_file = "converted_" + file
    try:
        subprocess.run(
            ["ffmpeg", "-i", file, "-vn", "-ar", "44100", "-ac", "2", "-b:a", "192k", output_file],
            check=True
        )
        return output_file
    except subprocess.CalledProcessError as e:
        print(f"Error al convertir el archivo: {e}")
        return None



test = convert_to_valid_mp3 ("audio_entrada.mp3")

test = file_duration("audio_entrada.mp3")

print(test)