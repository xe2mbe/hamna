import time
from os import environ, system, name
import requests
import yaml
from mutagen.mp3 import MP3
from mutagen import MutagenError
import subprocess
import os
os.environ["PATH"] = r"C:\Python\ffmpeg\bin;" + os.environ["PATH"]

BASE_URL = "http://stn8422.ip.irlp.net"

# Función para convertir segundos a formato hh:mm:ss
def convert_seconds_to_hhmmss(seconds):
    return time.strftime('%H:%M:%S', time.gmtime(seconds))

# Función para convertir tiempo en formato hh:mm:ss a segundos
def convert_hhmmss_to_seconds(hhmmss):
    h, m, s = map(int, hhmmss.split(':'))
    return h * 3600 + m * 60 + s

# Función para generar una barra de estado
def progress_bar(current, total, bar_length=45):
    fraction = current / total
    arrow = int(fraction * bar_length) * '█'
    padding = (bar_length - len(arrow)) * '░'
    #return f'[{arrow}{padding}]'
    return f'\033[92m[{arrow}{padding}]\033'

def clear_screen():
    if name == 'nt':  # Para Windows
        _ = system('cls')
    else:  # Para macOS y Linux
        _ = system('clear')

# Función para consumir la API de PTT
def ptt(action):
    if action not in ["on", "off"]:
        raise ValueError("La acción debe ser 'on' o 'off'.")

    url = f"{BASE_URL}/ptt_{action}"
    response = requests.get(url)
    if response.status_code == 200:
        print(response.json())  # Muestra el mensaje de respuesta
    else:
        print(f"Error: {response.status_code}")
        
#def file_duration(file):
#    audio_info = MP3(file)
#    total_duration = audio_info.info.length
#    return total_duration

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

def convert_to_valid_mp3(raw_file,mp3name,path):
    #name = file
    #output_file = name.replace("raw_","",1)
    name = path+mp3name
    try:
        subprocess.run(
            ["ffmpeg", "-i", raw_file, "-vn", "-ar", "44100", "-ac", "2", "-b:a", "192k", name],
            check=True
        )
        return mp3name
    except subprocess.CalledProcessError as e:
        print(f"Error al convertir el archivo: {e}")
        return None

def load_config(file_path="cfg.yml"):
    with open(file_path, "r",encoding='utf-8') as file:
        return yaml.safe_load(file)

def resume(file_yaml):

    # Leer el archivo
    with open(file_yaml, "r", encoding="utf-8") as file:
        configuracion = yaml.safe_load(file)

    # Acceder a las secciones
    secciones = configuracion.get("secciones", [])
    # Imprimir detalles de cada sección
    resumen = []
    for idx, seccion in enumerate(secciones, start=1):
        file = str(seccion['archivo'])
        duration = file_duration(seccion['archivo'])
        #Calculamos la duracion de la reprodución
        play_duration = duration - (seccion['fin'] - seccion['inicio'])
        print(play_duration)
        play_duration = convert_seconds_to_hhmmss(play_duration)
        print(play_duration)
        #sect = {seccion['nombre']}
        duration = convert_seconds_to_hhmmss(duration)
        resumen.append(
            f"Sección {idx}: {file}\n"
            f"  Duración Total: {duration}\n"
            f"  Archivo: {seccion['archivo']}\n"
            f"    Reproduccion: {play_duration}\n"
            f"     Inicio: {seccion['inicio']}\n"
            f"     Fin: {seccion['fin']}\n"
        )
    return "\n".join(resumen)

def resume_menu(file_yaml):

    # Leer el archivo
    with open(file_yaml, "r", encoding="utf-8") as file:
        configuracion = yaml.safe_load(file)

    # Acceder a las secciones
    secciones = configuracion.get("secciones", [])
    total_secciones = len(configuracion["secciones"])  # Contar el número total de secciones
    resumen = []
    for idx, seccion in enumerate(secciones, start=1):
        file = str(seccion['archivo'])
        duration = file_duration(seccion['archivo'])
        duration = convert_seconds_to_hhmmss(duration)
        custom_play = convert_hhmmss_to_seconds(duration)
        #Calculamos la duracion de la reprodución
        inicio = convert_hhmmss_to_seconds(seccion['inicio'])
        fin = convert_hhmmss_to_seconds(seccion['fin'])
        play_duration = (fin - inicio)
        #print(play_duration)
        play_duration = convert_seconds_to_hhmmss(play_duration)
        #print(play_duration)
        resumen.append(
            f"Sección {idx}: {file}\n"
            f"  Duración Total: {duration}\n"
            f"  Archivo: {seccion['archivo']}\n"
            f"  Inicio: {seccion['inicio']}\n"
            f"  Fin: {seccion['fin']}\n"
        )
        index = idx
        duration_total = duration
        file_name = seccion['archivo']
        start = seccion['inicio']
        end = seccion['fin']
        print (f'''
                 Sección {index} de {total_secciones}:
                     Archivo: {file_name}
                     Duración Total del archivo: {duration_total}
                     Tiempo de reproduccion: {play_duration}
                        Inicio: {start}
                        Fin: {end}
        '''
        )
    print(f'''
          Tiempo de reproduccion total del boletín ( {total_secciones} secciones ): {duration_total}
        ''')
def get_fileNameMP3(yml_file,main_key,values_dict,find_key):
    # Cargar el archivo YAML
    with open(yml_file, 'r', encoding='utf-8') as archivo:
        datos = yaml.safe_load(archivo)
    alertas_dict = {alerta[values_dict]: alerta for alerta in datos[main_key]}
    #value_list = alertas_dict[value][list]
    find_value = alertas_dict.get(find_key)
    value = find_value['archivo']
    
    return value
