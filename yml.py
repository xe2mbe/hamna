
from os import environ
import sys, os
import signal
import pygame
import time
import locale
from datetime import datetime
from mutagen.mp3 import MP3
from src.func.tts import tts
from src.func.functions import convert_seconds_to_hhmmss, convert_hhmmss_to_seconds, clear_screen, ptt, progress_bar, load_config, file_duration, resume,resume_menu

# Cargar configuración desde cfg.yml
config = load_config()

# Configuración general
locale.setlocale(locale.LC_TIME, config["general"]["locale"])
media_path = config["general"]["media_path"]

# Obtener fecha actual para los mensajes
fecha = datetime.now().strftime("%A, %d de %B de %Y")
mensaje_entrada = config["mensajes"]["entrada"]
mensaje_salida = config["mensajes"]["salida"].format(fecha=fecha)

# Generar audios de entrada y salida
entrada = media_path + "audio_entrada.mp3"
salida = media_path + "audio_salida.mp3"
tts(mensaje_entrada, entrada, 120)
tts(mensaje_salida, salida, 120)

# Inicializar Pygame y el mixer
pygame.init()
pygame.mixer.init()

# Cargar audios de entrada y salida
entry_message = pygame.mixer.Sound(entrada)
end_message = pygame.mixer.Sound(salida)

# Duraciones y tiempos
play_duration = config["duraciones"]["reproduccion"]
pause_duration = config["duraciones"]["pausa"]
alert_time = config["duraciones"]["alerta"]
rewind_time = config["duraciones"]["retroceso"]

# Función para manejar la reproducción de una sección
def play_section(section):
    #archivo = media_path + section["archivo"]
    archivo = section["archivo"]
    start_time = convert_hhmmss_to_seconds(section["inicio"])
    end_time = convert_hhmmss_to_seconds(section["fin"])

    # Validar límites
    audio_info = MP3(archivo)
    total_duration = audio_info.info.length

    if start_time >= total_duration or end_time > total_duration:
        raise ValueError(f"El tiempo de inicio o fin en la sección '{section['nombre']}' excede la duración del audio.")
    if start_time >= end_time:
        raise ValueError(f"El tiempo de inicio debe ser menor al tiempo de fin en la sección '{section['nombre']}'.")

    custom_duration = end_time - start_time

    pygame.mixer.music.load(archivo)
    pygame.mixer.music.play(start=0)
    pygame.mixer.music.set_pos(start_time)

    total_elapsed_time = start_time

    if custom_duration <= play_duration:
        while pygame.mixer.music.get_busy() and total_elapsed_time < end_time:
            time.sleep(1)
            total_elapsed_time += 1
            remaining_time = end_time - total_elapsed_time
            clear_screen()
            bar = progress_bar(total_elapsed_time - start_time, custom_duration)
            print(f"Sección '{section['nombre']}': Tiempo restante del boletín: {convert_seconds_to_hhmmss(remaining_time)} {bar}")
        pygame.mixer.music.stop()
        return

    while pygame.mixer.music.get_busy() and total_elapsed_time < end_time:
        elapsed_time = 0
        time_to_pause = play_duration

        while time_to_pause > 0 and total_elapsed_time < end_time:
            time.sleep(1)
            elapsed_time += 1
            total_elapsed_time += 1
            remaining_time = end_time - total_elapsed_time

            if total_elapsed_time >= end_time:
                pygame.mixer.music.stop()
                return

            if time_to_pause == alert_time:
                print(f"Sección '{section['nombre']}': Alerta de pausa...")
            clear_screen()
            bar = progress_bar(total_elapsed_time - start_time, custom_duration)
            print(f"Sección '{section['nombre']}': Tiempo restante del boletín: {convert_seconds_to_hhmmss(remaining_time)} {bar}")

            time_to_pause -= 1

        if total_elapsed_time < end_time:
            pygame.mixer.music.pause()
            print(f"Sección '{section['nombre']}': Pausa de {pause_duration} segundos.")
            
            time.sleep(pause_duration)
            total_elapsed_time -= rewind_time
            pygame.mixer.music.set_pos(total_elapsed_time)
            pygame.mixer.music.unpause()


# Reproducción principal
clear_screen()
print("Iniciando transmisión automatizada...")
#resumen = resume_menu("cfg.yml")
clear_screen()
print(f"""
           ################ H A M N A - Amateur Radio Network Automation #################
           ############ B y  R A D I O  C L U B   G U A D I A N A  A . C . ###############
      
           El boletin consta de las siguientes secciones:
      """)
resume_menu("cfg.yml")            

print(f"""         
           
           Un proyecto del Radio Club Guadiana A.C.
          
           Visita https://rcg.org.mx
           """)
#ptt("on")
time.sleep(2)
entry_message.play()
time.sleep(20)

for section in config["secciones"]:
    print(f"Reproduciendo sección: {section['nombre']}...")
    play_section(section)
    print(f"Sección '{section['nombre']}' finalizada.")

print("Reproducción finalizada. Reproduciendo mensaje de salida...")
end_message.play()
time.sleep(30)
#ptt("off")
input("Presiona Enter para salir...")
