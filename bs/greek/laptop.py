import threading
import signal
import sys
import os
import os.path
import subprocess
import json
import socket
import time
import argparse
import serial
import zmq

shutdown_event = threading.Event()
threading_process = None
pico_process = None
pinging_process = None
SUDO_PASSWORD = "123456"
config = None
bab = None
done_pinging_flag = False
START_FLAG = "neutral"
TARGET_IP = "10.42.0.56"  # Change this to the receiver's IP address (laptop)
PORT = 5000
BUFFER_SIZE = 1024
HOST = '0.0.0.0'
PORT_ZMQ_MSG = 12347
CONFIG_PATH = None
SERVER_HOST = 'localhost'
SERVER_PORT = 12346  # Updated to match the ZeroMQ file server por
SAVE_DIR = 'received_files'

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

def get_message():
    """
    Listens for an incoming connection on the global PORT and returns the received message.

    Returns:
        str: The received message.
    """
    global START_FLAG
    try:
        # Create a socket using IPv4 and TCP
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', PORT))
            s.listen(1)
            print(f"Listening for connections on port {PORT}...")
            conn, addr = s.accept()
            with conn:
                print(f"Connected by {addr}")
                data = conn.recv(BUFFER_SIZE)
                message = data.decode('utf-8')
                print(f"Received message: {message}")
                if message == "Start":
                    START_FLAG = "Start"
                elif message == "Stop":

                    START_FLAG = "Stop"
    except Exception as e:
        print(f"An error occurred in receive_message: {e}")
        return None

def send_message(message):
    """
    Sends the provided message to the receiver using the global TARGET_IP and PORT.

    Parameters:
        message (str): The message to send.
    """
    try:
        # Create a socket using IPv4 and TCP
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((TARGET_IP, PORT))
            s.sendall(message.encode('utf-8'))
            print(f"Message sent to {TARGET_IP}:{PORT}")
    except Exception as e:
        print(f"An error occurred in send_message: {e}")

def send_file(file_path):
    """
    Sends the full and complete file
    @param file_path: the path to the file to be sent
    """
    context = zmq.Context()
    socket = context.socket(zmq.PUSH)
    socket.setsockopt(zmq.LINGER, 0)  # Set linger to zero to close the socket immediately
    socket.connect(f"tcp://{SERVER_HOST}:{SERVER_PORT}")

    filename = os.path.basename(file_path)
    print(f"Sending file {file_path} to {SERVER_HOST}:{SERVER_PORT}...")

    socket.send_string(filename)  # Send the filename first

    with open(file_path, "rb") as f:
        while chunk := f.read(1024):  # Read file in 1024-byte chunks
            socket.send(chunk)

    socket.send(b"EOF")  # Send End of File marker
    print("File sent successfully.")
    socket.close()
    context.term()

def start_picoscenes():
    """Start the PicoScenes application.

    Launches PicoScenes as a subprocess using parameters from the global `config.json` file. If the
    process does not complete within the specified time limit, it is forcefully terminated.

    Raises:
        subprocess.TimeoutExpired: If the process does not complete within the time limit.
    """

    global pico_process

    # Start PicoScenes as a subprocess
    cmd = f"""PicoScenes \"-d debug; -i {config["picoscenes"]["monID1"]} --mode logger  --output {config["picoscenes"]["NIC_save_file1"]}; -q\""""

    print("Running injection command:")
    print(cmd)
    #result = subprocess.run(cmd, shell=True)
    pico_process = subprocess.Popen(cmd, shell=True)

    try:
        # Wait for process to complete, but enforce timeout
        pico_process.wait(timeout=float(config["picoscenes"]["timelimit"]))
        print("Command completed within time limit")

    except subprocess.TimeoutExpired:
        print(f"""Command did not complete within {config["picoscenes"]["timelimit"]} seconds""")
        print("Forcing termination of the process group")
        # Terminate entire process group
        os.killpg(os.getpgid(pico_process.pid), signal.SIGTERM)
        pico_process.wait() # Wait for termination to complete.


def master_handler():

    """Main handler for the base station.

    Initializes and manages the base station's functionality, including preparing and running
    PicoScenes, parsing data, and handling graceful shutdowns via Ctrl+C.
    """

    print("Base station is running. Press Ctrl+C to stop.")

    parser = argparse.ArgumentParser(description="Client to send files or messages to the server.")
    parser.add_argument('-1', '--file_1', type=str, help="Name of the first file to save")
    args = parser.parse_args()

    #start the get_message thread
    get_message_thread = threading.Thread(target=get_message)
    get_message_thread.start()

    while START_FLAG != "Start":
        pass

    # Wait for the PicoScenes preparation to complete
    print("PicoScenes preparation completed.")
    # Start PicoScenes
    picoscenes_thread = threading.Thread(target=start_picoscenes)
    picoscenes_thread.start()

    #wait for STOP to be received
    while START_FLAG != "Stop":
        pass

    os.killpg(os.getpgid(pico_process.pid), signal.SIGINT)
    #wait for the process to finish
    pico_process.wait()

    send_file(config["picoscenes"]["NIC_save_file1"])

    exit(0)


    # Handle Ctrl+C gracefully
    def signal_handler(sig, frame):
        global pico_process

        # Prevent infinite recursion by unbinding the signal temporarily
        signal.signal(signal.SIGINT, signal.SIG_IGN)

        print("\nShutting down server...")
        shutdown_event.set()

        # Gracefully terminate the PicoScenes subprocess
        if pico_process:
            try:
                print("Sending SIGINT to PicoScenes...")
                os.killpg(os.getpgid(pico_process.pid), signal.SIGINT)

                # Wait for PicoScenes to gracefully terminate
                pico_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                print("PicoScenes did not terminate, sending SIGTERM...")
                os.killpg(os.getpgid(pico_process.pid), signal.SIGTERM)

            except ProcessLookupError:
                print("PicoScenes process already terminated.")

        # Ensure no zombie processes
        if pico_process and pico_process.poll() is None:
            print("Force killing PicoScenes...")
            os.killpg(os.getpgid(pico_process.pid), signal.SIGKILL)

        # Restore the signal handler so another Ctrl+C works again
        signal.signal(signal.SIGINT, signal_handler)

        print("Shutdown complete.")
        sys.exit(0)

    # Register the signal handler for SIGINT (Ctrl+C)
    signal.signal(signal.SIGINT, signal_handler)
    signal.pause()



if __name__ == "__main__":
    # Load the configuration file
    load_config()
    # Start the base station
    master_handler()