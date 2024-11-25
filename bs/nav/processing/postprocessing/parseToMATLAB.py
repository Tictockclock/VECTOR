'''
This script should take CSI files in and output them in a MATLAB-friendly format.

We output a CSI matrix of size [AT AR S K], where:
- AT: Number of Transmit Antennas
- AR: Number of Receive Antennas
- S: Number of Subcarriers
- K: Number of CSI Snapshots
As well as the 'centerFreq' and 'chanBW', from which we can derive the wavelengths of 
    each subcarrier for later processing

We also output metadata (if so desired in USER INPUTS):
- count: Number of CSI frames
- file: file location (and name!)
- raw: Raw CSI data

NOTE:
- The AT-AR structure is set up for the BEST CASE SCENARIO:
    - Both receive antennas are in play (AR = antPerNIC * numNICS)
    - All NICs are receiving the same amount of Space-Time Streams (STS)
        (i.e. AT is constant between the time-related CSI frames along the NICs)
    - We choose this condition in order to maintain a HOMOGENEOUS MATRIX.
        - Makes the math easier if we consider it this way
        - However, this does reduce the amount of data we have at our disposal
            - If this becomes an issue, we can change the restriction to maintain only ONE tx antenna.
    - That is:
        - AT and AR and S DO NOT CHANGE over the course of the CSI collection
        - If (and WHEN) they do, we throw them out. 
        
..................................................................................
We expect WSL, running in a virtual environment (on the WSL instance). In other words:
:wsl
:source env/bin/activate

Set up instructions are here `https://gitlab.com/wifisensing/PicoScenes-Python-Toolbox`

Dimitry Melnikov
'''

################# USER INPUTS ##################################
# CSI Data Location
folder = "data/subsystemdemo"

# Array Geometry/Layout - Assume a Uniform Line Array (ULA) running off AX210 family
# Each Antenna
antPerNIC = 2       # Antennas per NIC (AX210 has 2 per each)

# Element Positions
elemPos = [
    [0, -1.5*3.5e-2, 0], # [X, Y, Z] for Elem 0...
    [0, -0.5*3.5e-2, 0], # [X, Y, Z] for Elem 1...
    [0, 0.5*3.5e-2, 0],
    [0, 1.5*3.5e-2, 0],    
]

# File location, as well as location relative to Array POV, facing out:
#               0             1               2              3
#         (AUX-2)-(MAIN-2)-(MAIN-1)-(AUX-1)
# AUX-2 represents the AUX (2) antenna attached to NIC 2, => NICdata[1]['AUX'] = 0
# NIC 2 is represented by being placed second in `NICdata`
NICdata = [
    {   # NIC 1
        'file':  "rx_11_241125_120734",
        0:     2,  # MAIN
        1:      3,  # AUX
    },

    {   # NIC 2
        'file': "rx_13_241125_120733",
        0:      1,  # MAIN
        1:      0,  # AUX
    },
]

# Processing Options
timestampTol = 100000   # Timestamp tolerance for related frames. Increase for more frames (but less accuracy along the array)
                    # Or decrease for fewer frames (but higher accuracy along the array)
                    # In DOA: Stationary Target can handle larger val. Moving tolerance needs tighter tolerance (lower value)
                    # Note also that the timestamp is an INTEGER!
overrideAT = 2 # Override: Only select frames with this many TX Antennas
overrideS = 57 # Override: Only select frames with this many S Antennas

# Output File Options
outputFilename = "relaxed-subdemo-mov90-45-matrix-only" #.mat suffix implied
wantToSave = True  # Keep this false when troubleshooting this script
matrixOnly = True   # If False, will save EVERYTHING. This is very time consuming + takes up loads of space lmao
                    # Set to True only if it's the first time running it, but be ready to wait

################################################################
from picoscenes import Picoscenes   # To process the CSI
import numpy as np                  # Numpy Processing
import scipy.io                     # To save data as a .mat file
import os                           # To retrieve the file

if overrideAT > 0:
    print("WARNING: Selected to override AT with " + str(overrideAT)  + " TX Ants")
if overrideS > 0:
    print("WARNING: Selected to override S with " + str(overrideS) +  " Subcarriers")

