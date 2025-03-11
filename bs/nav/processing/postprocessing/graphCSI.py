'''
This script should take in processed CSI files (saved as a .mat)
    output from the `parseToMATLAB.py`

This will help visualize the semi-raw (processed) CSI

(I recommend only doing one plot at a time)

We work with a CSI matrix of size [AT AR S K], where:
- AT: Number of Transmit Antennas
- AR: Number of Receive Antennas
- S: Number of Subcarriers
- K: Number of CSI Snapshots
As well as the 'centerFreq' and 'chanBW', from which we can derive the wavelengths of 
    each subcarrier for later processing

For now, we're going to focus on homogeneous datasets

More info about CSI Structure:
https://ps.zpj.io/matlab.html#structures-of-the-picoscenes-tx-and-rx-frames
'''
import numpy as np
import matplotlib.pyplot as plt             # For graphing
from matplotlib.widgets import Slider       # For graphing


import sys                                  # For Picoscenes library, among others
import scipy.io                             # To import .mat file
import os                                   # To retreive the file

################# USER INPUTS ##################################
# Data location (relative to location where this script is run in shell)
#folder = "bs/nav/csi_data/testing/outside/2-25-25_Outside/CAL"
#file   = "M21"
folder = "bs/nav/csi_data/testing/in_room/2-24-25/1_BS_LAPTOP_ROOM_90deg_4ft_BS/CAL"
file   = "CAL_M22"

loadMat = False # True if we're loading .mat output from `parseToMATLAB.py`
if (loadMat):
    csiPath = os.path.join(os.getcwd(), folder, file + ".mat")
    loadedStruct = scipy.io.loadmat(csiPath)
    Hest        = loadedStruct['outputMatrix']  # CSI Itself [AT AR S K]
    centerFreq  = loadedStruct['centerFreq']    # Center/Carrier Frequency of Collected CSI (Hz)
    chanBW      = loadedStruct['chanBW']        # Channel Bandwidth (Hz)
else:
    sys.path.append('/home/dt12/Code/VECTOR/bs/bs-venv/PicoscenesToolbox') #make sure that python can find the .so file
    from picoscenes import Picoscenes   # To process the CSI
    csiPath = os.path.join(os.getcwd(), folder, file + ".csi")
    currCSI = Picoscenes(csiPath)

    print("WARNING! CSI PARSING NOT IMPLEMENTED HERE. THIS WILL LIKELY NOT WORK!")
    # TODO - Implement some CSI Parsing here

doUnwrap = True # True if we want to unwrap phase. Leave false if want to keep raw

showMACPlot = True    # Plots end digit in Standard MAC Header Frames, associated with the TX/RX MAC Addresses
show2DPlot = False    # 2D Plot of CSI
show3DPlotAll = False # Plots all traces onto 3D plot
show3DPlotDif = False # This is a weird plot that should plot differences. I can't figure out how to interpret it, though.

#################################################################
# Variables of Interest:
if 'Hest' in locals():
    # Only do if we have Hest loaded
    Hest_shape = np.shape(Hest)
    AT = Hest_shape[0]; AR = Hest_shape[1]; S = Hest_shape[2]; K = Hest_shape[3]

    # Calculate the Frequency Axis:
    subcSpacing = chanBW / S # Chan BW / # Subcarriers S
    subcFreq    = np.linspace(centerFreq - chanBW/2, \
                            centerFreq + chanBW/2, \
                            S)
    subcFreq = subcFreq.flatten() 
else:
    print("WARNING! CSI (`Hest`) NOT LOADED!")

