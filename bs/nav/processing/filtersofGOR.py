'''
THE GREAT FILTERS OF GOR!

(G)ateway for (O)rthogonal (R)outing

(Modularized Version of the Former great filter of GOR!)

(Modules Script)
Dimitry Melnikov, 2/25/25
'''

################################################################
################# USER INPUTS ##################################
### ARRAY GEOMETRY
# Element Positions
elemPos = [ # Base Station Layout
    [0, -43.65e-3, 0], # [X, Y, Z] for Elem 0...
    [0, -14.55e-3, 0], # [X, Y, Z] for Elem 1...
    [0, 14.55e-3, 0],
    [0, 43.65e-3, 0],
]

## File location, as well as location relative to Array POV, facing out:
#               0             1               2              3
#         (AUX-2)-(MAIN-2)-(MAIN-1)-(AUX-1)
# AUX-2 represents the AUX (2) antenna attached to NIC 2, => NICdata[1]['AUX'] = 0
# NIC 2 is represented by being placed second in `NICdata`
NICdata = [
    # Base Station Layout
    {   # NIC 1
        'file':  "", # Leave empty to select during dialogue.
        0:      0,  # MAIN # TODO - ARE THE MAIN AND AUX CORRECTLY ASSIGNED BY THE PARSER?
        1:      1,  # AUX
        'mac':  [], # MAC Address for the NIC. Leave empty -- will be autopopulated
    },
    {   # NIC 2
        'file': "", # Leave empty to select during dialogue.
        0:      2,  # MAIN
        1:      3,  # AUX
        'mac':  [], # MAC Address for the NIC. Leave empty -- will be autopopulated
    }
]

# # NIC DATA & Element Positions for Laptop/UT Setup
# # Element Positions
# elemPos = [ # Laptop Layout (Estimated)
#     [0, -0.5*30e-3, 0], # [X, Y, Z] for Elem 0...
#     [0,  0.5*30e-3, 0], # [X, Y, Z] for Elem 1...
# ]

# NICdata = [
#     {   # NIC 1
#         'file':  "rx_2_250202_155435",
#         0:      0,  # MAIN # TODO - ARE THE MAIN AND AUX CORRECTLY ASSIGNED BY THE PARSER?
#         1:      1,  # AUX
#         'mac':  [], # MAC Address for the NIC. Leave empty -- will be autopopulated
#     },
# ]

### GOR FILTER OPTIONS
# MAC Address & To/From DS Alignment
# See https://mrncciew.com/2014/09/28/cwap-mac-headeraddresses/
toDS = 0; fromDS = 1
#macBS = [0x10, 0x5f, 0xad, 0xd6, 0xa3, 0x2b] # Base Station MAC Address
macBS = [0x6c, 0x2f, 0x80, 0xdf, 0x37, 0xca] # Base Station MAC Address
macUT = [0x8c, 0xe9, 0xee, 0xd9, 0xa2, 0xe2] # User Terminal MAC Address (antenna we're tracking)

forceAT = 1    # 0 to disable (but will truncate to minimum), otherwise will only select CSI with the corresponding # Transmit Antennas
forceAR = 2    # 0 to disable (but will truncate to minimum), otherwise will only select CSI with the corresponding # Receive Antennas

################################################################
######################## IMPORTS ###############################
# Import VECTOR Libraries
import os; import sys
VECTOR_ROOT = os.getenv("VECTOR_ROOT")
print("WARNING! VECTOR_ROOT NOT DEFINED! RUN THIS FROM VECTOR ROOT DIRECTORY: `export VECTOR_ROOT=$(pwd)`") if (VECTOR_ROOT is None) else None
sys.path.insert(0, VECTOR_ROOT) if (VECTOR_ROOT is not None) and (VECTOR_ROOT not in sys.path) else None
import setup; setup.loadModules()

import bs.nav.processing.utilsCSI as utilsCSI       # To import CSI from .mats
import bs.demo.graphing.plotCSI as plotCSI          # To plot manipulated CSI

# Import Picoscenes library
setup.loadPicoscenes()
from picoscenes import Picoscenes   # To process the CSI

