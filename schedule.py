import time
import subprocess
import os
import platform
import sys
from datetime import datetime, timedelta
from shutil import get_terminal_size

# === CONFIGURACIÓN ===
hora_objetivo_str = "08:59:50"  # Cambia aquí el formato HH:MM:SS
ruta_script = "cor.py"          # Nombre del script a ejecutar

# === FUNCIONES AUXILIARES ===
def limpiar_consola():
    os.system("cls" if platform.system() == "Windows" else "clear")

def archivo_existe(ruta):
    return os.path.isfile(ruta)

def formato_tiempo(segundos):
    hrs, rem = divmod(int(segundos), 3600)
    mins, secs = divmod(rem, 60)
    return f"{hrs:02}:{mins:02}:{secs:02}"

def barra_progreso(tiempo_total, restante):
    columnas = get_terminal_size((80, 20)).columns
    ancho_barra = min(50, columnas - 30)
    progreso = int((1 - (restante / tiempo_total)) * ancho_barra)
    return "[" + "█" * progreso + " " * (ancho_barra - progreso) + "]"

def color(texto, codigo):
    return f"\033[{codigo}m{texto}\033[0m"

# === VALIDACIÓN DE SCRIPT ===
if not archivo_existe(ruta_script):
    print(color(f"❌ Error: El archivo '{ruta_script}' no existe.", "91"))
    sys.exit(1)

# === CALCULAR HORA OBJETIVO CON SEGUNDOS ===
try:
    ahora = datetime.now()
    hoy = ahora.date()
    hora_objetivo = datetime.strptime(hora_objetivo_str, "%H:%M:%S").replace(
        year=hoy.year, month=hoy.month, day=hoy.day)
except ValueError:
    print(color("❌ Formato de hora inválido. Usa 'HH:MM:SS'", "91"))
    sys.exit(1)

if ahora > hora_objetivo:
    hora_objetivo += timedelta(days=1)

# === INICIO ===
limpiar_consola()
print(color(f"🚀 Esperando para ejecutar '{ruta_script}' a las {hora_objetivo.strftime('%Y-%m-%d %H:%M:%S')}\n", "96"))

tiempo_total = (hora_objetivo - datetime.now()).total_seconds()

while True:
    ahora = datetime.now()
    restante = (hora_objetivo - ahora).total_seconds()

    if restante <= 0:
        print("\n" + color("⏰ ¡Es hora! Ejecutando el script...\n", "93"))
        try:
            subprocess.run([sys.executable, ruta_script], check=True)
            print(color("✅ Script ejecutado exitosamente.", "92"))
        except subprocess.CalledProcessError as e:
            print(color(f"❌ Error al ejecutar el script: {e}", "91"))
        break
    else:
        tiempo_str = formato_tiempo(restante)
        barra = barra_progreso(tiempo_total, restante)
        print(f"\r⏳ {color(tiempo_str, '93')} {barra}", end="", flush=True)
        time.sleep(1)
