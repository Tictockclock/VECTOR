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



''' 
Pseudo Code

What do we want?
- multiply CSI from BS with CSI from UT, extract the angle using np.angle(), then execute the equation d_rtp = -1/2 * angle/2*pi * c/fc
    - c = speed of light = 3*10^8 m/s
    - fc = carrier frequency = 2412 MHz

H_RT(t2,t4) = H_AP(0,t2)*H_STA(0,t4)
- H_AP(0,t2) --> CSI from Base Station --> toDS == 0 and fromDS == 1
- H_STA(0,t4) --> CSI from User Terminal --> toDS == 1 and fromDS == 0 
with toDS meaning to the Base Station and fromDS meaning from the Base Station

How do we get this information?
- we must multiply each value of each respective frame with one another at the center frequency
    - for example, frame 1 of H_AP must be multiplied by frame 1 of H_STA at the specified center frequency
    - this can be done with two separate for loops, where we do the following:
        - specify the desired center frequency
        - iterate through each frame of H_AP, extract the value, and store it in an array
        - iterate through each frame of H_STA, extract the value, and store it in an array
        - we can call these arrays "H_AP extracted values" and "H_STA extracted values"
    - run another for loop, where we multiply each respective index/element of both arrays with each other, and store these in a new array
        - we can call this array "H_RT array"
    - now, run a for loop with the d_rtp equation, where we use np.angle() for each respective element in the array.
      we store this in a final array, called "d_rtp_array"
    - from here, we can plot the results of "d_rtp_array"


'''

'''

numpy is imported. do we need to import matplotlib.pyplot?

c = 3*10**8 # speed of light in m/s
fc = 2412 * 10**6 # carrier frequency in Hz (2142 MHz)


frames = ? # number of frames
# ^ need help with this

# Iterate through each frame to extract and multiply the CSI values
for i in range(frames):
   
    H_AP_extracted_values[i] = H_AP[i]
    H_STA_extracted_values[i] = H_STA[i]
    
    # Multiply the CSI values for the current frame
    H_RT[i] = H_AP_extracted[i] * H_STA_extracted[i]

# Iterate over H_RT array to compute the angle for each value
for i in range(frames):
    # Calculate the angle of the product for the current frame
    H_RT_angle = np.angle(H_RT[i])
    
#Calculate d_rtp for each angle 
    d_rtp_array[i] = -1/2 * (H_RT_angle / (2 * np.pi)) * (c / fc)


'''