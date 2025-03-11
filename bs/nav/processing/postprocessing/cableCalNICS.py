'''
#############################################################################
                        Inter-NIC Calibration Script
#############################################################################

ASSUMES AX210 NIC! (Specifically, a MAIN and an AUX antenna)

Operator Procedure:
- Run all final NICs + one reference NIC
- Connect reference NIC to each antenna, one at a time:
    - Reference MAIN to...
        - NIC0 Main: M0
        - NIC0 Aux:  X0
        - NIC1 Main: M1
        - NIC1 Aux:  X1


(Driver Script)
Dimitry Melnikov, 2/24/25
'''

#################################################################################
############################# USER INPUTS #######################################
calFolder = "/home/dt12/received_files/received_frames.csi"#"/home/dt12/Code/VECTOR/bs/nav/csi_data/testing/outside/3-4-25" # OPTIONAL! ABsolute path.
saveCalToMat = False

NICdata = [
    # [0, 1, 2, 3] -> [AUX, AUX, MAIN, MAIN] -> [X22, X21, M21, M22]
    # Base Station Layout
    {   # NIC 1
        0:      1,  # AUX
        1:      2,  # MAIN
    },
    {   # NIC 2
        0:      0,  # AUX
        1:      3,  # MAIN
    }
]

toDS = 1; fromDS = 0
macBS = [0x10, 0x5f, 0xad, 0xd6, 0xa3, 0x2b] # (21) Base Station MAC Address
macREF= [0x6c, 0x2f, 0x80, 0xdf, 0x37, 0xca] # (23) MAC Address for reference-NIC
#macREF= [0xd8, 0x3a, 0xdd, 0xfb, 0x68, 0xe1] # UT MAC Address

#################################################################################
############################## IMPORTS ##########################################
import numpy as np                  # Numpy Processing
import scipy.io                     # To save data to .mat file

####################### Import VECTOR Libraries ##################################
# Import VECTOR Libraries
import os; import sys
VECTOR_ROOT = os.getenv("VECTOR_ROOT")
sys.path.insert(0, VECTOR_ROOT) if (VECTOR_ROOT is not None) and (VECTOR_ROOT not in sys.path) else print("WARNING! VECTOR_ROOT NOT DEFINED! RUN THIS FROM VECTOR ROOT DIRECTORY: `export VECTOR_ROOT=$(pwd)`")
import setup; setup.loadModules()

import bs.nav.processing.filtersofGOR as filtersofGOR # To import raw CSI from .csi files
import bs.nav.processing.utilsCSI as utilsCSI       # To import CSI from .mats
import bs.demo.graphing.plotCSI as plotCSI          # To plot manipulated CSI

# Ordinary Imports
import tkinter as tk                # For file selection
from tkinter import filedialog      # For file selection (GUI)

#################################################################################
########################### DRIVER SETUP ########################################
### LOAD RAW .CSI ###
# Select Directory
# Have AR Receive Antennas, AR/2 NICs
# For each NIC:
#   Select Antenna MAIN .csi file
#   Select Antenna AUX  .csi file

### DETERMINE CSI FOR REFERENCE CABLE ###
# For each NIC:
    ### REMOVE LOW RSSI TRACES ###
#   Determine average RSSI (for trace of interest)
#   Remove CSI frames with RSSI below average (for trace of interest)
#   (Remaining frames will only be 'real' with high RSSI)
    ### FILTER BY SRC/DEST ###
#   Follow along with `filtersofGOR`
#   (Remaining frames will contain CSI sent from the reference port)
    ### AVERAGE THE FRAMES ###
#   Average the remaining frames along K
#
def loadCalCSIfromRAW(AR, calFolder=None):
    # Select CSI Folder
    if (calFolder is None) or (not os.path.isdir(calFolder)):
        calFolder = filedialog.askdirectory(initialdir=os.getcwd(),
                                                title="Please select CSI cal Folder.")

    loadedCalCSI = []

    # Load CSI Associated with each element in the array
    for ar in range(AR):
        [curCalCSI, _] = filtersofGOR.loadCSIfromRAW(calFolder,
                                                     f"Please select CSI Source File for Element {ar}")
        loadedCalCSI.append(curCalCSI)

    return loadedCalCSI

