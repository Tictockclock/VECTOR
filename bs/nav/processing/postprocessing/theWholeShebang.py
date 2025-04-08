"""
As of 3/16/2025, complete driver script.
Takes in a raw CSI file and a given configuration, does some stuff, and outputs the MUSIC Pseudospectra.

This is meant to be a blueprint for data processing for Evan.

Dimitry Melnikov, (Driver), 3/16/2025
"""

################################################################
################# USER INPUTS ##################################
calFolder = "/mnt/c/Users/dmtrm/OneDrive/Schoolwork/(5) Senior Year/Senior Design/VECTOR/bs/nav/csi_data/testing/asec_basement/3-11-25/CAL/"      # OPTIONAL! Absolute path to Calibration Folder
datasetFolder_Alpha = "/mnt/c/Users/dmtrm/OneDrive/Schoolwork/(5) Senior Year/Senior Design/VECTOR/bs/nav/csi_data/testing/in_room/3-27-reftest/"  # OPTIONAL! Absolute path to CSI Dataset Folder
datasetFolder_Beta = datasetFolder_Alpha
datasetFolder_Laptop = datasetFolder_Alpha

#calFolder =  "/mnt/c/Users/dmtrm/OneDrive/Schoolwork/(5) Senior Year/Senior Design/VECTOR/bs/nav/csi_data/testing/in_room/2-24-25/1_BS_LAPTOP_ROOM_90deg_4ft_BS/CAL/"
#datasetFolder = "/mnt/c/Users/dmtrm/OneDrive/Schoolwork/(5) Senior Year/Senior Design/VECTOR/bs/nav/csi_data/testing/in_room/2-24-25/1_BS_LAPTOP_ROOM_90deg_4ft_BS/"

## ARRAY GEOMETRY
# Element Positions
elemSpacing = 0.079961058 # 0.65 Lambda (f = 2.437GHz)
elemPos = [ # Base Station Layout
    [0, -(1.5)*elemSpacing, 0], # [X, Y, Z] for Elem 0...
    [0, -(0.5)*elemSpacing, 0], # [X, Y, Z] for Elem 1...
    [0,  (0.5)*elemSpacing, 0],
    [0,  (1.5)*elemSpacing, 0],
]

# File location, as well as location relative to Array POV, facing out:
#              0             1               2              3
#           (AUX-2)  -    (AUX-1)   -     (MAIN-1)   -   (AUX-1)
# AUX-2 represents the AUX (2) antenna attached to NIC 2, => NICdata[1]['AUX'] = 0
# NIC 2 is represented by being placed second in `NICdata`
NICdata = [
    # Base Station Layout
    {   # NIC 1
        'file':  "21",#"NIC21", # Leave empty to select during dialogue.
        0:      1,  # AUX
        1:      2,  # MAIN
        'mac':  [], # MAC Address for the NIC. Leave empty -- will be autopopulated
    },
    {   # NIC 2
        'file': "22",#"NIC22", # Leave empty to select during dialogue.
        0:      0,  # AUX
        1:      3,  # MAIN
        'mac':  [], # MAC Address for the NIC. Leave empty -- will be autopopulated
    }
]

### GOR FILTER OPTIONS
# MAC Address & To/From DS Alignment
# See https://mrncciew.com/2014/09/28/cwap-mac-headeraddresses/
toDS = 0; fromDS = 1
macBS = [0x6c, 0x2f, 0x80, 0xdf, 0x37, 0xca] # (Alt-BS Setup) (NIC 23) MAC Address for reference-NIC
#macBS = [0x10, 0x5f, 0xad, 0xd6, 0xa3, 0x2b] # (Patch Setup) Base Station MAC Address
#macUT = [0xd8, 0x3a, 0xdd, 0xfb, 0x68, 0xe1] # (UT) User Terminal MAC Address
macUT = [0x8c, 0xe9, 0xee, 0xd9, 0xa2, 0xe2] # (Laptop) User Terminal MAC Address (antenna we're tracking)
#macREF= [0x6c, 0x2f, 0x80, 0xdf, 0x37, 0xca] # (NIC 23) MAC Address for reference-NIC (for Cal)

macBS_REF = [0x12, 0x34, 0xb4, 0x63, 0x0a, 0x5a] # (HackRF) MAC Address 'Dest' from Injected Frames
macUT_REF = [0x00, 0x16, 0xea, 0x12, 0x34, 0x56] # (HackRF) MAC Address 'Src' from Injected Frames

forceAT = 1   # 0 to disable (but will truncate to minimum), otherwise will only select CSI with the corresponding # Transmit Antennas
forceAR = 2    # 0 to disable (but will truncate to minimum), otherwise will only select CSI with the corresponding # Receive Antennas

