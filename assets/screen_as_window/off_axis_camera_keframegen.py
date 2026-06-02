"""
render_off_axis_sequence.py

Purpose:
    This script creates a grid of off-axis camera keyframes in Blender.

    Instead of rendering immediately inside the script, it only prepares the
    camera animation. After running this script, the user can use:

        Render → Render Animation

    Blender will then render each frame normally using the scene's existing
    render settings, such as Cycles, GPU Compute, samples, resolution, and
    output format.

Project context:
    This script is used for a head-coupled 3D wallpaper / virtual window
    experiment.

    The monitor is treated as a fixed window into a virtual room.

    The camera represents the viewer's eye position.

    For every simulated eye position, the camera moves and the projection is
    shifted so that the screen opening remains pinned to the render boundaries.

Coordinate system:
    X = depth
    Y = horizontal screen direction
    Z = vertical screen direction

    Screen plane:
        X = 0

    Room:
        Extends behind the screen into negative X

    Camera / viewer:
        Placed in front of the screen at positive X
"""

import bpy
import math
import os


# ============================================================
# INPUTS
# ============================================================
# These are the main values you should edit when changing the
# image sequence resolution or render angle range.

# Name of the Blender camera object used for rendering.
# If your camera has a different name, change this.
CAMERA_NAME = "Camera.001"


# ------------------------------------------------------------
# Real monitor / virtual window dimensions
# ------------------------------------------------------------
# These values should match the physical visible area of the monitor.
#
# In this project:
#   Width  = Y axis
#   Height = Z axis
#
# Units here are centimeters.
SCREEN_WIDTH_CM = 33
SCREEN_HEIGHT_CM = 20.7


# ------------------------------------------------------------
# Fixed viewing distance
# ------------------------------------------------------------
# This is the distance from the screen plane to the viewer's eye.
#
# Since proximity tracking is not being used right now, this remains fixed.
#
# Units: centimeters.
EYE_X_CM = 45.8


# ------------------------------------------------------------
# View grid resolution
# ------------------------------------------------------------
# Y_VIEWS controls horizontal viewpoint resolution.
# Z_VIEWS controls vertical viewpoint resolution.
#
# Total rendered frames:
#   Y_VIEWS * Z_VIEWS
#
# Example:
#   60 * 9 = 540 images
Y_VIEWS = 60
Z_VIEWS = 9


# ------------------------------------------------------------
# View angle range
# ------------------------------------------------------------
# These are the maximum simulated viewing angles.
#
# Y angle:
#   Left/right head movement.
#
# Z angle:
#   Up/down head movement.
#
# These are not camera rotations.
# They are converted into physical eye offsets using:
#
#   offset = viewing_distance * tan(angle)
#
# Units: degrees.
Y_ANGLE_MIN = -25
Y_ANGLE_MAX = 25

Z_ANGLE_MIN = -10
Z_ANGLE_MAX = 10


# ------------------------------------------------------------
# Output folder
# ------------------------------------------------------------
# The // prefix means "relative to the current .blend file".
#
# Final frames will be named by Blender like:
#   view_0001.png
#   view_0002.png
#   ...
OUTPUT_FOLDER = "//renders/off_axis_sequence"


# ------------------------------------------------------------
# Unit conversion
# ------------------------------------------------------------
# Blender Python uses meters internally, even if the Blender UI is set to cm.
#
# Therefore:
#   1 cm = 0.01 m
CM = 0.01


# ============================================================
# SETUP
# ============================================================

# Get the camera object from the Blender scene.
cam = bpy.data.objects[CAMERA_NAME]

# Get the active scene.
scene = bpy.context.scene


# Convert important dimensions from cm to Blender meters.
screen_width = SCREEN_WIDTH_CM * CM
eye_x = EYE_X_CM * CM


# Set the active render camera.
scene.camera = cam


