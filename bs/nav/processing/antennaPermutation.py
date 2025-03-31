'''
#############################################################################
                Antenna Permutation Determination Script
#############################################################################

(Module)
Dimitry Melnikov, 3/17/25
'''

#################################################################################
############################# USER INPUTS #######################################
datasetFolder = "/mnt/c/Users/dmtrm/OneDrive/Schoolwork/(5) Senior Year/Senior Design/VECTOR/bs/nav/csi_data/testing/in_room/3-28-reftest/hackrf-1e3-VHT"  # OPTIONAL! Absolute path to CSI Dataset Folder
calFolder = "/mnt/c/Users/dmtrm/OneDrive/Schoolwork/(5) Senior Year/Senior Design/VECTOR/bs/nav/csi_data/testing/outside/2-25-25_Outside/CAL/"      # OPTIONAL! Absolute path to Calibration Folder

## ARRAY GEOMETRY
# Element Positions
elemSpacing = 0.079961058 # 0.65 Lambda (f = 2.437GHz)
elemPos = [ # Base Station Layout
    [0, -(1.5)*elemSpacing, 0], # [X, Y, Z] for Elem 0...
    [0, -(0.5)*elemSpacing, 0], # [X, Y, Z] for Elem 1...
    [0,  (0.5)*elemSpacing, 0],
    [0,  (1.5)*elemSpacing, 0],
]

# File location, as well as location relative to Array POV, facing out:
#              0             1               2              3
#           (AUX-2)  -    (AUX-1)   -     (MAIN-1)   -   (AUX-1)
# AUX-2 represents the AUX (2) antenna attached to NIC 2, => NICdata[1]['AUX'] = 0
# NIC 2 is represented by being placed second in `NICdata`
NICdata = [
    # Base Station Layout
    {   # NIC 1
        'file':  "21",#"NIC21", # Leave empty to select during dialogue.
        0:      1,  # AUX
        1:      2,  # MAIN
        'mac':  [], # MAC Address for the NIC. Leave empty -- will be autopopulated
    },
    {   # NIC 2
        'file': "22",#"NIC22", # Leave empty to select during dialogue.
        0:      0,  # AUX
        1:      3,  # MAIN
        'mac':  [], # MAC Address for the NIC. Leave empty -- will be autopopulated
    }
]

toDS = 0; fromDS = 0 # 0,0 for HackRF frames
macBS = [0x12, 0x34, 0xb4, 0x63, 0x0a, 0x5a] # (HackRF) MAC Address 'Dest' from Injected Frames
#macBS = [0x6c, 0x2f, 0x80, 0xdf, 0x37, 0xca] # (Alt-BS Setup) (NIC 23) MAC Address for reference-NIC
#macBS = [0x10, 0x5f, 0xad, 0xd6, 0xa3, 0x2b] # (Patch Setup) Base Station MAC Address
#macUT = [0xd8, 0x3a, 0xdd, 0xfb, 0x68, 0xe1] # (UT) User Terminal MAC Address
#macUT = [0x8c, 0xe9, 0xee, 0xd9, 0xa2, 0xe2] # (Laptop) User Terminal MAC Address (antenna we're tracking)
macUT = [0x00, 0x16, 0xea, 0x12, 0x34, 0x56] # (HackRF) MAC Address 'Src' from Injected Frames
#macREF= [0x6c, 0x2f, 0x80, 0xdf, 0x37, 0xca] # (NIC 23) MAC Address for reference-NIC (for Cal)
macREF = macUT #?

forceAT = 1   # 0 to disable (but will truncate to minimum), otherwise will only select CSI with the corresponding # Transmit Antennas
forceAR = 2    # 0 to disable (but will truncate to minimum), otherwise will only select CSI with the corresponding # Receive Antennas

# CABLE LENGTH
cablePts = [[2.436e9, -104.55],[2.447e9, -139.20],[2.458e9, -173.76]] # [Freq, Phase] (use to calculate group delay)

