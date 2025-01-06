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

def listen_events(s):
    try:
        while True:
            data = s.recv(4096).decode()
            if "Event: RPT_TXKEYED" in data:
                print(data)
    except KeyboardInterrupt:
        print("\nDeteniendo el script...")
        s.close()

if __name__ == "__main__":
    ami_socket = connect_ami()
    listen_events(ami_socket)

