'''
Implements Round Trip Phase Method
https://ieeexplore.ieee.org/stamp/stamp.jsp?arnumber=10274424

Goran Gjorgievski, 2/18/25
Dimitry Melnikov, 4/6/25 (Modularized)
'''
#################################################################################
############################# USER INPUTS #######################################
csiPath = "/mnt/c/Users/dmtrm/OneDrive/Schoolwork/(5) Senior Year/Senior Design/VECTOR/bs/nav/csi_data/testing/outside/2-25-25_Outside/2_BS_LAPTOP_OUTSIDE_90DEG_9-14FT/"
csiPath2 = "/mnt/c/Users/dmtrm/OneDrive/Schoolwork/(5) Senior Year/Senior Design/VECTOR/bs/nav/csi_data/testing/outside/2-25-25_Outside/2_BS_LAPTOP_OUTSIDE_90DEG_9-14FT/Laptop/"
#csiPath = "/home/dt12/Code/VECTOR/bs/nav/csi_data/testing/sim/ranging-tests/"
initPos = 9 * 0.3048 # Initial position, in meters.

bothSides = True # False for One-Trip Phase, True for Round-Trip Phase

loadViaMats = False # False to load from pre-processed .mat files
macBS = [0x10, 0x5f, 0xad, 0xd6, 0xa3, 0x2b] # (Patch Setup) Base Station MAC Address
macUT = [0x8c, 0xe9, 0xee, 0xd9, 0xa2, 0xe2] # (Laptop) User Terminal MAC Address (antenna we're tracking)

#################################################################################
############################## IMPORTS ##########################################
import numpy as np
import os
import sys
import scipy.interpolate
import warnings

####################### Import VECTOR Libraries ##################################
# Import VECTOR Libraries
VECTOR_ROOT = os.getenv("VECTOR_ROOT")
sys.path.insert(0, VECTOR_ROOT) if (VECTOR_ROOT is not None) and (VECTOR_ROOT not in sys.path) else None
import setup
setup.loadModules()

import bs.nav.processing.utilsCSI                       as utilsCSI             # To import CSI from .mats
import bs.demo.graphing.plotRanging                     as plotRanging          # To plot distance
import bs.nav.processing.filtersofGOR                   as filtersofGOR         # To load raw CSI
import bs.nav.processing.antennaPermutation             as antennaPermutation   # To unswitch raw CSI

#################################################################################
######################## TICKLE FUNCTIONS #######################################
def loadCSIfromRAW(csiFolder=None,
                   toDS=0, fromDS=0,
                   macBS=[], macUT=[]):
    import tkinter as tk
    from tkinter import filedialog

    # Select CSI Folder
    if (csiFolder is None) or (not os.path.isdir(csiFolder)):
        csiFolder = filedialog.askdirectory(initialdir=os.getcwd(),
                                                title="Please select CSI cal Folder.")

    # Load CSI
    [currCSI, csiPath] = filtersofGOR.loadCSIfromRAW(csiFolder,
                                                     f"Please select CSI Source File.")

    # Process CSI
    currCSI = filtersofGOR.alignSingle(currCSI)

    if not (macBS == []):
        currCSI = filtersofGOR.filterSrcDest(currCSI,
                                             toDS, fromDS, macBS, macUT)
    
    # Convert to usable matrix:
    [currMatrix, _, _, subcFreq_arr, timestamps] = filtersofGOR.convertSingToUsableMatrix(currCSI)

    return (currMatrix, subcFreq_arr[0], timestamps, currCSI, csiPath) # EW!

def alignCSIbsut(Hest1, timestamps1, Hest2, timestamps2, tol=5e-2):
    # The timestamps come from the raw frames, theoretically.
    validIndex1 = []
    validIndex2 = []
    for k1 in range(len(timestamps1)):
        minDiff = tol*2
        minK2 = 0
        
        for k2 in range(len(timestamps2)):
            diff = abs(timestamps1[k1] - timestamps2[k2])
            
            if (diff < tol) and (diff < minDiff):
                minDiff = diff
                minK2 = k2

        if minDiff < tol:
            validIndex1.append(k1)
            validIndex2.append(minK2)

    [AT, AR, S, _] = np.shape(Hest1)
    Hest1_new = np.zeros((AT, AR, S, len(validIndex1)), dtype=np.complex128)
    Hest2_new = np.zeros_like(Hest1_new)
    timestamps1_new = []
    timestamps2_new = []

    for k1 in range(len(validIndex1)):
        Hest1_new[:,:,:,k1] = Hest1[:,:,:,validIndex1[k1]]
        Hest2_new[:,:,:,k1] = Hest2[:,:,:,validIndex2[k1]]
        timestamps1_new.append(timestamps1[validIndex1[k1]])
        timestamps2_new.append(timestamps2[validIndex2[k1]])
    
    return (Hest1_new, timestamps1_new, Hest2_new, timestamps2_new)

####################### RTP-SPECIFIC STUFF ############################################

