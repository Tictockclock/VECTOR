import socket

SERVER_HOST = '127.0.0.1'
SERVER_PORT = 12345
FILE_TO_SEND = 'sample.txt'  # Change this to the file you want to send

def send_file():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
        client_socket.connect((SERVER_HOST, SERVER_PORT))
        client_socket.sendall(FILE_TO_SEND.encode() + b'\n')

        with open(FILE_TO_SEND, 'rb') as file:
            while chunk := file.read(1024):
                client_socket.sendall(chunk)

        print("File sent successfully.")

def send_udp_message(message):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client_socket:
        client_socket.sendto(message.encode('utf-8'), (SERVER_HOST, SERVER_PORT))
        print(f"Sent UDP message: {message}")

if __name__ == "__main__":
    # Uncomment to send a file
    send_file()

    # Send multiple UDP messages
    for i in range(0, 33):
        send_udp_message(f"Hello, UDP Server! {i}")