### DOA/MUSIC Options
windowSize = 2           # MUSIC Window (We do AR x K to get correlation)
thetaRange = [65, 115]   # Theta Range to Sample (MUSIC + Pseudospectra Plotting)

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

import bs.nav.doa.naiveMUSIC                            as naiveMUSIC       # For DOA estimation (double-check our work)
import bs.demo.graphing.plotDOA                         as plotDOA          # To plot DOA spectra
import bs.nav.processing.postprocessing.cableCalNICS    as cableCalNICS     # For some useful cal functions
import bs.nav.processing.filtersofGOR                   as filtersofGOR     # To import raw CSI from .csi files
import bs.nav.processing.utilsCSI                       as utilsCSI         # To import CSI from .mats
import bs.demo.graphing.plotCSI                         as plotCSI          # To plot manipulated CSI

# Ordinary Imports
import tkinter as tk                # For file selection
from tkinter import filedialog      # For file selection (GUI)

#################################################################################
######################## HELPER FUNCTIONS #######################################

def detectAcuteSwitch(Hest, timestamps):
    # Determine the array configuration given a target source at an acute angle from array parallel
    #
    #               (T)
    #               /
    #              /
    #             /
    #            /
    #   (0) (1) (2) (3)
    # (0 and 3 switch randomly) (1 and 2 switch randomly), assume no Phase Difference between cards on same NIC
    # Only one of four configurations possible:
    # 0 1 2 3,   3 1 2 0,   0 2 1 3,    3 2 1 0
    #
    # For each snapshot k, add or subtract based off of the array geometry:
    [AT, AR, S, K] = np.shape(Hest)
    
    phases = np.angle(Hest)
    #differences = np.zeros((1, AR, S, K), dtype=np.complex128)
    diff30 = wrapPhase(phases[0, 3, :, :] - phases[0, 0, :, :])#(phases[0, 3, :, :] - phases[0, 0, :, :]) % (2*np.pi) - (np.pi)  # 3 - 0 (Same NIC)
    diff21 = wrapPhase(phases[0, 2, :, :] - phases[0, 1, :, :])#(phases[0, 2, :, :] - phases[0, 1, :, :]) % (2*np.pi) - (np.pi)  # 2 - 1 (Same NIC)

    # switchAngleArray = np.tile([0, 0, 0, 0], (K, 1))
    # _s = S // 2 # Search through middle subcarrier
    # switchAngleArray[diff30[_s] < 0, 0], switchAngleArray[diff30[_s] < 0, 3] = 0, np.pi # Undo the pi subtraction
    # switchAngleArray[diff21[_s] < 0, 1], switchAngleArray[diff21[_s] < 0, 2] = 0, np.pi # Undo the pi subtraction

    # phaseCorrect = np.exp(1j * switchAngleArray[:, None, None, :])
    # Hest_switched = Hest * phaseCorrect.T

    # This one... depends on not shifting down by np.pi.
    # switchMatrix = np.tile([0, 1, 2, 3], (K, 1))
    # _s = S // 2 # Search along middle subcarrier (most accurate)
    # switchMatrix[diff30[_s] > np.pi, 0], switchMatrix[diff30[_s] > np.pi, 3] = 3, 0
    # switchMatrix[diff21[_s] > np.pi, 1], switchMatrix[diff21[_s] > np.pi, 2] = 2, 1
    # # Apply the switch:
    # # Prepare indices: transpose switchArray to shape (AR, K) and then expand dimensions
    # indices = switchArray.T[None, :, None, :]  # Now shape (1, AR, 1, K)
    # Hest_switched = np.take_along_axis(Hest, indices, axis=1) # Use take_along_axis to reorder the AR dimension per k

    _s = S // 2
    switchMatrix = np.ones_like(Hest)
    piShift = np.exp(-1j * np.pi)
    switchMatrix[0, 3, :, diff30[_s] < np.mean(diff30[_s])] = piShift
    switchMatrix[0, 2, :, diff21[_s] < np.mean(diff21[_s])] = piShift

    Hest_switched = Hest * switchMatrix

    phases = np.angle(Hest_switched)
    #differences = np.zeros((1, AR, S, K), dtype=np.complex128)
    #diff30 = (phases[0, 3, :, :] - phases[0, 0, :, :]) % (2*np.pi) - (np.pi)  # 3 - 0 (Same NIC)
    #diff21 = (phases[0, 2, :, :] - phases[0, 1, :, :]) % (2*np.pi) - (np.pi)  # 2 - 1 (Same NIC)
    """
    balls = np.zeros((1, 2, S, K), dtype=np.complex128)
    balls[0,0,:,:] = np.exp(1j*wrapPhase(phases[0, 3, :, :] - phases[0, 0, :, :]))
    balls[0,1,:,:] = np.exp(1j*wrapPhase(phases[0, 2, :, :] - phases[0, 1, :, :]))
    plotCSI.plot2DCSI_vsTime(balls, timestamps, doUnwrap=0, title="Unswitched del30, del21 (same NIC)")    

    balls2 = np.zeros((1, 2, S, K), dtype=np.complex128)
    balls2[0,0,:,:] = np.exp(1j*wrapPhase(phases[0, 3, :, :] - phases[0, 2, :, :]))
    balls2[0,1,:,:] = np.exp(1j*wrapPhase(phases[0, 1, :, :] - phases[0, 0, :, :]))
    plotCSI.plot2DCSI_vsTime(balls2, timestamps, doUnwrap=1, title="Unswitched del32, del10 (diff NICs - CFO)")

    balls3 = np.zeros((1, 2, S, K), dtype=np.complex128)
    balls3[0,0,:,:] = balls2[0,0,:,:] / balls2[0,1,:,:]
    balls3[0,1,:,:] = balls2[0,0,:,:] * balls2[0,1,:,:]
    plotCSI.plot2DCSI_vsTime(balls3, timestamps, doUnwrap=1, title="Unswitched del32-del10, del32+del10 (diff NICs - CFO)")
    
    plotCSI.plot2DCSI_vsTime(Hest_switched, timestamps, title="Unswitched Hest")
    """
    return (Hest_switched, switchMatrix)
    
    phasesC = np.angle(Hest_switched)
    diff30C = (phasesC[0, 3, :, :] - phasesC[0, 0, :, :]) % (2*np.pi) - (np.pi) # 3 - 0 (Same NIC)
    diff21C = (phasesC[0, 2, :, :] - phasesC[0, 1, :, :]) % (2*np.pi) - (np.pi) # 2 - 1 (Same NIC)
    diff32C = (phasesC[0, 3, :, :] - phasesC[0, 2, :, :]) % (2*np.pi) - (np.pi) # 3 - 2 (Different NIC)
    diff10C = (phasesC[0, 1, :, :] - phasesC[0, 0, :, :]) % (2*np.pi) - (np.pi) # 1 - 0 (Different NIC)

    #diff32D = (diff32C[:, 1:] - (diff32C[:, :-1] - diff21C[:, :-1])) % (2*np.pi) - (np.pi)
    #diff10D = (diff10C[:, 1:] + (diff10C[:, :-1] - diff21C[:, :-1])) % (2*np.pi) - (np.pi)
    
    import pdb; pdb.set_trace()
    # Exponential Moving Average (EMA) Filter
    #alpha = 0.9
    #estDiff_32 = np.zeros([S, K], dtype=np.complex128)
    #estDiff_32[:, 0] = (diff32C[:, 0] - diff21C[:, 0]) 
    #for k in range(1, K): estDiff_32[:, 0] = alpha * estDiff_32[:, k-1] + (1 - alpha) * (diff32C[:, k] - diff21C[:, k])

    koff = 0

    phasesD = np.copy(phasesC)
    #prevDiff_32 = (diff32C[:, :(0-koff)] - diff21C[:, :(0-koff)]) % (2*np.pi)
    #prevDiff_10 = -(diff10C[:, :(0-koff)] - diff21C[:, :(0-koff)]) % (2*np.pi)
    prevDiff_32 = (diff32C[:, :] - diff21C[:, :])
    prevDiff_10 = (diff21C[:, :] - diff10C[:, :])

    # Apply the correction to the corresponding indices
    phasesD[0, 3, :, (koff):] = (phasesC[0, 3, :, (koff):] - prevDiff_32)
    phasesD[0, 0, :, (koff):] = (phasesC[0, 0, :, (koff):] - prevDiff_10)

    diff30D = (phasesD[0, 3, :, :] - phasesD[0, 0, :, :]) % (2*np.pi)# - (np.pi) # 3 - 0 (Same NIC)
    diff21D = (phasesD[0, 2, :, :] - phasesD[0, 1, :, :]) % (2*np.pi)# - (np.pi) # 2 - 1 (Same NIC)
    diff32D = (phasesD[0, 3, :, :] - phasesD[0, 2, :, :]) % (2*np.pi)# - (np.pi) # 3 - 2 (Different NIC)
    diff10D = (phasesD[0, 1, :, :] - phasesD[0, 0, :, :]) % (2*np.pi)# - (np.pi) # 1 - 0 (Different NIC)

    balls = np.zeros([1, 4, S, K], dtype=np.complex128) 
    balls[0,0,:,:] = np.exp(1j*diff30D)
    balls[0,1,:,:] = np.exp(1j*diff21D)
    balls[0,2,:,:] = np.exp(1j*diff32D)
    balls[0,3,:,:] = np.exp(1j*diff10D)
    plotCSI.plot2DCSI_vsSnapshots(balls, doUnwrap=1)
    import pdb; pdb.set_trace()

    """
    for k in range(1, K): # Lose the first frame
        # Get previous offset from 32 to 21
        prevDiff_32 = diff32C[:,k-1] - diff21C[:,k-1]
        # Get previous offset from 10 to 21
        prevDiff_10 = -1*(diff10C[:,k-1] - diff21C[:,k-1])
        # Extract Average:
        avgF = (prevDiff_32 + prevDiff_10) / 2

        # Apply to 'current' phases to undo the offset
        phasesD[0, 3, :, k] = phasesC[0, 3, :, k] - avgF
        phasesD[0, 0, :, k] = phasesC[0, 0, :, k] - avgF
    """

    #### AHHHH

    switchArray = np.tile([0, 1, 2, 3], (K, 1)) # Search through middle subcarrier
    _s = S // 2
    switchArray[diff30[_s] < 0, 0], switchArray[diff30[_s] < 0, 3] = 3, 0
    switchArray[diff21[_s] < 0, 1], switchArray[diff21[_s] < 0, 2] = 2, 1

    diff30B = np.where(diff30 < 0, diff30 + np.pi, diff30)
    diff21B = np.where(diff21 < 0, diff21 + np.pi, diff21)

    diff32 = (phases[0, 3, :, :] - phases[0, 2, :, :]) % (2*np.pi) - (np.pi)  # 3 - 2 (Different NIC)
    diff10 = (phases[0, 1, :, :] - phases[0, 0, :, :]) % (2*np.pi) - (np.pi) # 1 - 0 (Different NIC)

    #diff32B = np.unwrap(diff32) - np.tile(np.mean(np.unwrap(diff21), axis=1), (K, 1)).T
    #diff10B = -1*np.unwrap(diff10) + np.tile(np.mean(np.unwrap(diff21), axis=1), (K, 1)).T
    
    diff32B = diff32 #- (diff30B)
    diff10B = -1*diff10 #+ diff21

    avgF = (diff32B + diff10B) / 2

    diff32B = diff32 - avgF
    diff10B = diff10 + avgF
    
    diff32B = np.where(diff32B < 0, diff32B + np.pi, diff32B) # TODO - Maybe shift by the mean here?
    #diff10B = np.where(diff10B < 0, diff10B + np.pi, diff10B)

    balls = np.zeros([1, 4, S, K], dtype=np.complex128) 
    balls[0,0,:,:] = np.exp(1j*diff30)
    balls[0,1,:,:] = np.exp(1j*diff21)
    balls[0,2,:,:] = np.exp(1j*diff32)
    balls[0,3,:,:] = np.exp(1j*diff10)
    plotCSI.plot2DCSI_vsSnapshots(balls, doUnwrap=0)
    import pdb; pdb.set_trace()
    #diff30 = diff30 - np.mean(diff30) # Switching between +/-. Shift down by the mean.
    #diff21 = diff21 - np.mean(diff21)

    
    # Apply the switch:
    # Prepare indices: transpose switchArray to shape (AR, K) and then expand dimensions
    indices = switchArray.T[None, :, None, :]  # Now shape (1, AR, 1, K)

    # Use take_along_axis to reorder the AR dimension per k
    Hest_switched = np.take_along_axis(Hest, indices, axis=1)

    #plotCSI.plot2DCSI_vsSnapshots(Hest, doUnwrap=1)
    #plotCSI.plot2DCSI_vsSnapshots(Hest_switched, doUnwrap=1)
    import pdb; pdb.set_trace()

    return (Hest_switched, switchArray)

