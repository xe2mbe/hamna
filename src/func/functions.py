import time
from os import environ, system, name
import requests
import yaml
from mutagen.mp3 import MP3
from mutagen import MutagenError
import subprocess
import os
import socket
import hid
import urllib.request
import urllib.error
os.environ["PATH"] = r"C:\ffmpeg\bin;" + os.environ["PATH"]

BASE_URL = "http://stn8422.ip.irlp.net"
BASE_URL = "http://192.168.1.37"

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

def convert_to_valid_mp3(raw_file, mp3name, path):
    # Ruta completa del archivo de salida
    output_file = os.path.join(path, mp3name)
    
    # Verificar si el archivo ya existe y eliminarlo
    if os.path.exists(output_file):
        os.remove(output_file)
        print(f"Archivo existente eliminado: {output_file}")
    
    try:
        # Ejecutar FFmpeg para convertir el archivo
        subprocess.run(
            ["ffmpeg", "-i", raw_file, "-vn", "-ar", "44100", "-ac", "2", "-b:a", "192k", output_file],
            check=True
        )
        print(f"Archivo convertido y guardado como: {output_file}")
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

def connect_ami(host, port, username, password):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((host, port))
        s.sendall(f"Action: Login\nUsername: {username}\nSecret: {password}\n\n".encode())
        return s
    except Exception as e:
        print(f"Error al conectar con AMI: {e}")
        return None

def close_ami(ami_socket):
    """
    Cierra la conexión AMI de forma explícita.
    """
    if ami_socket:
        try:
            ami_socket.close()
            print("Socket AMI cerrado exitosamente.")
        except Exception as e:
            print(f"Ocurrió un error al cerrar el socket: {e}")
    else:
        print("El socket ya está cerrado o no fue inicializado.")
def hub_activity(ami_socket):
    """
    Escucha eventos AMI desde un nodo HUB y muestra cuándo un nodo
    comienza (EventValue=1) o termina (EventValue=0) de transmitir (RPT_RXKEYED).
    """
    try:
        buffer = ""
        while True:
            # Recibir datos en 'chunks'
            chunk = ami_socket.recv(4096).decode(errors='ignore')
            if not chunk:
                break

            buffer += chunk
            # Procesar eventos completos separados por doble salto de línea
            while "\r\n\r\n" in buffer:
                raw_event, buffer = buffer.split("\r\n\r\n", 1)
                #print(raw_event)

                # Verificamos si es un evento RPT_RXKEYED
                if "ChannelStateDesc: Rsrvd" in raw_event:
                    cos = True
                    return cos
    except KeyboardInterrupt:
        print("Saliendo con CTRL+C...")


# ---------------- Desktop branch backend helpers (extracted from src/ui/app.py) ----------------

def parse_int(s: str, default=None):
    try:
        s = (s or "").strip()
        if not s:
            return default
        return int(s, 0)
    except Exception:
        return default

def cfg_paths():
    app_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.abspath(os.path.join(app_dir, "..", ".."))
    return (
        os.path.join(root_dir, "cfg.yaml"),
        os.path.join(root_dir, "cfg.yml"),
    )

def read_cfg():
    cfg_yaml, cfg_yml = cfg_paths()
    data = {}
    used = None
    if os.path.exists(cfg_yaml):
        try:
            with open(cfg_yaml, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except Exception:
            data = {}
        used = cfg_yaml
    elif os.path.exists(cfg_yml):
        try:
            with open(cfg_yml, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except Exception:
            data = {}
        used = cfg_yml
    return data, used

def save_cfg(settings: dict | None, ami: dict | None, radio: dict | None, api: dict | None, tts: dict | None = None):
    cfg_yaml, _ = cfg_paths()
    existing = {}
    if os.path.exists(cfg_yaml):
        try:
            with open(cfg_yaml, "r", encoding="utf-8") as f:
                existing = yaml.safe_load(f) or {}
        except Exception:
            existing = {}
    if settings is not None:
        existing.setdefault("settings", {}).update(settings)
    if ami is not None:
        existing.setdefault("ami", {}).update(ami)
    if radio is not None:
        existing.setdefault("radio_interface", {}).update(radio)
    if api is not None:
        existing.setdefault("api", {}).update(api)
    if tts is not None:
        existing.setdefault("tts", {}).update(tts)
    with open(cfg_yaml, "w", encoding="utf-8") as f:
        yaml.safe_dump(existing, f, allow_unicode=True, sort_keys=False)
    return cfg_yaml

# HID helpers
def hid_enumerate_filtered():
    devices = []
    labels = []
    for d in hid.enumerate():
        man = (d.get("manufacturer_string") or "")
        prod = (d.get("product_string") or "")
        vid = d.get("vendor_id")
        pid = d.get("product_id")
        if vid == 0x0D8C or "C-Media" in man or "C-Media" in prod or "USB Audio" in prod:
            devices.append(d)
            labels.append(f"{vid:04x}:{pid:04x}  {man} {prod}".strip())
    return devices, labels

def hid_open_device(d):
    dev = hid.device()
    path = d.get("path")
    if path:
        dev.open_path(path)
    else:
        dev.open(d.get("vendor_id"), d.get("product_id"))
    try:
        dev.set_nonblocking(True)
    except Exception:
        pass
    return dev

def hid_close_device(dev):
    try:
        dev.close()
    except Exception:
        pass

def hid_set_ptt(dev, ptt_bit: int, state: bool, invert: bool = False):
    if not dev:
        return False
    out_state = state if not invert else (not state)
    buf = bytes([0x00, ptt_bit if out_state else 0x00, 0x00, 0x00])
    try:
        dev.send_feature_report(buf)
        return True
    except Exception:
        try:
            dev.set_output_report(0x00, buf)
            return True
        except Exception:
            dev.write(buf)
            return True

def hid_read_cos(dev, cos_bit: int, invert: bool = True):
    if not dev:
        return None
    data = None
    try:
        data = dev.read(8, 50)
    except Exception:
        data = None
    if not data:
        try:
            data = dev.get_input_report(0x01, 4)
        except Exception:
            data = None
    if not data:
        return None
    try:
        b1 = data[1] if len(data) > 1 else 0
    except Exception:
        b1 = 0
    measured = bool(b1 & cos_bit)
    return (not measured) if invert else measured

# API helpers
def api_join(base: str, path: str) -> str:
    b = (base or "").rstrip("/")
    p = (path or "").strip()
    if not p:
        return b
    if not p.startswith("/"):
        p = "/" + p
    return b + p

def api_get(url: str, timeout: float = 5.0):
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.getcode(), resp.read()

# AMI test helper
def ami_test_connection(host: str, port: int, user: str, password: str):
    try:
        with socket.create_connection((host, int(port)), timeout=5) as s:
            s.settimeout(3)
            try:
                _banner = s.recv(1024).decode(errors="ignore")
            except Exception:
                _banner = ""
            login_cmd = (
                f"Action: Login\r\n"
                f"Username: {user}\r\n"
                f"Secret: {password}\r\n"
                f"Events: off\r\n\r\n"
            )
            s.sendall(login_cmd.encode())
            buf = ""
            deadline = time.time() + 5
            while time.time() < deadline:
                try:
                    chunk = s.recv(4096)
                    if not chunk:
                        break
                    buf += chunk.decode(errors="ignore")
                    if "Response:" in buf:
                        break
                except socket.timeout:
                    break
            ok = ("Response: Success" in buf and "Authentication failed" not in buf) or "Authentication accepted" in buf
            return ok, (buf.strip()[:600] or _banner.strip()[:600])
    except Exception as e:
        return False, str(e)