### CAL OPTIONS
# CABLE LENGTH
cablePts = [[2.436e9, -104.55],[2.447e9, -139.20],[2.458e9, -173.76]] # [Freq, Phase] (use to calculate group delay)

### DOA/MUSIC Options
windowSize = 2           # MUSIC Window (We do AR x K to get correlation)
thetaRange = [65, 115]   # Theta Range to Sample (MUSIC + Pseudospectra Plotting)

initPos = 9 * 0.3048 # Initial position, in meters.

armAngle = 45.0702

#################################################################################
############################## IMPORTS ##########################################
import numpy as np                  # Numpy Processing

####################### Import VECTOR Libraries ##################################
# Import VECTOR Libraries
import os; import sys
VECTOR_ROOT = os.getenv("VECTOR_ROOT")
sys.path.insert(0, VECTOR_ROOT) if (VECTOR_ROOT is not None) and (VECTOR_ROOT not in sys.path) else print("WARNING! VECTOR_ROOT NOT DEFINED! RUN THIS FROM VECTOR ROOT DIRECTORY: `export VECTOR_ROOT=$(pwd)`")
import setup; setup.loadModules()

import bs.nav.processing.filtersofGOR                   as filtersofGOR     # Import, parse, filter.
import bs.nav.processing.postprocessing.cableCalNICS    as cableCalNICS     # Calculate and apply calibration coefficients.
import bs.nav.doa.naiveMUSIC                            as naiveMUSIC       # To perform DOA Estimation
import bs.nav.ranging.ttPhase                           as ttPhase          # To perform Ranging Estimation

import bs.nav.processing.antennaPermutation             as antennaPermutation   # CSI Sanitization

import bs.demo.graphing.plotCSI                         as plotCSI          # Plot the CSI
import bs.demo.graphing.plotDOA                         as plotDOA          # Plot the MUSIC Pseudospectra
import bs.demo.graphing.plotRanging                     as plotRanging      # Plot the Displacement

#################################################################################
############################### DRIVER ##########################################
############################ Load in CSI ########################################
# CSI from Alpha (Passive Array) (for DoA)
numNICS = len(NICdata) # Number of CSI files we're parsing for single array
print("(Alpha) Loading CSI from Sensing Array:")
[loadedCSI_Alpha, NICdata_Alpha, csiPath_Alpha] = filtersofGOR.loadMultiNICS(NICdata, datasetFolder_Alpha)

# CSI from Beta (Hotspot) (for RTP)
print("(Beta) Loading CSI from Hotspot:")
[loadedCSI_Beta, csiPath_Beta] = filtersofGOR.loadCSIfromRAW(datasetFolder_Beta, f"Please select CSI (Hotspot) file.")

# CSI from Laptop (for RTP)
print("(Lap) Loading CSI from Laptop:")
[loadedCSI_Laptop, csiPath_Laptop] = filtersofGOR.loadCSIfromRAW(datasetFolder_Laptop, f"Please select CSI (Laptop) file.")

############################# Parse CSI ##########################################
# Alpha / Sensing Array:
print("(Alpha) Combining Sense Array CSI by aligning MPDU...")
combinedCSI_Alpha = filtersofGOR.alignMPDU(numNICS, loadedCSI_Alpha)

print("(Alpha) Filtering to TRAINING frames by Source/Destination MAC Addresses...")
macAlignedCSI_Alpha_TRAIN = filtersofGOR.filterSrcDest(combinedCSI_Alpha, toDS=0, fromDS=0, macBS=macBS_REF, macUT=macUT_REF)
print(f"Discarding CSI not matching parameters: AT: {forceAT}, AR: {forceAR}... for TRAIN")
forcedCSI_Alpha_TRAIN = filtersofGOR.filterForcedParams(macAlignedCSI_Alpha_TRAIN, forceAT, forceAR)
print("(Alpha) Converting TRAIN to usable matrix...")
[parsedMatrix_Alpha_TRAIN, _, _, subcFreq_arr_Alpha_TRAIN, timestamps_Alpha_TRAIN] = filtersofGOR.convertToUsableMatrix(forcedCSI_Alpha_TRAIN, NICdata)
subcFreq_Alpha_TRAIN = subcFreq_arr_Alpha_TRAIN[0]

print("(Alpha) Filtering to TRACKING frames by Source/Destination MAC Addresses...")
macAlignedCSI_Alpha_TRACK = filtersofGOR.filterSrcDest(combinedCSI_Alpha, toDS=1, fromDS=0, macBS=macBS, macUT=macUT)
print(f"Discarding CSI not matching parameters: AT: {forceAT}, AR: {forceAR}... for TRACK")
forcedCSI_Alpha_TRACK = filtersofGOR.filterForcedParams(macAlignedCSI_Alpha_TRACK, forceAT, forceAR)
print("(Alpha) Converting TRACK to usable matrix...")
[parsedMatrix_Alpha_TRACK, _, _, subcFreq_arr_Alpha_TRACK, timestamps_Alpha_TRACK] = filtersofGOR.convertToUsableMatrix(forcedCSI_Alpha_TRACK, NICdata)
subcFreq_Alpha_TRACK = subcFreq_arr_Alpha_TRACK[0]