def interpolateSubcarriers(Hest, subcFreq):
    # Return CSI over Snapshots (K) at the Center Subcarrier
    # Assume Coherent CSI
    [AT, AR, S, K] = np.shape(Hest)
    
    # Average center frequency
    centFreq = np.mean(subcFreq)

    # Interpolate over each frame
    H_RT = np.zeros((K,), dtype=np.complex128)
    for k in range(K):
        # Extract the subcarrier frequencies (x) and the CSI values (y) for frame k
        x = subcFreq
        y = np.angle(Hest[0, 0, :, k])  # Extracting CSI data for the first transmitting and receiving antenna pair

        # Perform linear interpolation using scipy's interp1d
        interpolate_function = scipy.interpolate.interp1d(x, y, kind='linear', fill_value="extrapolate")
        
        H_RT[k] = np.exp(1j*interpolate_function(centFreq))
    
    return (H_RT, centFreq)

def calculateDisplacement(H_RT, centFreq, initPos=0):
    # H_RT ~ [K] (1d complex vector of length equivalent to snapshots)
    #            (CSI at centFreq over snapshots)
    # centFreq ~ Hz (float corresponding to center frequency of CSI)
    # initPos ~ Starting position for dataset

    c = 299792458 # speed of light
    
    # Get the angle in radians for each frame in H_RT
    H_RT_angle = np.angle(H_RT)

    # Unwrap the phase to remove phase wrapping
    H_RT_angle_unwrapped = np.unwrap(H_RT_angle)

    # Each frame of H_RT applied to distance equation
    d_rtp_array = -1/2 * (H_RT_angle_unwrapped / (2 * np.pi)) * (c / centFreq)

    # Have d_rtp_array start at the correct starting position
    disp_offset = d_rtp_array[0] - initPos
    return d_rtp_array - disp_offset

def convertOTPtoRTP(d_rtp_array):
    # If we only simulated or extracted one side of the link, we need to convert the assumptions
    #  of the equations into real stuff.
    return d_rtp_array * -2 # If operating with one-side of link, we need to undo 'half' the distance (one-way)

def ft2m(ftIn):
    return ftIn * 0.3048

#################################### DRIVERS ############################################################
def getDistOTP(Hest, subcFreq, initPos=0):
    # One-Trip Phase. Good for the sim.
    [H_RT, centFreq] = interpolateSubcarriers(Hest, subcFreq)
    d_rtp_array = calculateDisplacement(H_RT, centFreq, initPos)
    d_rtp_array = convertOTPtoRTP(d_rtp_array)
    return (d_rtp_array, centFreq)

def getDistRTP(Hest1, subcFreq1, \
               Hest2, subcFreq2, \
               initPos=0):
    # Round-Trip Phase. Use both sides of the link to cancel out the Center Frequency Offset (CFO)
    [Hest1, centFreq1] = interpolateSubcarriers(Hest1, subcFreq1)
    [Hest2, centFreq2] = interpolateSubcarriers(Hest2, subcFreq2)

    if centFreq1 != centFreq2:
        warnings.warn(f"WARNING! Incoming center freq {centFreq1} and corresponding freq {centFreq2} are not equal!")
        print("Doing nothing...")

    H_RT = Hest1 * Hest2 # Multiply together to cancel CFO 
    d_rtp_array = calculateDisplacement(H_RT, centFreq1, initPos)
    return (d_rtp_array, centFreq1)

if __name__ == "__main__":
    # Load the data
    if loadViaMats:
        # Pre-processed (e.g. Digital Twin)
        print("Loading CSI from Base Station...")
        [Hest, _, _, subcFreq, timestamps, _, loadedStruct, csiPath] = utilsCSI.loadCSIfromMAT(csiPath=csiPath)
        print(f"CSI Loaded from Path: {csiPath}")
        subcFreq = loadedStruct['subcFreq'][:,0] if len(subcFreq) == 1 else subcFreq

        if bothSides:
            print("Loading CSI from User Terminal...")
            [Hest2, _, _, subcFreq2, timestamps2, _, loadedStruct2, csiPath2] = utilsCSI.loadCSIfromMAT(csiPath=csiPath2)
            print(f"CSI Loaded from Path: {csiPath2}")
            subcFreq2 = loadedStruct2['subcFreq'][:,0] if len(subcFreq2) == 1 else subcFreq2

    else:
        # Need to process (e.g. Real Data)
        print("Loading CSI from Base Station...")
        [Hest, subcFreq, timestamps, rawCSI, csiPath] = loadCSIfromRAW(csiPath, toDS=1, fromDS=0, macBS=macBS, macUT=macUT)

        if bothSides:
            print("Loading CSI from User Terminal...")
            [Hest2, subcFreq2, timestamps2, rawCSI2, csiPath2] = loadCSIfromRAW(csiPath2, toDS=0, fromDS=1, macBS=macBS, macUT=macUT)
            print(f"CSI Loaded from Path: {csiPath2}")

        # Align the CSI between the BS and UT to make sure they're referring to the same frame
        [Hest, timestamps, Hest2, timestamps2] = alignCSIbsut(Hest, timestamps, \
                                                                Hest2, timestamps2)
        
        [Hest,  _] = antennaPermutation.detectSwitchSingle(Hest)
        [Hest2, _] = antennaPermutation.detectSwitchSingle(Hest2)

    # Use the module
    if bothSides:
        [d_rtp_array, centFreq] = getDistRTP(Hest1=Hest, subcFreq1=subcFreq, \
                                             Hest2=Hest2, subcFreq2=subcFreq2, \
                                             initPos=initPos)    
    else:
        [d_rtp_array, centFreq] = getDistOTP(Hest, subcFreq, initPos)

    # Plotting
    plotRanging.plotDistance(d_rtp_array, timestamps)

    import pdb; pdb.set_trace()