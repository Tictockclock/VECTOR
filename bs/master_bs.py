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
CONFIG_PATH = "config.json"

def load_config():
    """Load configuration from JSON file"""
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
    while not shutdown_event.is_set():

        # Start PicoScenes as a subprocess
        cmd = f"""array_prepare_for_picoscenes \"{config["picoscenes"]["monID1"]} {config["picoscenes"]["monID2"]}\" \"{config["picoscenes"]["freq"]} {config["picoscenes"]["band"]}\""""

        print("Running setup command:")
        print(cmd)
        #result = subprocess.run(cmd, shell=True)
        proc = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        proc.communicate(input=f"{SUDO_PASSWORD}\n".encode())
        try:
            # Wait for process to complete, but enforce timeout
            proc.wait(timeout=config["picoscenes"]["timelimit"])
            print("Command completed within time limit")

        except subprocess.TimeoutExpired:
            print(f"""Command did not complete within {config["picoscenes"]["timelimit"]} seconds""")
            print("Forcing termination of the process group")
            # Terminate entire process group
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            proc.wait() # Wait for termination to complete.

def start_picoscenes():

    global pico_process
    while not shutdown_event.is_set():

        # Start PicoScenes as a subprocess
        cmd = f"""PicoScenes \"-d debug; -i {config["picoscenes"]["monID1"]} --mode logger;
          -i {config["picoscenes"]["monID2"]} --mode logger
         --forward-to {config["picoscenes"]["forward_to"]}\""""

        print("Running injection command:")
        print(cmd)
        #result = subprocess.run(cmd, shell=True)
        proc = subprocess.Popen(cmd, shell=True, preexec_fn=os.setsid)
        try:
            # Wait for process to complete, but enforce timeout
            proc.wait(timeout=config["picoscenes"]["timelimit"])
            print("Command completed within time limit")

        except subprocess.TimeoutExpired:
            print(f"""Command did not complete within {config["picoscenes"]["timelimit"]} seconds""")
            print("Forcing termination of the process group")
            # Terminate entire process group
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            proc.wait() # Wait for termination to complete.


def start_parsing():
    """Placeholder for parsing functionality."""
    while not shutdown_event.is_set():
        pass


def master_handler():
    print("Base station is running. Press Ctrl+C to stop.")

    # parser = argparse.ArgumentParser(description="Client to send files or messages to the server.")
    # parser.add_argument('-s', '--send', type=str, help="Path to the file to send")
    # parser.add_argument('-m', '--message', type=str, help="Message to send")
    # args = parser.parse_args()

    picoscenes_prepare_thread = threading.Thread(target=start_prepare_picoscenes)
    picoscenes_thread = threading.Thread(target=start_picoscenes)
    parsing_thread = threading.Thread(target=start_parsing)


    parsing_thread.start()

    picoscenes_prepare_thread.start()
    picoscenes_prepare_thread.join()

    picoscenes_thread.start()

    def signal_handler(sig, frame):
        global pico_process
        print("\nShutting down server...")
        shutdown_event.set()

        # Send SIGINT to the PicoScenes subprocess
        if pico_process:
            os.killpg(os.getpgid(pico_process.pid), signal.SIGTERM)
            pico_process.wait()  # Wait for the subprocess to terminate

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
