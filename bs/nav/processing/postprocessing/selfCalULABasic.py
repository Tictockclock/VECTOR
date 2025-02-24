'''
#############################################################################
                        Basic ULA Self-Calibration Script
#############################################################################

Takes in CSI from Uniform Line Array (ULA), returns an averaged CSI Offset to apply to new CSI
    - CSI from Neighboring Elements to Receiving Elements assumed
        - Given CSI in a .mat file with the following:
            - A CSI matrix of size [AT AR S K], where:
                - AT: Number of Transmit Antennas
                - AR: Number of Receive Antennas
                - S: Number of Subcarriers
                - K: Number of CSI Snapshots
            - 'centerFreq' and 'chanBW' to derive wavelengths of each subcarrier
            - 'elemPos', which we use to generate the Ideal CSI
        - Given Source Transmitter Locations (input in script)
            - From this, we derive the ideal locations (in future, would like this to be measured data)
    
    - Calculate Ideal CSI (assuming isotropic radiators, strictly from distance)
    - Divide Observed by Ideal CSI
        - Store as Offset
    - Return Averaged Offset
        - Apply Averaged Offset to the input CSI for visual validation

(Driver Script)
Dimitry Melnikov, 2/17/25
'''

#################################################################################
############################# USER INPUTS #######################################
spacing = 29.1e-3; # 29.1mm Spacing

# Element Positions relative to the Element Positions in the Input CSI
sourcePos = [
    [0, -(3+0.5)*spacing, 0], # [X, Y, Z] for Elem 0...
    [0, -(2+0.5)*spacing, 0], # [X, Y, Z] for Elem 1...
]
#################################################################################
############################## IMPORTS ##########################################
import numpy as np                  # Numpy Processing
import scipy.io                     # To save data to .mat file

####################### Import VECTOR Libraries ##################################
import os; import sys
VECTOR_ROOT = os.getenv("VECTOR_ROOT")
sys.path.insert(0, VECTOR_ROOT) if (VECTOR_ROOT is not None) and (VECTOR_ROOT not in sys.path) else None
import setup; setup.loadModules()

import bs.nav.processing.utilsCSI as utilsCSI       # To import CSI from .mats
import bs.demo.graphing.plotCSI as plotCSI          # To plot manipulated CSI

#################################################################################
########################### DRIVER SETUP ########################################
### LOAD CSI ###
[Hest, centerFreq, chanBW, elemPos, _, _] = utilsCSI.loadCSIfromMAT()

### EXTRACT CSI/SYSTEM CONSTANTS + EXTRACT SUBCARRIER FREQUENCIES ###
[AT, AR, S, K] = np.shape(Hest)
subcFreq = utilsCSI.getSubcFreq(centerFreq, chanBW, S)

#################################################################################
#################### CALCULATE IDEAL PHASE DATA #################################
# This data will fit into an [AT AR S] frame, 
#   since it should be constant across snapshots K
# Phase_ideal = -k_sub*d = -(2pi/lambda_sub)*d = -(2pi*f_sub/c)*d = -(2pi/c)*d*f_sub
idealCSI = np.zeros((AT, AR, S), dtype=np.complex128)
c = 299792458 # m/s

for t in range(AT):
    for r in range(AR):
        for s in range(S):
            # Get distance from TX (t) to RX (r)
            tPos = np.array(sourcePos[t])
            rPos = np.array(elemPos[r])
            d = np.linalg.norm(tPos - rPos)
            idealPhase = (-2*np.pi/c)*d*subcFreq[s] # (-2pi/c)*d*f_sub
            idealCSI[t, r, s] = 1*np.exp(1j*idealPhase)

# Plot the Ideal CSI for User
pltIdealCSI = np.zeros((AT, AR, S, 1), dtype=np.complex128); pltIdealCSI[:, :, :, 0] = idealCSI
plotCSI.plot2DCSI(pltIdealCSI, centerFreq, chanBW, title="Ideal CSI for Provided Geometry", doUnwrap=True)

#################################################################################
##################### SUBTRACT IDEAL PHASE DATA #################################
offsetCSI = np.zeros((AT, AR, S, K), dtype=np.complex128)
for k in range(K):
    # Divide the magnitudes, subtract the Phases
    offsetCSI[:, :, :, k] = Hest[:, :, :, k] / idealCSI

# Plot resulting CSI Offsets for User
plotCSI.plot2DCSI(offsetCSI, centerFreq, chanBW, title="Measured CSI Offset", doUnwrap=True)

#################################################################################
################ APPLY OFFSETS TO CAL DATA FOR VERIF ############################
# correctedCSI = np.zeros((AT, AR, S, K), dtype=np.complex128)
# correctedCSI[:, :, :, 0] = Hest[:, :, :, 0] / (Hest[:, :, :, -1] / idealCSI)
# import pdb; pdb.set_trace()
# for k in range(1, K-1):
#     correctedCSI[:, :, :, k] = Hest[:, :, :, k] / (Hest[:, :, :, k-1] / idealCSI)

# plotCSI.plot2DCSI(correctedCSI, centerFreq, chanBW, title="'Corrected' CSI?'", doUnwrap=True)
correctedCSI = np.zeros((AT, AR, S, K), dtype=np.complex128)
calOffset = np.mean(offsetCSI, axis=3)          # Get average offset-from-ideal over time
calOffsetMult = np.expand_dims(calOffset, axis=-1)      # Reintroduce the K dimension
calOffsetMult = np.repeat(calOffsetMult, K, axis=-1)    # Duplicate K times
correctedCSI = Hest / calOffsetMult                     # Apply Offset

plotCSI.plot2DCSI(correctedCSI, centerFreq, chanBW, title="'Corrected' CSI?'", doUnwrap=True)

#################################################################################
################## APPLY OFFSETS TO NON-CAL DATA  ###############################
print("Select Non-Calibrated CSI from same dataset")
### LOAD CSI ###
[preHest, _, _, _, preStruct_, preCSIPath] = utilsCSI.loadCSIfromMAT()
[_, _, _, preK] = np.shape(preHest)

### APPLY OFFSET ###
calOffsetMult = np.expand_dims(calOffset, axis=-1)
calOffsetMult = np.repeat(calOffsetMult, preK, axis=-1)
correctedCSI = preHest / calOffsetMult

plotCSI.plot2DCSI(correctedCSI, centerFreq, chanBW, title="'Post-Calibrated' CSI?", doUnwrap=True)

### SAVE MODIFIED CSI TO MATLAB FILE ###
print("Saving Modified CSI to .mat file...")   
matlabOutput = preStruct_
matlabOutput['outputMatrix'] = correctedCSI

filename = os.path.splitext(os.path.basename(preCSIPath))[0] + "_POSTCAL"
scipy.io.savemat(f"{filename}.mat", matlabOutput)

print(f"Done. Saved to {filename}.mat")

import pdb; pdb.set_trace()