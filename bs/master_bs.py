import threading
import signal
import sys
import os
import subprocess
import argparse
import json

shutdown_event = threading.Event()
pico_process = None
SUDO_PASSWORD = "123456"
config = None
CONFIG_PATH = "/home/dt12/Code/VECTOR/bs/config.json"
CONFIG_PATH = "/home/dt12/Code/VECTOR/bs/config.json"

def load_config():
    """Load configuration from a JSON file.

    Reads the configuration file specified by `CONFIG_PATH` and loads it into the global `config` variable.
    If the file is not found or cannot be parsed, the program exits with an error.

    Raises:
        FileNotFoundError: If the configuration file does not exist.
        json.JSONDecodeError: If the configuration file is not valid JSON.
    """
    """Load configuration from a JSON file.

    Reads the configuration file specified by `CONFIG_PATH` and loads it into the global `config` variable.
    If the file is not found or cannot be parsed, the program exits with an error.

    Raises:
        FileNotFoundError: If the configuration file does not exist.
        json.JSONDecodeError: If the configuration file is not valid JSON.
    """
    global config
    try:
        if not os.path.exists(CONFIG_PATH):
            raise FileNotFoundError(f"Config file {CONFIG_PATH} not found!")

        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)
    except Exception as e:
        print(f"Error loading config: {e}")
        sys.exit(1)

    print(config)

def start_prepare_picoscenes():
    """Prepare the environment for PicoScenes.

    Executes a shell command to prepare the system for running PicoScenes. The command is constructed
    using parameters from the global `config.json` file. If the command does not complete within the
    specified time limit, it is forcefully terminated.

    Raises:
        subprocess.TimeoutExpired: If the command does not complete within the time limit.
    """

    # Start PicoScenes as a subprocess
    cmd = f"""array_prepare_for_picoscenes \"{config["picoscenes"]["monID1"]} {config["picoscenes"]["monID2"]}\" \"{config["picoscenes"]["freq"]} {config["picoscenes"]["band"]}\""""

    print("Running setup command:")
    print(cmd)
    #result = subprocess.run(cmd, shell=True)
    proc = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    proc.communicate(input=f"{SUDO_PASSWORD}\n".encode())
    try:
        # Wait for process to complete, but enforce timeout
        proc.wait(timeout=float(config["picoscenes"]["timelimit"]))
        print("Command completed within time limit")
    print("Running setup command:")
    print(cmd)
    #result = subprocess.run(cmd, shell=True)
    proc = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
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

    """Start the PicoScenes application.

    Launches PicoScenes as a subprocess using parameters from the global `config.json` file. If the
    process does not complete within the specified time limit, it is forcefully terminated.

    Raises:
        subprocess.TimeoutExpired: If the process does not complete within the time limit.
    """

    global pico_process

    # Start PicoScenes as a subprocess
    cmd = f"""PicoScenes \"-d debug; -i {config["picoscenes"]["monID1"]} --mode logger;
        -i {config["picoscenes"]["monID2"]} --mode logger
        --forward-to {config["picoscenes"]["forward_to_ip"]}:{config["picoscenes"]["forward_to_port"]}\""""
    # Start PicoScenes as a subprocess
    cmd = f"""PicoScenes \"-d debug; -i {config["picoscenes"]["monID1"]} --mode logger;
        -i {config["picoscenes"]["monID2"]} --mode logger
        --forward-to {config["picoscenes"]["forward_to_ip"]}:{config["picoscenes"]["forward_to_port"]}\""""

    print("Running injection command:")
    print(cmd)
    #result = subprocess.run(cmd, shell=True)
    pico_process = subprocess.Popen(cmd, shell=True, preexec_fn=os.setsid)

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


def start_parsing():
    """Handle parsing functionality.

    This is a placeholder function for parsing logic. It runs in a loop until the `shutdown_event`
    is set, allowing for graceful termination.
    """
    while not shutdown_event.is_set():
        pass