# Ordinary Imports
import numpy as np                  # Numpy Processing
import scipy.io                     # To save data as a .mat file
import os                           # To retrieve the file

import tkinter as tk                # For file selection
from tkinter import filedialog      # For file selection (GUI)

print("GFOG: Libraries imported!")
###################### DRIVER CODE #############################
def loadCSIfromRAW(csiPath=None, selectionPrompt="Please select the CSI Source File:"):
    initialdir = os.getcwd()

    if (not os.path.isfile(csiPath)) and (not (csiPath is None)):
        print(f"File path invalid for csiPath: {csiPath}. Bringing up GUI dialog.")
        initialdir = os.path.dirname(csiPath) # We have the directory name for the CSI Path, if it's invalid.

    if (csiPath is None) or (not os.path.isfile(csiPath)):
        # Do GUI interface if path not specified
        # Ask the user to select a single file name.
        csiPath = filedialog.askopenfilename(initialdir=initialdir,
                                            title=selectionPrompt,
                                            filetypes=[('csi files', '.csi'), ('all files', '.*')])
    
    print(f"Loading CSI from: {csiPath}")

    return (Picoscenes(csiPath), csiPath) # Load in data

### LOAD CSI ###
def loadMultiNICS(NICdata, datasetFolder=None):
    """ Load in CSI for Multiple NICs

        Sample NICdata:
        ## File location, as well as location relative to Array POV, facing out:
        #               0             1               2              3
        #         (AUX-2)-(MAIN-2)-(MAIN-1)-(AUX-1)
        # AUX-2 represents the AUX (2) antenna attached to NIC 2, => NICdata[1]['AUX'] = 0
        # NIC 2 is represented by being placed second in `NICdata`
        NICdata = [
            # Base Station Layout
            {   # NIC 1
                'file':  "rx_213_250202_163506",
                0:      0,  # MAIN
                1:      1,  # AUX
                'mac':  [], # MAC Address for the NIC. Leave empty -- will be autopopulated
            },
            {   # NIC 2
                'file': "rx_211_250202_163506",
                0:      2,  # MAIN
                1:      3,  # AUX
                'mac':  [], # MAC Address for the NIC. Leave empty -- will be autopopulated
            }
        ]

    Args:
        NICdata (Struct): Stores NIC index, as well as antenna layout. 'file' field may be left empty.
        datasetFolder (str): (optional) Absolute path to folder in which CSI data (referred to by NICdata) is stored

    Returns:
        (loadedCSI, NICdata, csiPath): loadedCSI contains an array of Picoscenes Dictionary Arrays:
                                    loadedCSI[0].raw = [ (Frame 0):
                                        'StandardHeader'    : 802.11 MAC Header
                                        'RxSBasic'          : RxSBasic Segment
                                        'RxExtraInfo'       : ExtraInfo Segment (measured at RX end)
                                        'MPDUS'             : Raw MPDU data w/o FCS bytes
                                        'CSI'               : CSI measured from HT/VHT/HE/EHT-LTF Field
                                    ], [(Frame 1) ...], [(Frame 2) ...], ...]
                                    (loadedCSI[0, 1, 2, ...] refer to different NICs)

                                    More structure info in the documentation: https://ps.zpj.io/matlab.html
                                    (Can also dissect with Python debugger (pdb) and dir(loadedCSI[0])
                                NICdata is updated with the MAC address of the NIC at hand.
                                csiPath stores the path to the CSI of the last NIC accessed.
    """
    numNICS = len(NICdata)      # Number of CSI files that we're parsing
    loadedCSI = []              # List to contain the loaded in CSI

    if datasetFolder is None:
        datasetFolder = filedialog.askdirectory(initialdir=os.getcwd(), title="Please select CSI Dataset Folder.")

    # Iterate over our file names
    for nicNum in range(numNICS):
        nic = NICdata[nicNum]
        csiFilename = nic['file']
        csiPath = os.path.join(datasetFolder, csiFilename + ".csi") # Import
        [currCSI, csiPath] = loadCSIfromRAW(csiPath, f"Please select CSI for NIC {nicNum} in NICdata")
        loadedCSI.append(currCSI)

    ### RECORD THE MAC ADDRESS ASSOCIATED WITH EACH NIC THAT COLLECTED CSI ###
    # Not to be confused with the BS/UT mac address - these addresses are baked into the CSI
    #  (We use these in the final 'Matlab Conversion' section to make sure that the CSI comes 
    #   from the right NIC, in case things get shifted around during filtering.)
    for nic_index in range(numNICS):
        NICdata[nic_index]['mac'] = loadedCSI[nic_index].raw[0]['RxExtraInfo']['macaddr_cur']

    return [loadedCSI, NICdata, csiPath]

