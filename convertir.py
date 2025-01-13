import os
import subprocess
from asterisk.ami import AMIClient
import logging

def convertir_a_wav(archivo_audio):
    """
    Convierte un archivo de audio a formato WAV usando ffmpeg
    """
    nombre_archivo, extension = os.path.splitext(archivo_audio)
    if extension.lower() != ".wav":
        # Define el nombre del archivo de salida
        archivo_salida = nombre_archivo + ".wav"
        
        try:
            # Ejecuta la conversión usando ffmpeg
            comando = f"ffmpeg -i {archivo_audio} -ar 8000 -ac 1 -f wav {archivo_salida}"
            subprocess.run(comando, shell=True, check=True)
            logging.info(f"Archivo convertido exitosamente a WAV: {archivo_salida}")
            return archivo_salida
        except subprocess.CalledProcessError as e:
            logging.error(f"Error al convertir el archivo: {e}")
            return None
    else:
        logging.info("El archivo ya está en formato WAV.")
        return archivo_audio
    
wav = convertir_a_wav("Boletín FMRE 29 Dic 2024_normalized.wav")
    