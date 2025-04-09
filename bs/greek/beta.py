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
SAVE_DIR = 'received_files'

mypath = "/home/dt12/Code/VECTOR/bs/greek/config.json"
if os.path.exists(mypath):
    CONFIG_PATH = mypath
else:
    CONFIG_PATH = "/home/dt12/VECTOR/bs/server/burst_test/config.json"

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



def hack_rf_pinging():

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




def hack_rf_pinging2():

    """Perform network pinging using iperf3.

    Executes an `iperf3` command to send small packets to a target IP address. The command runs
    in a loop until the `shutdown_event` is set, allowing for graceful termination.
    """

    cmd = f"""PicoScenes \"-d debug -i hackrf0 --freq {config["hack_rf"]["freq"]} --rate {config["hack_rf"]["rate"]} --mode {config["hack_rf"]["mode"]} --repeat {config["hack_rf"]["repeat"]} --delay {config["hack_rf"]["delay"]} --preset {config["hack_rf"]["preset"]}; -i 2 --mode logger  --output BETA_HOTSPOT_CSI \""""

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

    # Disable power save on all interfaces
    run_command(f"""sudo -S iw dev {config["setup"]["ap_interface"]} set power_save off""")
    run_command(f"""sudo -S iw dev {config["setup"]["monitor_interface"]} set power_save off""")
    #run_command(f"""sudo -S iw dev {config["setup"]["reference_interface"]} set power_save off""")

    # Set the reference  hotspot to the chosen channel
    #run_command(f"""sudo -S iwconfig {config["setup"]["reference_interface"]} channel {config["setup"]["channel_number"]}""")
    run_command(f"""sudo -S nmcli connection modify {config["setup"]["hotspot_name"]}-hotspot 802-11-wireless.channel {config["setup"]["channel_number"]}""")
    run_command(f"""sudo -S nmcli connection modify {config["setup"]["hotspot_name"]}-hotspot ifname {config["setup"]["ap_interface"]}""")

    # Start the hotspot+
    run_command(f"""sudo -S nmcli connection up {config["setup"]["hotspot_name"]}-hotspot""")

    # Connect reference card to the hotspot
    #run_command(f"""sudo -S nmcli device wifi rescan ifname {config["setup"]["reference_interface"]}""")
    time.sleep(0.5)
    #run_command(f"""sudo -S nmcli device wifi rescan ifname {config["setup"]["reference_interface"]}""")
    #run_command(f"""sudo -S nmcli device wifi connect {config["setup"]["hotspot_name"]} ifname {config["setup"]["reference_interface"]} password {config["setup"]["hotspot_password"]}""")

    # Get center frequency and channel bandwidth for the AP interface
    run_command(f"iw dev {config['setup']['ap_interface']} info")


def pinging():

    """Perform network pinging using iperf3.

    Executes an `iperf3` command to send small packets to a target IP address. The command runs
    in a loop until the `shutdown_event` is set, allowing for graceful termination.
    """

    #cmd = f"""iperf3 -c {config["ping_settings"]["ip"]} -{config["ping_settings"]["protical"]} -b {config["ping_settings"]["bandwidth"]} -l {config["ping_settings"]["ping_amount"]} -n {config["ping_settings"]["total_size"]} -i {config["ping_settings"]["interval"]}"""
    cmd = f"""ping -i 5 -c 4 {config["ping_settings"]["ip"]}"""

    print("Running pinging command:")
    print(cmd)
    #result = subprocess.ru n(cmd, shell=True)
    proc = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    try:
        # Wait for process to complete, but enforce timeout
        proc.wait(timeout=float(config["picoscenes"]["timelimit"]))
        print("Command completed within time limit")

    except subprocess.TimeoutExpired:
        print(f"""Command did not complete within {config["picoscenes"]["timelimit"]} seconds""")
        print("Forcing termination of the process group")
        # Terminate entire process group
        os.killpg(os.getpgid(pico_process.pid), signal.SIGTERM)
        proc.wait() # Wait for termination to complete

def send_message_laptop(message):
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

def send_message_alpha(message):
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


def master_handler():

    """Main handler for the base station.

    Initializes and manages the base station's functionality, including preparing and running
    PicoScenes, parsing data, and handling graceful shutdowns via Ctrl+C.
    """

    print("Base station is running. Press Ctrl+C to stop.")

    parser = argparse.ArgumentParser(description="Client to send files or messages to the server.")
    parser.add_argument('-1', '--file_1', type=str, help="Name of the first file to save")
    parser.add_argument('-2', '--file_2', type=str, help="Name of the second file to save")
    args = parser.parse_args()


    # Set up the hotspot thread
    hotspot_thread = threading.Thread(target=hotspot_setup)
    hotspot_thread.start()
    hotspot_thread.join()

    hack_rf_pinging_thread = threading.Thread(target=hack_rf_pinging)
    hack_rf_pinging2_thread = threading.Thread(target=hack_rf_pinging2)

    input("Press Enter to start the PicoScenes process...")

    #send the message to the laptop and alpha
    send_message_laptop("Start")
    send_message_alpha("Start")
    # Start the PicoScenes process
    time.sleep(5)

    # hack_rf_pinging_thread.start()
    # hack_rf_pinging_thread.join()

    hack_rf_pinging2_thread.start()
    hack_rf_pinging2_thread.join()

    # Start the ZeroMQ file server
    # zmq_thread = threading.Thread(target=start_zmq_file_server)
    # zmq_thread.start()
    # #send message to laptop and alpha
    # send_message_laptop("Stop")
    # send_message_alpha("Stop")

    #parse the data


    #graph the data






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