#### CENTER FREQUENCY OFFSET ESTIMATION ####
def wrapPhase(phase):
    """Wrap phase to the interval [-pi, pi)."""
    return (phase + np.pi) % (2 * np.pi) - np.pi

class CFO_KF:
    def __init__(self, dt=1.0, phase_noise=0.1, freq_noise=1e-8, measurement_noise=0.16, initial_freq_var=1e10):
        self.dt = dt
        self.x = np.array([0.0, 0.0], dtype=float)  # [phase (unwrapped), frequency]
        self.P = np.diag([np.pi**2, initial_freq_var])  # Initial covariance
        self.R = np.array([[measurement_noise]])  # Measurement noise
        self.phase_noise = phase_noise  # Adjusted for multipath
        self.freq_noise = freq_noise    # Kept tiny for stable clocks

    def _compute_Q(self, dt):
        """Process noise scaled for stable freq and noisy phase."""
        q11 = (dt**3) / 3 * (self.phase_noise ** 2)  # Phase noise term
        q12 = (dt**2) / 2 * self.phase_noise * self.freq_noise
        q22 = dt * (self.freq_noise ** 2)             # Frequency noise term
        return np.array([[q11, q12], [q12, q22]])

    def predict(self, dt=None):
        if dt is not None:
            self.dt = dt
        self.F = np.array([[1, self.dt], [0, 1]])
        self.Q = self._compute_Q(self.dt)
        self.x = self.F @ self.x
        self.P = self.F @ self.P @ self.F.T + self.Q

    def update(self, z):
        predicted_phase = self.x[0]
        # Robust unwrapping: handle large phase jumps during gaps
        cycles = np.round((predicted_phase - z) / (2 * np.pi))
        measured_unwrapped = z + 2 * np.pi * cycles
        y = measured_unwrapped - predicted_phase  # Innovation
        
        H = np.array([[1, 0]])
        S = H @ self.P @ H.T + self.R
        K = self.P @ H.T @ np.linalg.inv(S)
        
        # Update state and covariance
        self.x += K.flatten() * y
        self.P = (np.eye(2) - K @ H) @ self.P

    def get_state(self):
        return wrapPhase(self.x[0]), self.x[1]

    def get_state_at(self, delta_t, include_noise=False):
        F_dt = np.array([[1, delta_t], [0, 1]])
        Q_dt = self._compute_Q(delta_t)
        x_pred = F_dt @ self.x
        x_pred[0] = wrapPhase(x_pred[0])
        P_pred = F_dt @ self.P @ F_dt.T + Q_dt
        return (x_pred[0], x_pred[1], P_pred) if include_noise else (x_pred[0], x_pred[1])
    