## Import the CSI, prep it for output
print("Loading CSI...")
# Note: You can inspect the contents of a Picoscenes frame with this:
#print(dir(importedCSI[1])); import pdb; pdb.set_trace();
numNICS = len(NICdata)       # Number of files we're running with
matlabOutputFull = {
    # Metadata Directly from PicoScenes CSI
    'count':              [],     # Number of CSI Frames
    'file':                 [],     # File location. Useful internally, less-so externally
    'raw':                 [],     # CSI Data itself
    'timestamps':     [],     # Timestamps for each frame. Should be a list of lists
    # Processed Data
    'outputMatrix':  [],     # The [A S K] sized matrix which we attempt to reconcile
    'centerFreq':     [],      # Center/Carrier Frequency of Collected CSI (Hz)
    'chanBW':          [],      # Channel Bandwidth (Hz)
    # User-Input Data
    'elemPos':          [],       # RX Antenna Element Positions
}   # Empty dict to which we'll shove things into

# Iterate over our file names
for nic in NICdata:
    csiFilename = nic['file']
    csiPath = os.path.join(os.getcwd(), folder, csiFilename + ".csi") # Import
    currCSI = Picoscenes(csiPath)   # Parse

    ## Place Metadata & Raw Data
    matlabOutputFull['count'].append(currCSI.count)
    matlabOutputFull['file'].append(currCSI.file)
    matlabOutputFull['raw'].append(currCSI.raw)

    timeList = []
    for i in range(currCSI.count):
        timeList.append(currCSI.raw[i]['RxSBasic']['systemns'])
        # Or maybe use systemns?

    matlabOutputFull['timestamps'].append(timeList)


matlabOutputFull['timestamps'] = np.array(matlabOutputFull['timestamps'], dtype=object) # Convert to np array 
                                    # to take advantage of functions
matlabOutputFull['elemPos'] = elemPos # Apply User-Supplied User Positions

print("...Done! CSI Loaded.")
#import pdb; pdb.set_trace()

## Parse the CSI into an [AT AR S K] Matrix
print("Parsing CSI for [AT AR S K] Matrix")
maxFramesIndex = np.argmax(matlabOutputFull['count'])

AT = AR =  S = -1 # To store our number of AT, AR, & S. Collected from the first time-related frame. 

