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

import bs.nav.processing.filtersofGOR as filtersofGOR   # To import raw CSI from .csi files
import bs.nav.processing.utilsCSI as utilsCSI           # To import CSI from .mats
import bs.demo.graphing.plotCSI as plotCSI              # To plot CSI

#################################################################################
#csiPath = "home/dt12/received_files/1742145148546.csi"
csiPath = "/home/dt12/Code/VECTOR/output_trimmed.csi"
#csiPath = "/home/dt12/Code/VECTOR/received_files/received_frames.csi"
#csiPath = "/home/dt12/UT_TEST_ROOM-3-11-2025.csi"
csiPath = "/home/dt12/csi_frames/1742148391299.csi"

[csiRaw, csiPath] = filtersofGOR.loadCSIfromRAW(csiPath)

print(f"Number of Frames: {len(csiRaw.raw)}")
print(f"First Standard MAC Header: {csiRaw.raw[0]['StandardHeader']}")

import pdb; pdb.set_trace()

#plotCSI.plotMACDEST(csiPath=csiPath)

