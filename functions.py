import time
from os import environ, system, name
import requests

BASE_URL = "http://192.168.1.37"

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