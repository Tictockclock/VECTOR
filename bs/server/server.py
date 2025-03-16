import zmq
import os
import threading
import signal
import sys
import socket

import tempfile

# Import your CSI processing modules
import numpy as np
import scipy.io

# Import VECTOR Libraries
import sys
VECTOR_ROOT = os.getenv("VECTOR_ROOT")
sys.path.insert(0, VECTOR_ROOT) if (VECTOR_ROOT is not None) and (VECTOR_ROOT not in sys.path) else print("WARNING! VECTOR_ROOT NOT DEFINED! RUN THIS FROM VECTOR ROOT DIRECTORY: `export VECTOR_ROOT=$(pwd)`")
import setup; setup.loadModules()

import bs.nav.processing.filtersofGOR as filtersofGOR
import bs.nav.processing.utilsCSI as utilsCSI
import bs.demo.graphing.plotCSI as plotCSI

HOST = '0.0.0.0'
PORT_ZMQ_FILE = 12346
PORT_ZMQ_MSG = 12347
PORT_UDP_1 = 12348
PORT_UDP_2 = 12349
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

TARGET_SEQUENCE = bytes([0x7b, 0x03, 0x00, 0x00])

REAL_TARGET_SEQUENCE = bytes([0x42, 0x61, 0x73, 0x69, 0x63, 0x00, 0x04])

def trim_data(data):
    """Finds the target sequence and trims the data before it."""
    # index = data.find(TARGET_SEQUENCE)
    # index2 = data.find(REAL_TARGET_SEQUENCE)

    # if index != -1:
    #     return data[index:]  # Keep everything from the sequence onwards

    # if index2 != -1:  # Keep everything from REAL_TARGET_SEQUENCE onwards
    #     return data[index2 + 10:]

    # print("Warning: Target sequence not found. Skipping frame.")
    # return None  # Skip processing if sequence is not found

    #return everything but the first byte
    return data[20:]

def read_file_bytes(file_path, num_bytes):
    with open(file_path, 'rb') as f:
        data = f.read(num_bytes)
        print(" ".join(f"{byte:02x}" for byte in data))

def print_csi_info(file_path):
    """Loads and prints CSI data from a .csi file."""
    [csiRaw, _] = filtersofGOR.loadCSIfromRAW(file_path)
    #print(f"Number of Frames: {csiRaw.raw}")
    print(f"First Standard MAC Header: {csiRaw.raw[0]['StandardHeader']}")
    #print(f"Basic frame info: {csiRaw.raw[0]['RxSBasic']}\n\n\n\n\n")
    print(f"MPDU: {csiRaw.raw[0]['MPDUS']}")


def start_udp_server(port):
    """Listens for UDP packets on the given port, processes CSI data, and passes it to print_csi_info()."""
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.bind((HOST, port))
    print(f"UDP Server listening on {HOST}:{port}")

    while not shutdown_event.is_set():
        try:
            data, addr = udp_socket.recvfrom(4096)  # Receive UDP data
            trimmed_data = trim_data(data)

            #trimmed_data = data

            if trimmed_data:
                with tempfile.NamedTemporaryFile(delete=True, suffix=".csi") as temp_file:
                    temp_file.write(trimmed_data)
                    temp_file.flush()
                    read_file_bytes(temp_file.name, 100)
                    print(f"Processing CSI data from {addr} - {len(trimmed_data)} bytes (Port {port})")
                    print_csi_info(temp_file.name)
            print("\n")

        except Exception as e:
            if not shutdown_event.is_set():
                print(f"UDP error on port {port}: {e}")

        print("\n\n")

def start_server():
    print("Server is running. Press Ctrl+C to stop.")
    zmq_file_thread = threading.Thread(target=start_zmq_file_server)
    zmq_msg_thread = threading.Thread(target=start_zmq_msg_server)
    udp_thread_1 = threading.Thread(target=start_udp_server, args=(PORT_UDP_1,))
    udp_thread_2 = threading.Thread(target=start_udp_server, args=(PORT_UDP_2,))

    udp_thread_1.start()
    udp_thread_2.start()

    # zmq_file_thread.start()
    # zmq_msg_thread.start()

    def signal_handler(sig, frame):
        print("\nShutting down server...")
        shutdown_event.set()
        # zmq_file_thread.join()
        # zmq_msg_thread.join()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.pause()

if __name__ == "__main__":
    start_server()