def getElemMapping(NICdata):
    """ Pull element mapping via NICdata

    For instance:
        NICdata = [
        # [0, 1, 2, 3] -> [AUX, AUX, MAIN, MAIN] -> [X22, X21, M21, M22]
        # Base Station Layout
        {   # NIC 1
            0:      1,  # AUX
            1:      2,  # MAIN
        },
        {   # NIC 2
            0:      0,  # AUX
            1:      3,  # MAIN
        }
        ]
    Maps to:
        [0, 0, 1, 1]

    Args:
        NICdata (Struct Array): Similar to `filtersofGOR` user input. See callout above for structure.

    Returns:
        arr: Array mapping each element position to the NIC antenna assignment.
    """
    # NICdata = [{0: 1, 1: 2},
    #            {0: 0, 1: 3}]
    # [0, 1, 2, 3] -> [AUX, AUX, MAIN, MAIN] -> [0, 0, 1, 1] -> [X22, X21, M21, M22]

    # Pull out the Element Mapping for standard-format NICdata
    elemMapping = np.zeros(len(NICdata) * 2, dtype=int) # 2 antennas per NIC
    for nic in NICdata:
        for ant in range(2):
            elemMapping[nic[ant]] = ant

    return elemMapping


def parseCalCSI(loadedCalCSI, NICdata,
                toDS, fromDS, macBS, macREF):
    # Assume all NICdata is homogeneous
    # loadedCalCSI ~ [[CSI for Elem 0], [CSI for Elem 1], ... [CSI for Elem AR-1]]
    AR = len(loadedCalCSI)
    parsedCalCSI = []

    elemMapping = getElemMapping(NICdata) # ew ew ew

    for ar in range(AR):
        # For each NIC:
        currCalCSI = filtersofGOR.alignSingle(loadedCalCSI[ar])
        plotCSI.plotMACDEST(currCalCSI)
        import pdb; pdb.set_trace()
        # Remove Low RSSI Traces:
        currCalCSI = filtersofGOR.filterByRSSI(currCalCSI)
        # Filter by Source/Destination
        currCalCSI = filtersofGOR.filterSrcDest(currCalCSI,
                                                toDS, fromDS, macBS, macREF)
        # Convert the frames to something useful:
        [currCalMatrix, centerFreq_arr, chanBW_arr, subcFreq_arr] \
                   = filtersofGOR.convertSingToUsableMatrix(currCalCSI) # NICdata deposits the trace in the right place.
        # Average the Frames
        avgCalMatrix = np.mean(currCalMatrix, axis=3) # Average over time (K axis)
        # We have [AT, AR, S] -> [0 (first transmitter), ar (current element), : (all subcarriers)]
        currAnt = elemMapping[ar] # Get AUX/MAIN assignment from elemMapping (via NICdata)
        currCalValue = avgCalMatrix[0, currAnt, :]
        # Append averaged CSI as [AT AR S] frame
        parsedCalCSI.append(currCalValue)

    # Package for output: [AT AR S K]
    calMatrix = np.zeros((1, AR, np.shape(currCalMatrix)[2], 1), dtype=np.complex128)
    calMatrix[0, :, :, 0] = np.array(parsedCalCSI) # Assumed homogeneous
    calMatrix = 1/calMatrix # If we multiply by `outputMatrix`, we want to 'cancel it out'

    #plotCSI.plotMACDEST(currCalCSI)
    plotCSI.plot2DCSI(calMatrix, subcFreq_arr[0])
    print(f"Calibration Matrix Complete! [AT, AR, S, K] ~ {np.shape(calMatrix)}")

    return [calMatrix, centerFreq_arr, chanBW_arr, subcFreq_arr]

