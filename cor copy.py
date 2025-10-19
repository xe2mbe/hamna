import sys, os
import signal
import pygame
import time
import locale
from datetime import datetime
from mutagen.mp3 import MP3
from textwrap import dedent
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
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((host, port))
    login_cmd = (
        f"Action: Login\r\n"
        f"Username: {user}\r\n"
        f"Secret: {password}\r\n"
        f"Events: on\r\n"
        f"\r\n"
    )
    s.sendall(login_cmd.encode())
    return s

def cos_monitor(shared_dict, host, port, user, password):
    ami_socket = connect_ami(host, port, user, password)
    buffer = ""
    shared_dict["COS"] = False

    try:
        while True:
            chunk = ami_socket.recv(4096).decode(errors="ignore")
            if not chunk:
                time.sleep(0.1)
                continue

            buffer += chunk
            while "\r\n\r\n" in buffer:
                raw_event, buffer = buffer.split("\r\n\r\n", 1)

                if "Event: RPT_RXKEYED" in raw_event:
                    lines = raw_event.split("\r\n")
                    event_data = {}
                    for line in lines:
                        if ": " in line:
                            k, v = line.split(": ", 1)
                            event_data[k.strip()] = v.strip()
                    if event_data.get("EventValue") == "1":
                        shared_dict["COS"] = True
                    else:
                        shared_dict["COS"] = False

    except Exception as e:
        print(f"[cos_monitor] Error en el monitor de COS: {e}")
    finally:
        ami_socket.close()

def start_cos_monitor(host, port, user, password):
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

def validar_archivos_y_duraciones(config):
    print("\nValidando archivos y duraciones definidos en cfg.yml...\n")
    errores = []
    resumen = []
    total_boletin = 0

    for i, sec in enumerate(config["secciones"], 1):
        nombre = sec.get("nombre")
        archivo = sec.get("archivo")
        inicio = convert_hhmmss_to_seconds(sec.get("inicio"))
        fin = convert_hhmmss_to_seconds(sec.get("fin"))

        if not os.path.exists(archivo):
            errores.append(f"[ERROR] Archivo no encontrado: {archivo}")
            continue

        audio_info = MP3(archivo)
        duracion_real = int(audio_info.info.length)

        if inicio >= fin:
            errores.append(f"[ERROR] Inicio mayor o igual que fin en sección '{nombre}'")
            continue

        if fin > duracion_real:
            errores.append(f"[ERROR] Fin fuera del rango real en sección '{nombre}' (duración real: {duracion_real}s)")
            continue

        duracion = fin - inicio
        total_boletin += duracion
        resumen.append((nombre, convert_seconds_to_hhmmss(duracion)))

    for r in resumen:
        print(f"Sección: {r[0]:<30} Duración: {r[1]}")

    print(f"\nDuración total estimada del boletín: {convert_seconds_to_hhmmss(total_boletin)}\n")

    if errores:
        print("Se encontraron los siguientes errores:\n")
        for e in errores:
            print(e)
        print("\nCorrige los errores antes de continuar.")
        sys.exit(1)

    print("Todos los archivos y duraciones están correctos.\n")
    print("El boletín está listo para transmitirse.")

    print("\n¿Deseas iniciar la emisión? (Presiona Ctrl+C para cancelar)")
    try:
        for i in range(10, 0, -1):
            print(f"Iniciando en {i} segundos...", end="\r")
            time.sleep(1)
        print("\n")
    except KeyboardInterrupt:
        print("\nEmisión cancelada por el usuario.")
        sys.exit(0)

def main():
    clear_screen()

    def handle_exit_signal(signal_number, frame):
        print("\nInterrupción detectada. Deteniendo audio y desactivando PTT...")
        pygame.mixer.music.stop()
        ptt('off')
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_exit_signal)

    global config
    config = load_config()

    validar_archivos_y_duraciones(config)

    total_secciones = len(config["secciones"])
    locale.setlocale(locale.LC_TIME, 'es_ES')
    media_path = config["general"]["media_path"]
    fecha = datetime.now().strftime("%A, %d de %B de %Y")
    mensaje_entrada = config["mensajes"]["entrada"]
    mensaje_salida = config["mensajes"]["salida"].format(fecha=fecha)

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

    pygame.init()
    pygame.mixer.init()
    entry_message = pygame.mixer.Sound(entrada)
    end_message = pygame.mixer.Sound(salida)

    play_duration = config["duraciones"]["reproduccion"]
    pause_duration = config["duraciones"]["pausa"]
    alert_time = config["duraciones"]["alerta"]
    rewind_time = config["duraciones"]["retroceso"]

    user = config["ami"]["username"]
    password = config["ami"]["password"]
    host = config["ami"]["host"]
    port = config["ami"]["port"]

    shared_dict, cos_process = start_cos_monitor(host, port, user, password)

    # (Aquí sigue el resto del script con la reproducción y manejo de PTT)
    # ...

if __name__ == "__main__":
    freeze_support()
    main()
