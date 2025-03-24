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
calFolder = "/mnt/c/Users/dmtrm/OneDrive/Schoolwork/(5) Senior Year/Senior Design/VECTOR/bs/nav/csi_data/testing/asec_basement/3-11-25/CAL/" # OPTIONAL! ABsolute path.
saveCalToMat = False
saveCorrToMat= True

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

## CABLE LENGTH
cablePts = [[2.436e9, -104.55],[2.447e9, -139.20],[2.458e9, -173.76]] # [Freq, Phase] (use to calculate group delay)

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

def getCableDelay(pts):
    """ Get Cable Phase Delay from measured points
    Gets line of best fit, then returns lambda function with same characteristics.
    Can use to get phase delay at a given frequency (which may be different from measurement)

    lambda(freq (Hz)) -> Phase (deg)

    Args:
        pts (list of lists): [[freq1 (Hz), phase1 (deg)], [freq2, phase2], ...]

    Returns:
        lambda: lambda(freq) yields the phase delay in degrees.
    """
    # Extract x and y:
    x = np.array([point[0] for point in pts])
    y = np.array([point[1] for point in pts])

    # Linear regression (y = mx + b)
    m, b = np.polyfit(x, y, 1)

    print(f"Calculated group delay of {m} deg/Hz!")

    # Return lambda function
    return lambda freq: (m * freq + b)

def applyCableDelay(calMatrix, calSubcFreq, cablePts=[]):
    if not cablePts:
        # No pts to fit to. Assume ideal (Mag 1, Phase Delay 0) for all subcarriers
        print("No measured cable points! Assuming ideal channel (Phase Delay 0)")
        return calMatrix
    else:
        # We have pts to fit to.
        cableDelay = getCableDelay(cablePts)
        phaseDelayPerSub = cableDelay(calSubcFreq) # Input in Hz, output in Deg
        phaseDelayPerSub = phaseDelayPerSub*np.pi/180 # Convert to radians
        phaseDelayPerSub = np.exp(1j*phaseDelayPerSub)# Make complex
        
        [AT, AR, S, K] = np.shape(calMatrix)
        # AT = 1, K = 1 by definition -- everything comes from one reference, and is averaged to a single frame.
        newMatrix = np.zeros(np.shape(calMatrix), dtype=np.complex128)
        for ar in range(AR):
            newMatrix[0, ar, :, 0] = calMatrix[0, ar, :, 0]*phaseDelayPerSub # Apply cable delay.

        return newMatrix

def sortCalCSI(calMatrix):
    """ Sorts `calMatrix` by AR Fit for each AT & K

    Sample would return: calMatrix ~ [AT AR S K]:
        where [0, 0, :, 0] ~ CSI for AR w/ best fit to a line for AT=0, K=0
        where [0, 1, :, 0] ~ CSI for AR w/ second best fit to a line. for AT=0, K=0

    (For a cable, we expect a line. If the signal's seeping out of the cable, the phase would end
     up nonlinear over subcarriers.)

    (Note - Picoscenes gives CSI already in dB, but without the (-) sign.)
    (As a result, we would get 12 = np.abs(...) corresponding to -12dB)
    (-12dB > -100dB, but 12 < 100. The way we sort, the -12dB will end up at the 'greater magnitude index')
    (^^^ This could also be wrong. But, either way, the 0th should be the greatest. -- this is if we're sorting by avg)
    
    Args:
        calMatrix ([AT AR S K] Matrix): CSI Matrix

    Returns:
        ([AT AR S K] Matrix): Sorted CSI
    """
    
    [AT, AR, S, K] = np.shape(calMatrix)

    sortedMatrix = np.zeros(np.shape(calMatrix), dtype=np.complex128)
    for k in range(K):
        for at in range(AT): 
            # Determine which AR trace has the cleanest (highest R^2) in the dataset
            x = np.arange(S)
            y = utilsCSI.unwrapFromMiddle(np.angle(calMatrix[at, :, :, k]))

            R2Scores = []           # Store the correlation coefficient
            for ar in range(AR):
                R2Scores.append(np.corrcoef(x, y[ar, :])[0, 1] ** 2)

            arOrder = np.argsort(R2Scores)#[::-1] # Best to Worst Correlation (descending order)

            #avgPerSubcarrier = np.mean(-1*np.abs(calMatrix[at, :, :, k]), axis=1) # Take stdev of magnitude for each AR, run along the Subcarriers
            #arOrder = np.argsort(avgPerSubcarrier)

            sortedSlice = calMatrix[at, :, :, k]
            sortedSlice = sortedSlice[arOrder, :]
            sortedMatrix[at, :, :, k] = sortedSlice

    return sortedMatrix

