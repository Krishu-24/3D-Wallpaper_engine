"""
off_axis_camera.py

This script creates an off-axis camera setup in Blender.

Purpose:
    Make the Blender camera behave like a viewer looking through a real monitor.

In this project:
    X = depth
    Y = screen width / horizontal movement
    Z = screen height / vertical movement

The virtual screen opening is fixed at X = 0.

The camera represents the viewer's eye.
When the eye moves left/right or up/down, the screen opening should still remain
locked to the render boundaries.

This is what creates the "monitor as a window into a 3D room" effect.
"""

import bpy
import math


# ------------------------------------------------------------
# Unit conversion
# ------------------------------------------------------------
# Blender's Python API uses meters internally.
# Even if the Blender UI displays centimeters, Python values are still meters.
#
# Example:
#   1 cm = 0.01 m
#   45.8 cm = 0.458 m

CM = 0.01


# ------------------------------------------------------------
# Screen / room opening settings
# ------------------------------------------------------------
# The front opening of the virtual room represents the real monitor.
#
# Coordinate system:
#   X = depth
#   Y = width
#   Z = height
#
# The screen plane is placed at X = 0.
# The room extends backward into negative X.

screen_x = 0 * CM

# Real measured monitor opening dimensions
screen_width = 33 * CM      # Y direction
screen_height = 20.7 * CM   # Z direction


# ------------------------------------------------------------
# Eye / camera position
# ------------------------------------------------------------
# The camera represents the user's eye position.
#
# eye_x_in:
#   Distance of the viewer from the screen.
#   Keep this fixed for now because proximity tracking is not being used yet.
#
# eye_y_in:
#   Horizontal head movement.
#   Positive / negative values simulate moving left and right.
#
# eye_z_in:
#   Vertical head movement.
#   Positive / negative values simulate moving up and down.

eye_x_in = 45.8   # cm, fixed viewing distance from monitor
eye_y_in = 0      # cm, left/right movement
eye_z_in = 0      # cm, up/down movement


# Convert cm values to Blender meters
eye_x = eye_x_in * CM
eye_y = eye_y_in * CM
eye_z = eye_z_in * CM


# ------------------------------------------------------------
# Get the Blender camera
# ------------------------------------------------------------
# Change this name if your camera has a different name.
# Example:
#   "Camera"
#   "Camera.001"

cam = bpy.data.objects["Camera.001"]


# ------------------------------------------------------------
# Position the camera
# ------------------------------------------------------------
# The camera is placed in front of the screen.
#
# Since the screen plane is at X = 0, the camera must be at positive X.
#
# Example:
#   Camera X = +45.8 cm
#   Screen X = 0 cm
#   Room extends to X = -50 cm

cam.location = (eye_x, eye_y, eye_z)


# ------------------------------------------------------------
# Rotate the camera
# ------------------------------------------------------------
# Blender cameras look along their local negative Z axis by default.
#
# This rotation makes the camera look toward negative X,
# which is where the virtual room is located.

cam.rotation_euler = (
    math.radians(90),
    0,
    math.radians(90)
)


# ------------------------------------------------------------
# Distance from eye to screen plane
# ------------------------------------------------------------
# This is the real viewing distance.
#
# It is used to calculate the correct field of view.

d = eye_x - screen_x


# ------------------------------------------------------------
# Basic camera type setup
# ------------------------------------------------------------
# We use a perspective camera because this effect depends on perspective.
#
# sensor_fit = 'HORIZONTAL' means the horizontal field of view is the reference.
# This worked correctly for the horizontal pinning in the current setup.

cam.data.type = 'PERSP'
cam.data.sensor_fit = 'HORIZONTAL'


# ------------------------------------------------------------
# Field of view calculation
# ------------------------------------------------------------
# The horizontal FOV is calculated from the real screen width
# and the real viewing distance.
#
# Formula:
#
#   FOV = 2 * atan((screen_width / 2) / viewing_distance)
#
# This makes the camera see exactly the width of the monitor at X = 0.

cam.data.angle_x = 2 * math.atan((screen_width / 2) / d)


# ------------------------------------------------------------
# Off-axis projection correction
# ------------------------------------------------------------
# This is the most important part.
#
# A normal camera has a symmetric frustum.
# That means if the camera moves sideways, the screen opening will no longer
# stay aligned with the render boundaries.
#
# To fix that, we shift the camera projection.
#
# The camera physically moves to the eye position,
# but the projection is shifted so that the screen opening stays pinned.
#
# In the current working setup:
#
#   shift_x uses horizontal head movement divided by screen width.
#   shift_y uses vertical head movement divided by screen width.
#
# Note:
#   shift_y also using screen_width may look strange, but this matched Blender's
#   camera shift behavior with sensor_fit = 'HORIZONTAL' in this project.
#
# If the movement direction feels reversed, flip the sign.

cam.data.shift_x = -eye_y / screen_width
cam.data.shift_y = -eye_z / screen_width


# ------------------------------------------------------------
# Clipping distances
# ------------------------------------------------------------
# clip_start:
#   How close the camera can see.
#
# clip_end:
#   How far the camera can see.
#
# These values are in meters.

cam.data.clip_start = 0.001
cam.data.clip_end = 100


# ------------------------------------------------------------
# Debug output
# ------------------------------------------------------------
# These print values in Blender's console.
# Useful for checking whether the script is using the expected values.

print("Off-axis camera updated")
print("-----------------------")
print("Camera name:", cam.name)
print("Camera location:", cam.location)
print("Eye position in cm:", eye_x_in, eye_y_in, eye_z_in)
print("Screen width in cm:", screen_width / CM)
print("Screen height in cm:", screen_height / CM)
print("Viewing distance in cm:", d / CM)
print("Horizontal FOV in degrees:", math.degrees(cam.data.angle_x))
print("Shift X:", cam.data.shift_x)
print("Shift Y:", cam.data.shift_y)