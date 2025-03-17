import threading
import signal
import sys
import os
import os.path
import subprocess
import json
import time
import argparse


shutdown_event = threading.Event()
threading_process = None
pico_process = None
SUDO_PASSWORD = "123456"
config = None
bab = None
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
    cmd = f"""PicoScenes \"-d debug; -i {config["picoscenes"]["monID1"]} --mode logger --forward-to {config["picoscenes"]["forward_to_ip"]}:{config["picoscenes"]["forward_to_port1"]} --output {config["picoscenes"]["NIC_save_file1"]}; -i {config["picoscenes"]["monID2"]} --mode logger --forward-to {config["picoscenes"]["forward_to_ip"]}:{config["picoscenes"]["forward_to_port2"]} --output {config["picoscenes"]["NIC_save_file2"]}\""""

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


def start_parsing():
    """Handle parsing functionality.

    This is a placeholder function for parsing logic. It runs in a loop until the `shutdown_event`
    is set, allowing for graceful termination.
    """
    while not shutdown_event.is_set():
        pass

def calibrate_setup():
    #"Calibrate the hotspot and connect the reference card to the hotspot."
    def run_command(cmd):
        print(cmd)
        proc = subprocess.Popen(cmd, shell=True)
        if cmd[0:4] == "sudo":
            proc.communicate(input=f"{SUDO_PASSWORD}\n".encode())


def hotspot_setup():
    """
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
    freq_output = run_command(f"iw dev {config['setup']['ap_interface']} info")
    if freq_output:
        lines = freq_output.split('\n')
        center_freq = None
        chan_bw = None

        for line in lines:
            if "channel" in line:
                parts = line.split()
                chan_bw = parts[5]
                center_freq = parts[8]
                break

        if center_freq and chan_bw:
            arr_prep_pico_str = f"{center_freq} HT{chan_bw}"
            print(f"CENTER_FREQ: {center_freq}, CHAN_BW: {chan_bw}")
        else:
            print("Failed to extract frequency and bandwidth")
    else:
        print("Failed to get output from iw dev command")


def pinging():

    """Perform network pinging using iperf3.

    Executes an `iperf3` command to send small packets to a target IP address. The command runs
    in a loop until the `shutdown_event` is set, allowing for graceful termination.
    """

    #cmd = f"""iperf3 -c {config["ping_settings"]["ip"]} -{config["ping_settings"]["protical"]} -b {config["ping_settings"]["bandwidth"]} -l {config["ping_settings"]["ping_amount"]} -n {config["ping_settings"]["total_size"]} -i {config["ping_settings"]["interval"]}"""
    cmd = f"""ping -i 4 -c 1200 {config["ping_settings"]["ip"]}"""

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

def master_handler():

    """Main handler for the base station.

    Initializes and manages the base station's functionality, including preparing and running
    PicoScenes, parsing data, and handling graceful shutdowns via Ctrl+C.
    """

    print("Base station is running. Press Ctrl+C to stop.")

    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Client to send files or messages to the server.")
    parser.add_argument('-n', '--normal', action='store_true', help="Start it the way we used to")
    parser.add_argument('-c', '--calibrate', action='store_true', help="Run through the calibration process and start")
    parser.add_argument('-s', '--start_picoscenes', action='store_true', help=f"Start without setting up the hotspot and calibration")
    parser.add_argument('-1', '--file_1', type=str, help="Start the pinging process")
    parser.add_argument('-2', '--file_2', type=str, help="Start the pinging process")
    args = parser.parse_args()

    # Setup the threads
    picoscenes_prepare_thread = threading.Thread(target=start_prepare_picoscenes)
    picoscenes_thread = threading.Thread(target=start_picoscenes)
    parsing_thread = threading.Thread(target=start_parsing)
    pinging_thread = threading.Thread(target=pinging)
    setup_thread = threading.Thread(target=hotspot_setup)

    if args.file_1:
        config["picoscenes"]["NIC_save_file1"] = args.file_1
    if args.file_2:
        config["picoscenes"]["NIC_save_file2"] = args.file_2

    # Start the threads based on the command line arguments
    if args.normal:

        parsing_thread.start()
        setup_thread.start()
        setup_thread.join()

        input("Make sure the UT is connected then press Enter to continue...")

        # setup_thread.start()
        # setup_thread.join()

        picoscenes_prepare_thread.start()
        picoscenes_prepare_thread.join()

        picoscenes_thread.start()

        time.sleep(10)
        pinging_thread.start()
        pinging_thread.join()

    if args.calibrate:
        pass

    if args.start_picoscenes:

        parsing_thread.start()
        picoscenes_thread.start()

        time.sleep(10)
        pinging_thread.start()
        pinging_thread.join()

    if not pinging_thread.is_alive():
        os.kill(os.getpid(), signal.SIGINT)



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