### STITCH THE CSI || ALIGN MPDU ###
def alignMPDU(numNICS, loadedCSI):
    """ Aligns CSI in `loadedCSI` by matching MPDU in each CSI frame
        (STITCH THE CSI ||| ALIGN MPDU)
        MPDU should correspond to the raw bytes contained in the captured packet.
        Theoretically, it should be unique to each CSI frame.
        When we find matching MPDUs across different NICs, we theoretically match the CSI instances.

    Args:
        numNICS (int): Number of NICs in consideration.
        loadedCSI (list of picoscenes frames): Array of Picoscenes dictionaries. Returned directly by loadMultiNICS

    Returns:
        (list of picoscenes frames): Similar in shape to loadedCSI. `combinedCSI[0]` corresponds to the first correlated frame 
                                        between the NICs 
                                     Frames in each NIC CSI set with no MPDU matches are discarded.
    """
    combinedCSI = []              # List to contain stitched-together CSI
    for frameOuter in loadedCSI[0].raw: # Iterate over the frames in the first NIC...
        mpduOuter = frameOuter['MPDUS'] # Extract MPDU to search for
        
        group = [frameOuter]            # Group of matched MPDUs

        for nic_index in range(1, numNICS): # Skip the first NIC since we're accessing it from the top
            # Find all matches in this NIC
            matches = [
                frameInner for frameInner in loadedCSI[nic_index].raw
                if frameInner['MPDUS'] == mpduOuter
            ]   # ^^ Store `frameInner` for each match.
            # Add all found matches
            group.extend(matches)

        # Only add `group` if we had at least one match from another NIC
        if len(group) > 1 or (numNICS == 1):
            combinedCSI.append(group)

    # notes: in theory, we'll have some sets of combinedCSI that are > numNICS
    #       (these could be empty packets that we don't care much about -- garbage. Those we care about have a unique MPDU b/c timestamp? etc.)
    print(f"Combined CSI! Total co-related CSI frames: {len(combinedCSI)}")
    return combinedCSI

