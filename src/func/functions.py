import time
from os import environ, system, name
import requests
import yaml
from mutagen.mp3 import MP3

BASE_URL = "http://stn8422.ip.irlp.net"

# Función para convertir segundos a formato hh:mm:ss
def convert_seconds_to_hhmmss(seconds):
    return time.strftime('%H:%M:%S', time.gmtime(seconds))

# Función para convertir tiempo en formato hh:mm:ss a segundos
def convert_hhmmss_to_seconds(hhmmss):
    h, m, s = map(int, hhmmss.split(':'))
    return h * 3600 + m * 60 + s

# Función para generar una barra de estado
def progress_bar(current, total, bar_length=50):
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
        
def file_duration(file):
    audio_info = MP3(file)
    total_duration = audio_info.info.length
    return total_duration

def load_config(file_path="cfg.yml"):
    with open(file_path, "r") as file:
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
        sect = {seccion['nombre']}
        duration = convert_seconds_to_hhmmss(duration)
        resumen.append(
            f"Sección {idx}: {file}\n"
            f"  Duración Total: {duration}\n"
            f"  Archivo: {seccion['archivo']}\n"
            f"  Inicio: {seccion['inicio']}\n"
            f"  Fin: {seccion['fin']}\n"
        )
    return "\n".join(resumen)

def resume_menu(file_yaml):

    # Leer el archivo
    with open(file_yaml, "r", encoding="utf-8") as file:
        configuracion = yaml.safe_load(file)

    # Acceder a las secciones
    secciones = configuracion.get("secciones", [])
    resumen = []
    for idx, seccion in enumerate(secciones, start=1):
        file = str(seccion['archivo'])
        duration = file_duration(seccion['archivo'])
        duration = convert_seconds_to_hhmmss(duration)
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
                 Sección {index}:
                     Archivo: {file_name}
                     Duración Total del archivo: {duration_total}
                     Inicio: {start}
                     Fin: {end}
        '''
        )
    #return resumen
#resumen = resume_menu("cfg.yml")
#print(resumen)