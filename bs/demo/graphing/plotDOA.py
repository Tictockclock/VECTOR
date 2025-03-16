'''
Plots DOA Pseudospectra

We expect an DOA matrix of size [AT T S K], where:
- AT: Number of Transmit Antennas
- T: Number of Angles (Theta) Sampled
- S: Number of Subcarriers
- K: Number of CSI Snapshots
As well as the ThetaRange (containing the min/max values for Theta) and

(Module)
Dimitry Melnikov 2/17/25
'''
# Regular Imports
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button

# Import VECTOR Libraries
import os; import sys
VECTOR_ROOT = os.getenv("VECTOR_ROOT")
print("WARNING! VECTOR_ROOT NOT DEFINED! RUN THIS FROM VECTOR ROOT DIRECTORY: `export VECTOR_ROOT=$(pwd)`") if (VECTOR_ROOT is None) else None
sys.path.insert(0, VECTOR_ROOT) if (VECTOR_ROOT is not None) and (VECTOR_ROOT not in sys.path) else None
import setup; setup.loadModules()

import bs.demo.graphing.plotUtils as plotUtils

####### FUNCTIONS #####################################################################
def plotDOA_vsSubcarrier(doaSpectrum, thetaRange, \
                            title="DOA Pseudospectrum vs. Subcarriers"):
    """ Plot likelihood pseudospectrum vs. subcarriers.
        Sliders to select Transmitting Antenna + Snapshot

        If K = 1, or [AT T S], will process as such.

    Args:
        doaSpectrum (Numpy Matrix): Size [AT, T, S, K] for [Num TX Ants, Num Theta Angles, Num Subcarriers, Num Snapshots]
        thetaRange (Numpy Arr): Contains minimum and maximum values for Theta Angles
    """

    # First, define the sizes
    if (len(np.shape(doaSpectrum)) == 4):
        [AT, T, S, K] = np.shape(doaSpectrum)
    else:
        [AT, T, S] = np.shape(doaSpectrum); K = 1
        pltDoaSpectrum = np.zeros((AT, T, S, K), dtype=float)
        pltDoaSpectrum[:, :, :, 0] = doaSpectrum
        doaSpectrum = pltDoaSpectrum # Override
    
    # Variables for plotting
    theta = np.linspace(thetaRange[0], thetaRange[1], T)
    subcarriers = np.arange(1, S+1) # MATLAB uses 1-indexing
    X, Y = np.meshgrid(subcarriers, theta)

    # Set up main plot
    fig, ax = plt.subplots()
    plt.subplots_adjust(bottom=0.25)

    # Plot initial data (using the first TX antenna and first snapshot)
    init_at = 0
    init_k  = 0
    musicSpectrum = np.squeeze(doaSpectrum[init_at, :T, :S, init_k])
    # pcolormesh creates a 2D colored plot analogous to top-down view of 3D mesh
    cax = ax.pcolormesh(X, Y, musicSpectrum, shading='auto')
    ax.set_xlabel("Subcarrier (#)")
    ax.set_ylabel("DOA (deg)")
    ax.set_title(f"{title} | TX: {init_at+1}, Snapshot: {init_k+1}")
    fig.colorbar(cax, ax=ax, label="Likelihood (dB)")

    [sliderAT, buttonAT_left, buttonAT_right] = \
        plotUtils.makeBtnSlider([0.1, 0.1, 0.3, 0.03], 'TX Antenna', AT)

    [sliderK, buttonK_left, buttonK_right] = \
        plotUtils.makeBtnSlider([0.6, 0.1, 0.3, 0.03], 'Snapshot', K)

    def update(val):
        # Update Plot on Slider Change
        # Get slider values (convert from 1-index to 0-indexed)
        at = int(sliderAT.val) - 1
        k  = int(sliderK.val) - 1
        musicSpectrum = np.squeeze(doaSpectrum[at, :T, :S, k])

        # Update color mesh without clearing the axis
        cax.set_array(musicSpectrum.ravel())

        # Update title
        ax.set_title(f"{title} | TX: {at+1}, Snapshot: {k+1}")

        # Redraw canvas
        fig.canvas.draw_idle()

    def btn_update(slider, step):
        # Update Slider on Button Press
        new_val = slider.val + step
        if slider.valmin <= new_val <= slider.valmax:
            slider.set_val(new_val)
            plt.gcf().canvas.flush_events()

    # Slider Actions
    sliderAT.on_changed(update)
    sliderK.on_changed(update)

    # Plot w/o blocking
    plt.show(block=False)


