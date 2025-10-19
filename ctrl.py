import serial
import time

SERIAL_PORT = 'COM13'
BAUDRATE = 9600

def send_command(ser, command):
    ser.write((command + '\r').encode())
    time.sleep(0.3)
    response = ser.read_all().decode().strip()
    return response or "[Sin respuesta]"

def read_menu_61(ser):
    print("🔎 Leyendo valor actual del menú 61A (crossband repeater)...")
    response = send_command(ser, "EX06101001;")
    print(f"Respuesta: {response}")



def main():
    try:
        ser = serial.Serial(
            port=SERIAL_PORT,
            baudrate=BAUDRATE,
            timeout=1,
            rtscts=False,
            dsrdtr=False,
            write_timeout=1
        )
        ser.dtr = False
        ser.rts = False

        read_menu_61(ser)

        ser.close()
        print("Conexión cerrada.")

    except serial.SerialException as e:
        print("Error de conexión:", e)

if __name__ == "__main__":
    main()
