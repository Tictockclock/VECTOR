import socket
import os
import zmq
import threading
import signal
import sys

HOST = '0.0.0.0'  # Listen on all network interfaces
PORT_TCP = 12345  # Port for TCP
PORT_ZMQ_FILE = 12346  # Port for ZeroMQ file transfer
PORT_ZMQ_MSG = 12347  # Port for ZeroMQ messages
SAVE_DIR = 'received_files'  # Directory to save received files

shutdown_event = threading.Event()

def start_tcp_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind((HOST, PORT_TCP))
        server_socket.listen()
        print(f"TCP Server listening on {HOST}:{PORT_TCP}")

        while not shutdown_event.is_set():
            server_socket.settimeout(1.0)
            try:
                conn, addr = server_socket.accept()
            except socket.timeout:
                continue

            print(f"TCP Connection from {addr}")
            try:
                os.makedirs(SAVE_DIR, exist_ok=True)
                save_path = os.path.join(SAVE_DIR, f"received_file_{addr[1]}")
                with open(save_path, 'wb') as file:
                    while True:
                        data = conn.recv(1024)
                        if not data:
                            break
                        file.write(data)
                print(f"File received successfully and saved to {save_path}.")
                conn.sendall(b"File received successfully.")
            except Exception as e:
                print(f"Error handling TCP client {addr}: {e}")
                conn.sendall(b"Error processing file.")
            finally:
                conn.close()

def start_zmq_file_server():
    context = zmq.Context()
    socket = context.socket(zmq.PULL)
    socket.bind(f"tcp://{HOST}:{PORT_ZMQ_FILE}")
    print(f"ZeroMQ File Server listening on {HOST}:{PORT_ZMQ_FILE}")

    os.makedirs(SAVE_DIR, exist_ok=True)  # Ensure the directory exists

    while not shutdown_event.is_set():
        try:
            filename = socket.recv_string(flags=zmq.NOBLOCK)
        except zmq.Again:
            if shutdown_event.is_set():
                return
            continue

        save_path = os.path.join(SAVE_DIR, filename)
        with open(save_path, "wb") as f:
            while True:
                try:
                    chunk = socket.recv(flags=zmq.NOBLOCK)
                except zmq.Again:
                    if shutdown_event.is_set():
                        return
                    continue
                if chunk == b"EOF":
                    break
                f.write(chunk)
        print(f"File received successfully via ZeroMQ and saved to {save_path}.")

def start_zmq_msg_server():
    context = zmq.Context()
    socket = context.socket(zmq.PULL)
    socket.bind(f"tcp://{HOST}:{PORT_ZMQ_MSG}")
    print(f"ZeroMQ Message Server listening on {HOST}:{PORT_ZMQ_MSG}")

    while not shutdown_event.is_set():
        try:
            message = socket.recv_string(flags=zmq.NOBLOCK)
        except zmq.Again:
            if shutdown_event.is_set():
                return
            continue
        print(f"Received ZeroMQ message: {message}")

def start_server():
    print("Server is running. Press Ctrl+C to stop.")
    tcp_thread = threading.Thread(target=start_tcp_server)
    zmq_file_thread = threading.Thread(target=start_zmq_file_server)
    zmq_msg_thread = threading.Thread(target=start_zmq_msg_server)

    tcp_thread.start()
    zmq_file_thread.start()
    zmq_msg_thread.start()

    def signal_handler(sig, frame):
        print("\nShutting down server...")
        shutdown_event.set()
        tcp_thread.join()
        zmq_file_thread.join()
        zmq_msg_thread.join()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.pause()

if __name__ == "__main__":
    start_server()