### FILTER ToDS AND FromDS || MAC ADDRESS ALIGNMENT ###
def filterSrcDest(combinedCSI, toDS, fromDS, macBS, macUT):
    """ Filter co-related frames in `combinedCSI` by the intended Source/Destinations
    (Filter ToDS AND FromDS ||| MAC ADDRESS ALIGNMENT)
    (For cards in Monitor mode, ALL frames are being collected -- we only wish to 
     collect CSI from 'real' data)

    Sample inputs:
        toDS = 1; fromDS = 0
        macBS = [0x6c, 0x2f, 0x80, 0xdf, 0x37, 0xca] # Base Station MAC Address
        macUT = [0x8c, 0xe9, 0xee, 0xd9, 0xa2, 0xe2] # User Terminal MAC Address (antenna we're tracking)

    Info: https://mrncciew.com/2014/09/28/cwap-mac-headeraddresses/

    Args:
        combinedCSI (list of picoscenes frames): Output from `alignMPDU`. List of frames that are correlated by MPDU
        toDS (int): Frame intended for Base Station?
        fromDS (int): Frame sourced from Base Station?
        macBS (_type_): Base Station MAC Address
        macUT (_type_): User Terminal MAC Address

    Returns:
        (list of picoscenes frames): Similar in shape to `combinedCSI`. However, any sets of 
                                    frames not matching inputs toDS/fromDS criteria are dropped.
    """
    # Configure the correct expected source/destination MAC addresses
    # (Furthermore, make sure no changes in MCS occur)
    # Info: https://mrncciew.com/2014/09/28/cwap-mac-headeraddresses/
    if (toDS == 1) and (fromDS == 0): # toDS = 1, fromDS = 0
        macSRC = macUT; macDEST = macBS # Sending from UT to BS 
    else:             # toDS = 0, fromDS = 1 (or other cases)
        macSRC = macBS; macDEST = macUT # Sending from BS to UT

    macAlignedCSI = []  # List to contain CSI that has expected MAC Addresses + To/FromDS
    for combinedFrames in combinedCSI:
        # Find all MAC Address matches in the frame
        matches = [
            singleFrame for singleFrame in combinedFrames
            if (singleFrame['StandardHeader']['ControlField']['ToDS'] == toDS)        and \
            (singleFrame['StandardHeader']['ControlField']['FromDS'] == fromDS)    and \
            (singleFrame['StandardHeader']['Addr1'] == macDEST)                    and \
            (singleFrame['StandardHeader']['Addr2'] == macSRC)
        ]   # Only return frames that match ALL of the fields.

        # Only add `matches` if we have any matches.
        if (len(matches) > 0): 
            # Make sure the Modulation & Coding Scheme is consistent (MCS stays constant)
            firstMCS = matches[0]['RxSBasic']['MCS']
            matchesMCS = [
                singleFrame for singleFrame in matches
                if (singleFrame['RxSBasic']['MCS'] == firstMCS)
            ]   # Only return frames with matching MCS

            # Only add `matchesMCS` if MCS didn't change over those frames.
            if (len(matchesMCS) > 0):
                # Now, investigate duplicates (eg if a NIC measured the same frame more than once (?))
                frameNICMAC = [
                    nic['RxExtraInfo']['macaddr_cur'] for nic in matchesMCS
                ]
                numUniqueNICS = len(set(tuple(nicmac) for nicmac in frameNICMAC)) # Convert to Set (removes duplicates from set)
                # Only add `matchesMCS` if we have only have unique CSI from every recording NIC
                if (len(matchesMCS) == numUniqueNICS):
                    macAlignedCSI.append(matchesMCS)

    # notes: - If we don't filter the MCS, we'll still end up with > numNICS in a `macAlignedCSI[i]` slot
    #           As of writing, it's unclear why this happens. Looking at `RxSBasic`, `MCS` changes some of the non-`numNICS` sized slots.
    #           (Means that Modulation & Coding Scheme changes in the middle. Could be momentary downgrades that we don't have control over from BS)
    #        - If we don't filter the duplicates, we'll still end up with > numNICS in a `macAlignedCSI[i]` slot, even with the MCS filter.
    #           The only difference I've been able to spot is the `macaddr_rom/cur` is the duplicated at times
    #           (I think this means we recapture the same CSI frame on the same NIC? Unclear.)
    #           (macaddr_rom/cur corresponds to the mac address of the NIC itself.)
    # VV Oneliner that prints out CSI 
    print(f"...Printing CSI Frames in macAlignedCSI with more frames than expected. If you see an output below, investigate! There shouldn't be anything.")
    for i in range(len(macAlignedCSI)): print(f"Index: {i} Size: {len(macAlignedCSI[i])}") if(len(macAlignedCSI[i]) > 2) else None
    print(f"Filtered SRC/DEST MAC Addresses! Total CSI frames remaining: {len(macAlignedCSI)}")
    # >> Shows Packet Format outliers. for i in range(len(combinedCSI)): print(f"Index: {i} Format: {(combinedCSI[i][0]['RxSBasic']['packetFormat'])}") if(combinedCSI[i][0]['RxSBasic']['packetFormat'] > 1) else None
    return macAlignedCSI

