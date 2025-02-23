import socket
import os
import threading

HOST = '0.0.0.0'  # Listen on all network interfaces
PORT_TCP = 12345  # Port for TCP
PORT_UDP = 12346  # Port for UDP
SAVE_DIR = 'received_files'  # Directory to save received files

def handle_tcp_client(conn, addr):
    print(f"TCP Connection from {addr}")
    try:
        filename = conn.recv(1024).decode().strip()
        if not filename:
            conn.sendall(b"Invalid filename.")
            return

        save_path = os.path.join(SAVE_DIR, filename.rsplit("/", 1)[-1])
        print(f"Receiving file: {filename}, saving to {save_path}")

        os.makedirs(SAVE_DIR, exist_ok=True)
        with open(save_path, 'wb') as file:
            while True:
                data = conn.recv(1024)
                if not data:
                    break
                file.write(data)
        print("File received successfully.")
        conn.sendall(b"File received successfully.")
    except Exception as e:
        print(f"Error handling TCP client {addr}: {e}")
        conn.sendall(b"Error processing file.")
    finally:
        conn.close()

def start_tcp_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind((HOST, PORT_TCP))
        server_socket.listen()
        print(f"TCP Server listening on {HOST}:{PORT_TCP}")

        while True:
            conn, addr = server_socket.accept()
            threading.Thread(target=handle_tcp_client, args=(conn, addr), daemon=True).start()

def start_udp_server():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as server_socket:
        server_socket.bind((HOST, PORT_UDP))
        print(f"UDP Server listening on {HOST}:{PORT_UDP}")

        while True:
            data, client_address = server_socket.recvfrom(4096)
            message = data.decode('utf-8').strip()
            print(f"Received UDP message from {client_address}: {message}")

            if message:
                response = message.upper().encode('utf-8')
                server_socket.sendto(response, client_address)
                print(f"Sent response to {client_address}: {response.decode('utf-8')}")
            else:
                server_socket.sendto(b"Unknown request.", client_address)

def start_server():
    threading.Thread(target=start_tcp_server, daemon=True).start()
    threading.Thread(target=start_udp_server, daemon=True).start()

    print("Server is running. Press Ctrl+C to stop.")
    while True:
        try:
            pass  # Keep the main thread alive
        except KeyboardInterrupt:
            print("Shutting down server.")
            break

if __name__ == "__main__":
    start_server()
