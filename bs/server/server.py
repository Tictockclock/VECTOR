import zmq
import os
import threading
import signal
import sys
import socket
import json
import tempfile
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib import style
import queue
import logging
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
import bs.nav.processing.postprocessing.cableCalNICS    as cableCalNICS     # Calculate and apply calibration coefficients.

HOST = '0.0.0.0'
PORT_ZMQ_FILE = 12346
PORT_ZMQ_MSG = 12347
PORT_UDP_1 = 12348
PORT_UDP_2 = 12349
SAVE_DIR = 'received_files'
loadedCSI = []
data_queue = queue.Queue()
shutdown_event = threading.Event()


CONFIG_PATH = None
mypath = "/home/dt12/Code/VECTOR/bs/config.json"
if os.path.exists(mypath):
    CONFIG_PATH = mypath
else:
    CONFIG_PATH = "/home/dt12/VECTOR/bs/config.json"

# Create a figure and axis
fig, ax = plt.subplots()
x_data = np.linspace(0, 2*np.pi, 100)
lines = [ax.plot([], [], label=f"Trace {i+1}")[0] for i in range(4)]

def configure_plot():
    # Set up plot limits and labels
    ax.set_xlim(0, 2*np.pi)
    ax.set_ylim(-1.5, 1.5)
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.set_title("Live Plot with Multiple Traces")
    ax.legend()

def update_plot(frame):
    for i, line in enumerate(lines):
        # Simulate new data coming in by generating new y values
        y_data = np.sin(x_data + frame / 10 + i * np.pi / 4)
        y_data_list[i].append(y_data)

        # Concatenate the data to create the full trace
        line.set_data(x_data, np.array(y_data_list[i]).flatten())

    plt.draw()
    plt.pause(0.1)  # Pause for a short period to update the plot
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
            logging.info(f"Received filename: {filename}")

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

            logging.info(f"File saved to {save_path}.")
            socket.send_string("File received successfully.")

        except zmq.ZMQError as e:
            if shutdown_event.is_set():
                break
            logging.info(f"ZeroMQ error: {e}")

def start_zmq_msg_server():
    context = zmq.Context()
    socket = context.socket(zmq.PULL)
    socket.bind(f"tcp://{HOST}:{PORT_ZMQ_MSG}")
    logging.info(f"ZeroMQ Message Server listening on {HOST}:{PORT_ZMQ_MSG}")

    poller = zmq.Poller()
    poller.register(socket, zmq.POLLIN)

    while not shutdown_event.is_set():
        socks = dict(poller.poll(100))  # 100ms timeout
        if socks.get(socket) == zmq.POLLIN:
            message = socket.recv_string()
            logging.info(f"Received message: {message}")

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

    # logging.info("Warning: Target sequence not found. Skipping frame.")
    # return None  # Skip processing if sequence is not found

    #return everything but the first byte
    return data[20:]

def read_file_bytes(file_path, num_bytes):
    with open(file_path, 'rb') as f:
        data = f.read(num_bytes)
        logging.info(" ".join(f"{byte:02x}" for byte in data))

def split_csi_info(temp_file):
    file_path = temp_file.name
    """Loads and logging.infos CSI data from a .csi file."""
    [csiRaw, _] = filtersofGOR.loadCSIfromRAW(file_path)
    #logging.info(f"Number of Frames: {csiRaw.raw}")
    # logging.info(f"First Standard MAC Header: {csiRaw.raw[0]['StandardHeader']}")
    #logging.info(f"Basic frame info: {csiRaw.raw[0]['RxSBasic']}\n\n\n\n\n")
    # logging.info(f"MPDU: {csiRaw.raw[0]['MPDUS']}")
    logging.info(csiRaw.raw[0]['RxExtraInfo']['macaddr_cur'])
    if csiRaw.raw[0]['RxExtraInfo']['macaddr_cur'] == config["gor_filter_options"]["mac21"]:
        config["NICdata"][0]["mac"] = csiRaw.raw[0]['RxExtraInfo']['macaddr_cur']
        return 21
    elif csiRaw.raw[0]['RxExtraInfo']['macaddr_cur'] == config["gor_filter_options"]["mac22"]:
        config["NICdata"][1]["mac"] = csiRaw.raw[0]['RxExtraInfo']['macaddr_cur']
        return 22
    else:
        return -1

def append_to_file(source_file, destination_file):
    """Appends the contents of source_file to destination_file."""
    with open(source_file, "rb") as src, open(destination_file, "ab") as dest:
        dest.write(src.read())

# Global variables for figure, axes, and line
fig, ax, line = None, None, None

def plotliveCSI(Hest, subcFreq, title="Live CSI Plot", doUnwrap=True):
    global fig, ax, line  # Ensure modifications to existing figure

    if fig is None or ax is None:
        plt.ion()  # Interactive mode for fast updates
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.set_title(title)
        ax.set_xlabel("Frequency (Hz)")
        ax.set_ylabel("Phase (Rad)")
        ax.grid()

        # Initialize the plot with an empty line
        line, = ax.plot(subcFreq, np.zeros_like(subcFreq), 'b-', label="CSI Data")
        ax.legend()

    # Select first antenna pair for visualization
    t, r, k = 0, 0, -1
    y_data = np.unwrap(np.abs(Hest[t, r, :, k])) if doUnwrap else np.abs(Hest[t, r, :, k])

    # **FAST UPDATE**: Modify existing line instead of re-plotting
    line.set_ydata(y_data)

    # Adjust axes dynamically
    ax.relim()
    ax.autoscale_view()

    plt.draw()
    plt.pause(0.001)  # Super-fast refresh without blocking


