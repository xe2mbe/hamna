from asterisk.ami import AMIClient
import logging

# Configurar el sistema de registro
logging.basicConfig(
    filename="transmisiones.log",  # Nombre del archivo de registro
    level=logging.INFO,           # Nivel de registro (INFO, ERROR, etc.)
    format="%(asctime)s - %(levelname)s - %(message)s",  # Formato de los registros
    datefmt="%Y-%m-%d %H:%M:%S"   # Formato de fecha y hora
)

def conectar_ami():
    try:
        # Conexión al AMI
        client = AMIClient(address="192.168.1.37", port=5038)  # Cambia la IP y el puerto si es necesario
        client.login(username="admin", secret="Guadiana*.")  # Credenciales de AMI
        logging.info("Conexión exitosa al AMI.")
        return client
    except Exception as e:
        logging.error(f"Error al conectar con AMI: {e}")
        return None

def transmitir_audio(client, nodo, archivo):
    try:
        # Comando para transmitir el archivo de audio
        action = {
            "Action": "Command",
            "Command": f"rpt localplay {nodo} {archivo}"
        }
        
        # Enviar el comando AMI y obtener la respuesta
        response = client.send_action(action)
        
        # Verificar la respuesta
        if response and 'Response' in response:
            if response["Response"] == "Follows":
                logging.info(f"Transmisión iniciada exitosamente para el archivo: {archivo}")
            else:
                logging.error(f"Error en la transmisión del archivo: {archivo}. Respuesta AMI: {response}")
        else:
            logging.error(f"Respuesta inesperada del AMI: {response}")
    except Exception as e:
        logging.error(f"Error al transmitir audio: {e}")

if __name__ == "__main__":
    # Conectar al AMI
    client = conectar_ami()
    if client:
        try:
            # Pedir el número del nodo y el archivo
            nodo = input("Introduce el número del nodo: ")
            archivo = input("Introduce la ruta completa del archivo de audio: ")

            # Transmitir el audio
            transmitir_audio(client, nodo, archivo)
            
        finally:
            client.logoff()
            logging.info("Conexión al AMI cerrada.")


