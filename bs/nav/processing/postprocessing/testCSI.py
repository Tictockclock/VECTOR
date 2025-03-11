# Test Script for Troubleshooting CSI

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


#################################################################################
csiPath = "/home/dt12/Code/VECTOR/bs/nav/csi_data/EVANSBALLS.csi"
#csiPath = "/home/dt12/Code/VECTOR/received_files/received_frames.csi"
#csiPath = "/home/dt12/Code/VECTOR/bs/nav/csi_data/testing/outside/2-25-25_Outside/2_BS_LAPTOP_OUTSIDE_90DEG_9-14FT/rx_21_250225_161936.csi"
[csiRaw, csiPath] = filtersofGOR.loadCSIfromRAW(csiPath)

print(f"Number of Frames: {len(csiRaw.raw)}")
import pdb; pdb.set_trace()
print(f"First Standard MAC Header: {csiRaw.raw[0]['StandardHeader']}")