# Set the animation frame range.
#
# One frame represents one rendered viewpoint.
#
# Example:
#   60 horizontal views * 9 vertical views = 540 frames
scene.frame_start = 1
scene.frame_end = Y_VIEWS * Z_VIEWS


# Create the output folder if it does not already exist.
output_dir = bpy.path.abspath(OUTPUT_FOLDER)
os.makedirs(output_dir, exist_ok=True)


# Set output file path.
#
# Blender automatically appends the frame number during animation render.
#
# Example output:
#   view_0001.png
#   view_0002.png
#   view_0003.png
scene.render.filepath = os.path.join(output_dir, "view_")


# Set output image format.
scene.render.image_settings.file_format = "PNG"


# ------------------------------------------------------------
# Camera fixed settings
# ------------------------------------------------------------
# The camera stays perspective because the effect depends on perspective.
cam.data.type = "PERSP"

# The current working setup uses horizontal sensor fit.
#
# This means the horizontal field of view is the reference.
cam.data.sensor_fit = "HORIZONTAL"


# Calculate horizontal field of view from real screen width and viewing distance.
#
# Formula:
#   FOV = 2 * atan((screen_width / 2) / viewing_distance)
#
# This makes the camera see the monitor width correctly at X = 0.
cam.data.angle_x = 2 * math.atan((screen_width / 2) / eye_x)


# Camera clipping distances.
#
# These are in meters.
cam.data.clip_start = 0.001
cam.data.clip_end = 100


# ------------------------------------------------------------
# Clear old animation
# ------------------------------------------------------------
# This prevents previous camera keyframes from interfering with the new sequence.
#
# cam.animation_data_clear():
#   Clears camera object animation such as location and rotation.
#
# cam.data.animation_data_clear():
#   Clears camera data animation such as shift_x and shift_y.
cam.animation_data_clear()
cam.data.animation_data_clear()


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def lerp(a, b, t):
    """
    Linearly interpolate between a and b.

    Parameters:
        a:
            Start value.

        b:
            End value.

        t:
            Interpolation amount from 0 to 1.

    Returns:
        Value between a and b.
    """
    return a + (b - a) * t


def angle_to_offset_cm(distance_cm, angle_deg):
    """
    Convert a viewing angle into a physical eye offset.

    This is used because the script input range is easier to think about
    in degrees, but the Blender camera needs a physical position.

    Formula:
        offset = distance * tan(angle)

    Example:
        If the viewer is 45.8 cm away from the screen and the desired
        horizontal viewing angle is 25 degrees:

            offset = 45.8 * tan(25 degrees)

    Parameters:
        distance_cm:
            Viewing distance from screen in centimeters.

        angle_deg:
            Desired viewing angle in degrees.

    Returns:
        Physical eye offset in centimeters.
    """
    return distance_cm * math.tan(math.radians(angle_deg))


# ============================================================
# CREATE KEYFRAMES
# ============================================================
# The sequence is arranged as a 2D grid:
#
#   Z index = vertical viewpoint row
#   Y index = horizontal viewpoint column
#
# Frame order:
#
#   z0_y0, z0_y1, z0_y2, ...
#   z1_y0, z1_y1, z1_y2, ...
#   z2_y0, z2_y1, z2_y2, ...
#
# This makes it easier later to map:
#
#   frame_index = z_index * Y_VIEWS + y_index
#
# or to load the images as:
#
#   images[z_index][y_index]

frame = 1


