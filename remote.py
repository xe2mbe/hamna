import socket
import threading
import time

HOST = "192.168.1.37"
PORT = 5038
USERNAME = "asl"
PASSWORD = "RCG_Gu4d14n4"

# Diccionario global para guardar el estado de los nodos (COS o no).
# La llave será el número de nodo (str), y el valor un bool:
# True  = COS activo (EventValue=1)
# False = COS inactivo (EventValue=0)
node_cos_status = {}

# Para evitar condiciones de carrera, utilizamos un candado (lock) al modificar node_cos_status
lock = threading.Lock()

def connect_ami():
    """
    Conecta con el Asterisk Manager Interface y retorna el socket listo.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((HOST, PORT))
    login_cmd = (
        f"Action: Login\r\n"
        f"Username: {USERNAME}\r\n"
        f"Secret: {PASSWORD}\r\n"
        f"Events: on\r\n"     # Importante para recibir eventos
        f"\r\n"
    )
    s.sendall(login_cmd.encode())
    return s

def ami_event_listener():
    """
    Hilo que permanece escuchando eventos del AMI en un bucle infinito.
    Cada vez que aparece un RPT_RXKEYED o RPT_TXKEYED, se actualiza el 
    estado global 'node_cos_status' con la información de COS (EventValue).
    """
    ami_socket = connect_ami()
    print("AMI conectado. Iniciando lectura de eventos...")

    buffer = ""
    try:
        while True:
            chunk = ami_socket.recv(4096).decode(errors='ignore')
            if not chunk:
                # Si no hay datos, significa desconexión o fin de stream
                time.sleep(0.1)
                continue

            buffer += chunk

            # Procesamos cada evento separado por doble salto de línea
            while "\r\n\r\n" in buffer:
                raw_event, buffer = buffer.split("\r\n\r\n", 1)

                # Podrías buscar ambos eventos RPT_RXKEYED o RPT_TXKEYED.
                # En un nodo HUB, normalmente RPT_RXKEYED indica actividad entrante.
                # RPT_TXKEYED indicaría que el nodo (o HUB) está transmitiendo algo.
                # Ajusta esto según lo que quieras monitorear.
                if "Event: RPT_RXKEYED" in raw_event or "Event: RPT_TXKEYED" in raw_event:
                    lines = raw_event.split("\r\n")
                    event_data = {}
                    for line in lines:
                        if ": " in line:
                            k, v = line.split(": ", 1)
                            event_data[k.strip()] = v.strip()

                    node = event_data.get("Node")
                    event_value = event_data.get("EventValue")  # "1" o "0"
                    event_name = event_data.get("Event")        # "RPT_RXKEYED" / "RPT_TXKEYED"

                    if node and event_value in ["0", "1"]:
                        # Actualizamos el estado global
                        # True = hay COS (1), False = no hay COS (0)
                        is_keyed = (event_value == "1")
                        with lock:
                            node_cos_status[node] = is_keyed

                        # Ejemplo de log en la consola:
                        print(f"[{event_name}] Nodo {node} => COS = {is_keyed}")

    except Exception as e:
        print(f"Ocurrió un error en la lectura AMI: {e}")
    finally:
        ami_socket.close()
        print("Socket AMI cerrado.")

def start_ami_listener():
    """
    Inicia el hilo que escucha los eventos del AMI.
    """
    thread = threading.Thread(target=ami_event_listener, daemon=True)
    thread.start()
    return thread

def is_node_cos_active(node_number):
    """
    Permite consultar en cualquier momento el estado COS (True/False)
    de un nodo en particular.
    """
    with lock:
        return node_cos_status.get(str(node_number), False)

# ---------------------------------------------------------------------
# Ejemplo de uso en tu script principal:
# ---------------------------------------------------------------------
if __name__ == "__main__":
    # 1. Inicia el hilo de lectura AMI
    start_ami_listener()

    # 2. Tu lógica principal podría hacer algo como:
    try:
        while True:
            # Consultamos el estado COS de, por ejemplo, el nodo 299080
            node = "299080"
            cos_state = is_node_cos_active(node)
            if cos_state:
                print(f"El nodo {node} tiene COS activo en este momento.")
            else:
                print(f"El nodo {node} NO está recibiendo (COS inactivo).")
            
            time.sleep(3)

    except KeyboardInterrupt:
        print("Saliendo...")