def plotDOA_vsSnapshots(doaSpectrum, thetaRange, windowSize=1, \
                            title="DOA Pseudospectrum vs. Snapshots"):
    """ Plot likelihood pseudospectrum vs. subcarriers.
        Sliders to select Transmitting Antenna + Snapshot

        If K = 1, or [AT T S], will process as such.

    Args:
        doaSpectrum (Numpy Matrix): Size [AT, T, S, K] for [Num TX Ants, Num Theta Angles, Num Subcarriers, Num Snapshots]
        thetaRange (Numpy Arr): Contains minimum and maximum values for Theta Angles
        windowSize (optional, int): Number of snapshots in each averaging window. Cuts off `windowSize` frames from the end
    """
    # First, define the sizes
    if (len(np.shape(doaSpectrum)) == 4):
        [AT, T, S, K] = np.shape(doaSpectrum)
    else:
        [AT, T, S] = np.shape(doaSpectrum); K = 1
        pltDoaSpectrum = np.zeros((AT, T, S, K), dtype=float)
        pltDoaSpectrum[:, :, :, 0] = doaSpectrum
        doaSpectrum = pltDoaSpectrum # Override
    
    # Variables for plotting
    theta = np.linspace(thetaRange[0], thetaRange[1], T)
    snapshots = np.arange(0, (K+1) - windowSize+1) # MATLAB uses 1-indexing
    X, Y = np.meshgrid(snapshots, theta)

    # Set up main plot
    fig, ax = plt.subplots()
    plt.subplots_adjust(bottom=0.25)

    # Plot initial data (using the first TX antenna and first snapshot)
    init_at = 0
    init_s  = 0
    musicSpectrum = np.squeeze(doaSpectrum[init_at, :T, init_s, 0:(len(snapshots))])
    # pcolormesh creates a 2D colored plot analogous to top-down view of 3D mesh
    cax = ax.pcolormesh(X, Y, musicSpectrum, shading='auto')
    ax.set_xlabel("Snapshot (#)")
    ax.set_ylabel("DOA (deg)")
    ax.set_title(f"{title} | TX: {init_at+1}, Subcarrier: {init_s+1}")
    fig.colorbar(cax, ax=ax, label="Likelihood (dB)")

    [sliderAT, buttonAT_left, buttonAT_right] = \
        plotUtils.makeBtnSlider([0.1, 0.1, 0.3, 0.03], 'TX Antenna', AT)

    [sliderS, buttonS_left, buttonS_right] = \
        plotUtils.makeBtnSlider([0.6, 0.1, 0.3, 0.03], 'Subcarrier', S)

    def update(val):
        # Update Plot on Slider Change
        # Get slider values (convert from 1-index to 0-indexed)
        at = int(sliderAT.val) - 1
        s  = int(sliderS.val) - 1
        musicSpectrum = np.squeeze(doaSpectrum[at, :T, s, 0:(len(snapshots))])

        # Update color mesh without clearing the axis
        cax.set_array(musicSpectrum.ravel())
        
        # Update title
        ax.set_title(f"{title} | TX: {at+1}, Subcarrier: {s+1}")

        # Redraw canvas
        fig.canvas.draw_idle()

    # Slider Actions
    sliderAT.on_changed(update)
    sliderS.on_changed(update)

    plt.show(block=False)