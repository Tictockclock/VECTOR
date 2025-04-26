'''
Implements Round Trip Phase Method
https://ieeexplore.ieee.org/stamp/stamp.jsp?arnumber=10274424

Goran Gjorgievski, 2/18/25
'''

import numpy as np
import os
import sys
import scipy.interpolate

VECTOR_ROOT = os.getenv("VECTOR_ROOT")
sys.path.insert(0, VECTOR_ROOT) if (VECTOR_ROOT is not None) and (VECTOR_ROOT not in sys.path) else None
import setup
setup.loadModules()

# To import CSI from .mats
import bs.nav.processing.utilsCSI as utilsCSI
# To plot manipulated CSI
import bs.demo.graphing.plotCSI as plotCSI

print("Please select Filtered CSI")
csiPath_BS = "/home/dt12/Code/VECTOR/bs/nav/csi_data/testing/sim/ranging-tests/"

[Hest_BS, centerFreq_BS, chanBW_BS, subcFreq_BS, timestamps_BS, elemPos_BS, loadedStruct_BS, csiPath_BS] = utilsCSI.loadCSIfromMAT(csiPath=csiPath_BS)
subcFreq_BS = loadedStruct_BS['subcFreq'][:, 0]
print(f"CSI Loaded from Path: {csiPath_BS}")

# plotCSI.plot2DCSI(Hest_BS, subcFreq_BS, title="CSI from BS", doUnwrap=True)

# Global variables
c = 3e8 # speed of light
# fc = 2.447e9 # center frequency (initial guess, interpolate later)

# Assign the shape of Hest_BS to a variable
# This will output (AT, AR, S, K)
shape_BS = np.shape(Hest_BS)
print(f"Shape of Shape_BS: {shape_BS}")

# Initialize H_RT array to store the interpolated results
K_BS = shape_BS[3]  # Number of frames (K)
H_RT = np.zeros((K_BS,), dtype=complex)  # Initialize the H_RT array, with size (K, S)

# Interpolate over each frame
for k in range(K_BS):
    # Extract the subcarrier frequencies (x) and the CSI values (y) for frame k
    x = subcFreq_BS
    y = np.angle(Hest_BS[0, 0, :, k])  # Extracting CSI data for the first transmitting and receiving antenna pair

    # Perform linear interpolation using scipy's interp1d
    interpolate_function = scipy.interpolate.interp1d(x, y, kind='linear', fill_value="extrapolate")
    
    # Interpolate at the center frequency (Interpolated center frequency could be fixed or computed)
    center_freq_interpolated = np.mean(subcFreq_BS)  # Interpolated center frequency, or you could use another method
    H_RT[k] = np.exp(1j*interpolate_function(center_freq_interpolated))

# Debugging print for the shape of H_RT
print(f"Shape of H_RT: {H_RT.shape}")

# This will iterate through every frame and assign a value of H_RT to each frame at the specific freq
# H_RT = Hest_BS[0,1,centerFreqFrame_BS, :minK]

# Get the angle in radians for each frame in H_RT
H_RT_angle = np.angle(H_RT)

# Unwrap the phase to remove phase wrapping
H_RT_angle_unwrapped = np.unwrap(H_RT_angle)

print(f"Shape of H_RT_angle_unwrapped: {H_RT_angle_unwrapped.shape}")

# Each frame of H_RT applied to distance equation
d_rtp_array = -1/2 * (H_RT_angle_unwrapped / (2 * np.pi)) * (c / center_freq_interpolated)
d_rtp_array = d_rtp_array * -2 # previous only gives us half the distance (one-way)


# Plotting
import matplotlib.pyplot as plt
fig, ax = plt.subplots(figsize=(10, 6))
ax.plot(np.arange(K_BS), d_rtp_array)
plt.show()

#import pdb; pdb.set_trace()


#############################
# Assign a variable K to the number of frames in Hest_BS
# K_BS = shape_BS[3]
# minK = np.min([K_BS]) # This assigns both K_BS and K_UT to the minimum number of frames between the two

# # Extract the exact position in the array where the particular carrier frequency is 2447 MHz (This is our center freq)
# # Don't need -- already extracted. subcFreq_BS = utilsCSI.getSubcFreq(centerFreq_BS,chanBW_BS,shape_BS[2]

# # Pull out the frame associated with carrier frequency
# centerFreqFrame_BS = np.where(subcFreq_BS == 2.447e9)

# # This will iterate through every frame and assign a value of H_RT to each frame at the specific freq
# H_RT = Hest_BS[0,1,centerFreqFrame_BS,:minK]

# Unwrap the phase to remove phase wrapping
#H_RT_angle_unwrapped = np.unwrap(H_RT_angle)

#import pdb; pdb.set_traceq
# () # Breakpoint, as needed

#print(f"Shape of H_RT_angle_unwrapped: {H_RT_angle_unwrapped.shape}")



#import pdb; pdb.set_trace() #Breakpoint, as needed

# Output the complex number for 1 Transmit Antenna, 1 Received antenna, location test3, subcarrier 0
# Hest_BS[1,1,test3,0]

#H_RT = np.zeros((1, K))
#for k in range(minK):
#    H_RT[k] = Hest_BS[1,1,centerFreqFrame_BS,k] * Hest_UT[1,1,centerFreqFrame_UT,k]

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