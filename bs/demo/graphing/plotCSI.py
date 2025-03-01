'''
Plots CSI Traces

We expect an CSI matrix of size [AT AR S K], where:
- AT: Number of Transmit Antennas
- AR: Number of Receive Antennas
- S: Number of Subcarriers
- K: Number of CSI Snapshots
As well as the 'centerFreq' and 'chanBW', from which we can derive the wavelengths of 
    each subcarrier for later processing

(Module)
Dimitry Melnikov 2/17/25
'''
# Regular Imports
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider

# Import VECTOR Libraries
import os; import sys
VECTOR_ROOT = os.getenv("VECTOR_ROOT")
print("WARNING! VECTOR_ROOT NOT DEFINED! RUN THIS FROM VECTOR ROOT DIRECTORY: `export VECTOR_ROOT=$(pwd)`") if (VECTOR_ROOT is None) else None
sys.path.insert(0, VECTOR_ROOT) if (VECTOR_ROOT is not None) and (VECTOR_ROOT not in sys.path) else None
import setup; setup.loadModules()

import bs.nav.processing.utilsCSI as utilsCSI

####### FILES #####################################################################

def plot2DCSI(Hest, centerFreq, chanBW, \
              title="CSI Phase vs. Subcarriers", doUnwrap=True):
    """ Plots CSI Phase in 2D Plot with Slider over Snapshots

    Args:
        Hest (Numpy Matrix): Size [AT, AR, S, K], for [Num TX Ants, Num RX Ants, Num Subcarriers, Num Snapshots]
        centerFreq (integer): Center/Carrier Frequency (Hz)
        chanBW (integer): Channel Bandwidth (Hz)
        doUnwrap (bool, optional): Unwrap Phase. Defaults to True.
    """
    fig, ax = plt.subplots(figsize=(10, 6))
    plt.subplots_adjust(bottom=0.2)

    # Extract Subcarrier Frequencies & Other Constants
    if (len(np.shape(Hest)) == 3):
        # Single [AT AR S] frame, need to stretch it to plot it.
        [AT, AR, S] = np.shape(Hest); K = 1
        pltHest = np.zeros((AT, AR, S, K), dtype=np.complex128)
        pltHest[:, :, :, 0] = Hest
        Hest = pltHest # Override

    else:
        [AT, AR, S, K] = np.shape(Hest)
    
    subcFreq = utilsCSI.getSubcFreq(centerFreq, chanBW, S)

    # Set up colors
    # Colormap for each AT
    colormaps = [plt.cm.Blues, plt.cm.Oranges, plt.cm.Greens, plt.cm.Purples]  # Add more if needed
    if AT > len(colormaps):
        raise ValueError("Not enough colormaps defined for the number of Transmitting Antennas.")
    # Generate colors for each AR trace, making them darker as AR increases
    colors = []
    for t in range(AT):
        base_colormap = colormaps[t % len(colormaps)]  # Cycle through colormaps if AT > len(colormaps)
        colors.append([base_colormap(0.2 + 0.6 * r / AR) for r in range(AR)])  # Darker shades for higher AR

    if(doUnwrap):
        lines = [ax.plot(subcFreq, np.unwrap(np.angle(Hest[t, r, :, 0])), marker='o', color=colors[t][r], label=f"AT {t+1} - AR {r+1}")[0] for t in range(AT) for r in range(AR)]
    else:
        lines = [ax.plot(subcFreq, (np.angle(Hest[t, r, :, 0])), marker='o', color=colors[t][r], label=f"AT {t+1} - AR {r+1}")[0] for t in range(AT) for r in range(AR)]

    ax.set_title(title)
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
    plt.show()

def plotMACDEST(currCSI=None, NICnum=0, csiPath=None):
    """ Plots Source/Destinations for captured packets in raw CSI.
        Can call either from within a file to peek at `currCSI` or load in the raw file.

        If calling during parsing/filtering, use kinda like this:
            plotCSI.plotMACDEST(combinedCSI, axis=0)
        If using for raw .csi file use like this:
            plotCSI.plotMACDEST() # (This will call up a GUI to select the CSI file in question.)

    Args:
        currCSI (list of picoscenes frames, optional): Similar in shape to `filtersofGOR.alignSingle` [[frame0], [frame1], ...]. Defaults to None.
        csiPath (str, optional): Absolute path to .csi file. If both args empty, brings up GUI. Defaults to None.
    """
    if (currCSI is None) or (not (csiPath is None)):
        # Import CSI only if it's not supplied.
        print("Importing filtersofGOR for loading...")
        import bs.nav.processing.filtersofGOR as filtersofGOR
        
        [currCSI, csiPath] = filtersofGOR.loadCSIfromRAW(csiPath)
        currCSI = filtersofGOR.alignSingle(currCSI) # Standardizes the shape, pulls it into `raw` form that we work with usually.
        NICnum = 0                                    # Only one axis to choose from.

    # [[frame0_NIC0, frame0_NIC1], [frame1_NIC0, frame1_NIC1], ...] -> [frame0_NIC0, frame1_NIC0, ...] for NICnum=0
    currCSI = [frame[NICnum] for frame in currCSI] # Flatten the CSI along the axis of interest.

    # Assumes access to the raw CSI file, parsed by Picoscenes.
    # https://mrncciew.com/2014/09/28/cwap-mac-headeraddresses/
    timestamps = []                     # PPDU-associated timestamp
    addr1 = []; addr2 = []; addr3 = []  # Contents of MAC Header
    tofromDS = []                       # Combination of To/From DS
    for i in range(len(currCSI)):
        toDS = currCSI[i]['StandardHeader']['ControlField']['ToDS'];
        fromDS = currCSI[i]['StandardHeader']['ControlField']['FromDS'];

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

        timestamps.append(currCSI[i]['RxSBasic']['timestamp'])

        addr1.append(currCSI[i]['StandardHeader']['Addr1'])
        addr2.append(currCSI[i]['StandardHeader']['Addr2'])
        addr3.append(currCSI[i]['StandardHeader']['Addr3'])

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