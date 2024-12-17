from os import environ
environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
import pygame
import time
import locale
from datetime import datetime
from mutagen.mp3 import MP3
from tts import tts

# Configura la localización a español
locale.setlocale(locale.LC_TIME, 'es_ES')

# Inicializamos Pygame y el mixer
pygame.init()
pygame.mixer.init()

# Configuración del puerto serie 
#puerto = 'COM12' # Reemplaza 'COM3' con el puerto correcto en tu sistema (ej. /dev/ttyS1 en Linux) 
#baudrate = 9600 # Velocidad de baudios, debe coincidir con la configuración del dispositivo

fecha = datetime.now()
fecha = fecha.strftime("%A, %d de %B de %Y")

#Definimos Mensajes de Bienvenida
mensaje_entrada = """Bienvenidos al boletín dominical de la Federación Mexicana de Radio Experimentadores A C. 
Gracias por sintonizarnos, en un instante iniciamos. 
Esta es una transmisión automátizada mediante la aplicación HAMNA"""

mensaje_salida = (f"""Gracias por sintonizar el boletín dominical de la Federación Mexicana de Radio Experimentadores A C. 
Hemos terminado con nuestra emisión de este día {fecha}. 
Les recordamos que esta es una transmisión automátizada mediante la aplicación HAMNA, desarrollada por el Radio Club Guadiana A C.
Agradecemos por escuchar este medio de dufusión de la máxima autoridad de radio afición en nuestro país, 
hasta la próxima edición, 73 y feliz día.""")

#Generamos los audios de entrada y de salida
# Generamos audio de entrada
tts(mensaje_entrada,"audio_entrada.mp3",120)
# Generamos audio de salida
tts(mensaje_salida,"audio_salida.mp3",120)


#Definimos archivos
boletin = 'FMRE.mp3'
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

#Obtenemos la duracion de los archivos
boletin_load = MP3(boletin)
boletin_length = boletin_load.info.length
pausa_load = MP3(pausa)
pausa_length = pausa_load.info.length
continua_load = MP3(continua)
continua_length = continua_load.info.length

# Función para reproducir audio desde una posición específica
def play_audio_from_position(start_pos):
    pygame.mixer.music.play(start=0)
    pygame.mixer.music.set_pos(start_pos)

def sound_length(sound_file):
    load = MP3(sound_file)
    length = load.info.length
    #length = int(length)
    print(length)
    return length


# Duración de reproducción antes de la pausa (en segundos)
play_duration = 1 * 30  # 3 minutos en segundos
pause_duration = 8  # 5 segundos de pausa

# Posición inicial del audio (en segundos)
initial_position = 425  # por ejemplo, iniciar desde los 120 segundos (2 minutos)

# Reproduce el archivo de audio principal desde la posición inicial
#play_audio_from_position(initial_position)


entry_message.play()
#wait=sound_length(entry_message)
#wait = int(wait)
time.sleep(20)
pygame.mixer.music.play()


print(f"""########### R A D I O  C L U B   G U A D I A N A  A . C .##############
      
          Duracion del Audio del Boletin: {boletin_length} segundos
          Nombre del archivo: {boletin_length}
          Reprodución desde: {initial_position} segundos
          
          
          derecho reservados @rcg.org.mx
          """)

# Ciclo de reproducción y pausa
while pygame.mixer.music.get_busy():
    start_time = time.time()

    # Reproducción del audio durante 3 minutos
    for i in range(play_duration):
        if not pygame.mixer.music.get_busy():
            break
        remaining_time = play_duration - i
        print(f"Tiempo restante antes de la pausa: {remaining_time} segundos")
        
        # Reproduce el sonido de alerta cuando falten 5 segundos para la pausa
        if remaining_time == 5:
            print(f"Alerta de Pausa:  {remaining_time} segundos")
            alert_sound.play()
        
        time.sleep(1)

    # Pausar el audio por 5 segundos
    
    pygame.mixer.music.pause()
    pausa_message.play()
    print("Audio en pausa por 5 segundos...")
    print("PTT:OFF")

    time.sleep(7)

    # Reanudar la reproducción del audio
    print("PTT:ON")
    continue_message.play()
    time.sleep(continua_length)
    pygame.mixer.music.unpause()
    print("Boletin reanudado")

end_message.play()
time.sleep(1)
print("El Boletin de la FMRE a terminado de reproducirse.")
input("Pulsa Enter para salir")

