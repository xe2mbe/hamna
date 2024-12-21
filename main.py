from os import environ, system
import sys
import signal
environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
import pygame
import time
import locale
from datetime import datetime
from mutagen.mp3 import MP3
from src.func.tts import tts
from src.func.functions import convert_seconds_to_hhmmss, convert_hhmmss_to_seconds, clear_screen, ptt, progress_bar

# Función para manejar CTRL+C
def handle_exit_signal(signal_number, frame):
    print("\nInterrupción detectada. Deteniendo audio y desactivando PTT...")
    pygame.mixer.music.stop()  # Detener música
    ptt('off')  # Apagar PTT
    sys.exit(0)  # Salir del programa

# Asignar el manejador de señal para SIGINT
signal.signal(signal.SIGINT, handle_exit_signal)

# Configura la localización a español
locale.setlocale(locale.LC_TIME, 'es_ES')

# Obtén la fecha actual y formatearla en español
fecha = datetime.now()
fecha = fecha.strftime("%A, %d de %B de %Y")

# Mensajes de bienvenida y salida
mensaje_entrada = """Bienvenidos al boletín dominical de la Federación Mexicana de Radio Experimentadores A C. 
Gracias por sintonizarnos, en un instante iniciamos. 
Esta es una transmisión automátizada mediante la aplicación HAMNA"""

mensaje_salida = (f"""Gracias por sintonizar el boletín dominical de la Federación Mexicana de Radio Experimentadores A C. 
Hemos terminado con nuestra emisión de este día {fecha}. 
Les recordamos que esta es una transmisión automátizada mediante la aplicación HAMNA, desarrollada por el Radio Club Guadiana A C.
Agradecemos por escuchar este medio de difusión de la máxima autoridad de radio afición en nuestro país, 
ahora damos paso a la estación control para que inicie la toma de reportes, hasta la próxima edición, 73 y feliz día.""")

# Generar audios de entrada y salida
tts(mensaje_entrada, "audio_entrada.mp3", 120)
tts(mensaje_salida, "audio_salida.mp3", 120)

# Inicializar Pygame y el mixer
pygame.init()
pygame.mixer.init()

# Archivos de audio
boletin = 'FMRE.mp3'
alerta = 'pause_alert2.mp3'
pausa = 'pausa.mp3'
continua = 'continuamos.mp3'
entrada = 'audio_entrada.mp3'
salida = 'audio_salida.mp3'

# Carga archivos de audio
pygame.mixer.music.load(boletin)
alert_sound = pygame.mixer.Sound(alerta)
alert_sound.set_volume(1.0) 
pausa_message = pygame.mixer.Sound(pausa)
continue_message = pygame.mixer.Sound(continua)
entry_message = pygame.mixer.Sound(entrada)
end_message = pygame.mixer.Sound(salida)

# Obtén la duración total del audio
boletin_load = MP3(boletin)
boletin_length = boletin_load.info.length
boletin_length_formatted = convert_seconds_to_hhmmss(boletin_length)

# Configuración de parámetros
play_duration = 150
pause_duration = 8
alert_time = 7
rewind_time = 3

# Configurar tiempos de inicio y fin (en formato hh:mm:ss)
start_time_str = "00:00:00"
end_time_str = "00:30:07"

# Convertir tiempos a segundos
start_time = convert_hhmmss_to_seconds(start_time_str)
end_time = convert_hhmmss_to_seconds(end_time_str)

# Validar límites
if start_time >= boletin_length or end_time > boletin_length:
    raise ValueError("El tiempo de inicio o fin excede la duración del boletín.")
if start_time >= end_time:
    raise ValueError("El tiempo de inicio debe ser menor al tiempo de fin.")

# Nueva duración para este intervalo
custom_duration = end_time - start_time

clear_screen()

print(f"""
          ################ H A M N A - Amateur Radio Network Automation #################
          ############ B y  R A D I O  C L U B   G U A D I A N A  A . C . ###############
      
          Nombre del archivo: {boletin}.
          Duración del total del archivo: {boletin_length_formatted}
          Intervalo de reproducción seleccionado: {start_time_str} - {end_time_str}
          Duración del intervalo seleccionado: {convert_seconds_to_hhmmss(custom_duration)} (hh:mm:ss).
          Retroceso de audio después de pausa: {rewind_time} segundos.
          
          © rcg.org.mx
          """)
ptt('on')
time.sleep(2)
entry_message.play()
time.sleep(20)

# Función para manejar reproducción y pausas
def manage_play_pause(play_duration, pause_duration, alert_time, rewind_time, start_time, end_time, custom_duration):
    total_elapsed_time = start_time
    pygame.mixer.music.play(start=0)
    pygame.mixer.music.set_pos(start_time)

    if custom_duration <= play_duration:
        # Reproducción continua sin pausas
        print("Duración menor a play_duration, reproduciendo sin pausas...")
        while pygame.mixer.music.get_busy() and total_elapsed_time < end_time:
            time.sleep(1)
            total_elapsed_time += 1
            remaining_time = end_time - total_elapsed_time
            if total_elapsed_time >= end_time:
                break
            clear_screen()
            bar = progress_bar(total_elapsed_time - start_time, custom_duration)
            print(f"Tiempo restante del boletín: {convert_seconds_to_hhmmss(remaining_time)} {bar}")
        pygame.mixer.music.stop()
        return

    # Reproducción con pausas
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
                alert_sound.play()
            clear_screen()
            bar = progress_bar(total_elapsed_time - start_time, custom_duration)
            print(f"Tiempo restante del boletín: {convert_seconds_to_hhmmss(remaining_time)} {bar}")

            time_to_pause -= 1

        if total_elapsed_time < end_time:
            pygame.mixer.music.pause()
            clear_screen()
            print("Audio en pausa por 5 segundos...")
            pausa_message.play()
            time.sleep(3)
            ptt('off')
            time.sleep(pause_duration)
            total_elapsed_time -= rewind_time
            pygame.mixer.music.set_pos(total_elapsed_time)
            ptt('on')
            time.sleep(1)
            continue_message.play()
            time.sleep(4)
            pygame.mixer.music.unpause()
            print(f"Boletín reanudado, retrocedido {rewind_time} segundos")

# Llamar a la función para manejar la reproducción
manage_play_pause(play_duration, pause_duration, alert_time, rewind_time, start_time, end_time, custom_duration)

ptt('on')
end_message.play()
clear_screen()
print("Reproducción finalizada.")
print("Reproduciendo mensaje de salida...")
time.sleep(45)
ptt('off')
input("################################## Pulsa Enter para salir ####################################")

