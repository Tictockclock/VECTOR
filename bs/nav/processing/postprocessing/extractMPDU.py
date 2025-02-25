'''
Extract the WiFi Frames from Collected CSI for Rebroadcasting

Given a single CSI file, with chosen MAC Header properties, 
extract the raw MPDU for rebroadcasting

DISCLAIMER: FOR EDUCATIONAL PURPOSES ONLY. 
WE DO NOT TAKE RESPONSIBILITY FOR MISUSE OF CODE.

(Driver Script)
Dimitry Melnikov, 2/23/25
'''
################################################################
###################### USER INPUTS #############################
# MAC Address & To/From DS Alignment
# See https://mrncciew.com/2014/09/28/cwap-mac-headeraddresses/
toDS = 1; fromDS = 0
macBS = [0x6c, 0x2f, 0x80, 0xdf, 0x37, 0xca] # Base Station MAC Address
macUT = [0x8c, 0xe9, 0xee, 0xd9, 0xa2, 0xe2] # User Terminal MAC Address (antenna we're tracking)

################################################################
######################## IMPORTS ###############################
import sys                          # Make sure that python can find the .so file VVVV
sys.path.append('/home/dt12/Code/VECTOR/bs/bs-venv/PicoscenesToolbox')
from picoscenes import Picoscenes   # To process the CSI

import tkinter as tk                # For file selection
from tkinter import filedialog      # For file selection

import numpy as np                  # Numpy Processing
import scipy.io                     # To save data as a .mat file
import os                           # To retrieve the file

import subprocess                   # To launch Picoscenes subprocess
import signal                       # To kill Picoscenes subprocess

print("Libraries imported!")
###################### DRIVER CODE #############################
def loadCSIfromRAW(csiPath=None):
    """ Load raw CSI from .csi file
        Example use:
        `[loadedCSI, csiPath] = loadCSIfromRAW()`

    Args:
        csiPath (string, optional): Absolute path to .csi file. Defaults to None.

    Returns:
        Tuple [Picoscenes Dictionary Array, csiPath): 
            {RETURNEDOBJNAME}.raw = [ (Frame 0):
                'StandardHeader'    : 802.11 MAC Header
                'RxSBasic'          : RxSBasic Segment
                'RxExtraInfo'       : ExtraInfo Segment (measured at RX end)
                'MPDUS'             : Raw MPDU data w/o FCS bytes
                'CSI'               : CSI measured from HT/VHT/HE/EHT-LTF Field
            ], [(Frame 1) ...], [(Frame 2) ...], ...]

            More structure info in the documentation: https://ps.zpj.io/matlab.html
            (Can also dissect with Python debugger (pdb) and dir({RETURNEDOBJNAME}))

        csiPath: Absolute Path to loaded .csi file.
    """

    if csiPath is None:
        # Do GUI interface if path not specified
        # Ask the user to select a single file name.
        csiPath = filedialog.askopenfilename(initialdir=os.getcwd(),
                                            title="Please select the CSI Source File:",
                                            filetypes=[('csi files', '.csi'), ('all files', '.*')])
        
    return (Picoscenes(csiPath), csiPath) # Load in data


def extractMPDU(toDS, fromDS, macBS, macUT, loadedCSI):
    """ Extract MPDUs from collected CSI frames, for rebroadcasting.

    Args:
        toDS (Boolean): Addressed to Router/BS (See https://mrncciew.com/2014/09/28/cwap-mac-headeraddresses/)
        fromDS (Boolean): Addressed from Router/BS
        macBS (Hex List): MAC Address for the Base Station (BS) / Data Service
        macUT (Hex List): MAC Address for the User Terminal / User Peripheral
        loadedCSI (Picoscenes CSI Object): Loaded in CSI, returned directly from `Picoscenes(csiPath)`

    Returns:
        mpdus: List of raw MPDUs with corresponding to/fromDS characteristics.
    """
    if len(loadedCSI.raw) == 0:
        print("No frames found in the CSI File!")
        return None

    # Filter out the CSI with the correct toDS, fromDS:
    # Info: https://mrncciew.com/2014/09/28/cwap-mac-headeraddresses/
    if (toDS == 1) and (fromDS == 0): # toDS = 1, fromDS = 0
        macSRC = macUT; macDEST = macBS # Sending from UT to BS 
    else:             # toDS = 0, fromDS = 1 (or other cases)
        macSRC = macBS; macDEST = macUT # Sending from BS to UT

    # Find all MAC Address matches in the frame
    matches = [
        frame for frame in loadedCSI.raw
        if (frame['StandardHeader']['ControlField']['ToDS'] == toDS)        and \
           (frame['StandardHeader']['ControlField']['FromDS'] == fromDS)    and \
           (frame['StandardHeader']['Addr1'] == macDEST)                    and \
           (frame['StandardHeader']['Addr2'] == macSRC)
    ]   # Only return frames that match ALL of the fields.

    if len(matches) == 0:
        print(f"No matching CSI frames found for toDS: {toDS}, fromDS: {fromDS}, macBS: {macBS}, macUT: {macUT}")
        return None
    
    # Return ONLY the 'MPDUS' field.
    mpdus = [
        frame['MPDUS'] for frame in matches
    ]

    return mpdus


