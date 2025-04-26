import threading
import signal
import sys
import os
import os.path
import subprocess
import json
import time
import argparse
import zmq
import logging
import socket
shutdown_event = threading.Event()
threading_process = None
pico_process = None
pinging_process = None
SUDO_PASSWORD = "123456"
config = None
bab = None
done_pinging_flag = False
START_FLAG = False
TARGET_IP = "10.42.0.56"  # Change this to the receiver's IP address (laptop)
PORT = 5000
BUFFER_SIZE = 1024
HOST = '0.0.0.0'
PORT_ZMQ_MSG = 12347
CONFIG_PATH = None
mypath = "/home/dt12/Code/VECTOR/bs/server/burst_test/new_config.json"
if os.path.exists(mypath):
    CONFIG_PATH = mypath
else:
    CONFIG_PATH = "/home/dt12/VECTOR/bs/server/burst_test/new_config.json"

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

def start_prepare_picoscenes():
    """Prepare the environment for PicoScenes.

    Executes a shell command to prepare the system for running PicoScenes. The command is constructed
    using parameters from the global `config.json` file. If the command does not complete within the
    specified time limit, it is forcefully terminated.

    Raises:
        subprocess.TimeoutExpired: If the command does not complete within the time limit.
    """

    # Start PicoScenes as a subprocess
    cmd = f"""array_prepare_for_picoscenes \"{config["picoscenes"]["monID2"]} \" \"{config["picoscenes"]["freq"]} {config["picoscenes"]["band"]}\""""

    print("Running setup command:")
    print(cmd)
    #result = subprocess.run(cmd, shell=True)
    proc = subprocess.Popen(cmd, shell=True)
    proc.communicate(input=f"{SUDO_PASSWORD}\n".encode())
    try:
        # Wait for process to complete, but enforce timeout
        proc.wait(timeout=float(config["picoscenes"]["timelimit"]))
        print("Command completed within time limit")

    except subprocess.TimeoutExpired:
        print(f"""Command did not complete within {config["picoscenes"]["timelimit"]} seconds""")
        print("Forcing termination of the process group")
        # Terminate entire process group
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)

        proc.wait() # Wait for termination to complete.

    # Start PicoScenes as a subprocess
    cmd = f"""array_prepare_for_picoscenes \"{config["picoscenes"]["monID1"]} \" \"{config["picoscenes"]["freq"]} {config["picoscenes"]["band"]}\""""

    print("Running setup command:")
    print(cmd)
    #result = subprocess.run(cmd, shell=True)
    proc = subprocess.Popen(cmd, shell=True)
    proc.communicate(input=f"{SUDO_PASSWORD}\n".encode())
    try:
        # Wait for process to complete, but enforce timeout
        proc.wait(timeout=float(config["picoscenes"]["timelimit"]))
        print("Command completed within time limit")

    except subprocess.TimeoutExpired:
        print(f"""Command did not complete within {config["picoscenes"]["timelimit"]} seconds""")
        print("Forcing termination of the process group")
        # Terminate entire process group
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)

        proc.wait() # Wait for termination to complete.




def start_picoscenes():
    """Start the PicoScenes application.

    Launches PicoScenes as a subprocess using parameters from the global `config.json` file. If the
    process does not complete within the specified time limit, it is forcefully terminated.

    Raises:
        subprocess.TimeoutExpired: If the process does not complete within the time limit.
    """

    global pico_process

    # Start PicoScenes as a subprocess
    cmd = f"""PicoScenes \"-d debug; -i {config["picoscenes"]["monID1"]} --mode logger --forward-to {config["picoscenes"]["forward_to_ip"]}:{config["picoscenes"]["forward_to_port1"]} --output {config["picoscenes"]["NIC_save_file1"]}; -i {config["picoscenes"]["monID2"]} --mode logger --forward-to {config["picoscenes"]["forward_to_ip"]}:{config["picoscenes"]["forward_to_port2"]} --output {config["picoscenes"]["NIC_save_file2"]} -q\""""

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



def hotspot_setup():
    """q
    Setup the hotspot and connect the reference card to the hotspot.



    """
    #path = "/home/dt12/Code/VECTOR/bs/bash/setupbs.sh"
    #cmd = f"""sudo -S bash {path} {config["setup"]["ap_interface"]} {config["setup"]["monitor_interface"]} {config["setup"]["reference_interface"]} {config["setup"]["channel_number"]}"""


    def run_command(cmd):
        print(cmd)
        proc = subprocess.Popen(cmd, shell=True)
        if cmd[0:4] == "sudo":
            proc.communicate(input=f"{SUDO_PASSWORD}\n".encode())

    run_command(f"""sudo -S nmcli connection up {config["setup"]["hotspot_name"]}-hotspot""")

