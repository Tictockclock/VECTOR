'''
Implements Round Trip Phase Method
Similar to Decimeter-Level Ranging Paper (Insert Link Here)

Goran Gjorgievski, 2/18/25
'''

import numpy as np

import os; import sys
VECTOR_ROOT = os.getenv("VECTOR_ROOT")
sys.path.insert(0, VECTOR_ROOT) if (VECTOR_ROOT is not None) and (VECTOR_ROOT not in sys.path) else None
import setup; setup.loadModules()

import bs.nav.processing.utilsCSI as utilsCSI       # To import CSI from .mats
import bs.demo.graphing.plotCSI as plotCSI          # To plot manipulated CSI

[Hest_BS, centerFreq_BS, chanBW_BS, elemPos_BS, _] = utilsCSI.loadCSIfromMAT()
[Hest_UT, centerFreq_UT, chanBW_UT, elemPos_UT, _] = utilsCSI.loadCSIfromMAT()

plotCSI.plot2DCSI(Hest_BS, centerFreq_BS, chanBW_BS, title="CSI from BS", doUnwrap=True)
plotCSI.plot2DCSI(Hest_UT, centerFreq_UT, chanBW_UT, title="CSI from UT", doUnwrap=True)

import pdb; pdb.set_trace()