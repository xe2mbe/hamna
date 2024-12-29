import schedule
import time
import subprocess  # Para ejecutar el script .bat

def ejecutar_bat():
    subprocess.run(["hamna.bat"], shell=True)  # Cambia la ruta por la correcta

# Programa la tarea
schedule.every().sunday.at("09:00").do(ejecutar_bat)  # Cambia "18:23" por la hora deseada (24h)

print("Esperando para ejecutar el script .bat...")
while True:
    schedule.run_pending()
    time.sleep(1)