def testCFO_KF(true_phase = 1.2, true_freq = 7975, dt_init=0.0004, n_steps=30, dt_pause=1/25):
    # For instance:
    """
    true_phase = 1.2; true_freq = 2500*(2*np.pi); dt_init = 1/2550 #1/(true_freq/(2*np.pi))
    testCFO_KF(true_phase, true_freq, dt_init)
    print(f"True Phase (rad): {true_phase}, True Freq (Hz): {true_freq*1/(2*np.pi)}, dt (s): {dt_init}, fs (Hz)= {1/dt_init}")
    """
    # Simulate a true process. Phase in rad, Freq Offset in rad/s
    #ckf = CFO_KF(dt=dt_init)#, dt_max=dt_init * 1.1)# In the test case:
    ckf = CFO_KF(
        dt=dt_init, 
        process_noise_scale=1e5,  # Adjusted for large gaps
        measurement_noise=0.16,
        initial_freq_var=1e10
    )

    dt_pause = dt_pause if dt_pause is not None else 1/25 # Pauses for 1/25Hz
    
    measurements = []
    true_phases = []
    time_stamps = [0] # Start time at 123456 nanoseconds

    np.random.seed(0) # For reproducibility

    # Simulate measurements with variable dt values
    for k in range(n_steps):
        if (k % 9) == 0:
            #dt = np.random.uniform(dt_pause - dt_pause/100, dt_pause + dt_pause/100)
            dt = dt_pause
        else:
            #dt = np.random.uniform(dt_init - dt_init/100, dt_init + dt_init/100)
            dt = dt_init

        time_stamps.append(time_stamps[-1] + dt)
        true_phase += true_freq * dt
        true_phase = wrapPhase(true_phase)
        # Simulate a measurement with some noise
        meas = wrapPhase(true_phase + np.random.normal(0, 0.4))
        measurements.append(meas)
        true_phases.append(true_phase)

    est_phases = []
    est_freqs = []

    for k, (z, dt) in enumerate(zip(measurements, np.diff(time_stamps))):
        ckf.predict(dt=dt)
        ckf.update(z)
        est_phase, est_freq = ckf.get_state()
        est_phases.append(est_phase)
        est_freqs.append(est_freq)
        print(f"Step {k}: dt = {dt:.2f}, measurement = {z:.2f} rad, est phase = {est_phase:.2f} rad, estimated freq = {est_freq:.3f} rad/s")

    # Plot true vs. estimated phase (only at the update times)
    import matplotlib.pyplot as plt
    plt.figure(figsize=(10, 4))
    plt.plot(time_stamps[1:], (true_phases), label='True Phase', marker='o')
    plt.plot(time_stamps[1:], (est_phases), label='Estimated Phase', marker='x')
    plt.xlabel("Time (s)")
    plt.ylabel("Phase (rad)")
    plt.legend()
    plt.title("Circular Kalman Filter Phase Tracking")
    plt.show()
    
    # Plot estimated frequency offset over time
    plt.figure(figsize=(10, 4))
    plt.plot(time_stamps[1:], est_freqs, label='Estimated Frequency Offset', marker='x')
    plt.xlabel("Time (s)")
    plt.ylabel("Frequency Offset (rad/s)")
    plt.legend()
    plt.title("Estimated Frequency Offset")
    plt.show()

    import pdb; pdb.set_trace()

