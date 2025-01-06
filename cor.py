import socket

host = "192.168.1.37"
port = 5038
username = "asl"
password = "RCG_Gu4d14n4"

def connect_ami():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((host, port))
    s.sendall(f"Action: Login\nUsername: {username}\nSecret: {password}\n\n".encode())
    return s

def check_cos():
    ami_socket = connect_ami()
    response = {}

    try:
        while True:
            data = ami_socket.recv(4096).decode()
            
            # Verificar si se detecta el evento RPT_TXKEYED
            if "Event: RPT_TXKEYED" in data:
                # Parsear los valores relevantes
                value_line = next(line for line in data.split("\n") if "Value:" in line)
                value = int(value_line.split(":")[1].strip()) == 1  # True si Value es 1, False si es 
                
                node_line = next(line for line in data.split("\n") if "Node:" in line)
                node = node_line.split(":")[1].strip()
                
                variable_line = next(line for line in data.split("\n") if "Variable:" in line)
                variable = variable_line.split(":")[1].strip()
                
                # Construir el diccionario con los datos
                response = {
                    "Value": value,
                    "Node": node,
                    "Variable": variable
                }
                break  # Detener después de obtener los datos
            else:
                print("No se detectó COS")

    except KeyboardInterrupt:
        print("\nDeteniendo el script...")
        ami_socket.close()

    return response

if __name__ == "__main__":
    while True:
        cos_status = check_cos()
        #print (cos_status)
        cos = cos_status.get("Value")
        if cos == True:
            print(cos)
        elif cos == False:
            print(cos)# Imprimir el diccionario con los resultados