### COUNT UP FORCED PARAMETERS IN REMAINING CSI (STATISTICS) ###
def statsForcedParams(macAlignedCSI):
    """ Provide statistics on AT and AR counts in `macAlignedCSI` frames.
    (Count up forced parameters in remaining CSI)

    Args:
        macAlignedCSI (list of picoscenes frames): Similar to output from `filterSrcDest`

    Returns:
        None
    """
    countForcedUnpaired = np.zeros((2, 2))
    countForcedPaired   = np.zeros((2, 2))
    for alignedFrames in macAlignedCSI:
        # Count up the unpaired ones.
        for singleFrame in alignedFrames:
            numTX = singleFrame['CSI']['numTx'] - 1 # Never have frames with 0 numTX (ie dimensions)
            numRX = singleFrame['CSI']['numRx'] - 1

            countForcedUnpaired[numTX][numRX] = countForcedUnpaired[numTX][numRX] + 1

        # Count up the paired ones (that match one another)
        matches = [
            singleFrame for singleFrame in alignedFrames
            if  ((singleFrame['CSI']['numTx'] == alignedFrames[0]['CSI']['numTx']))        and \
                ((singleFrame['CSI']['numRx'] == alignedFrames[0]['CSI']['numRx']))
        ]   # Only return frames that match ALL of the fields.

        # Count up the paired ones now.
        numTX = matches[0]['CSI']['numTx'] - 1
        numRX = matches[0]['CSI']['numRx'] - 1
        
        countForcedPaired[numTX][numRX] = countForcedPaired[numTX][numRX] + 1

    print(f"Number of Frames with forced parameters")
    print(f"(Y DIMENSION) AT (max amnt: { np.shape(countForcedUnpaired)[0]})")
    print(f"(X DIMENSION) AR (max amnt: { np.shape(countForcedUnpaired)[1]})")
    print("Unpaired (Don't care if they're paired up)")
    print(countForcedUnpaired)
    print("Pairs (Sets that share those same properties)")
    print(countForcedPaired)
    return

### FILTER FORCED PARAMETERS ###
def filterForcedParams(macAlignedCSI, forceAT=0, forceAR=0):
    """ Filter out Forced Parameters

    If we wish to force the recorded CSI to ONLY have certain characteristics,
    we filter everything out in `macAlignedCSI` and return it. 

    (There's almost certainly a better way to do this.)

    Args:
        macAlignedCSI (list of picoscenes frames): Similar to output from `filterSrcDest()`
        forceAT (int): Forced `numTx` associated with NIC. Disabled if < 1
        forceAR (int): Forced `numRx` associated with NIC. Disabled if < 1

    Returns:
        (list of picoscenes frames)): Similar to output from `filterSrcDest()`. Sets of frames not
                                        matching the input criteria are dropped.
    """

    # Discard CSI with parameters not matching 'forced' variations.
    # If invalid number (<1) then ignore.
    forcedCSI = []
    for alignedFrames in macAlignedCSI:
        # Find all matches for parameters
        matches = [
            singleFrame for singleFrame in alignedFrames
            if  ((forceAT < 1) or (singleFrame['CSI']['numTx'] == forceAT))        and \
                ((forceAR < 1) or (singleFrame['CSI']['numRx'] == forceAR))
        ]   # Only return frames that match ALL of the fields.

        # Only add `matches` if we have any matches
        if (len(matches) > 0):
            forcedCSI.append(matches)

    print(f"Force-Filter Complete. Total CSI frames remaining: {len(forcedCSI)}")
    return forcedCSI

