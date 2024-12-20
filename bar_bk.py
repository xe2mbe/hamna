from os import environ, system, name
environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
import pygame
import time
import locale
from datetime import datetime
from mutagen.mp3 import MP3
from tts import tts
import requests

# URL de la API 
# URL base de la API
BASE_URL = "http://192.168.1.37"

# Configura la localización a español
locale.setlocale(locale.LC_TIME, 'es_ES')

# Obtén la fecha actual y formatearla en español
fecha = datetime.now()
fecha = fecha.strftime("%A, %d de %B de %Y")

# Definimos Mensajes de Bienvenida
mensaje_entrada = """Bienvenidos al boletín dominical de la Federación Mexicana de Radio Experimentadores A C. 
Gracias por sintonizarnos, en un instante iniciamos. 
Esta es una transmisión automátizada mediante la aplicación HAMNA"""

mensaje_salida = (f"""Gracias por sintonizar el boletín dominical de la Federación Mexicana de Radio Experimentadores A C. 
Hemos terminado con nuestra emisión de este día {fecha}. 
Les recordamos que esta es una transmisión automátizada mediante la aplicación HAMNA, desarrollada por el Radio Club Guadiana A C.
Agradecemos por escuchar este medio de difusión de la máxima autoridad de radio afición en nuestro país, 
ahora damos paso a la estación control para que inicie la toma de reportes, hasta la próxima edición, 73 y feliz día.""")

# Función para convertir segundos a formato hh:mm:ss
def convert_seconds_to_hhmmss(seconds):
    return time.strftime('%H:%M:%S', time.gmtime(seconds))

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

# Generamos los audios de entrada y de salida
# Generamos audio de entrada
tts(mensaje_entrada, "audio_entrada.mp3", 120)
# Generamos audio de salida
tts(mensaje_salida, "audio_salida.mp3", 120)

# Inicializamos Pygame y el mixer
pygame.init()
pygame.mixer.init()

# Archivos
boletin = 'mi_audio.mp3'
alerta = 'beep-warning.mp3'
pausa = 'pausa.mp3'
continua = 'continuamos.mp3'
entrada = 'audio_entrada.mp3'
salida = 'audio_salida.mp3'

# Carga los archivos de audio
pygame.mixer.music.load(boletin)
alert_sound = pygame.mixer.Sound(alerta)
pausa_message = pygame.mixer.Sound(pausa)
continue_message = pygame.mixer.Sound(continua)
entry_message = pygame.mixer.Sound(entrada)
end_message = pygame.mixer.Sound(salida)

# Obtiene la duración del archivo
boletin_load = MP3(boletin)
boletin_length = boletin_load.info.length
boletin_length_formated = convert_seconds_to_hhmmss(boletin_load.info.length)

# Duración de reproducción antes de la pausa (en segundos)
play_duration = 150
pause_duration = 5
# Duración de retroceso al salir de la pausa (en segundos)
rewind_time = 5

# Posición inicial del audio (en segundos)
initial_position = 0

clear_screen()

print(f"""
          ################ H A M N A - Amateur Radio Network Automation #################
          ############ B y  R A D I O  C L U B   G U A D I A N A  A . C . ###############
      
          Nombre del archivo: {boletin}.
          Duración del audio del boletín: {boletin_length_formated} (hh:mm:ss).
          Retroceso de audio después de pausa: {rewind_time} segundos.
          Reprodución desde: {initial_position} segundos.
          
          
          © rcg.org.mx
          """)
ptt('on')
time.sleep(2)
entry_message.play()
#wait=sound_length(entry_message)
#wait = int(wait)
time.sleep(20)

# Función para manejar la reproducción y pausa
def manage_play_pause(play_duration, pause_duration, rewind_time, initial_position, boletin_length):
    total_elapsed_time = initial_position
    pygame.mixer.music.play(start=0)
    pygame.mixer.music.set_pos(initial_position)

    while pygame.mixer.music.get_busy():
        elapsed_time = 0

        # Reproducción hasta la pausa
        time_to_pause = play_duration
        while time_to_pause > 0 and pygame.mixer.music.get_busy():
            time.sleep(1)
            elapsed_time += 1
            total_elapsed_time += 1
            remaining_time = boletin_length - total_elapsed_time
            
            if time_to_pause == 5:
                alert_sound.play()
            clear_screen()  
            bar = progress_bar(total_elapsed_time, boletin_length)
            print(f"Tiempo restante del boletín: {convert_seconds_to_hhmmss(remaining_time)} {bar}")

            time_to_pause -= 1
        
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.pause()
            time.sleep(1)
            system('cls')
            print("Audio en pausa por 5 segundos...")
            pausa_message.play()
            time.sleep(4)
            ptt('off')
            time.sleep(pause_duration)

            # Reanudar la reproducción del audio retrocediendo unos segundos

            time.sleep(pause_duration)
            total_elapsed_time -= rewind_time  # Ajustar el tiempo total transcurrido
            pygame.mixer.music.set_pos(total_elapsed_time)  # Retroceder unos segundos
            ptt('on')
            time.sleep(1)
            continue_message.play()
            time.sleep(4)
            pygame.mixer.music.unpause()
            print(f"Boletín reanudado, retrocedido {rewind_time} segundos")

# Llamar a la función para manejar la reproducción y pausa
manage_play_pause(play_duration, pause_duration, rewind_time, initial_position, boletin_length)
ptt('on')
end_message.play()
clear_screen()
print("Reproducción finalizada.")
print("Reproduciendo mensaje de salida...")
time.sleep(45)
ptt('off')
input("################################## Pulsa Enter para salir ####################################")