def getCFO10(deswitchedMatrix, _s):
    phases = np.angle(deswitchedMatrix)
    return (phases[0, 1, _s, :] - phases[0, 0, _s, :])

def getCFO32(deswitchedMatrix, _s):
    phases = np.angle(deswitchedMatrix)
    return (phases[0, 3, _s, :] - phases[0, 2, _s, :])


def pushToKF(deswitchedMatrix, timestamps, ckf=None, lasttimestamp=-1):
    # Push all frames in the `deswitchedMatrix`, one frame at a time, to the Circular Kalman Filter
    # Assume input array is already sorted by timestamp
    # Assume timestamps in seconds
    # Assume K = len(timestamps) = np.shape(deswitchedMatrix)[3]
    if ckf is None:
        print("Instantiating Kalman Filter...")
        ckf = CFO_KF(
            dt=timestamps[1] - timestamps[0],
            phase_noise=1e5,      # Moderate phase noise (multipath-like)
            freq_noise=1e-5,      # Tiny frequency noise (stable clock)
            measurement_noise=0.16,  # 0.4^2 = 0.16
            initial_freq_var=1e10    # Allow rapid initial convergence
        )

    if np.max(timestamps) < lasttimestamp:
        print(f"WARNING! INPUT TIMESTAMPS AREN'T CURRENT!")
        print(f"MOST RECENT INPUT: {np.max(timestamps)}ns VS MOST RECENT UPDATE: {lasttimestamp}")
        print("Doing nothing...")
        return ckf, lasttimestamp

    [AT, AR, S, K] = np.shape(deswitchedMatrix)

    est_phases = []

    # Push the frames in, one at a time
    # First timestamp that's bigger than the 'last timestamp'
    lowestIndex = np.min(np.argwhere(np.array(timestamps) > lasttimestamp))
    _s = S // 2 # Middle Subcarrier. Use as discriminator -- should be the most stable.

    # Define commonly used functions:
    def updateKF(deswitchedMatrix, dt, k):
        ckf.predict(dt)
        z = wrapPhase(getCFO10(deswitchedMatrix, _s)[k])
        ckf.update(z)
        return ckf.get_state()

    if lasttimestamp == -1:
        # Assume ideal sampling time
        dt_init = 1/2550
    else:
        # Get distance from lasttimestamp to current
        dt_init = timestamps[lowestIndex] - lasttimestamp

    # Push the first frame
    est_phase, _ = updateKF(deswitchedMatrix, dt_init, lowestIndex)
    est_phases.append(est_phase)

    if K > 1:
        # Handle the rest of the frames
        for k in range(lowestIndex+1, K):
            dt = timestamps[k] - timestamps[k-1]
            est_phase, _ = updateKF(deswitchedMatrix, dt, k)
            est_phases.append(est_phase)

    lasttimestamp = timestamps[-1]

    # Plot the estimates:
    import matplotlib.pyplot as plt
    plt.figure(figsize=(10, 4))
    _time = np.array(timestamps[lowestIndex+1:]) - timestamps[lowestIndex] 
    plt.plot(_time, (wrapPhase(getCFO10(deswitchedMatrix, _s)[lowestIndex+1:])), label='Measured Phase', marker='o')
    plt.plot(_time, (wrapPhase(np.array(est_phases[1:]))), label='Estimated Phase', marker='x')
    plt.xlabel("Time (s)")
    plt.ylabel("Phase (rad)")
    plt.legend()
    plt.title("Circular Kalman Filter Phase Tracking")
    plt.show(block=False)

    return ckf, lasttimestamp # Return KF reference + most recent timestamp for the Kalman Filter