### CONVERT TO USABLE MATRIX ###
def convertToUsableMatrix(forcedCSI, NICdata):
    """ Convert sets of CSI to a homogeneous Matrix of dimensions [AT, AR, S, K]
        If inhomogeneous, truncates to minimum AT and AR.
    
    Args:
        forcedCSI (list of picoscenes frames): Output similar to `filterForcedParams` or `filterSrcDest`
        numNICS (int): Number of NICs considered

    Returns:
        (Tuple): [outputMatrix, centerFreq_arr, chanBW_arr]
        (Numpy Matrix [AT, AR, S, K]): AT ~ Number of TX Ants, AR ~ Num of RX Ants, 
                                        S ~ Number of Subcarriers, K ~ Number of Frames
        (centerFreq_arr, chanBW_arr): Arrays corresponding to the freq/chanBW of each relevant frame
    """
    # At this point, all of the data should be exactly the same.
    # Every index in alignedFrames holds the same CSI frame at each instant as seen by each NIC.
    # Arrays to hold data for output.
    outputMatrix    = [] # Output [AT AR S K] Matrix
    centerFreq_arr  = [] # Center Frequency
    chanBW_arr      = [] # Channel Bandwidth

    numNICS = len(NICdata)

    for alignedFrames in forcedCSI:
        # Pull out the frame dimensions
        firstCSIFrame = alignedFrames[0]['CSI'] # CSI from the 0th NIC in `alignedFrames`

        AT = firstCSIFrame['numTx']         # Number of Transmit Antennas
        AR_SING = firstCSIFrame['numRx']    # Number of Receive Antennas on Single NIC
        AR = AR_SING*numNICS                # Number of Antennas in total, over the entire array
        S  = firstCSIFrame['numTones']      # Number of Subcarriers Tracked
        centerFreq_arr.append(float(firstCSIFrame['CarrierFreq'])) # Given in Hz
        chanBW_arr.append(float(firstCSIFrame['CBW']*1e6))        # Channel BW given in MHz, convert to Hz

        ATARSframe = np.zeros((AT, AR, S), dtype=np.complex128)

        # Match the Current Frame to the Indicated NIC via NIC MAC Address & Deposit the Frame in ATARSframe
        for currFrame in alignedFrames:         # In each frame:
            for nicIndex in range(numNICS):     # In each NIC:
                if (currFrame['RxExtraInfo']['macaddr_cur'] == NICdata[nicIndex]['mac']): 
                    # Matching MAC + # Traces
                    # Reshape CSI Frame Data to fit what we need:
                    # Figure out which trace belongs to which antenna (educated guess)
                    # (eg: 2 TX, 2 RX, 50 Subcarriers => size(CSI) = (2x2x50, ))
                    # If we reshape it to (2, 2, 50) => CSI[0, 0, 50] ~ RX1 <- TX1
                    #                                   CSI[0, 1, 50] ~ RX1 <- TX2
                    #                                   CSI[1, 0, 50] ~ RX2 <- TX1
                    # So, if we assume MAIN ~ RX1, AUX ~ RX2, then:
                    #                                   CSI[0, 0, 50] ~ MAIN <- TX1
                    #                                   CSI[1, 0, 50] ~ AUX  <- TX1
                    _localATARS = np.reshape(currFrame['CSI']['CSI'], (AT, AR_SING, S))
                    # If our NIC is located in positions MAIN: 0, AUX: 1, then:
                    # ATARSframe[:, 0, :] = _localATARS[:, 0, :]
                    for ant in range(AR_SING):
                        antIndex = NICdata[nicIndex][ant] # Corresponds to postion in array, from left to right
                        ATARSframe[:, antIndex, :] = _localATARS[:, ant, :] # Deposit.
                        # TODO - Maybe check to see if this is empty, or has a different MIMO configuration?

        # Finally, with our [AT AR S] frame ready, we append it:
        if not np.all(ATARSframe == 0):
            # But only append if the frame is not empty.
            outputMatrix.append(ATARSframe)

    # We currently have an inhomogeneous array. Need to flatten it along the other dimensions.
    print("Detecting inhomogeneous array and truncating where necessary...")
    min_AT = min(arr.shape[0] for arr in outputMatrix) # Look for smallest amount of AT (minimum along dimension 0 (AT))
    min_AR = min(arr.shape[1] for arr in outputMatrix) # Look for smallest amount of AR (minimum along dimension 1 (AR))
    trimmedOutputArrays = [arr[:min_AT, :min_AR, ...] for arr in outputMatrix] # Trim extraneous dimensions
    trimmedOutputMatrix = np.stack(trimmedOutputArrays, axis=-1)      # Stack the elements
    # ^^^ With all frames deposited in the first dimension, we ended up permuting them to fit the output expectations
    # [(K) AT AR S] -> [AT AR S (K)]

    if (len(outputMatrix) == 0):
        print("WARNING! OUTPUT MATRIX EMPTY.")

    # With all frames deposited in the first dimension, want to permute them to fit the output expectations
    # [(K) AT AR S] -> [AT AR S (K)]
    print(f"Output Matrix (numTX, numRX, numSubcarriers, numSnapshots) ~ {np.shape(trimmedOutputMatrix)}")
    return [trimmedOutputMatrix, centerFreq_arr, chanBW_arr]