def saveMPDU(mpdus, dirName, csiPath):
    """ Save raw `mpdus` to a folder (dirName) a level below `csiPath`

    Args:
        mpdus (List): List of lists. `mpdus[i][0]` returns the `ith` mpdu collected. 
        dirName (String): Name of Directory on which to save (on same level as `csiPath`)
        csiPath (String): Absolute path to source .csi file.

    Returns:
        String: mpduDir to which we saved the mpdus
    """

    # Determine the MPDU Folder Path
    csiDir = os.path.dirname(csiPath) 

    # Make MPDU Directory
    mpduDir = os.path.join(csiDir, dirName)
    os.makedirs(mpduDir, exist_ok="True")

    # Write the raw packets to binary files
    for i in range(len(mpdus)):
        framePath = os.path.join(mpduDir, f"frame_{i}.bin")
        frameBytes = bytes(mpdus[i][0]) # Flatten it first

        with open(framePath, "wb") as f:
            f.write(frameBytes)

    return mpduDir

def injectFrameAndListen(framePath, injectID="231", monID="211", 
                         chan="2412 HT20",
                         timelimit=10):
    """ Runs PicoScenes to inject frame at `framePath` from interface `injectID`, then
        listen on `monID` to output to CSI file.

    Args:
        framePath (str): Absolute path to MPDU frame.
        injectID (str, optional): _description_. Defaults to "231".
        monID (str, optional): _description_. Defaults to "211".
        chan (str, optional): _description_. Defaults to "2412 HT20".
        timelimit (int, optional): _description_. Defaults to 10.
    """
    # Timeout in seconds
    # Great Big WiFi Channelization Table: https://ps.zpj.io/channels.html#id1

    # Build the injection command string
    cmd = f"PicoScenes \"-d debug; -i {injectID} --mode injector --tx-from-file {framePath} --repeat 1 --delay 0 --channel '{chan}'; -i {monID} --mode logger; q\""

    print("Running injection command:")
    print(cmd)
    #result = subprocess.run(cmd, shell=True)
    proc = subprocess.Popen(cmd, shell=True, preexec_fn=os.setsid)
    try:
        # Wait for process to complete, but enforce timeout
        proc.wait(timeout=timelimit)
        print("Command completed within time limit")

    except subprocess.TimeoutExpired:
        print(f"Command did not complete within {timelimit} seconds")
        print("Forcing termination of the process group")
        # Terminate entire process group
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        proc.wait() # Wait for termination to complete.


def main(toDS, fromDS, macBS, macUT, csiPath=None):
    # Load in the CSI File
    print("Loading CSI File...")
    [loadedCSI, csiPath] = loadCSIfromRAW(csiPath)

    # Extract the necessary MPDUs
    print("Filtering out frames without selected characteristics...")
    mpdus = extractMPDU(toDS, fromDS, macBS, macUT, loadedCSI)

    # Save MPDUs to an output file
    print("Saving MPDUs to raw binary files for later rebroadcasting...")
    mpduDir = saveMPDU(mpdus, f"MPDUS_TO{toDS}_FM{fromDS}", csiPath)

    print(f"...done. Saved to {mpduDir}")

if __name__ == "__main__":
    # Extract + Save the data:
    #main(toDS, fromDS, macBS, macUT)

    # Inject the data:
    framePath = "/home/dt12/Code/VECTOR/bs/nav/csi_data/testing/asec_basement/1_BS_LAPTOP_90DEG_9FT_BS/MPDUS_TO1_FM0/frame_0.bin"
    injectFrameAndListen(framePath, injectID="231", monID="211",\
                         chan="2412 HT20", timelimit=100)