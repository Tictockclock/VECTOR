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