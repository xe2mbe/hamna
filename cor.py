import socket

host = "192.168.1.37"
port = 5038
username = "asl"
password = "RCG_Gu4d14n4"

def connect_ami():
    """
    Establece conexión con el AMI (Asterisk Manager Interface).
    """
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((host, port))
        s.sendall(f"Action: Login\nUsername: {username}\nSecret: {password}\n\n".encode())
        return s
    except Exception as e:
        print(f"Error al conectar con AMI: {e}")
        return None

def monitor_cos():
    """
    Monitorea continuamente el estado del COS a través del AMI.
    """
    ami_socket = connect_ami()
    if not ami_socket:
        print("No se pudo conectar al AMI. Terminando.")
        return

    buffer = ""
    current_cos_state = None  # Estado actual del COS (None, True o False)

    try:
        while True:
            # Recibir datos del socket
            data = ami_socket.recv(4096).decode()
            if not data:
                print("No se recibieron datos del servidor. Cerrando conexión.")
                break

            # Agregar datos al buffer
            buffer += data

            # Depuración: Mostrar datos crudos recibidos
            print(f"Datos recibidos:\n{data}\n")

            # Procesar eventos completos del buffer
            while "\n\n" in buffer:
                raw_event, buffer = buffer.split("\n\n", 1)  # Separar un evento completo
                if "Event: RPT_TXKEYED" in raw_event:
                    try:
                        # Extraer valores relevantes
                        value_line = next((line for line in raw_event.split("\n") if "Value:" in line), None)
                        node_line = next((line for line in raw_event.split("\n") if "Node:" in line), None)
                        variable_line = next((line for line in raw_event.split("\n") if "Variable:" in line), None)

                        if value_line:
                            value = int(value_line.split(":")[1].strip()) == 1
                        else:
                            value = None

                        node = node_line.split(":")[1].strip() if node_line else "Desconocido"
                        variable = variable_line.split(":")[1].strip() if variable_line else "Desconocido"

                        # Detectar cambios en el estado del COS
                        if current_cos_state != value:
                            current_cos_state = value
                            print(f"Estado del COS cambiado: {'Presente' if value else 'Ausente'}")
                            print(f"Detalles: Node={node}, Variable={variable}")
                    except Exception as e:
                        print(f"Error al procesar el evento: {e}")

    except KeyboardInterrupt:
        print("\nScript detenido por el usuario.")
    except Exception as e:
        print(f"Error durante la ejecución: {e}")
    finally:
        ami_socket.close()

if __name__ == "__main__":
    monitor_cos()