def hotspot_setup():
    path = "/home/dt12/Code/VECTOR/bs/bash/setupbs.sh"
    cmd = f"""sudo bash {path}
    {config["setup"]["ap_interface"]}
    {config["setup"]["monitor_interface"]}
    {config["setup"]["reference_interface"]}
    {config["setup"]["ssid"]} {config["setup"]["channel_number"]}
    """
    proc = subprocess.Popen(cmd, shell=True, preexec_fn=os.setsid)

    try:
        # Wait for process to complete, but enforce timeout
        proc.wait(timeout=float(config["picoscenes"]["timelimit"]))
        print("Command completed within time limit")
    print("Running injection command:")
    print(cmd)
    #result = subprocess.run(cmd, shell=True)
    pico_process = subprocess.Popen(cmd, shell=True, preexec_fn=os.setsid)

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


def start_parsing():
    """Handle parsing functionality.

    This is a placeholder function for parsing logic. It runs in a loop until the `shutdown_event`
    is set, allowing for graceful termination.
    """
    while not shutdown_event.is_set():
        pass

def hotspot_setup():
    path = "/home/dt12/Code/VECTOR/bs/bash/setupbs.sh"
    cmd = f"""sudo bash {path}
    {config["setup"]["ap_interface"]}
    {config["setup"]["monitor_interface"]}
    {config["setup"]["reference_interface"]}
    {config["setup"]["ssid"]} {config["setup"]["channel_number"]}
    """
    proc = subprocess.Popen(cmd, shell=True, preexec_fn=os.setsid)

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


def pinging():

    """Perform network pinging using iperf3.

    Executes an `iperf3` command to send small packets to a target IP address. The command runs
    in a loop until the `shutdown_event` is set, allowing for graceful termination.
    """

    cmd = f"""iperf3 -c {config["ping_settings"]["ip"]} -{config["ping_settings"]["protical"]} -b {config["ping_settings"]["bandwidth"]} -l {config["ping_settings"]["bandwidth"]}"""

    print("Running pinging command:")
    print(cmd)
    #result = subprocess.ru n(cmd, shell=True)
    proc = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


    while not shutdown_event.is_set():
        pass

def master_handler():

    """Main handler for the base station.

    Initializes and manages the base station's functionality, including preparing and running
    PicoScenes, parsing data, and handling graceful shutdowns via Ctrl+C.
    """

    print("Base station is running. Press Ctrl+C to stop.")

    # parser = argparse.ArgumentParser(description="Client to send files or messages to the server.")
    # parser.add_argument('-s', '--send', type=str, help="Path to the file to send")
    # parser.add_argument('-m', '--message', type=str, help="Message to send")
    # args = parser.parse_args()

    picoscenes_prepare_thread = threading.Thread(target=start_prepare_picoscenes)
    picoscenes_thread = threading.Thread(target=start_picoscenes)
    parsing_thread = threading.Thread(target=start_parsing)
    # pinging_thread = threading.Thread(target=pinging)
    # setup_thread = threading.Thread(target=hotspot_setup)
    # pinging_thread = threading.Thread(target=pinging)
    # setup_thread = threading.Thread(target=hotspot_setup)

    parsing_thread.start()

    # setup_thread.start()
    # setup_thread.join()

    # setup_thread.start()
    # setup_thread.join()

    picoscenes_prepare_thread.start()
    picoscenes_prepare_thread.join()

    picoscenes_thread.start()



    def signal_handler(sig, frame):
        global pico_process
        print("\nShutting down server...")
        shutdown_event.set()

        # Send SIGINT to the PicoScenes subprocess
        if pico_process:
            os.killpg(os.getpgid(pico_process.pid), signal.SIGINT)
            os.killpg(os.getpgid(pico_process.pid), signal.SIGINT)
            os.killpg(os.getpgid(pico_process.pid), signal.SIGTERM)
            os.killpg(os.getpgid(pico_process.pid), signal.SIGKILL)

            #pico_process.wait()  # Wait for the subprocess to terminate
            os.killpg(os.getpgid(pico_process.pid), signal.SIGKILL)

            #pico_process.wait()  # Wait for the subprocess to terminate

        # Wait for threads to finish
        picoscenes_thread.join()
        parsing_thread.join()
        sys.exit(0)

    # Register the signal handler for SIGINT (Ctrl+C)
    signal.signal(signal.SIGINT, signal_handler)
    signal.pause()



if __name__ == "__main__":
    load_config()
    master_handler()