def saveCSItoMAT(outputMatrix, centerFreq, chanBW, elemPos, outputFilename, outputFolder=None):
    """ Save processed CSI to .mat file.

    Sample `elemPos`:
        # Element Positions
        elemPos = [ # Base Station Layout
            [0, -43.65e-3, 0], # [X, Y, Z] for Elem 0...
            [0, -14.55e-3, 0], # [X, Y, Z] for Elem 1...
            [0, 14.55e-3, 0],
            [0, 43.65e-3, 0],
        ]

    Args:
        outputMatrix (numpy matrix [AT, AR, S, K]]): Output from `convertToUsableMatrix`. Homogeneous.
        centerFreq (float): _description_
        chanBW (float): _description_
        elemPos (struct): Struct corresponding to element position for elements 0, 1, 2, 3..
        outputFilename (str): Output filename (not path, no suffix either)
        outputFolder (str, optional): Absolute path to output folder. Defaults to None.

    Returns:
        filepath: Absolute path to .mat file location
    """
    if (outputFolder is None):
        outputFolder = filedialog.askdirectory(initialdir=os.getcwd(), title="Please select folder in which to save.")    

    ### SAVE CSI TO MATLAB FILE ### 
    
    matlabOutput = {
        # The [AT AR S K]-sized Matrix containing the Parsed CSI
        'outputMatrix':     outputMatrix,     
        # Center/Carrier Frequency of Collected CSI (Hz)
        'centerFreq':       centerFreq,   
        # Channel Bandwidth (Hz)
        'chanBW':           chanBW,
        # RX Antenna Element Positions
        'elemPos':          elemPos,
    }   # Output Dictionary to shove things into

    # Put where we need it
    filepath = os.path.join(outputFolder, f"{outputFilename}.mat")

    scipy.io.savemat(filepath, matlabOutput)
    print(f"...Saved CSI to {outputFilename}.mat")

    return filepath

######################### DRIVER SECTION ####################################
def main(elemPos, NICdata, 
         toDS, fromDS, macBS, macUT, 
         forceAT=0, forceAR=0):
    numNICS = len(NICdata)  # Number of CSI files that we're parsing
    
    print("Loading CSI from raw .csi files:")
    [loadedCSI, NICdata, csiPath] = loadMultiNICS(NICdata)

    print("Combining CSI by aligning MPDU...")
    combinedCSI = alignMPDU(numNICS, loadedCSI)

    print("Filtering frames by Source/Destination MAC Addresses...")
    macAlignedCSI = filterSrcDest(combinedCSI, toDS, fromDS, macBS, macUT)

    statsForcedParams(macAlignedCSI)

    print(f"Discarding CSI not matching parameters: AT: {forceAT}, AR: {forceAR}...")
    forcedCSI = filterForcedParams(macAlignedCSI, forceAT, forceAR)

    print("Converting to usable matrix...")
    [outputMatrix, centerFreq_arr, chanBW_arr] = convertToUsableMatrix(forcedCSI, NICdata)

    print("Saving CSI to .mat file...")  
    outputFilename = (os.path.dirname(csiPath)) # Output filename is the same as old directory
    filepath = saveCSItoMAT(outputMatrix, centerFreq=centerFreq_arr[0], chanBW=chanBW_arr[0], \
                            elemPos=elemPos, outputFilename=outputFilename)


if __name__ == "__main__":
    main(elemPos, NICdata, toDS, fromDS, macBS, macUT, forceAT, forceAR)