# Loop over vertical viewpoints first.
for z_index in range(Z_VIEWS):

    # Convert z_index into a normalized value from 0 to 1.
    #
    # If Z_VIEWS is 1, use 0 so there is no division by zero.
    z_t = 0 if Z_VIEWS == 1 else z_index / (Z_VIEWS - 1)

    # Convert normalized value into an actual vertical viewing angle.
    z_angle = lerp(Z_ANGLE_MIN, Z_ANGLE_MAX, z_t)

    # Convert vertical angle into physical eye height offset.
    eye_z_cm = angle_to_offset_cm(EYE_X_CM, z_angle)


    # Loop over horizontal viewpoints.
    for y_index in range(Y_VIEWS):

        # Convert y_index into a normalized value from 0 to 1.
        #
        # If Y_VIEWS is 1, use 0 so there is no division by zero.
        y_t = 0 if Y_VIEWS == 1 else y_index / (Y_VIEWS - 1)

        # Convert normalized value into an actual horizontal viewing angle.
        y_angle = lerp(Y_ANGLE_MIN, Y_ANGLE_MAX, y_t)

        # Convert horizontal angle into physical eye side offset.
        eye_y_cm = angle_to_offset_cm(EYE_X_CM, y_angle)


        # Convert eye offsets from centimeters to Blender meters.
        eye_y = eye_y_cm * CM
        eye_z = eye_z_cm * CM


        # Move Blender timeline to the current frame.
        scene.frame_set(frame)


        # ----------------------------------------------------
        # Camera position
        # ----------------------------------------------------
        # Camera represents the viewer's eye.
        #
        # X stays fixed because proximity is not being tracked.
        # Y changes for horizontal movement.
        # Z changes for vertical movement.
        cam.location = (eye_x, eye_y, eye_z)


        # ----------------------------------------------------
        # Camera rotation
        # ----------------------------------------------------
        # Blender cameras normally look along their local negative Z axis.
        #
        # This rotation makes the camera look toward negative X,
        # which is where the virtual room is located.
        #
        # The camera is not being rotated based on head movement.
        # The viewpoint changes because the eye position and projection shift.
        cam.rotation_euler = (
            math.radians(90),
            0,
            math.radians(90)
        )


        # ----------------------------------------------------
        # Off-axis projection shift
        # ----------------------------------------------------
        # This is the key part of the script.
        #
        # A normal perspective camera has a symmetric frustum.
        # If the camera is only moved sideways or vertically, the room
        # opening no longer stays aligned with the render frame.
        #
        # To simulate a real viewer looking through a fixed monitor window,
        # the camera projection must shift in the opposite direction.
        #
        # This keeps the screen opening pinned to the image boundaries.
        #
        # Current working formulas:
        #
        #   shift_x = -eye_y / screen_width
        #   shift_y = -eye_z / screen_width
        #
        # Note:
        #   shift_y also uses screen_width because this matched Blender's
        #   camera shift behavior with sensor_fit = "HORIZONTAL".
        cam.data.shift_x = -eye_y / screen_width
        cam.data.shift_y = -eye_z / screen_width


        # ----------------------------------------------------
        # Insert keyframes
        # ----------------------------------------------------
        # These store the camera state for the current frame.
        #
        # Object keyframes:
        #   location
        #   rotation_euler
        #
        # Camera data keyframes:
        #   shift_x
        #   shift_y
        #
        # angle_x is not keyframed because viewing distance is fixed.
        cam.keyframe_insert(data_path="location", frame=frame)
        cam.keyframe_insert(data_path="rotation_euler", frame=frame)
        cam.data.keyframe_insert(data_path="shift_x", frame=frame)
        cam.data.keyframe_insert(data_path="shift_y", frame=frame)


        # Print progress in Blender's console.
        print(
            f"Frame {frame}: "
            f"z_index={z_index}, y_index={y_index}, "
            f"Y angle={y_angle:.2f}, Z angle={z_angle:.2f}, "
            f"eye_y={eye_y_cm:.2f} cm, eye_z={eye_z_cm:.2f} cm"
        )


        # Move to next frame.
        frame += 1


# Return timeline to the first frame after creating all keyframes.
scene.frame_set(1)


# ============================================================
# FINAL STATUS MESSAGE
# ============================================================

print("Done creating off-axis camera keyframes.")
print(f"Frames: {scene.frame_start} to {scene.frame_end}")
print(f"Total frames: {Y_VIEWS * Z_VIEWS}")
print(f"Output folder: {output_dir}")