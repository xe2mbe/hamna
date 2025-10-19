import sys, os
import signal
import pygame
import time
import locale
from datetime import datetime
from mutagen.mp3 import MP3
from textwrap import dedent, fill
from os import environ

# Módulos propios
from src.func.tts import tts
from src.func.functions import (
    convert_seconds_to_hhmmss, convert_hhmmss_to_seconds, clear_screen,
    ptt, progress_bar, load_config, file_duration, resume,
    resume_menu, get_fileNameMP3, convert_to_valid_mp3
)

# Para el monitoreo de COS en segundo plano
import socket
from multiprocessing import Manager, Process, freeze_support

############################################
# Funciones / Clases para monitor de COS   #
############################################
def connect_ami(host, port, user, password):
    """
    Se conecta al Asterisk Manager Interface y retorna el socket.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((host, port))
    login_cmd = (
        f"Action: Login\r\n"
        f"Username: {user}\r\n"
        f"Secret: {password}\r\n"
        f"Events: on\r\n"  # Importante para recibir eventos (RPT_RXKEYED, etc.)
        f"\r\n"
    )
    s.sendall(login_cmd.encode())
    return s

def cos_monitor(shared_dict, host, port, user, password):
    """
    Proceso que se mantiene leyendo AMI y 
    actualiza shared_dict["COS"] = True/False
    si detecta actividad en el HUB (RPT_RXKEYED).
    """
    ami_socket = connect_ami(host, port, user, password)
    buffer = ""
    shared_dict["COS"] = False  # Arrancamos asumiendo inactivo

    try:
        while True:
            chunk = ami_socket.recv(4096).decode(errors="ignore")
            if not chunk:
                time.sleep(0.1)
                continue

            buffer += chunk

            # Separar por eventos completos
            while "\r\n\r\n" in buffer:
                raw_event, buffer = buffer.split("\r\n\r\n", 1)

                if "Event: RPT_RXKEYED" in raw_event:
                    lines = raw_event.split("\r\n")
                    event_data = {}
                    for line in lines:
                        if ": " in line:
                            k, v = line.split(": ", 1)
                            event_data[k.strip()] = v.strip()

                    # Detectar COS (EventValue=1)
                    if event_data.get("EventValue") == "1":
                        shared_dict["COS"] = True
                    else:
                        # Suponemos que EventValue=0 => COS liberado
                        shared_dict["COS"] = False

    except Exception as e:
        print(f"[cos_monitor] Error en el monitor de COS: {e}")
    finally:
        ami_socket.close()

def start_cos_monitor(host, port, user, password):
    """
    Arranca el proceso monitor que actualizará shared_dict["COS"].
    Retorna (shared_dict, proceso).
    """
    manager = Manager()
    shared_dict = manager.dict()
    shared_dict["COS"] = False

    p = Process(
        target=cos_monitor,
        args=(shared_dict, host, port, user, password),
        daemon=True
    )
    p.start()
    return shared_dict, p


############################################
#                 MAIN SCRIPT             #
############################################
def main():
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
    # locale.setlocale(locale.LC_TIME, config["general"]["locale"])
    locale.setlocale(locale.LC_TIME, 'es_ES')
    media_path = config["general"]["media_path"]
    # Nuevo parámetro: nivel de volumen para TTS
    tts_volume = config["general"].get("tts_volume", 1.0)

    # Obtener fecha actual para los mensajes
    fecha = datetime.now().strftime("%A, %d de %B de %Y")
    mensaje_entrada = config["mensajes"]["entrada"]
    print(mensaje_entrada)
    mensaje_salida = config["mensajes"]["salida"].format(fecha=fecha)
    print(mensaje_salida)

    # Generar audios de entrada y salida
    raw_entrada = media_path + "raw_audio_entrada.mp3"
    raw_salida = media_path + "raw_audio_salida.mp3"
    tts(mensaje_entrada, raw_entrada, 120)
    time.sleep(5)
    convert_to_valid_mp3(raw_entrada, "audio_entrada.mp3", media_path)
    tts(mensaje_salida, raw_salida, 120)
    time.sleep(5)
    convert_to_valid_mp3(raw_salida, "audio_salida.mp3", media_path)
    entrada = media_path + "audio_entrada.mp3"
    salida = media_path + "audio_salida.mp3"

    # Inicializar Pygame y el mixer
    pygame.init()
    pygame.mixer.init()
    
    # Volumen global
    global_volume = float(config["general"].get("volume", 1.0))  # default 1.0

    # Cargar audios de entrada y salida
    entry_message = pygame.mixer.Sound(entrada)
    entry_message.set_volume(global_volume)
    end_message = pygame.mixer.Sound(salida)
    end_message.set_volume(global_volume)

    # Duraciones y tiempos
    play_duration = config["duraciones"]["reproduccion"]
    pause_duration = config["duraciones"]["pausa"]
    alert_time = config["duraciones"]["alerta"]
    rewind_time = config["duraciones"]["retroceso"]

    # Datos de AMI (para el monitor de COS)
    user = config["ami"]["username"]
    password = config["ami"]["password"]
    host = config["ami"]["host"]
    port = config["ami"]["port"]
    print("Usuario AMI:", user)
    print("Password AMI:", password)
    print("Host AMI:", host)
    print("Port AMI:", port)

    # Iniciar el proceso que monitoriza COS
    shared_dict, cos_process = start_cos_monitor(host, port, user, password)

    def play_section(section):
        global config

        archivo = section["archivo"]
        start_time = convert_hhmmss_to_seconds(section["inicio"])
        end_time = convert_hhmmss_to_seconds(section["fin"])

        # Validar límites
        audio_info = MP3(archivo)
        total_duration = audio_info.info.length

        if start_time >= total_duration or end_time > total_duration:
            ptt('off')
            raise ValueError(f"El tiempo de inicio o fin en la sección '{section['nombre']}' excede la duración del audio.")
        if start_time >= end_time:
            ptt('off')
            raise ValueError(f"El tiempo de inicio debe ser menor al tiempo de fin en la sección '{section['nombre']}'.")

        custom_duration = end_time - start_time
        media_path = config["general"]["media_path"]

        pygame.mixer.music.load(archivo)
        pygame.mixer.music.play(start=0)
        pygame.mixer.music.set_pos(start_time)

        alerta = get_fileNameMP3('cfg.yml','alertas','nombre','pause_alert')
        alert_sound = pygame.mixer.Sound(media_path + alerta)
        alert_sound.set_volume(0.8)

        pausa = get_fileNameMP3('cfg.yml','alertas','nombre','pause')
        pausa_message = pygame.mixer.Sound(media_path + pausa)
        pausa_message_idle = file_duration(media_path+pausa) + 1.5

        continua = get_fileNameMP3('cfg.yml','alertas','nombre','continuamos')
        continue_message = pygame.mixer.Sound(media_path + continua)
        continue_message_idle = file_duration(media_path+continua) + 1.5

        total_elapsed_time = start_time

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
                print(f"""
                ################################### HAMNA - Amateur Radio Net Automation ###################################
                
                   Sección '{section['nombre']}': Tiempo de Reproducción: {custom_duration} s.
                   La sección es menor a {play_duration} s, será reproducida sin pausas.
                   Tiempo restante de la sección: {convert_seconds_to_hhmmss(remaining_time)}
                   {bar.strip()}
                """)
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
                    print(f"Sección '{section['nombre']}': Alerta de pausa...")
                    alert_sound.play()

                clear_screen()
                bar = progress_bar(total_elapsed_time - start_time, custom_duration)
                print(f"""
                ################################### HAMNA - Amateur Radio Net Automation ###################################
                
                   Sección '{section['nombre']}': Tiempo de Reproducción: {custom_duration} s.
                   La sección será reproducida con pausas cada {play_duration} s.
                   Tiempo restante de la sección: {convert_seconds_to_hhmmss(remaining_time)}
                   {bar.strip()}
                """)

                time_to_pause -= 1

            if total_elapsed_time < end_time:
                # Pausa
                pygame.mixer.music.pause()
                time.sleep(1)
                clear_screen()
                print(f"Sección '{section['nombre']}': Pausa de {pause_duration} segundos.")
                pausa_message.play()
                time.sleep(pausa_message_idle)
                ptt('off')

                time.sleep(pause_duration)

                # Retrocede
                total_elapsed_time -= rewind_time
                pygame.mixer.music.set_pos(total_elapsed_time)

                # *** Aquí verificamos COS antes de reanudar ***
                print("Verificando si el HUB está ocupado (COS activo) antes de reanudar...")
                while shared_dict["COS"]:
                    print("COS activo, esperando...")
                    time.sleep(2)

                # HUB libre => Reanudamos
                ptt('on')
                time.sleep(1)
                continue_message.play()
                time.sleep(continue_message_idle)
                pygame.mixer.music.unpause()
                print(f"Boletín reanudado, retrocedido {rewind_time} segundos")

    # Reproducción principal
    clear_screen()
    print("Iniciando transmisión automatizada...")

    clear_screen()
    print(f"""
           ################ H A M N A - Amateur Radio Net Automation #################
           ############ B y  R A D I O  C L U B   G U A D I A N A  A . C . ###############
      
           El boletin consta de las siguientes {total_secciones} secciones:
    """)
    resume_menu("cfg.yml")
    print(f"""         
           Un proyecto del Radio Club Guadiana A.C.
           Visita https://rcg.org.mx
    """)

    while shared_dict["COS"]:
        print("COS activo antes de iniciar sección, esperando...")
        time.sleep(2)
    ptt("on")
    time.sleep(2)
    entry_message_idle = file_duration(entrada) + 1.5
    print(entry_message_idle)
    entry_message.play()
    time.sleep(entry_message_idle)
    ptt("off")
    time.sleep(6)
    clear_screen()

    for section in config["secciones"]:
        # Verifica COS antes de iniciar la sección
        while shared_dict["COS"]:
            print("COS activo antes de iniciar sección, esperando...")
            time.sleep(2)
        ptt("on")
        print(f"Reproduciendo sección: {section['nombre']}...")
        time.sleep(2)
        play_section(section)
        clear_screen()
        print(f"Sección '{section['nombre']}' finalizada.")
        time.sleep(2)
        ptt("off")
        time.sleep(8)


    while shared_dict["COS"]:
            print("COS activo antes de iniciar sección, esperando...")
            time.sleep(2)
    ptt("on")
    print("Reproducción finalizada. Reproduciendo mensaje de salida...")
    time.sleep(2)
    end_message_idle = file_duration(salida) + 1.5
    end_message.play()
    time.sleep(end_message_idle)
    ptt("off")

    # Finalizar el proceso monitor si deseas
    cos_process.terminate()
    print("Monitor de COS finalizado.")

    input("Presiona Enter para salir...")

############################################
#    Protección de bloque principal        #
############################################
if __name__ == "__main__":
    freeze_support()  # Recomendado en Windows para PyInstaller, etc.
    main()
