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

[Hest_BS, centerFreq_BS, chanBW_BS, elemPos_BS, _, csiPath_BS] = utilsCSI.loadCSIfromMAT()
[Hest_UT, centerFreq_UT, chanBW_UT, elemPos_UT, _, csiPath_UT] = utilsCSI.loadCSIfromMAT()

plotCSI.plot2DCSI(Hest_BS, centerFreq_BS, chanBW_BS, title="CSI from BS", doUnwrap=True)
plotCSI.plot2DCSI(Hest_UT, centerFreq_UT, chanBW_UT, title="CSI from UT", doUnwrap=True)



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
        - we can call these arrays "H_AP_extracted_values" and "H_STA_extracted_values"
    - run another for loop, where we multiply each respective index/element of both arrays with each other, and store these in a new array
        - we can call this array "H_RT_array"
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
    H_RT_angle = np.angle(H_RT[i])*180/pi # Convert from rad to degrees
    
# Calculate d_rtp for each angle 
    d_rtp_array[i] = -1/2 * (H_RT_angle / (2 * np.pi)) * (c / fc)


'''

'''
- first step is to assign the shape of Hest_BS to a variable with np.shape(Hest_BS)
    - test = np.shape(Hest_BS)
- we can assign a variable K to the number of frames in Hest_BS
    - for example, K = test[3]
- now, we need to extract the exact position in the array where the particular carrier frequency is 2412 MHz
    - first, define test2 = utilsCSI.getSubcFreq(centerFreq_BS,ChanBW_BS,S) where S is the number of subcarriers defined in Hest_BS
        - how do we automate S? would it just be test[2]?
    - now, use command command np.where(test2 == 2.412e9) to pull out the frame associated with 2412 MHz
        - test3 = np.where(test2 == 2.412e9)
- run Hest_BS[1,1,test3,0] to output the complex number
    - similarly, we can just run H_RT_angle = np.angle(Hest_BS[1,1,test3,0])*180/np.pi to output the answer in degrees
- lastly, plug H_RT_angle into equation d_rtp_array[i] = -1/2 * (H_RT_angle / (2 * np.pi)) * (c / fc)

'''

# Global variables
c = 3.8e8 # speed of light
fc = 2.412e9 # center frequency 2412 MHz

# Assign the shape of Hest_BS and Hest_UT to a variable
# This will output (AT, AR, S, K)
shape_BS = np.shape(Hest_BS)
shape_UT = np.shape(Hest_UT)

# Assign a variable K to the number of frames in Hest_BS
K_BS = shape_BS[3]
K_UT = shape_UT[3]
minK = np.min([K_BS, K_UT]) # This assigns both K_BS and K_UT to the minimum number of frames between the two 

# Extract the exact position in the array where the particular carrier frequency is 2412 MHz (This is our center freq)
subcFreq_BS = utilsCSI.getSubcFreq(centerFreq_BS,chanBW_BS,shape_BS[2])
subcFreq_UT = utilsCSI.getSubcFreq(centerFreq_UT,chanBW_UT,shape_UT[2])

# Pull out the frame associated with 2412 MHz
centerFreqFrame_BS = np.where(subcFreq_BS == 2.412e9)
centerFreqFrame_UT = np.where(subcFreq_UT == 2.412e9)

# This will iterate through every frame and assign a value of H_RT to each frame at the specific freq
H_RT = Hest_BS[0,1,centerFreqFrame_BS,:minK] * Hest_UT[0,1,centerFreqFrame_UT,:minK]

# Get the angle in radians for each frame in H_RT
H_RT_angle = np.angle(H_RT)

# Each frame of H_RT applied to distance equation
d_rtp_array = -1/2 * (H_RT_angle / (2 * np.pi)) * (c / fc)

# Plotting
import matplotlib.pyplot as plt
fig, ax = plt.subplots(figsize=(10, 6))
ax.plot(np.arange(minK), (d_rtp_array[0, 0, :]))
plt.show()

import pdb; pdb.set_trace()

# Output the complex number for 1 Transmit Antenna, 1 Received antenna, location test3, subcarrier 0
# Hest_BS[1,1,test3,0]

#H_RT = np.zeros((1, K))
#for k in range(minK):
#    H_RT[k] = Hest_BS[1,1,centerFreqFrame_BS,k] * Hest_UT[1,1,centerFreqFrame_UT,k]