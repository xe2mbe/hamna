
from os import environ
import sys, os
import signal
import pygame
import time
import locale
from datetime import datetime
from mutagen.mp3 import MP3
from src.func.tts import tts
from textwrap import dedent, fill
from src.func.functions import  clear_screen, ptt, load_config, connect_ami, close_ami, hub_activity

clear_screen()
# Función para manejar CTRL+C
def handle_exit_signal(signal_number, frame):
    print("\nInterrupción detectada. Deteniendo audio y desactivando PTT...")
    pygame.mixer.music.stop()  # Detener música
    ptt('off')  # Apagar PTT
    sys.exit(0)  # Salir del programa

# Asignar el manejador de señal para SIGINT
signal.signal(signal.SIGINT, handle_exit_signal)

# Cargar configuración desde cfg.yml
global config
config = load_config()

total_secciones = len(config["secciones"])  # Contar el número total de secciones
# Configuración general
#locale.setlocale(locale.LC_TIME, config["general"]["locale"])
locale.setlocale(locale.LC_TIME, 'es_ES')
media_path = config["general"]["media_path"]

user=config["ami"]["username"]
print(user)
password=config["ami"]["password"]
print(password)
host=config["ami"]["host"]
print(host)
port=config["ami"]["port"]
print(port)

if __name__ == "__main__":
    # Conectar al AMI
    ami = connect_ami(host, port, user, password)
    #if not ami:
    #   sys.exit(1)
        
 # 2. Iniciamos el monitoreo en un bloque try-except
    try:
        cor=hub_activity(ami)
        print ("COS: ",cor)
        

    except KeyboardInterrupt:
        print("\nMonitoreo detenido por el usuario (Ctrl + C).")
    
    finally:
        # 3. Cerramos la conexión pase lo que pase
        close_ami(ami)
        sys.exit(0)  # Salimos del programa de forma limpia