'''
Plots Ranging Estimates

(Module)
Dimitry Melnikov 4/7/25
'''
# Regular Imports
import numpy as np
import matplotlib.pyplot as plt

# Import VECTOR Libraries
import os; import sys
VECTOR_ROOT = os.getenv("VECTOR_ROOT")
print("WARNING! VECTOR_ROOT NOT DEFINED! RUN THIS FROM VECTOR ROOT DIRECTORY: `export VECTOR_ROOT=$(pwd)`") if (VECTOR_ROOT is None) else None
sys.path.insert(0, VECTOR_ROOT) if (VECTOR_ROOT is not None) and (VECTOR_ROOT not in sys.path) else None
import setup; setup.loadModules()

####### FUNCTIONS #####################################################################
def plotDistance(distArray, timestamps, \
                            title="Linear Distance over Time"):
    """ Plot distance over time

    Args:
        distArray (list): Distance (m)
        timestamps (list): Timestamps (s)
    """
    fig, ax = plt.subplots(figsize=(10, 6))
    time = timestamps[0] if len(timestamps) == 1 else timestamps
    ax.plot(time, distArray)
    ax.set_title("Linear Distance over Time")
    ax.set_xlabel("Time (sec)")
    ax.set_ylabel("Distance (m)")
    plt.grid()
    plt.show(block=False)