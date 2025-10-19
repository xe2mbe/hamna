import serial
import time
import streamlit as st

SERIAL_PORT = 'COM13'
BAUDRATE = 9600

MODES = {
    '1': 'LSB',
    '2': 'USB',
    '3': 'CW',
    '4': 'FM',
    '5': 'AM',
    '6': 'FSK',
    '7': 'CW-R',
    '8': 'FSK-R'
}

@st.cache_resource
def init_serial():
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
        return ser
    except Exception as e:
        st.error(f"No se pudo abrir el puerto {SERIAL_PORT}: {e}")
        return None

def send_command(ser, command):
    if not command.endswith(';'):
        command += ';'
    ser.write(command.encode())
    time.sleep(0.3)
    response = ser.read_all().decode().strip()
    return response or "[Sin respuesta]"

def get_freq_mode_rs(ser):
    raw = send_command(ser, 'FA;')
    freq = "Desconocida"
    for part in raw.split(';'):
        if part.startswith("FA"):
            try:
                freq_hz = int(part[2:])
                freq = f"{freq_hz / 1_000_000:.5f} MHz"
                break
            except ValueError:
                pass

    mode_raw = send_command(ser, 'MD;')
    mode_code = mode_raw.replace("MD", "").replace(";", "")
    mode = MODES.get(mode_code, "Desconocido")

    rm_raw = send_command(ser, 'RM;')
    rs_val = 0
    for part in rm_raw.split(';'):
        if part.startswith("RM"):
            try:
                rs_val = int(part[2:])
            except ValueError:
                pass
            break

    s_units = min(rs_val // 28, 9)
    sm_str = "S9+" if s_units >= 9 else f"S{s_units}"
    bar = f"[{'#' * s_units}{'-' * (9 - s_units)}]"
    sm_display = f"{sm_str}  {bar} (RM={rs_val})"

    return freq, mode, sm_display

def set_frequency(ser, freq_khz):
    try:
        freq_hz = int(float(freq_khz) * 1000)
        freq_str = str(freq_hz).zfill(11)
        return send_command(ser, f'FA{freq_str};')
    except ValueError:
        return "Frecuencia inválida"

def set_mode(ser, mode_code):
    return send_command(ser, f'MD{mode_code};')

def ptt_on(ser):
    return send_command(ser, 'TX;')

def ptt_off(ser):
    return send_command(ser, 'RX;')

def read_menu_61A(ser):
    return send_command(ser, 'EX06101000;')

def write_menu_61A(ser, value):
    return send_command(ser, f'EX06101001{value};')

def main():
    st.title("Control Kenwood TS-2000 vía CAT")
    ser = init_serial()
    if not ser:
        return

    st.subheader("Lectura del radio")
    if st.button("📡 Leer frecuencia, modo y señal"):
        freq, mode, sm = get_freq_mode_rs(ser)
        st.success(f"Frecuencia: {freq}")
        st.info(f"Modo: {mode}")
        st.warning(f"RS: {sm}")

    st.subheader("Control de frecuencia y modo")
    col1, col2 = st.columns(2)
    with col1:
        freq_input = st.text_input("Nueva frecuencia (kHz)", "146520")
        if st.button("Establecer frecuencia"):
            result = set_frequency(ser, freq_input)
            if '?' in result:
                st.error(f"Error: {result}")
            else:
                st.success("✅ Frecuencia establecida.")
    with col2:
        mode_select = st.selectbox("Modo", list(MODES.items()), format_func=lambda x: f"{x[0]} - {x[1]}")
        if st.button("Cambiar modo"):
            result = set_mode(ser, mode_select[0])
            if '?' in result:
                st.error(f"Error: {result}")
            else:
                st.success("✅ Modo cambiado.")

    st.subheader("Control de PTT")
    col3, col4 = st.columns(2)
    with col3:
        if st.button("🔴 Activar PTT (TX)"):
            result = ptt_on(ser)
            if '?' in result:
                st.error(result)
            else:
                st.success("✅ Transmitiendo")
    with col4:
        if st.button("⚪ Desactivar PTT (RX)"):
            result = ptt_off(ser)
            if '?' in result:
                st.error(result)
            else:
                st.success("✅ Recepción")

    st.subheader("Menú 61A (Modo Repetidor)")
    if st.button("Leer menú 61A"):
        result = read_menu_61A(ser)
        if '?' in result:
            st.error(f"❌ {result}")
        else:
            st.success(f"📖 Respuesta: {result}")
    menu_val = st.selectbox("Establecer valor menú 61A", [("0", "OFF"), ("1", "LOCK-ED"), ("2", "CROSS")], format_func=lambda x: f"{x[0]} - {x[1]}")
    if st.button("Guardar valor menú 61A"):
        result = write_menu_61A(ser, menu_val[0])
        if '?' in result:
            st.error(f"❌ {result}")
        else:
            st.success("✅ Menú actualizado")

    st.subheader("Enviar comando CAT manual")
    cmd = st.text_input("Comando CAT", "FA;")
    if st.button("Enviar comando"):
        result = send_command(ser, cmd)
        if '?' in result or result.strip() == '' or not result.endswith(';'):
            st.error(f"⚠️ Respuesta del radio: {result}")
        else:
            st.success("✅ Comando enviado correctamente.")

if __name__ == "__main__":
    main()
