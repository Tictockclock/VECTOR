'''
#############################################################################
                  MUSIC-based Direction of Arrival Estimator
#############################################################################

(Module)
Dimitry Melnikov, 3/12/25 (Translated from MATLAB)
'''

#################################################################################
############################# USER INPUTS #######################################
csiPath = "" # Parsed .mat file

windowSize = 2           # MUSIC Window (We do AR x K to get correlation)
thetaRange = [65, 115]   # Theta Range to Sample (MUSIC + Pseudospectra Plotting)

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
import bs.demo.graphing.plotDOA as plotDOA          # To plot DOA spectra

###################################################################################
########################## HELPER FUNCTION ########################################
def signedDistances(elemPos):
    """
    Compute signed distances of array elements from the centroid along the principal axis.
    
    Parameters:
        elemPos (np.ndarray): Array positions of shape (AR, 3).

    Returns:
        np.ndarray: 1D array of signed distances for each element.
    """
    elemPos = np.array(elemPos)
    # Center the positions
    centroid = np.mean(elemPos, axis=0)
    centered = elemPos - centroid
    # Use SVD to determine the principal direction
    U, S_vals, Vh = np.linalg.svd(centered)
    principal_direction = Vh[0]
    # Project each element onto the principal axis
    distances = centered @ principal_direction
    return distances

###################################################################################
########################## MUSIC FUNCTION #########################################
def getMUSICSpectrum(Hest, subcFreq, elemPos, windowSize, thetaRange):
    """ Return Direction of Arrival in Degrees (via ULA Steering Equation)
        DOA given relative to the Array Parallel (doa = 90 corresponds to Array Normal)
    
    NOTE - THIS ONLY ASSUMES ONE SIGNAL OF INTEREST! Theoretically can be adjusted for >1 signal source

    DIMENSIONS OF INTEREST
        AT ~ Number of TX Antennas
        AR ~ Number of RX Antennas
        S  ~ Number of Subcarriers
        K  ~ Number of Snapshots

    Args:
        Hest (Numpy Matrix): CSI Matrix. Dimensions [AT AR S K]
        subcFreq (Numpy Array): Dimensions [1 S]. Subcarrier Frequencies for each S (Hz)
        elemPos (Numpy Matrix): Dimensions [AR 3]. Positions for each RX Antenna (Assume a ULA)
        windowSize (int): Number of snapshots in each averaging window
        thetaRange (List): [minAngle, maxAngle] (deg). Angles off of Array Parallel to run MUSIC on
    """
    # Get dimensions:
    [AT, AR, S, K] = np.shape(Hest)

    # Compute signed distance from each element to the origin
    ulaPos = signedDistances(elemPos) # [AR,]

    c = 299792458 # Speed of light (m/s)
    subcLambda = c / subcFreq.astype(np.float64) # [S,]

    # Compute Array Manifold Vector V ~ [S, AR]
    V = np.zeros((S, AR))
    for s in range(S):
        for ar in range(AR):
            V[s, ar] = -1*2*np.pi*(ulaPos[ar] / subcLambda[s])

    # Determine last valid snapshot index (for moving window)
    lastValidK = K - windowSize + 1

    # Preallocate arrays for MUSIC Spectrum and DoA Estimates
    T = 180*3 # Number of theta grid points ~ T
    theta = np.linspace(thetaRange[0], thetaRange[1], T) # All possible angles to search through (deg)

    doaMUSIC = np.zeros((AT, T, S, K))
    for k in range(lastValidK):
        print(f"Processing Frame of {K}: {k}")
        for at in range(AT):
            for s in range(S):
                # Extract CSI for current window [AT, windowSize]
                CSI = Hest[at, :, s, k:k+windowSize]
                # Compute coveriance matrix R [AR, AR]
                R = (1 / CSI.shape[1]) * (CSI @ CSI.conj().T)

                # Eigen decomposition of covariance matrix
                eigenValues, eigenVectors = np.linalg.eigh(R)
                # Sort eigenvalues (and eigenvectors corresponding) in descending order
                idx = np.argsort(eigenValues)[::-1]
                eigenVectors = eigenVectors[:, idx] # Largest eigenvalue corresponds to Signal, lowest to noise
                # Define noise subspace (skip first eigenvector, corresponding to signal)
                noiseSubspace = eigenVectors[:, 1:]

                # Initialize MUSIC Spectrum for each angle in theta grid
                musicSpectrum = np.zeros(len(theta))
                for t in range(len(theta)):
                    # Compute steering vector for current theta (cosine in degrees)
                    V_test = np.exp(1j * V[s, :] * np.cos(np.deg2rad(theta[t])))
                    # Compute pseudospec value
                    den = np.abs(np.conj(V_test) @ (noiseSubspace @ noiseSubspace.conj().T) @ V_test)
                    musicSpectrum[t] = 1 / den if den != 0 else 0

                # Normalize:
                if np.max(musicSpectrum) != 0:
                    musicSpectrum = 10 * np.log10(musicSpectrum / np.max(musicSpectrum))
                else:
                    musicSpectrum = 10 * np.log10(musicSpectrum + 1e-12)  # avoid log10(0)

                doaMUSIC[at, :, s, k] = musicSpectrum

    return doaMUSIC

if __name__ == "__main__":
    # Load in the data:
    [Hest, centerFreq, chanBW, subcFreq, elemPos, _, csiPath] = \
        utilsCSI.loadCSIfromMAT(csiPath=csiPath)
    
    Hest = Hest[:, :, :, :]

    # Display the CSI:
    plotCSI.plot2DCSI(Hest, subcFreq, title="Loaded CSI", doUnwrap=True)

    # Do the DOA Estimation itself:
    doaMUSIC = getMUSICSpectrum(Hest, subcFreq, elemPos, windowSize, thetaRange)

    # Plot MUSIC Pseudospectra:
    plotDOA.plotDOA_vsSubcarrier(doaMUSIC, thetaRange=thetaRange,
                                title="MUSIC DOA vs. Subcarrier")
    plotDOA.plotDOA_vsSnapshots(doaMUSIC, thetaRange=thetaRange, windowSize=windowSize,
                                title="MUSIC DOA vs. Snapshots")
    
    import pdb; pdb.set_trace()