def sortAndAverageCalCSI(calMatrix):
    [AT, AR, S, K] = np.shape(calMatrix)

    m_arr = [] # Slopes for each slice
    b_arr = [] # Y-Intercepts for each slice
    slice_arr = []
    for k in range(K):
        for at in range(AT):
            # Determine which AR trace has the cleanest (highest R^2) in the dataset
            x = np.arange(S)
            y = utilsCSI.unwrapFromMiddle(np.angle(calMatrix[at, :, :, k]))

            import pdb; pdb.set_trace()

            R2Scores = [] # Store correlation coefficient
            for ar in range(AR):
                R2Scores.append(np.corrcoef(x, y[ar, :])[0, 1] ** 2)

            # Select the arSlice with the cleanest correlation coefficient
            arSlice = np.argsort(R2Scores)[-1] # Highest is the right one.

            # Now, perform a curve fit to the middle few subcarriers:
            middleSubcIndex = len(y[0])//2
            m, b = np.polyfit(x[(middleSubcIndex-5):(middleSubcIndex+5)], y[arSlice, (middleSubcIndex-5):(middleSubcIndex+5)], 1)
            m_arr.append(m)
            b_arr.append(b)
            slice_arr.append(calMatrix[at, arSlice, :, k])

    medianIndex = np.argsort(m_arr)[len(m_arr)//2]

    m_avg = m_arr[medianIndex]; b_avg = b_arr[medianIndex]
    fitPhase = x*m_avg + b_avg
    bulkDelay = np.repeat(np.mean(fitPhase), S)

    return np.exp(1j*bulkDelay) # Return bulk delay, with group delay removed (to avoid divergence)
    #return slice_arr[medianIndex] # Return 'real' data, but with group delay applied.


def parseCalCSI(loadedCalCSI, NICdata,
                toDS, fromDS, macBS, macREF,
                cablePts):
    # Assume all NICdata is homogeneous
    # loadedCalCSI ~ [[CSI for Elem 0], [CSI for Elem 1], ... [CSI for Elem AR-1]]
    AR = len(loadedCalCSI)
    parsedCalCSI = []

    elemMapping = getElemMapping(NICdata) # ew ew ew

    for ar in range(AR):
        # For each NIC:
        currCalCSI = filtersofGOR.alignSingle(loadedCalCSI[ar])
        # Remove Low RSSI Traces:
        currCalCSI = filtersofGOR.filterByRSSI(currCalCSI)
        # Filter by Source/Destination
        ##currCalCSI = filtersofGOR.filterSrcDest(currCalCSI,
        ##                                        toDS, fromDS, macBS, macREF)

        # Convert the frames to something useful:
        [currCalMatrix, centerFreq_arr, chanBW_arr, subcFreq_arr] \
                   = filtersofGOR.convertSingToUsableMatrix(currCalCSI) # NICdata deposits the trace in the right place.
        
        # Sort matrix and return the averaged Cal CSI
        currCalValue = sortAndAverageCalCSI(currCalMatrix)

        # Sort the matrix to push the highest magnitude frames to the top:
        #currCalMatrix = sortCalCSI(currCalMatrix)

        # Extract the per-subcarrier values that we need (w/ max magnitude):
        #currCalValue = currCalMatrix[0, 0, :, :] # Select AR=0 for Maximum Magnitude

        # Average the frames
        #currCalValue = np.mean(currCalValue, axis=1) # Average over time (truncated K axis)

        # Append, but make sure the subcarriers are the same (and aligned!)
        if ar == 0:
            # First iteration, don't care about subcarrier dimension.
            # Append averaged CSI as [AT AR S] frame
            parsedCalCSI.append(currCalValue)
            minSubcFreq = subcFreq_arr[0]
        else:
            # Check if the number of subcarriers changed. If so, merge them.
            currSubcFreq = subcFreq_arr[0]
            if (len(minSubcFreq) < len(currSubcFreq)):
                # Update currCalValue and minSubcFreq (since we have this specific case)
                print("WARNING - SUBCARRIERS CHANGED DURING CAL!")
                matPrev = np.zeros((1, 1, len(minSubcFreq), 1), dtype=np.complex128); matPrev[0, 0, :, 0] = parsedCalCSI[0]
                matCurr = np.zeros((1, 1, len(currSubcFreq),1), dtype=np.complex128); matCurr[0, 0, :, 0] = currCalValue
                [matCurr, matPrev, currSubcFreq, minSubcFreq] = \
                    mergeSubcarrierFrequencies(matCurr, matPrev, currSubcFreq, minSubcFreq)
                currCalValue = matCurr[0, 0, :, 0]
            # Append.
            parsedCalCSI.append(currCalValue) # Append only the correct slice!

    # Package for output: [AT AR S K]
    calMatrix = np.zeros((1, AR, len(minSubcFreq), 1), dtype=np.complex128)
    calMatrix[0, :, :, 0] = np.array(parsedCalCSI) # Assumed homogeneous
    
    # Apply Cable Delay to Output Matrix:
    calMatrix = applyCableDelay(calMatrix, subcFreq_arr[0], cablePts)

    # Invert Calibration Matrix:
    calMatrix = 1/calMatrix # Invert. If we multiply by `outputMatrix` we want to 'cancel it out'

    #plotCSI.plotMACDEST(currCalCSI)
    #plotCSI.plot2DCSI(calMatrix, subcFreq_arr[0])
    #plotCSI.plot2DCSIMAG(calMatrix, subcFreq_arr[0])
    print(f"Calibration Matrix Complete! [AT, AR, S, K] ~ {np.shape(calMatrix)}")

    return [calMatrix, centerFreq_arr, chanBW_arr, subcFreq_arr]

def mergeSubcarrierFrequencies(matA, matB, subcFreqA, subcFreqB):
    # Truncate matA or matB according to the Subcarrier Frequency Dimension (S)
    if (len(subcFreqA) < len(subcFreqB)):
        print("TRUNCATING MATRIX B")
        Hest_min = matA;                subcFreq_min = subcFreqA
        Hest_max = matB;                subcFreq_max = subcFreqB
    else:
        print("TRUNCATING MATRIX A")
        Hest_min = matB;                subcFreq_min = subcFreqB
        Hest_max = matA;                subcFreq_max = subcFreqA

    [AT_min, AR_min, S_min, K_min] = np.shape(Hest_min)
    [AT_max, AR_max, S_max, K_max] = np.shape(Hest_max)
    
    Hest_new = np.zeros((AT_max, AR_max, S_min, K_max), dtype=np.complex128)

    for s_min in range(len(subcFreq_min)):
        for s_max in range(len(subcFreq_max)):
            if (subcFreq_min[s_min] == subcFreq_max[s_max]):
                # Put the larger one into the smaller one.
                Hest_new[:, :, s_min, :] = Hest_max[:, :, s_max, :]
                continue

    if (len(subcFreqA) < len(subcFreqB)):
        matB = Hest_new;                subcFreqB = subcFreq_min
    else:
        matA = Hest_new;                subcFreqA = subcFreq_min

    return [matA, matB, subcFreqA, subcFreqB]

def applyCalOffset(calMatrix, calSubcFreq, Hest, subcFreq):
    # Extract dimensions of interest
    [AT, AR, S, K] = np.shape(Hest)

    # Check to see if the subcarriers are the same.
    # Duplicate to extend axes.
    calMatrixMult = np.repeat(calMatrix, K, axis=3) # Want to apply to all K frames

    # Apply to each AT trace"
    if AT > np.shape(calMatrix)[0]:
        # Duplicate along axis.
        numReps = AT - np.shape(calMatrixMult)[0]
        calMatrixMult = np.repeat(calMatrixMult, numReps + 1, axis=0)

    if ((np.shape(subcFreq) != np.shape(calSubcFreq)) or (not np.all(subcFreq == calSubcFreq))):
        print(f"WARNING! INCOMING SUBCARRIER FREQUENCIES DIFFERENT FROM CALIBRATION.")
        print(f"RESIZING THE LARGER CHANNEL MATRIX")

        [calMatrix, Hest, calSubcFreq, subcFreq] = \
                    mergeSubcarrierFrequencies(calMatrix, Hest, calSubcFreq, subcFreq)

    # Apply Offset:
    correctedCSI = Hest * calMatrixMult

    return [correctedCSI, subcFreq]

def applyCalOffsetToMAT(calMatrix, calSubcFreq, csiPath,
                        saveCorrToMat):
    plotCSI.plot2DCSI(calMatrix, calSubcFreq, title="Calibration Matrix", doUnwrap=True)

    print("Select Uncalibrated CSI from the same dataset")
    # Load Pre-Parsed CSI:
    [Hest, centerFreq, chanBW, subcFreq, elemPos, loadedStruct, csiPath] = utilsCSI.loadCSIfromMAT(csiPath)

    plotCSI.plot2DCSI(Hest, subcFreq, title="CSI Pre-Calibration", doUnwrap=True)

    [correctedCSI, subcFreq] = applyCalOffset(calMatrix, calSubcFreq, Hest, subcFreq)

    # Show user:
    plotCSI.plot2DCSI(correctedCSI, subcFreq, title="CSI Post-Calibration", doUnwrap=True)

    # Save to .mat file:
    if saveCorrToMat:
        corrFilename = os.path.splitext(os.path.basename(csiPath))[0] + "_POSTCAL"
        filtersofGOR.saveCSItoMAT(correctedCSI, centerFreq, chanBW, subcFreq, elemPos, corrFilename)

    return [correctedCSI, csiPath]


def generateCalOffset(NICdata, calFolder,
                      toDS, fromDS, macBS, macREF,
                      cablePts,
                      saveCalToMat=False):
    print("We wish to generate Phase Calibration Offsets for each element in a given array")
    print("We operate under the assumption that the 'Calibration Data' is generated by a cable,")
    print("   which is plugged into a 'reference source,' then recorded by each element in the array.")
    print("Given that 'reference source', we wish every element to have the same response.")
    print("The calculated calibration coefficients will make it such that each will exhibit close to 0deg.")

    print(f"")
    print(f"NOTE: TODS={toDS}, FROMDS={fromDS}")
    print(f"MAC for Base Station: {macBS}")
    print(f"MAC for Calibration Reference: {macREF}")

    AR = len(NICdata) * 2
    # Load RAW .CSI files
    loadedCalCSI = loadCalCSIfromRAW(AR, calFolder)
    # Determine CSI for reference cable for each trace
    [calMatrix, centerFreq_arr, chanBW_arr, subcFreq_arr] \
                 = parseCalCSI(loadedCalCSI, NICdata,
                               toDS, fromDS, macBS, macREF,
                               cablePts)
    # Save Cal Offset to Matlab file
    if saveCalToMat:
        calPath = filtersofGOR.saveCSItoMAT(calMatrix, centerFreq_arr[0], chanBW_arr[0], subcFreq_arr[0], [],
                                            "calMatrix", calFolder)

    return [calMatrix, subcFreq_arr[0]]

if __name__ == "__main__":
    # Calculate Calibration Coefficients
    [calMatrix, calSubcFreq] = generateCalOffset(NICdata, calFolder,
                      toDS, fromDS, macBS, macREF, 
                      cablePts, 
                      saveCalToMat)

    # Apply Calibration Offset to parsed .mat file
    [correctedCSI, csiPath] = applyCalOffsetToMAT(calMatrix, calSubcFreq, calFolder, saveCorrToMat)