def start_udp_server(port):
    """Listens for UDP packets on the given port, processes CSI data, and passes it to print_csi_info()."""
    # if not hasattr(start_udp_server, "loadedCSI"):
    #     start_udp_server.loadedCSI = []

    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.bind((HOST, port))
    logging.info(f"UDP Server listening on {HOST}:{port}")

    while not shutdown_event.is_set():
        try:
            data, addr = udp_socket.recvfrom(4096)  # Receive UDP data
            trimmed_data = trim_data(data)

            if trimmed_data:
                with tempfile.NamedTemporaryFile(delete=True, suffix=".csi") as temp_file:
                    temp_file.write(trimmed_data)
                    temp_file.flush()
                    #read_file_bytes(temp_file.name, 100)
                    logging.info(f"Processing CSI data from {addr} - {len(trimmed_data)} bytes (Port {port})")
                    NIC_number = split_csi_info(temp_file)
                    logging.info(f"NIC Number: {NIC_number}")
                    if not NIC_number == -1:
                        append_to_file(temp_file.name, f"/home/dt12/Code/VECTOR/bs/nav/csi_data/live_collection/{NIC_number}.csi")
                        [csiRaw, _] = filtersofGOR.loadCSIfromRAW(temp_file.name) # Load CSI data
                        NICdata = config["NICdata"]

                        # Convert keys "0" and "1" to integers
                        NICdata_fixed = []
                        for entry in NICdata:
                            new_entry = {
                                int(k) if k.isdigit() else k: v  # Convert numeric string keys to integers
                                for k, v in entry.items()
                            }
                            NICdata_fixed.append(new_entry)
                        NICdata = NICdata_fixed
                        global loadedCSI
                        loadedCSI = filtersofGOR.placeMultiNICS(csiRaw, NIC_number - 21, NICdata, loadedCSI)
                        logging.info(loadedCSI)
                        try:
                            combinedCSI = filtersofGOR.alignMPDU(len(NICdata), loadedCSI)

                            macAlignedCSI = filtersofGOR.filterSrcDest(combinedCSI, config["gor_filter_options"]["toDS"], config["gor_filter_options"]["fromDS"], config["gor_filter_options"]["macBS"], config["gor_filter_options"]["macUT"])
                            filtersofGOR.statsForcedParams(macAlignedCSI)

                            forcedCSI = filtersofGOR.filterForcedParams(macAlignedCSI, config["gor_filter_options"]["forceAT"], config["gor_filter_options"]["forceAR"])

                            [parsedMatrix, centerFreq_arr, chanBW_arr, subcFreq_arr] = filtersofGOR.convertToUsableMatrix(forcedCSI, NICdata)
                            #import pdb; pdb.set_trace()

                            #[correctedMatrix, subcFreq] = cableCalNICS.applyCalOffset(calMatrix, calSubcFreq, parsedMatrix, subcFreq_arr[0])
                            # Non-HT vs HT ~ format, RSSI, tods/fromds, addr1 mac, addr2 mac, timestamp/systemns

                            logging.info(f"HT or non-HT: {'HT' if csiRaw.raw[0]['RxSBasic']['packetFormat'] == 1 else 'non-HT'}")
                            logging.info(f"rssi: {csiRaw.raw[0]['RxSBasic']['rssi']}")
                            logging.info(f"rssi1: {csiRaw.raw[0]['RxSBasic']['rssi1']}")
                            logging.info(f"rssi2: {csiRaw.raw[0]['RxSBasic']['rssi2']}")
                            logging.info(f"rssi3: {csiRaw.raw[0]['RxSBasic']['rssi3']}")
                            logging.info(f"ToDS: {csiRaw.raw[0]['StandardHeader']['ControlField']['ToDS']}")
                            logging.info(f"FromDS: {csiRaw.raw[0]['StandardHeader']['ControlField']['FromDS']}")
                            logging.info(f"Address 2 MAC: {csiRaw.raw[0]['StandardHeader']['Addr2']}")
                            logging.info(f"Address 1 MAC: {csiRaw.raw[0]['StandardHeader']['Addr1']}")
                            # logging.info(f"Timestamp: {csiRaw.raw[0]['RxSBasic']['timestamp']}")

                            meanMag = np.mean(np.abs(parsedMatrix[0, :, :, -1]), axis=1) # [,AR,S,] -> [,AR,,] ~ Shape (,AR)
                            stdvMag =  np.std(np.abs(parsedMatrix[0, :, :, -1]), axis=1) # [,AR,S,] -> [,AR,,] ~ Shape (,AR)

                            logging.info(f"Mean & Std of Magnitude: {meanMag} +/- {stdvMag}")

                            data_queue.put((parsedMatrix, subcFreq_arr))
                            #plt.show()

                            # logging.info shapes for verification
                            # logging.info("Mean shape:", meanMag)  # Expected: (AT, AR, S)
                            # logging.info("Std shape:", std_per_AR)    # Expected: (AT, AR, S)
                            #import pdb; pdb.set_trace()
                            # parsedMatrix ~ std & mean of each AR trace with respect to subcarrier
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
    try:
        while True:
            if not data_queue.empty():
                Hest, subcFreq = data_queue.get()
                plotliveCSI(Hest, subcFreq)

    except KeyboardInterrupt:
        print("\nShutting down server...")
        shutdown_event.set()
        udp_thread_1.join()
        plt.ioff()
        plt.show()  # Show final plot when stopping
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