# Beta / Hotspot Antenna:
print("(Beta) Self-Aligning Single CSI Source...")
currCSI_Beta = filtersofGOR.alignSingle(loadedCSI_Beta)
print("(Beta) Filtering frames from Laptop to Hotspot...")
currCSI_Beta = filtersofGOR.filterSrcDest(currCSI_Beta, toDS=1, fromDS=0, macBS=macBS, macUT=macUT)
print("(Beta) Converting to usable matrix...")
[parsedMatrix_Beta, _, _, subcFreq_arr_Beta, timestamps_Beta] = filtersofGOR.convertSingToUsableMatrix(currCSI_Beta)
subcFreq_Beta = subcFreq_arr_Beta[0]


# Laptop Antenna:
print("(Lap) Self-Aligning Single CSI Source...")
currCSI_Lap = filtersofGOR.alignSingle(loadedCSI_Laptop)
print("(Lap) Filtering frames from Laptop to Hotspot...")
currCSI_Lap = filtersofGOR.filterSrcDest(currCSI_Lap, toDS=0, fromDS=1, macBS=macBS, macUT=macUT)
print("(Lap) Converting to usable matrix...")
[parsedMatrix_Lap, _, _, subcFreq_arr_Lap, timestamps_Lap] = filtersofGOR.convertSingToUsableMatrix(currCSI_Lap)
subcFreq_Lap = subcFreq_arr_Lap[0]

############################ Sanitize CSI ########################################
# Time-align Hotspot (BS) and Laptop (UT) for RTP
print("(Beta/Lap) Time-Aligning CSI with Hotspot and Laptop...")
[Hest_Beta, timestamps_Beta, Hest_Lap, timestamps_Lap] = ttPhase.alignCSIbsut(parsedMatrix_Beta, timestamps_Beta, parsedMatrix_Lap, timestamps_Lap)
# Undo internal switching by looking over mean phase (Can't use reference card/HackRF since it doesn't generate CSI on Hotspot)
print("(Beta) Detecting and undoing internal NIC switching...")
[Hest_Beta, _] = antennaPermutation.detectSwitchSingle(Hest_Beta)
print("(Lap) Detecting and undoing internal NIC switching...")
[Hest_Lap, _] = antennaPermutation.detectSwitchSingle(Hest_Lap)

Hest_Alpha = antennaPermutation.applyTrainingMatrix(parsedMatrix_Alpha_TRACK, timestamps_Alpha_TRACK, \
                                                    parsedMatrix_Alpha_TRAIN, timestamps_Alpha_TRAIN, \
                                                    np.mean(subcFreq_Alpha_TRAIN), armAngle=armAngle) # TODO - what the fuck?
subcFreq_Alpha = subcFreq_Alpha_TRACK

############################ Solve Navigation ####################################
print("Estimating Direction of Arrival via MUSIC Algorithm...")
doaMUSIC = naiveMUSIC.getMUSICSpectrum(Hest_Alpha[:,:,:,:], subcFreq_Alpha, elemPos, windowSize, thetaRange)

print("Estimating Displacement via Round-Trip Phase Method...")
[d_rtp_array, centFreq] = ttPhase.getDistRTP(Hest1=Hest_Beta, subcFreq1=subcFreq_Beta, \
                                             Hest2=Hest_Lap,  subcFreq2=subcFreq_Lap, \
                                             initPos=initPos)

############################### Plot Results ######################################
# Plot MUSIC Pseudospectra
plotDOA.plotDOA_vsSubcarrier(doaMUSIC, thetaRange=thetaRange,
                                title="MUSIC DOA vs. Subcarrier")
plotDOA.plotDOA_vsSnapshots(doaMUSIC, thetaRange=thetaRange, windowSize=windowSize,
                                title="MUSIC DOA vs. Snapshots")
# Plot Displacement
plotRanging.plotDistance(d_rtp_array, timestamps_Beta, 
                                title="Linear Distance over Time")

########################### Package for Export ####################################
outDOA = naiveMUSIC.getDOAfromSpectrum(doaMUSIC, thetaRange) # sSlice = S//2, atSlice = 0
print(f"DOA Array over Snapshots: {outDOA}")
print(f"Distance Array over Snapshots: {d_rtp_array}")

import pdb; pdb.set_trace() # To keep the graphs alive.