################ Initialize MAC Plot ################################
if showMACPlot:
    # Assumes access to the raw CSI file, parsed by Picoscenes.
    # https://mrncciew.com/2014/09/28/cwap-mac-headeraddresses/
    timestamps = []                     # PPDU-associated timestamp
    addr1 = []; addr2 = []; addr3 = []  # Contents of MAC Header
    tofromDS = []                       # Combination of To/From DS
    for i in range(currCSI.count):
        toDS = currCSI.raw[i]['StandardHeader']['ControlField']['ToDS'];
        fromDS = currCSI.raw[i]['StandardHeader']['ControlField']['FromDS'];

        if toDS == 0 and fromDS == 0:
            # Local Traffic
            tofromDS.append(0)
        elif toDS == 0 and fromDS == 1:
            # From Base Station / AP to User Terminal / STA
            tofromDS.append(1)
        elif toDS == 1 and fromDS == 0:
            # From User Terminal / STA to Base Station / AP
            tofromDS.append(2)
        else:
            # Bigger Network Traffic (Unlikely)
            tofromDS.append(3) 

        timestamps.append(currCSI.raw[i]['RxSBasic']['timestamp'])

        addr1.append(currCSI.raw[i]['StandardHeader']['Addr1'])
        addr2.append(currCSI.raw[i]['StandardHeader']['Addr2'])
        addr3.append(currCSI.raw[i]['StandardHeader']['Addr3'])

    # Cast to Numpy Array for ease of use. Normalize to first timestamp.
    timestamps = np.array(timestamps)
    timestamps = timestamps - timestamps[0]
    
    addr1 = np.array(addr1); addr2 = np.array(addr2); addr3 = np.array(addr3)
    tofromDS = np.array(tofromDS)

    titles = [f"End Byte of MAC Header Addr1/2/3 Frames - ToDS=0, FromDS=0",
              f"End Byte of MAC Header Addr1/2/3 Frames - ToDS=0, FromDS=1",
              f"End Byte of MAC Header Addr1/2/3 Frames - ToDS=1, FromDS=0",
              f"End Byte of MAC Header Addr1/2/3 Frames - ToDS=1, FromDS=1"]
    
    fig, axs = plt.subplots(2, 2)

    for i in range(len(titles)):
        # Apply mask to plot only what we need:
        dsMASK = tofromDS == i # Wherever the combo is equal to 0, 1, 2, or 3...
        time_tmp = timestamps[dsMASK] / 1e5 # Mask + Convert to 0.1s
        addr1_tmp= addr1[dsMASK]
        addr2_tmp= addr2[dsMASK]
        addr3_tmp= addr3[dsMASK]

        row = i//2  # Integer division to get the row
        col = i%2   # The remainder goes in to the column
        curr_ax = axs[row][col]
        
        curr_ax.scatter(time_tmp, addr1_tmp[:, 5], label='Addr1')
        curr_ax.scatter(time_tmp, addr2_tmp[:, 5], label='Addr2')
        curr_ax.scatter(time_tmp, addr3_tmp[:, 5], label='Addr3')
        curr_ax.set_title(titles[i])
        curr_ax.set_xlabel("Time Since First Timestamp (0.1s)")
        curr_ax.set_ylabel("Value")
        curr_ax.legend()
        curr_ax.grid(True)

    plt.show()

################ Initialize 2D Plot #################################
if show2DPlot:
    fig, ax = plt.subplots(figsize=(10, 6))
    plt.subplots_adjust(bottom=0.2)

    if(doUnwrap):
        lines = [ ax.plot(subcFreq, np.unwrap(np.angle(Hest[t, r, :, 0])), label=f"AT {t+1} - AR {r+1}")[0] for t in range(AT) for r in range(AR)]
    else:
        lines = [ ax.plot(subcFreq, np.angle(Hest[t, r, :, 0]), label=f"AT {t+1} - AR {r+1}")[0] for t in range(AT) for r in range(AR)]

    ax.set_title("CSI Phase vs Subcarriers")
    ax.set_xlabel("Frequency (Hz)")
    ax.set_ylabel("Phase (radians)")
    ax.legend()
    ax.grid()

    # Slider
    ax_slider = plt.axes([0.2, 0.05, 0.6, 0.03])
    slider = Slider(ax_slider, "Snapshot (K)", 0, K - 1, valinit=0, valstep=1)

    # Update function (for slider)
    def update(val):
        k = int(slider.val)
        for t in range(AT):
            for r in range(AR):
                phase = np.angle(Hest[t, r, :, k])

                if(doUnwrap):
                    phase = np.unwrap(phase)

                lines[t * AR + r].set_ydata(phase)
        fig.canvas.draw_idle()

    slider.on_changed(update)