def applyCalOffset(calMatrix, calSubcFreq, csiPath):
    print("Select Uncalibrated CSI from the same dataset")
    # Load Pre-Parsed CSI:
    [Hest, centerFreq, chanBW, subcFreq, elemPos, loadedStruct, csiPath] = utilsCSI.loadCSIfromMAT(csiPath)
    [AT, AR, S, K] = np.shape(Hest)

    # Check to see if the subcarriers are the same.

    # Duplicate to extend axes.
    calMatrixMult = np.repeat(calMatrix, K, axis=3) # Want to apply to all K frames

    # Apply to each AT trace"
    if AT > np.shape(calMatrix)[0]:
        # Duplicate along axis.
        numReps = AT - np.shape(calMatrixMult)[0]
        calMatrixMult = np.repeat(calMatrixMult, numReps + 1, axis=0)

    if ((np.shape(subcFreq) != np.shape(calSubcFreq)) or (np.equals(subcFreq, calSubcFreq))):
        print(f"WARNING! INCOMING SUBCARRIER FREQUENCIES DIFFERENT FROM CALIBRATION.")
        print(f"RESIZING THE LARGER CHANNEL MATRIX")

        if (len(subcFreq) < len(calSubcFreq)):
            print("TRUNCATING CALIBRATION MATRIX")
            Hest_min = Hest;                subcFreq_min = subcFreq
            Hest_max = calMatrixMult;       subcFreq_max = calSubcFreq
        else:
            print("TRUNCATING INCOMING MATRIX")
            Hest_min = calMatrixMult;       subcFreq_min = calSubcFreq
            Hest_max = Hest;                subcFreq_max = subcFreq

        Hest_new = np.zeros(np.shape(Hest_min), dtype=np.complex128)

        for s_min in range(len(subcFreq_min)):
            for s_max in range(len(subcFreq_max)):
                if (subcFreq_min[s_min] == subcFreq_max[s_max]):
                    # Put the larger one into the smaller one.
                    Hest_new[:, :, s_min, :] = Hest_max[:, :, s_max, :]
                    continue

        if (len(subcFreq) < len(calSubcFreq)):
            calMatrixMult = Hest_new;   calSubcFreq = subcFreq_min
        else:
            Hest   = Hest_new;          subcFreq    = subcFreq_min

    # Apply Offset:
    correctedCSI = Hest * calMatrixMult

    # Show user:
    plotCSI.plot2DCSI(correctedCSI, subcFreq, title="CSI Post-Calibration", doUnwrap=True)

    # Save to .mat file:
    corrFilename = os.path.splitext(os.path.basename(csiPath))[0] + "_POSTCAL"
    filtersofGOR.saveCSItoMAT(correctedCSI, centerFreq, chanBW, subcFreq, elemPos, corrFilename)

def generateCalOffset(NICdata, calFolder,
                      toDS, fromDS, macBS, macREF,
                      saveCalToMat=False):
    print("We wish to generate Phase Calibration Offsets for each element in a given array")
    print("We operate under the assumption that the 'Calibration Data' is generated by a cable,")
    print("   which is plugged into a 'reference source,' then recorded by each element in the array.")
    print("Given that 'reference source', we wish every element to have the same response.")
    print("The calculated calibration coefficients will make it such that each will exhibit close to 0deg.")

    AR = len(NICdata) * 2
    # Load RAW .CSI files
    loadedCalCSI = loadCalCSIfromRAW(AR, calFolder)
    # Determine CSI for reference cable for each trace
    [calMatrix, centerFreq_arr, chanBW_arr, subcFreq_arr] \
                 = parseCalCSI(loadedCalCSI, NICdata,
                               toDS, fromDS, macBS, macREF)
    # Save Cal Offset to Matlab file
    if saveCalToMat:
        calPath = filtersofGOR.saveCSItoMAT(calMatrix, centerFreq_arr[0], chanBW_arr[0], subcFreq_arr[0], [],
                                            "calMatrix", calFolder)

    return [calMatrix, subcFreq_arr[0]]

if __name__ == "__main__":
    # Calculate Calibration Coefficients
    [calMatrix, calSubcFreq] = generateCalOffset(NICdata, calFolder,
                      toDS, fromDS, macBS, macREF, saveCalToMat)

    # Apply Calibration Offset to parsed .mat file
    applyCalOffset(calMatrix, calSubcFreq, calFolder)
