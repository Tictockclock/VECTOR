"""
As of 3/16/2025, complete driver script.
Takes in a raw CSI file and a given configuration, does some stuff, and outputs the MUSIC Pseudospectra.

This is meant to be a blueprint for data processing for Evan.

Dimitry Melnikov, (Driver), 3/16/2025
"""

################################################################
################# USER INPUTS ##################################
calFolder = "/mnt/c/Users/dmtrm/OneDrive/Schoolwork/(5) Senior Year/Senior Design/VECTOR/bs/nav/csi_data/testing/asec_basement/3-11-25/CAL/"      # OPTIONAL! Absolute path to Calibration Folder
datasetFolder = "/mnt/c/Users/dmtrm/OneDrive/Schoolwork/(5) Senior Year/Senior Design/VECTOR/bs/nav/csi_data/testing/in_room/3-27-reftest/"  # OPTIONAL! Absolute path to CSI Dataset Folder


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
macREF = macBS

forceAT = 1   # 0 to disable (but will truncate to minimum), otherwise will only select CSI with the corresponding # Transmit Antennas
forceAR = 2    # 0 to disable (but will truncate to minimum), otherwise will only select CSI with the corresponding # Receive Antennas

### CAL OPTIONS
# CABLE LENGTH
cablePts = [[2.436e9, -104.55],[2.447e9, -139.20],[2.458e9, -173.76]] # [Freq, Phase] (use to calculate group delay)

### DOA/MUSIC Options
windowSize = 2           # MUSIC Window (We do AR x K to get correlation)
thetaRange = [65, 115]   # Theta Range to Sample (MUSIC + Pseudospectra Plotting)

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

import bs.demo.graphing.plotCSI                         as plotCSI          # Plot the CSI
import bs.demo.graphing.plotDOA                         as plotDOA          # Plot the MUSIC Pseudospectra

#################################################################################
############################### DRIVER ##########################################
## GENERATE CALIBRATION MATRIX ##
print("Generating Calibration Matrix...")
# [calMatrix, calSubcFreq] = cableCalNICS.generateCalOffset(NICdata, calFolder,
#                       toDS, fromDS, macBS, macREF,
#                       cablePts,
#                       saveCalToMat=False)
# Plot Calibration Matrix
#plotCSI.plot2DCSI(calMatrix, calSubcFreq, title="Calibration Matrix", doUnwrap=True)

## CARBON COPY OF `filtersofGOR.py` DRIVER: ##
numNICS = len(NICdata) # Number of CSI files we're parsing (minus the saving)

print("Loading CSI from raw .csi files:")
[loadedCSI, NICdata, csiPath] = filtersofGOR.loadMultiNICS(NICdata, datasetFolder)
import pdb; pdb.set_trace()
print("Combining CSI by aligning MPDU...")
combinedCSI = filtersofGOR.alignMPDU(numNICS, loadedCSI)

print("Filtering frames by Source/Destination MAC Addresses...")
macAlignedCSI = filtersofGOR.filterSrcDest(combinedCSI, toDS, fromDS, macBS, macUT)

filtersofGOR.statsForcedParams(macAlignedCSI)

print(f"Discarding CSI not matching parameters: AT: {forceAT}, AR: {forceAR}...")
forcedCSI = filtersofGOR.filterForcedParams(macAlignedCSI, forceAT, forceAR)
import pdb; pdb.set_trace()
# Plot useful MAC Header Information:
# for _nic in range(numNICS):
#     plotCSI.plotMACDEST(forcedCSI, NICnum=_nic)

print("Converting to usable matrix...")
[parsedMatrix, centerFreq_arr, chanBW_arr, subcFreq_arr, timestamps] = filtersofGOR.convertToUsableMatrix(forcedCSI, NICdata)

# Plot Parsed Matrix
##plotCSI.plot2DCSI(parsedMatrix, subcFreq_arr[0], title="CSI Pre-Calibration", doUnwrap=True)

## APPLY CALIBRATION OFFSET TO PARSED MATRIX ##
print("Applying Calibration Matrix to Parsed Matrix...")
[correctedMatrix, subcFreq] = cableCalNICS.applyCalOffset(calMatrix, calSubcFreq, parsedMatrix, subcFreq_arr[0])

# Plot Calibrated Matrix
##plotCSI.plot2DCSI(correctedMatrix, subcFreq, title="CSI Post-Calibration", doUnwrap=True)

## PERFORM DOA VIA MUSIC ALGORITHM ##
print("Estimating Direction of Arrival via MUSIC Algorithm...")
doaMUSIC = naiveMUSIC.getMUSICSpectrum(correctedMatrix, subcFreq, elemPos, windowSize, thetaRange)

# Plot MUSIC Pseudospectra
plotDOA.plotDOA_vsSubcarrier(doaMUSIC, thetaRange=thetaRange,
                                title="MUSIC DOA vs. Subcarrier")
plotDOA.plotDOA_vsSnapshots(doaMUSIC, thetaRange=thetaRange, windowSize=windowSize,
                                title="MUSIC DOA vs. Snapshots")

import pdb; pdb.set_trace() # To keep the graphs alive.