################ Initialize 3D Plot #################################
if show3DPlotAll:    
    # 3D Plot for Phase vs Subcarriers vs Snapshots
    ax2 = plt.figure().add_subplot(projection='3d')
    
    # Slider for AT-AR pair selection
    ax_slider_at_ar = plt.axes([0.2, 0.05, 0.6, 0.03])
    slider_at_ar = Slider(ax_slider_at_ar, "AT-AR Pair", 0, AT * AR - 1, valinit=0, valstep=1)
    
    # Update function for 3D plot (AT-AR Pair)
    def update_at_ar(val):
        idx = int(slider_at_ar.val)
        t, r = divmod(idx, AR)  # Map slider index to (t, r) pair
        phase_data = np.angle(Hest[t, r, :, :])  # Get phase data for all subcarriers and snapshots
        if doUnwrap:
            phase_data = np.unwrap(phase_data, axis=1)  # Unwrap phase along the snapshots axis (axis=1)

        # Create meshgrid for subcarriers (X) and snapshots (Y)
        X, Y = np.meshgrid(subcFreq, np.arange(K))  # Create meshgrid for subcarriers and snapshots
        
        # Ensure X, Y, and Z are compatible for surface plotting
        Z_data = phase_data  # Phase data for all subcarriers and snapshots

        # Reshape Z_data to be a 2D array of shape (S, K) for surface plotting
        Z_data = Z_data.T  # Transpose so that it matches the dimensions (subcarriers, snapshots)

        # Clear previous 3D plot and plot new one for selected AT-AR pair
        ax2.cla()
        ax2.plot_surface(X, Y, Z_data, cmap='viridis')

        ax2.set_title(f"CSI Phase vs Subcarriers vs Snapshots (AT {t+1} - AR {r+1})")
        ax2.set_xlabel("Subcarriers")
        ax2.set_ylabel("Snapshots (K)")
        ax2.set_zlabel("Phase (radians)")
        fig.canvas.draw_idle()

    slider_at_ar.on_changed(update_at_ar)
    update_at_ar(0)  # Initialize the plot with the first AT-AR pair

################ Initialize 3D Difference Plot #################################
if show3DPlotDif: 
    # 3D Plot for Phase vs Subcarriers vs Snapshots (Difference)
    ax3 = plt.figure().add_subplot(projection='3d')

    # Slider for AT pair differences
    ax_slider_at_diff = plt.axes([0.2, 0.05, 0.6, 0.03])
    slider_at_diff = Slider(ax_slider_at_diff, "AT Pair Difference", 0, (AT - 1) * AR, valinit=0, valstep=1)

    # Update function for 3D plot (AT Pair Differences)
    def update_at_diff(val):
        idx = int(slider_at_diff.val)
        t, r = divmod(idx, AR)  # Map slider index to (t, r) pair for AT pair difference
        phase_diff_data = np.angle(Hest[t+1, r, :, :] - Hest[t, r, :, :])  # Difference between AT[t+1, r] and AT[t, r]
        if doUnwrap:
            phase_diff_data = np.unwrap(phase_diff_data, axis=1)  # Unwrap phase along the snapshots axis (axis=1)

        # Create meshgrid for subcarriers (X) and snapshots (Y)
        X, Y = np.meshgrid(subcFreq, np.arange(K))  # Create meshgrid for subcarriers and snapshots
        
        # Ensure X, Y, and Z are compatible for surface plotting
        Z_data = phase_diff_data  # Phase difference data for all subcarriers and snapshots

        # Reshape Z_data to be a 2D array of shape (S, K) for surface plotting
        Z_data = Z_data.T  # Transpose so that it matches the dimensions (subcarriers, snapshots)

        # Clear previous 3D plot and plot new one for selected AT pair differences
        ax3.cla()
        ax3.plot_surface(X, Y, Z_data, cmap='viridis')

        ax3.set_title(f"CSI Phase Difference (AT {t+1} - AT {t+2}) - AR {r+1}")
        ax3.set_xlabel("Subcarriers")
        ax3.set_ylabel("Snapshots (K)")
        ax3.set_zlabel("Phase Difference (radians)")
        fig.canvas.draw_idle()

    slider_at_diff.on_changed(update_at_diff)
    update_at_diff(0)  # Initialize the plot with the first AT pair difference

#####################################################################
# Show plot
plt.show()   