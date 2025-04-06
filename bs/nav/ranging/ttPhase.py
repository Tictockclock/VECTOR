'''
Implements Round Trip Phase Method
https://ieeexplore.ieee.org/stamp/stamp.jsp?arnumber=10274424

Goran Gjorgievski, 2/18/25
Dimitry Melnikov, 4/6/25 (Modularized)
'''
#################################################################################
############################# USER INPUTS #######################################
csiPath = "/mnt/c/Users/dmtrm/OneDrive/Schoolwork/(5) Senior Year/Senior Design/VECTOR/bs/nav/csi_data/testing/sim/ranging-tests/"
csiPath2 = "/mnt/c/Users/dmtrm/OneDrive/Schoolwork/(5) Senior Year/Senior Design/VECTOR/bs/nav/csi_data/testing/sim/ranging-tests/"
#csiPath = "/home/dt12/Code/VECTOR/bs/nav/csi_data/testing/sim/ranging-tests/"
bothSides = False # False for One-Trip Phase, True for Round-Trip Phase
initPos = 9 * 0.3048 # Initial position, in meters.

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

import bs.nav.processing.utilsCSI as utilsCSI           # To import CSI from .mats
import bs.demo.graphing.plotCSI as plotCSI              # To plot manipulated CSI

#################################################################################
######################## TICKLE FUNCTIONS #######################################
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
    print("Loading CSI from Base Station...")
    [Hest, _, _, subcFreq, timestamps, _, loadedStruct, csiPath] = utilsCSI.loadCSIfromMAT(csiPath=csiPath)
    print(f"CSI Loaded from Path: {csiPath}")
    subcFreq = loadedStruct['subcFreq'][:,0] if len(subcFreq) == 1 else subcFreq

    if bothSides == True:
        # Load more data
        print("Loading CSI from User Terminal...")
        [Hest2, _, _, subcFreq2, _, _, loadedStruct2, csiPath2] = utilsCSI.loadCSIfromMAT(csiPath=csiPath2)
        print(f"CSI Loaded from Path: {csiPath2}")
        subcFreq2 = loadedStruct2['subcFreq'][:,0] if len(subcFreq2) == 1 else subcFreq2

        [d_rtp_array, centFreq] = getDistRTP(Hest1=Hest, subcFreq1=subcFreq, \
                                             Hest2=Hest2, subcFreq2=subcFreq2, \
                                             initPos=initPos)    

    else:
        # Use the module
        [d_rtp_array, centFreq] = getDistOTP(Hest, subcFreq, initPos)

    # Plotting
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(timestamps[0], d_rtp_array)
    ax.set_title("Linear Distance over Time")
    ax.set_xlabel("Time (sec)")
    ax.set_ylabel("Distance (m)")
    plt.grid()
    plt.show(block=False)

    import pdb; pdb.set_trace()