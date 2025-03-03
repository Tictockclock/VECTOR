import zmq
import os
import threading
import signal
import sys

HOST = '0.0.0.0'
PORT_ZMQ_FILE = 12346
PORT_ZMQ_MSG = 12347
SAVE_DIR = 'received_files'

shutdown_event = threading.Event()

def start_zmq_file_server():
    context = zmq.Context()
    socket = context.socket(zmq.REP)
    socket.bind(f"tcp://0.0.0.0:{PORT_ZMQ_FILE}")
    print(f"ZeroMQ File Server listening on 0.0.0.0:{PORT_ZMQ_FILE}")

    os.makedirs(SAVE_DIR, exist_ok=True)

    poller = zmq.Poller()
    poller.register(socket, zmq.POLLIN)

    while not shutdown_event.is_set():
        try:
            # Wait for messages with a timeout to allow shutdown checks
            socks = dict(poller.poll(100))  # 100ms timeout
            if not socks:
                continue  # No message, loop to check shutdown_event

            # Process incoming filename
            filename = socket.recv_string()
            print(f"Received filename: {filename}")

            # Acknowledge readiness to receive chunks
            socket.send_string("Ready to receive file chunks.")

            save_path = os.path.join(SAVE_DIR, filename)
            with open(save_path, "wb") as f:
                while True:
                    chunk = socket.recv()
                    if chunk == b"EOF":
                        break
                    f.write(chunk)
                    # Acknowledge each chunk
                    socket.send_string("Chunk received.")

            print(f"File saved to {save_path}.")
            socket.send_string("File received successfully.")

        except zmq.ZMQError as e:
            if shutdown_event.is_set():
                break
            print(f"ZeroMQ error: {e}")

def start_zmq_msg_server():
    context = zmq.Context()
    socket = context.socket(zmq.PULL)
    socket.bind(f"tcp://{HOST}:{PORT_ZMQ_MSG}")
    print(f"ZeroMQ Message Server listening on {HOST}:{PORT_ZMQ_MSG}")

    poller = zmq.Poller()
    poller.register(socket, zmq.POLLIN)

    while not shutdown_event.is_set():
        socks = dict(poller.poll(100))  # 100ms timeout
        if socks.get(socket) == zmq.POLLIN:
            message = socket.recv_string()
            print(f"Received message: {message}")

def start_server():
    print("Server is running. Press Ctrl+C to stop.")
    zmq_file_thread = threading.Thread(target=start_zmq_file_server)
    zmq_msg_thread = threading.Thread(target=start_zmq_msg_server)

    zmq_file_thread.start()
    zmq_msg_thread.start()

    def signal_handler(sig, frame):
        print("\nShutting down server...")
        shutdown_event.set()
        zmq_file_thread.join()
        zmq_msg_thread.join()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.pause()

if __name__ == "__main__":
    start_server()