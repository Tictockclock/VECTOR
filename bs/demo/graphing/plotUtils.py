'''
Plot Utilities

(Like buttons, sliders, etc.)
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

####### HELPER FUNCTIONS ##############################################################
def makeBtnSlider(rect, label, DIM):
    """ Make a slider with inc/dec buttons
        Inc/Dec Buttons will be below the slider, placed with dimensions
        [left, bottom, width, height]

    Args:
        rect (list): [left, bottom, width, height] for slider itself.
        label (str): Slider Label
        DIM (int): Extents of the Slider

    Returns:
        [slider, btn_left, btn_right]: matplotlib.widgets references to each.
    """
    [left, bottom, width, height] = rect

    ax_slider    = plt.axes([left, bottom, width, height]) # [left, bottom, width, height]
    ax_btn_left  = plt.axes([left, bottom-height, width/2, height])
    ax_btn_right = plt.axes([left+width/2, bottom-height, width/2, height])

    slider = Slider(ax_slider, label, 1, DIM, valinit=1, valstep=1)
    btn_left = Button(ax_btn_left, "◀", color='0.85', hovercolor='0.95'); ax_btn_left._btn = btn_left   # Dangling ref to keep it alive
    btn_right = Button(ax_btn_right, "▶", color='0.85', hovercolor='0.95'); ax_btn_right._btn = btn_right   # Dangling ref to keep it alive

    def btn_update(step):
        # Update slider on button press
        new_val = slider.val + step
        if slider.valmin <= new_val <= slider.valmax:
            slider.set_val(new_val)
            plt.gcf().canvas.flush_events() # Make more responsive

    btn_left.on_clicked(lambda event: btn_update(-1)) # Decrement the left one
    btn_right.on_clicked(lambda event: btn_update(1)) # Increment the right one

    if DIM < 2:
        # Make invisible if inapplicable.
        slider.ax.set_visible(False)
        btn_left.ax.set_visible(False)
        btn_right.ax.set_visible(False)

    return [slider, btn_left, btn_right]