import tkinter as tk
import threading
import time
import hid   # usa el paquete correcto

# -------- CONFIGURACIÓN --------
# VID/PID detectados automáticamente, pero puedes forzarlos aquí si deseas:
VID = 0x0d8c
PID = 0x0012
PTT_BIT = 0x01   # puede variar: 0x01 o 0x08 según versión
COS_BIT = 0x02   # puede variar: 0x02 o 0x04
REFRESH_MS = 200 # tiempo de refresco GUI
# --------------------------------


def find_cm108():
    """Busca un dispositivo C-Media automáticamente"""
    for d in hid.enumerate():
        if "C-Media" in (d["manufacturer_string"] or ""):
            print("Usando dispositivo:", d["product_string"])
            return d["vendor_id"], d["product_id"]
    return VID, PID


class CM108Interface:
    def __init__(self):
        self.vid, self.pid = find_cm108()
        self.dev = None
        self.ptt_state = False
        self.connect()

    def connect(self):
        try:
            self.dev = hid.device()
            self.dev.open(self.vid, self.pid)
            print(f"Conectado a {self.dev.get_manufacturer_string()} {self.dev.get_product_string()}")
        except Exception as e:
            print("Error al abrir dispositivo HID:", e)
            self.dev = None

    def set_ptt(self, state: bool):
        """Activa o libera el PTT"""
        if not self.dev:
            return
        self.ptt_state = state
        try:
            # Para CM108, se envían 4 bytes; el segundo define el estado del GPIO
            data = [0x00, 0x00, 0x00, 0x00]
            if state:
                data[1] = PTT_BIT
            self.dev.send_feature_report(data)
        except Exception as e:
            print("Error al enviar PTT:", e)

    def read_cos(self):
        """Lee el estado COS (Carrier Operated Squelch)"""
        if not self.dev:
            return False
        try:
            data = self.dev.get_input_report(0x01, 4)
            # Algunos modelos invierten la lógica, prueba ambas si es necesario
            cos_active = not bool(data[1] & COS_BIT)
            return cos_active
        except Exception as e:
            print("Error al leer COS:", e)
            return False

    def close(self):
        if self.dev:
            try:
                self.set_ptt(False)
                self.dev.close()
            except:
                pass


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("HAMNA-COS Monitor CM108")
        self.root.geometry("320x220")

        self.cm108 = CM108Interface()
        self.running = True

        # ---- UI ----
        self.cos_label = tk.Label(root, text="COS: ---", bg="gray", fg="white", font=("Consolas", 14))
        self.cos_label.pack(pady=20, fill="x")

        self.ptt_btn = tk.Button(root, text="PTT OFF", bg="red", fg="white", font=("Consolas", 14),
                                 command=self.toggle_ptt)
        self.ptt_btn.pack(pady=20, fill="x")

        self.status = tk.Label(root, text="Conectado" if self.cm108.dev else "Sin dispositivo",
                               font=("Arial", 10))
        self.status.pack(pady=5)

        threading.Thread(target=self.poll_cos, daemon=True).start()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def toggle_ptt(self):
        new_state = not self.cm108.ptt_state
        self.cm108.set_ptt(new_state)
        self.ptt_btn.config(
            text=f"PTT {'ON' if new_state else 'OFF'}",
            bg="green" if new_state else "red"
        )

    def poll_cos(self):
        """Lee COS periódicamente"""
        while self.running:
            cos = self.cm108.read_cos()
            color = "green" if cos else "gray"
            text = "COS: ACTIVO" if cos else "COS: inactivo"
            self.cos_label.config(text=text, bg=color)
            time.sleep(REFRESH_MS / 1000)

    def on_close(self):
        self.running = False
        self.cm108.close()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