def pinging():

    """Perform network pinging using iperf3.

    Executes an `iperf3` command to send small packets to a target IP address. The command runs
    in a loop until the `shutdown_event` is set, allowing for graceful termination.
    """

    cmd = f"""PicoScenes \"-d debug -i hackrf0 --freq {config["hack_rf"]["freq"]} --rate {config["hack_rf"]["rate"]} --mode {config["hack_rf"]["mode"]} --repeat {config["hack_rf"]["repeat"]} --delay {config["hack_rf"]["delay"]} --preset {config["hack_rf"]["preset"]}\""""

    print("Running setup command:")
    print(cmd)
    #result = subprocess.run(cmd, shell=True)
    proc = subprocess.Popen(cmd, shell=True)
    proc.communicate(input=f"{SUDO_PASSWORD}\n".encode())
    try:
        # Wait for process to complete, but enforce timeout
        proc.wait(timeout=20)
        print("Command completed within time limit")

    except subprocess.TimeoutExpired:
        print(f"""Command did not complete within {config["picoscenes"]["timelimit"]} seconds""")
        print("Forcing termination of the process group")
        # Terminate entire process group
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)

        proc.wait() # Wait for termination to complete.


def pinging2():

    """Perform network pinging using iperf3.

    Executes an `iperf3` command to send small packets to a target IP address. The command runs
    in a loop until the `shutdown_event` is set, allowing for graceful termination.
    """

    cmd = f"""PicoScenes \"-d debug -i hackrf0 --freq {config["hack_rf"]["freq"]} --rate {config["hack_rf"]["rate"]} --mode {config["hack_rf"]["mode"]} --repeat {config["hack_rf"]["repeat"]} --delay {config["hack_rf"]["delay"]} --preset {config["hack_rf"]["preset"]}\""""

    print("Running setup command:")
    print(cmd)
    #result = subprocess.run(cmd, shell=True)
    proc = subprocess.Popen(cmd, shell=True)
    proc.communicate(input=f"{SUDO_PASSWORD}\n".encode())
    try:
        # Wait for process to complete, but enforce timeout
        proc.wait(timeout=9999)
        print("Command completed within time limit")

    except subprocess.TimeoutExpired:
        print(f"""Command did not complete within {config["picoscenes"]["timelimit"]} seconds""")
        print("Forcing termination of the process group")
        # Terminate entire process group
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)

        proc.wait() # Wait for termination to complete.



def get_message():
    """
    Listens for an incoming connection on the global PORT and returns the received message.

    Returns:
        str: The received message.
    """
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
                    global START_FLAG
                    START_FLAG = True
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

def master_handler():

    """Main handler for the base station.

    Initializes and manages the base station's functionality, including preparing and running
    PicoScenes, parsing data, and handling graceful shutdowns via Ctrl+C.
    """

    print("Base station is running. Press Ctrl+C to stop.")

    parser = argparse.ArgumentParser(description="Client to send files or messages to the server.")
    parser.add_argument('-s', '--server', action='store_true', help="Start it the way we used to")
    parser.add_argument('-b', '--base', action='store_true', help="Start it with cable calibration")
    parser.add_argument('-1', '--file_1', type=str, help="Name of the first file to save")
    parser.add_argument('-2', '--file_2', type=str, help="Name of the second file to save")
    args = parser.parse_args()

    if args.server:
        # Setup the threads
        picoscenes_prepare_thread = threading.Thread(target=start_prepare_picoscenes)
        picoscenes_thread = threading.Thread(target=start_picoscenes, )
        pinging_thread = threading.Thread(target=pinging)
        setup_thread = threading.Thread(target=hotspot_setup)


        # Start the threads
        setup_thread.start()
        setup_thread.join()

        input("Make sure the UT is connected AND make sure the laptop is setup, then press Enter to continue...")

        picoscenes_prepare_thread.start()
        picoscenes_prepare_thread.join()


        send_message("Start")
        time.sleep(10)

        picoscenes_thread.start()

        os.killpg(os.getpgid(pico_process.pid), signal.SIGTERM)
        pico_process.wait() # Wait for termination to complete.

    if args.base:

        picoscenes_thread = threading.Thread(target=pinging )
        picoscenes_thread = threading.Thread(target=pinging2)
        recive_thread = threading.Thread(target=get_message)

        recive_thread.start()
        while not START_FLAG:
            pass
        picoscenes_thread.start()
        picoscenes_thread.join()






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