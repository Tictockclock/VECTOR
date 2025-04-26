# NOTE: ALL ANGLES ARE BASED ON THE THE POV OF THE REFERENCE ANTENNA.
# MEANING THAT THE LEFT OF THE ARRAY IS TREATED AS -180 DEGREES AND THE RIGHT IS TREATED AS 180 DEGREES

import math
import numpy as np

# x-off: 122.3mm122.6mm
hinge_x =  45.6   # x-offset side/side from closest antenna (mm)
hinge_y = -93.4   # y-offset out from closest antenna (mm) (negative = downward)
antennas = [
        (239.88, 0),      # Antenna 0
        (159.92, 0),      # Antenna 1
        (79.96, 0),       # Antenna 2
        (0, 0),           # Antenna 3
            ]

def reference_antenna_position(theta_deg):
    theta_deg = 270 - theta_deg # Convert to Off-Parallel Coord System
    theta = math.radians(theta_deg)
    ref_x = hinge_x + 174.5 * math.cos(theta)
    ref_y = hinge_y + 174.5 * math.sin(theta)
    return ref_x, ref_y

def acute_angle_to_antennas(theta_deg):
    ref_x, ref_y = reference_antenna_position(theta_deg)
    angles = []
    for x, y in antennas:
        dx = x - ref_x
        dy = y - ref_y
        angle_rad = math.atan2(dy, dx)
        angle_deg = math.degrees(angle_rad)
        # Convert to acute angle (0° to 90°)
        acute_angle = min(abs(angle_deg), 180 - abs(angle_deg))
        angles.append(acute_angle)
    return np.array(angles) # Convert to Numpy Array for ease of use.

def distance_to_antennas(theta_deg):
    ref_x, ref_y = reference_antenna_position(theta_deg)
    dists = []
    for x, y in antennas:
        dx = x - ref_x
        dy = y - ref_y
        dists.append(np.sqrt(dx**2 + dy**2))
        
    dists = np.array(dists) * 1e-3 # Convert to Numpy Array for ease of use (and to meters)

    return dists

def phase_to_antennas(theta_deg, cent_freq):
    # Given an Arm Angle off of parallel (theta_deg = 0 is flat against the wall, theta_deg = +90 is straight out, going CCW from top)
    # Cent_Freq ~ Center Frequency, in Hz.
    # Return Phases for [Elem 0, Elem 1, Elem 2, Elem 3]
    dists = distance_to_antennas(theta_deg)
    k = 2 * np.pi * cent_freq / 299792458 # speed of light (Wavenumber)
    return dists * k

if __name__ == "__main__":
    # Input angle from 270 to 0 degrees! Where 270 is straight down and 0 is to the right (relative to reference antenna)
    user_angle = 45.0702
    cent_freq = 2447e6
    dists = distance_to_antennas(user_angle)
    phases = phase_to_antennas(user_angle, cent_freq)
    print(f"Distance & Phase from reference antenna (θ = {user_angle}):")
    for i, dist in enumerate(dists, start=1):
        print(f"Antenna {i}: {dist:.4f} m, {phases[i-1]:.4f} rad")
