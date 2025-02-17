'''
CSI Utilities

(Module)
Dimitry Melnikov, 2/17/25
'''

#################################################################################
############################## IMPORTS ##########################################
import tkinter as tk                # For file selection
from tkinter import filedialog      # For file selection

import numpy as np                  # Numpy Processing
import scipy.io                     # Load data from .mat file
import os                           # To retrive files

#################################################################################
############################# FUNCTIONS #########################################
def loadCSIfromMAT(csiPath=None):
    """ Load Parsed CSI from .mat file 

    Args:
        csiPath (string, optional): Absolute path to .mat file. Defaults to None.

    Returns:
        [
            Hest,           # CSI itself [AT AR S K]
            centerFreq,     # Center/Carrier Frequency for collected CSI
            chanBW,         # Channel Bandwidth (Hz)
            elemPos,        # Element Positions [[X0, Y0, Z0], [X1, Y1, Z1], ...]
            loadedStruct    # Source Struct
        
        ]: Tuple with variables of interest.
    """
    if csiPath is None:
        # Do GUI interface if path not specified
        # Ask the user to select a single file name.
        csiPath = filedialog.askopenfilename(initialdir=os.getcwd(),
                                            title="Please select the CSI Source File:",
                                            filetypes=[('mat files', '.mat'), ('all files', '.*')])
    # Load in the Matlab File
    loadedStruct = scipy.io.loadmat(csiPath)

    # Stick everything into a tuple.
    Hest            = loadedStruct['outputMatrix']  # CSI Itself [AT AR S K]
    centerFreq      = loadedStruct['centerFreq']    # Center/Carrier Frequency for collected CSI (Hz)
    chanBW          = loadedStruct['chanBW']        # Channel Bandwidth (Hz)
    elemPos         = loadedStruct['elemPos']       # Positions for each element [[X0, Y0, Z0], [X1, Y1, Z1], ...]

    return [Hest, centerFreq, chanBW, elemPos, loadedStruct]
    



def getSubcFreq(centerFreq, chanBW, S):
    """ Return Subcarrier Frequencies for Given CSI

    Args:
        centerFreq (integer): Center/Carrier Frequency (Hz)
        chanBW (integer): Channel Bandwidth (Hz)
        S (integer): Number of Subcarriers. ([AT AR S K] ~ np.size(Hest, 2))

    Returns:
        np.array: Numpy array of size `S` corresponding to the frequencies of each subcarrier
    """
    # Calculate the Frequency Axis
    subcSpacing = chanBW / S # Channel BW / Num Subcarriers (S)
    subcFreq    = np.linspace(centerFreq - chanBW/2, \
                              centerFreq + chanBW/2, \
                              S)
    subcFreq = subcFreq.flatten()

    return subcFreq