for i in range(max(matlabOutputFull['count'])): # Go over as many indices as possible
    ## First, we need to figure out which other processed frames share
    #   the same (or similar) timestamp.
    # That is, we are searching for |||K|||
    #print("Frame: " +str(i))
    relatedFrameIndices = -1*np.ones(numNICS) # Frames in the other CSI files that are
                    # 'close enough' to our timestamp
                    # i.e. -- they are considered to be in the same snapshot 
    relatedFrameIndices[maxFramesIndex] = i; # Our timestamp is stored in the right place   
    
    targetTime = matlabOutputFull['timestamps'][maxFramesIndex][i]
    
    # Search through each CSI file...
    for j in range(numNICS):
        if j == maxFramesIndex: # We're talking about ourselves
            continue # Break out of the `j` loop, to the next File

        queryTime = matlabOutputFull['timestamps'][j]

        # Figure out which index holds the closest timestamp
        absDiff = np.abs(np.array(queryTime) - targetTime)
        # Find the index of the minimum difference
        closestIndex = np.argmin(absDiff)
        # Check to see if the closest value is within the tolerance
        if absDiff[closestIndex] <= timestampTol:
            relatedFrameIndices[j] = closestIndex
        else:
            break # No need to check anything else.

    # If no frames are 'close enough' in time, dump it and move on
    if np.any(relatedFrameIndices < 0):
        continue # Break out of the `i` loop, to the next CSI Frame
    print("Frames co-related!")

    ## Knowing which frames are Temporally Related (same K), we now need to extract the
    #  CSI corresponding to each Receiving Antenna (Figure out AT, AR, and S)
    currCSIFrame = matlabOutputFull['raw'][maxFramesIndex][i]['CSI']
    # Check to see if we've assigned our global AT, AR, S sizes (to ensure homogeneous matrix)
    if AT < 0: # If we haven't assigned it yet
        # If there's no override, go for it
        # If there is an override, match the variable to the override
        if overrideAT == 0 or currCSIFrame['numTx'] == overrideAT:
            if overrideS == 0 or currCSIFrame['numTones'] == overrideS:
                AT = currCSIFrame['numTx']
                AR = antPerNIC*numNICS          # Number of Antennas in total, over the entire array
                S   = currCSIFrame['numTones']# Number of Subcarriers tracked
                matlabOutputFull['centerFreq'] = float(currCSIFrame['CarrierFreq']) # Given in Hz
                matlabOutputFull['chanBW'] = float(currCSIFrame['CBW']*1e6) # Channel BW given in MHz
            else:
                continue
        else:
            continue
        
    ATARSframe = np.zeros((AT, AR, S), dtype=np.complex128)
    
    # Search through each related CSI file, verify dimensions and insert. 
    for j in range(numNICS):
        _relatedFrameIndex = int(relatedFrameIndices[j])
        _currCSIFrame = matlabOutputFull['raw'][j][_relatedFrameIndex]['CSI']

        # Verify that dimensions match
        if (_currCSIFrame['numTx'] != AT) or (_currCSIFrame['numRx'] != antPerNIC) or \
                (_currCSIFrame['numTones'] != S):
            ATARSframe = None
            break # Throw frame away if we end up with nonhomogeneous output matrix
    
        # Figure out which trace belongs to which antenna (this is an educated guess)
        # (e..g: 2 TX, 2 RX, 50 Subcarriers => size(CSI) = (2x2x50, ))
        # If we reshape it to (2, 2, 50) => CSI[0, 0, 50] ~ RX1 <- TX1
        #                                                   CSI[0, 1, 50] ~ RX1 <- TX2
        #                                                   CSI[1, 0, 50] ~ RX2 <- TX1
        # If we assume that MAIN ~ RX1, AUX ~ RX2, then:
        #                                                   CSI[0, 0, 50] ~ MAIN <- TX1
        #                                                   CSI[1, 0 ,50] ~ AUX <- TX1
        _localATARS = np.reshape(_currCSIFrame['CSI'], (AT, antPerNIC, S))
        # If our NIC is located in positions MAIN: 0, AUX: 1, then:
        # ATARSframe[:, 0, :] = _localATARS[:, 0, :]
        for ant in range(antPerNIC):
            antIndex = NICdata[j][ant] # Corresponds to position in the array, from left to right
            ATARSframe[:, antIndex, :] = _localATARS[:, ant, :]

    if ATARSframe is None:
        continue # Break out of the `i` loop, to the next CSI Frame
    print("Frames compatible with output matrix!")


    ## Finally, with our [A S] frame ready, we append it.
    print("Depositing a frame!")
    matlabOutputFull['outputMatrix'].append(ATARSframe)

# Now that all frames have been deposited in the first dimension, we'd like to 
#  permute them to fit the header of this file
# [(K) AT AR S] -> [AT AR S (K)]
if (np.size(matlabOutputFull['outputMatrix']) == 0):
    print("ERROR: OUTPUT MATRIX EMPTY!");

matlabOutputFull['outputMatrix'] = np.transpose(matlabOutputFull['outputMatrix'], (1, 2, 3, 0))
print("Output Matlab Matrix (numTX, numRX, numSubcarriers, numSnapshots) ~ " + str(np.shape(matlabOutputFull['outputMatrix'])))

## Save CSI to a MATLAB File
if wantToSave:
    print("Saving CSI to .mat file")
    #import pdb; pdb.set_trace()
    if matrixOnly == False:
        matlabOutput = matlabOutputFull
    else:
        matlabOutput = {
            'outputMatrix': matlabOutputFull['outputMatrix'],
            'centerFreq': matlabOutputFull['centerFreq'],
            'chanBW':      matlabOutputFull['chanBW'],
            'elemPos':      matlabOutputFull['elemPos'],
        }

    scipy.io.savemat(outputFilename+'.mat', matlabOutput)
    print("...Done! Saved to " + outputFilename+'.mat')
