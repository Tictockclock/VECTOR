import zmq
import os
import threading
import signal
import sys
import socket
import json
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
loadedCSI = []

shutdown_event = threading.Event()


CONFIG_PATH = None
mypath = "/home/dt12/Code/VECTOR/bs/config.json"
if os.path.exists(mypath):
    CONFIG_PATH = mypath
else:
    CONFIG_PATH = "/home/dt12/VECTOR/bs/config.json"
def load_config():
    """Load configuration from a JSON file.

    Reads the configuration file specified by `CONFIG_PATH` and loads it into the global `config` variable.
    If the file is not found or cannot be parsed, the program exits with an error.

    Raises:
        FileNotFoundError: If the configuration file does not exist.
        json.JSONDecodeError: If the configuration file is not valid JSON.
    """
    #load the congiguration file into config
    global config
    try:
        if not os.path.exists(CONFIG_PATH):
            raise FileNotFoundError(f"Config file {CONFIG_PATH} not found!")

        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)
    except Exception as e:
        print(f"Error loading config: {e}")
        sys.exit(1)

    #print(config)

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

def split_csi_info(temp_file):
    file_path = temp_file.name
    """Loads and prints CSI data from a .csi file."""
    [csiRaw, _] = filtersofGOR.loadCSIfromRAW(file_path)
    #print(f"Number of Frames: {csiRaw.raw}")
    # print(f"First Standard MAC Header: {csiRaw.raw[0]['StandardHeader']}")
    #print(f"Basic frame info: {csiRaw.raw[0]['RxSBasic']}\n\n\n\n\n")
    # print(f"MPDU: {csiRaw.raw[0]['MPDUS']}")

    if csiRaw.raw[0]['RxExtraInfo']['macaddr_cur'] == [16, 95, 173, 215, 141, 234]:
        config["NICdata"][0]["mac"] = csiRaw.raw[0]['RxExtraInfo']['macaddr_cur']
        return 21
    elif csiRaw.raw[0]['RxExtraInfo']['macaddr_cur'] == [108, 47, 128, 223, 55, 202]:
        config["NICdata"][1]["mac"] = csiRaw.raw[0]['RxExtraInfo']['macaddr_cur']
        return 22
    else:
        return -1

def append_to_file(source_file, destination_file):
    """Appends the contents of source_file to destination_file."""
    with open(source_file, "rb") as src, open(destination_file, "ab") as dest:
        dest.write(src.read())

def start_udp_server(port):
    """Listens for UDP packets on the given port, processes CSI data, and passes it to print_csi_info()."""
    # if not hasattr(start_udp_server, "loadedCSI"):
    #     start_udp_server.loadedCSI = []

    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.bind((HOST, port))
    print(f"UDP Server listening on {HOST}:{port}")

    while not shutdown_event.is_set():
        try:
            data, addr = udp_socket.recvfrom(4096)  # Receive UDP data
            trimmed_data = trim_data(data)

            if trimmed_data:
                with tempfile.NamedTemporaryFile(delete=True, suffix=".csi") as temp_file:
                    temp_file.write(trimmed_data)
                    temp_file.flush()
                    #read_file_bytes(temp_file.name, 100)
                    print(f"Processing CSI data from {addr} - {len(trimmed_data)} bytes (Port {port})")
                    NIC_number = split_csi_info(temp_file)
                    if not NIC_number == -1:
                        append_to_file(temp_file.name, f"/home/dt12/Code/VECTOR/bs/nav/csi_data/live_collection/{NIC_number}.csi")
                        [csiRaw, _] = filtersofGOR.loadCSIfromRAW(temp_file.name) # Load CSI data
                        # NICdata = [
                        #         # Base Station Layout
                        #         {   # NIC 1
                        #             'file':  "21",#"NIC21", # Leave empty to select during dialogue.
                        #             0:      1,  # AUX
                        #             1:      2,  # MAIN
                        #             'mac':  [05 00 00 15 03 15], # MAC Address for the NIC. Leave empty -- will be autopopulated
                        #         },
                        #         {   # NIC 2
                        #             'file': "22",#"NIC22", # Leave empty to select during dialogue.
                        #             0:      0,  # AUX
                        #             1:      3,  # MAIN
                        #             'mac':  [], # MAC Address for the NIC. Leave empty -- will be autopopulated
                        #         }
                        # ]
                        # print(NICdata)
                        NICdata = config["NICdata"]
                        global loadedCSI
                        print(loadedCSI)
                        loadedCSI = filtersofGOR.placeMultiNICS(csiRaw, NIC_number - 21, NICdata, loadedCSI)
                        try:
                            combinedCSI = filtersofGOR.alignMPDU(len(NICdata), loadedCSI)
                            macAlignedCSI = filtersofGOR.filterSrcDest(combinedCSI, config["gor_filter_options"]["toDS"], config["gor_filter_options"]["fromDS"], config["gor_filter_options"]["macBS"], config["gor_filter_options"]["macUT"])
                            filtersofGOR.statsForcedParams(macAlignedCSI)
                            forcedCSI = filtcaersofGOR.filterForcedParams(macAlignedCSI, config["gor_filter_options"]["forceAT"], config["gor_filter_options"]["forceAR"])
                            [parsedMatrix, centerFreq_arr, chanBW_arr, subcFreq_arr] = filtersofGOR.convertToUsableMatrix(forcedCSI, NICdata)
                            [correctedMatrix, subcFreq] = cableCalNICS.applyCalOffset(calMatrix, calSubcFreq, parsedMatrix, subcFreq_arr[0])
                        except Exception as e:
                            print(e)
                            print("Error processing CSI data.")

            print("\n")

        except Exception as e:
            if not shutdown_event.is_set():
                print(e)
                print(f"UDP error on port {port}: {e}")

        print("\n\n")

def start_server():
    #TODO add the MAC to the config
    print("Server is running. Press Ctrl+C to stop.")
    zmq_file_thread = threading.Thread(target=start_zmq_file_server)
    zmq_msg_thread = threading.Thread(target=start_zmq_msg_server)
    udp_thread_1 = threading.Thread(target=start_udp_server, args=(PORT_UDP_1,))

    parsing_thread = threading.Thread(target=split_csi_info)
    # udp_thread_2 = threading.Thread(target=start_udp_server, args=(PORT_UDP_2,))

    udp_thread_1.start()
    # udp_thread_2.start()

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
    load_config()
    start_server()