def testKF_REAL(deswitchedMatrix, timestamps):
    [AT, AR, S, K] = np.shape(deswitchedMatrix)
    calMatrix = deswitchedMatrix[:,:,:,:K-100]
    calTimestamps = timestamps[:K-100]

    realMatrix = deswitchedMatrix[:,:,:,K-100:-1]
    realTimestamps = timestamps[K-100:-1]

    # 'Training' Phase
    [ckf, lasttimestamp] = pushToKF(calMatrix[:,:,:,:K-200], calTimestamps[:K-200]) # 'one burst'
    [ckf, lasttimestamp] = pushToKF(calMatrix[:,:,:,:], calTimestamps[:], ckf, lasttimestamp) # later, 'future' burst.

    # 'Tracking' Phase
    estPhase = []
    for k in range(0, len(realTimestamps)):
        dt = realTimestamps[k] - lasttimestamp
        phase_pred, freq_pred, P_pred = ckf.get_state_at(dt, include_noise=True)
        estPhase.append(phase_pred)  # Get current state

    # Plot the estimates to validate:
    import matplotlib.pyplot as plt
    plt.figure(figsize=(10, 4))
    _time = np.array(realTimestamps) - realTimestamps[0]
    plt.plot(_time, wrapPhase(getCFO10(realMatrix, S//2)), label='Measured Phase', marker='o')
    plt.plot(_time, wrapPhase(np.array(estPhase)), label='Estimated Phase', marker='x')
    plt.xlabel("Time (s)")
    plt.ylabel("Phase (rad)")
    plt.legend()
    plt.title("Circular Kalman Filter Phase Tracking")
    plt.show(block=False)
    
    import pdb; pdb.set_trace()


def predictCoherenceMatrix(deswitchedMatrix, refTimestamps, switchMatrix, currTime):
    # For the given timestamp, return a modified matrix, as well as the calibration matrix to 'undo' 
    # the bulk offset from one NIC to the next, making the resulting CSI coherent.
    return 0 # TODO

if __name__ == "__main__":
    # Calculate Cable Calibration Coefficients
    """
    print("Generating Calibration Matrix...")
    [calMatrix, calSubcFreq] = cableCalNICS.generateCalOffset(NICdata, calFolder,
                      toDS, fromDS, macBS, macREF,
                      cablePts,
                      saveCalToMat=False)
    """
    #true_phase = 1.40; true_freq = -7975; dt_init = 0.0004
    #testCFO_KF(true_phase, true_freq, dt_init)
    #print(f"True Phase (rad): {true_phase}, True Freq (Hz): {true_freq*1/(2*np.pi)}, dt (s): {dt_init}, fs (Hz)= {1/dt_init}")
    #import pdb; pdb.set_trace()
    # Load CSI, Parse CSI
    numNICS = len(NICdata) # Number of CSI files we're parsing (minus the saving)

    print("Loading CSI from raw .csi files:")
    [loadedCSI, NICdata, csiPath] = filtersofGOR.loadMultiNICS(NICdata, datasetFolder)

    print("Combining CSI by aligning MPDU...")
    combinedCSI = filtersofGOR.alignMPDU(numNICS, loadedCSI)

    print("Filtering frames by Source/Destination MAC Addresses...")
    macAlignedCSI = filtersofGOR.filterSrcDest(combinedCSI, toDS, fromDS, macBS, macREF)

    filtersofGOR.statsForcedParams(macAlignedCSI)

    print(f"Discarding CSI not matching parameters: AT: {forceAT}, AR: {forceAR}...")
    forcedCSI = filtersofGOR.filterForcedParams(macAlignedCSI, forceAT, forceAR)
    # Extract to Usable Hest Matrix
    print("Converting to usable matrix...")
    [parsedMatrix, centerFreq_arr, chanBW_arr, subcFreq_arr, timestamps] = filtersofGOR.convertToUsableMatrix(forcedCSI, NICdata)

    # Detect Switches and Apply them
    [deswitchedMatrix, switchMatrix] = detectAcuteSwitch(parsedMatrix, timestamps)
    
    #[ckf, lasttimestamp] = pushToKF(deswitchedMatrix, timestamps)
    testKF_REAL(deswitchedMatrix, timestamps)
    import pdb; pdb.set_trace()
    #[coherentMatrix, coherenceMatrix] = predictCoherentFrame(deswitchedMatrix, )
    
    """
    print("Applying Calibration Matrix to Parsed Matrix...")
    [correctedMatrix, subcFreq] = cableCalNICS.applyCalOffset(calMatrix, calSubcFreq, deswitchedMatrix, subcFreq_arr[0])

    # Perform DOA Estimation
    print("Estimating Direction of Arrival via MUSIC Algorithm...")
    doaMUSIC = naiveMUSIC.getMUSICSpectrum(correctedMatrix[:, :, :, 0:100], subcFreq, elemPos, windowSize, thetaRange)

    # Plot MUSIC Pseudospectra
    plotDOA.plotDOA_vsSubcarrier(doaMUSIC, thetaRange=thetaRange,
                                    title="MUSIC DOA vs. Subcarrier")
    plotDOA.plotDOA_vsSnapshots(doaMUSIC, thetaRange=thetaRange, windowSize=windowSize,
                                    title="MUSIC DOA vs. Snapshots")
    """
    import pdb; pdb.set_trace()