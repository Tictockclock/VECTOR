'''
This script should take in processed CSI files (saved as a .mat)
    output from the `parseToMATLAB.py`

This will help visualize the semi-raw (processed) CSI

We work with a CSI matrix of size [AT AR S K], where:
- AT: Number of Transmit Antennas
- AR: Number of Receive Antennas
- S: Number of Subcarriers
- K: Number of CSI Snapshots
As well as the 'centerFreq' and 'chanBW', from which we can derive the wavelengths of 
    each subcarrier for later processing

For now, we're going to focus on homogeneous datasets
'''
import numpy as np
import matplotlib.pyplot as plt             # For graphing
from matplotlib.widgets import Slider       # For graphing

import scipy.io                             # To import .mat file
import os                                   # To retreive the file

################# USER INPUTS ##################################
# Data location (relative to location where this script is run in shell)
folder = ""#"bs/nav/csi_data/testing/in_room/basic_sets/at-boresight"
file   = "DT_110deg"

loadMat = True # True if we're loading .mat output from `parseToMATLAB.py`
if (loadMat):
    csiPath = os.path.join(os.getcwd(), folder, file + ".mat")
    loadedStruct = scipy.io.loadmat(csiPath)
    Hest        = loadedStruct['outputMatrix']  # CSI Itself [AT AR S K]
    centerFreq  = loadedStruct['centerFreq']    # Center/Carrier Frequency of Collected CSI (Hz)
    chanBW      = loadedStruct['chanBW']        # Channel Bandwidth (Hz)

doUnwrap = True # True if we want to unwrap phase. Leave false if want to keep raw

show2DPlot = True
show3DPlotAll = True # Plots all traces onto 3D plot
show3DPlotDif = False # This is a weird plot that should plot differences. I can't figure out how to interpret it, though.

#################################################################
# Variables of Interest:
Hest_shape = np.shape(Hest)
AT = Hest_shape[0]; AR = Hest_shape[1]; S = Hest_shape[2]; K = Hest_shape[3]

# Calculate the Frequency Axis:
subcSpacing = chanBW / S # Chan BW / # Subcarriers S
subcFreq    = np.linspace(centerFreq - chanBW/2, \
                          centerFreq + chanBW/2, \
                          S)
subcFreq = subcFreq.flatten() 

################ Initialize 2D Plot #################################
if show2DPlot:
    fig, ax = plt.subplots(figsize=(10, 6))
    plt.subplots_adjust(bottom=0.2)

    if(doUnwrap):
        lines = [ ax.plot(subcFreq, np.unwrap(np.angle(Hest[t, r, :, 0])), label=f"AT {t+1} - AR {r+1}")[0] for t in range(AT) for r in range(AR)]
    else:
        lines = [ ax.plot(subcFreq, np.angle(Hest[t, r, :, 0]), label=f"AT {t+1} - AR {r+1}")[0] for t in range(AT) for r in range(AR)]

    ax.set_title("CSI Phase vs Subcarriers")
    ax.set_xlabel("Frequency (MHz)")
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
    ax_slider_at_ar = plt.axes([0.2, 0.2, 0.6, 0.03])
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
    ax_slider_at_diff = plt.axes([0.2, 0.1, 0.6, 0.03])
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