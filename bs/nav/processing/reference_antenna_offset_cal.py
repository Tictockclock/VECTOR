# NOTE: ALL ANGLES ARE BASED ON THE THE POV OF THE REFERENCE ANTENNA.
# MEANING THAT THE LEFT OF THE ARRAY IS TREATED AS -180 DEGREES AND THE RIGHT IS TREATED AS 180 DEGREES

import math

def reference_antenna_position(theta_deg):
    theta = math.radians(theta_deg)
    hinge_x = 53.975  # 2.125 inches in mm
    hinge_y = -95.25  # 3.75 inches in mm (negative = downward)
    ref_x = hinge_x + 174.5 * math.cos(theta)
    ref_y = hinge_y + 174.5 * math.sin(theta)
    return ref_x, ref_y

def acute_angle_to_antennas(theta_deg):
    ref_x, ref_y = reference_antenna_position(theta_deg)
    antennas = [
        (0, 0),           # Antenna 1
        (79.96, 0),       # Antenna 2
        (159.92, 0),      # Antenna 3
        (239.88, 0)       # Antenna 4
    ]
    angles = []
    for x, y in antennas:
        dx = x - ref_x
        dy = y - ref_y
        angle_rad = math.atan2(dy, dx)
        angle_deg = math.degrees(angle_rad)
        # Convert to acute angle (0° to 90°)
        acute_angle = min(abs(angle_deg), 180 - abs(angle_deg))
        angles.append(acute_angle)
    return angles

if __name__ == "__main__":
    # Input angle from 270 to 0 degrees! Where 270 is straight down and 0 is to the right (relative to reference antenna)
    user_angle = 270
    angles = acute_angle_to_antennas(user_angle)
    print(f"Acute angles from reference antenna (θ = {user_angle}):")
    for i, angle in enumerate(angles, start=1):
        print(f"Antenna {i}: {angle:.1f}°")
