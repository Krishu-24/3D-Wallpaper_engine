# Session 3 - FOV Based Angle Mapping Prototype

## Objective

Build a more accurate face tracked wallpaper prototype by mapping the user's real head position to the correct rendered image based on viewing angle, instead of simply eyeballing the webcam x coordinate range.

The goal was to make the image sequence respond according to real world geometry:

- Head position in webcam frame
- Real world x/y offset from the screen center
- Viewing angle from camera/screen
- Matching rendered camera angle
- Correct image index from the rendered sequence

## Background

The earlier prototype mapped the webcam x-coordinate directly to the image sequence.

Example:

```python
image_index = int((face_center_x / frame_width) * (num_images - 1))
```

This worked visually, but it was not physically accurate.

The problem was that the webcam coordinate range does not directly represent the render angle. A face at the left side of the webcam frame does not automatically mean `-30°`, `-60°`, or any fixed angle. The real angle depends on:

- Webcam field of view
- Distance from camera/screen
- Width and height covered by the webcam at that distance
- Number of rendered images
- Rendered field of view range

So the mapping needed to be based on angle, not raw pixel position.

## FOV Testing

To calculate the usable camera field of view, I tested the webcam tracking view at a fixed distance.

Measured values:

```text
Distance from camera: 45.8 cm
Visible x range at this distance: 47 cm
Visible y range at this distance: 34 cm
```

These values were used to estimate the webcam's real world horizontal and vertical field of view.

Formula used:

```text
camera_fov = 2 * atan((visible_range / 2) / distance)
```

For the x axis:

```text
camera_x_fov = 2 * atan((47 / 2) / 45.8)
```

For the y axis:

```text
camera_y_fov = 2 * atan((34 / 2) / 45.8)
```

This gave the program enough information to convert face position in the webcam frame into a real viewing angle.

## Rendered Image Sequence

The new image sequence contains:

```text
x steps: 60
y steps: 9
total images: 540
```

The images are stored as:

```text
view_0001.png
view_0002.png
view_0003.png
...
view_0540.png
```

The Blender render order is:

```text
view_0001 = bottom-left
view_0060 = bottom-right
view_0061 = next row above, left
view_0540 = top-right
```

So the image index formula is:

```python
image_index = y_index * x_steps + x_index
```

This means each y row contains all x views before moving to the next y row.

## Rendered FOV Settings

The rendered views cover:

```text
x render angle range: -30° to +30°
y render angle range: -10° to +10°
```

So the program knows:

```text
x index 0  = -30°
x index 59 = +30°

y index 0 = -10°
y index 8 = +10°
```

Since there are 60 x steps, there is no single exact center image on the x axis. The 0° position lies between the two middle x images.

For the y axis, since there are 9 steps, the center row maps exactly to 0°.

## Mapping Logic

The final mapping works like this:

```text
webcam face center
→ normalized offset from webcam center
→ real-world cm offset
→ real viewing angle
→ closest rendered angle
→ x/y image index
→ final image number
```

## Step 1 - Get Face Center

The face detector gives a rectangle:

```python
x, y, w, h
```

Where:

```text
x = left edge of face rectangle
y = top edge of face rectangle
w = width of face rectangle
h = height of face rectangle
```

The center of the face is calculated using:

```python
face_center_x = x + w // 2
face_center_y = y + h // 2
```

This is better than using only `x`, because the left edge of the face box changes based on face size.

## Step 2 - Convert Webcam Coordinate to Normalized Offset

The webcam center is treated as 0.

```python
x_offset_normalized = (face_center_x - (fw / 2)) / (fw / 2)
y_offset_normalized = (face_center_y - (fh / 2)) / (fh / 2)
```

This gives:

```text
center of webcam = 0
left edge         = -1
right edge        = +1
top edge          = -1
bottom edge       = +1
```

So instead of saying "the face is at x = 230 pixels", the program says "the face is this far away from the center".

## Step 3 - Convert Normalized Offset to Real-World CM Offset

The measured camera range is used to convert normalized position into physical distance.

```python
x_offset_cm = x_offset_normalized * (camera_x_range_cm / 2)
y_offset_cm = y_offset_normalized * (camera_y_range_cm / 2)
```

Current measured values:

```python
camera_x_range_cm = 47.0
camera_y_range_cm = 34.0
```

This means:

```text
left edge of webcam frame  ≈ -23.5 cm
center of webcam frame     ≈ 0 cm
right edge of webcam frame ≈ +23.5 cm
```

And for y:

```text
top edge of webcam frame    ≈ -17 cm
center of webcam frame      ≈ 0 cm
bottom edge of webcam frame ≈ +17 cm
```

## Step 4 - Convert CM Offset to Real Viewing Angle

Once the physical offset is known, the real viewing angle can be calculated.

Formula:

```text
angle = atan(offset / distance)
```

In code:

```python
raw_x_angle = math.degrees(
    math.atan(x_offset_cm / distance_from_camera_cm)
)

raw_y_angle = -math.degrees(
    math.atan(y_offset_cm / distance_from_camera_cm)
)
```

The y angle is inverted because OpenCV's y-axis increases downward, while render angle logic treats upward as positive.

Current distance value:

```python
distance_from_camera_cm = 45.8
```

So the program now knows the real horizontal and vertical angle of the user's head relative to the center.

## Step 5 - Smooth the Angle

Face detection is not perfectly stable. Haar Cascade can slightly shift the detected rectangle between frames, even when the user is not moving.

To reduce jumping, smoothing was added:

```python
smooth_x_angle = (1 - smooth_strength) * smooth_x_angle + smooth_strength * raw_x_angle
smooth_y_angle = (1 - smooth_strength) * smooth_y_angle + smooth_strength * raw_y_angle
```

Current smoothing value:

```python
smooth_strength = 0.25
```

This makes the image movement more stable while still responding to head movement.

## Step 6 - Convert Viewing Angle to Render Index

The rendered image sequence already has known angle limits.

For x:

```python
rendered_x_fov_min = -30.0
rendered_x_fov_max = 30.0
x_steps = 60
```

For y:

```python
rendered_y_fov_min = -10.0
rendered_y_fov_max = 10.0
y_steps = 9
```

The angle is converted to an index using:

```python
normalized = (angle - angle_min) / (angle_max - angle_min)
index = round(normalized * (steps - 1))
```

So if the rendered x range is:

```text
-30° to +30°
```

Then:

```text
-30° maps to x index 0
0° maps to the center region
+30° maps to x index 59
```

For y:

```text
-10° maps to y index 0
0° maps to y index 4
+10° maps to y index 8
```

## Image Indexing Formula

The Blender output order is bottom left to top right.

This means the sequence is arranged as rows:

```text
view_0001 to view_0060 = bottom row, left to right
view_0061 to view_0120 = next row above, left to right
...
view_0481 to view_0540 = top row, left to right
```

Therefore the correct formula is:

```python
image_index = y_index * x_steps + x_index
```

Example:

```text
x_index = 0
y_index = 0
image_index = 0
image file = view_0001.png
```

```text
x_index = 59
y_index = 0
image_index = 59
image file = view_0060.png
```

```text
x_index = 0
y_index = 1
image_index = 60
image file = view_0061.png
```

```text
x_index = 59
y_index = 8
image_index = 539
image file = view_0540.png
```

## X-Axis Flip Issue

After testing, the x axis movement was reversed.

The fix was not to reverse the whole image list, because that would break the 2D sequence order.

Instead, only the x index mapping was flipped.

Current setting:

```python
reverse_x = True
reverse_y = False
```

The function used:

```python
def get_image_index(x_index, y_index):
    if reverse_x:
        x_index = (x_steps - 1) - x_index

    if reverse_y:
        y_index = (y_steps - 1) - y_index

    return y_index * x_steps + x_index
```

This corrected horizontal movement while preserving the bottom left to top right image order.

## Important Fixes

### File Naming Fix

The first load attempt failed because the code was looking for:

```text
0001.png
0002.png
0003.png
...
0540.png
```

But Blender output was actually:

```text
view_0001.png
view_0002.png
view_0003.png
...
view_0540.png
```

The loading path was fixed to:

```python
path = os.path.join(folder, f"view_{frame:04d}.png")
```

### Image Order Fix

The image sequence should not be reversed using:

```python
images.reverse()
```

For the 540 image 2D grid, reversing the full list would break both x and y ordering.

Only the required axis should be flipped mathematically using:

```python
reverse_x = True
```

## Final Working Settings

```python
x_steps = 60
y_steps = 9

distance_from_camera_cm = 45.8

camera_x_range_cm = 47.0
camera_y_range_cm = 34.0

rendered_x_fov_min = -30.0
rendered_x_fov_max = 30.0

rendered_y_fov_min = -10.0
rendered_y_fov_max = 10.0

reverse_x = True
reverse_y = False

smooth_strength = 0.25
```

## Current Working Features

The prototype now supports:

- Loading a 540 image Blender render sequence
- Using image names from `view_0001.png` to `view_0540.png`
- Webcam based face tracking
- Face center detection
- Real-world x/y position calculation
- Real viewing angle calculation
- Angle based render index mapping
- Correct 2D image sequence indexing
- Fullscreen wallpaper display
- Tracking debug window
- x/y angle display
- x/y index display
- Current image number display
- Smoothing to reduce jitter
- x-axis flipping without breaking y axis or sequence order

## Why This Is Better Than Raw Coordinate Mapping

The older method was:

```python
image_index = int((face_center_x / frame_width) * (num_images - 1))
```

This only maps pixel position to image number.

The new method maps:

```text
real head position
→ real viewing angle
→ rendered camera angle
→ correct image
```

This is more physically correct because the rendered views are based on camera angles, not webcam pixels.

## Final Result

The prototype is now working correctly.

The displayed render changes according to the user's actual viewing angle. This makes the 3D wallpaper feel more like a real screen-as-window effect.

When the user moves their head left or right, the program calculates the real x angle and selects the matching x render.

When the user moves their head up or down, the program calculates the real y angle and selects the matching y render.

The final image is selected from the 540 image sequence using:

```python
image_index = y_index * x_steps + x_index
```

with x-axis correction handled by:

```python
reverse_x = True
```

## Next Steps

- Test if the y-axis direction feels correct during real use.
- Tune `smooth_strength` for better responsiveness versus stability.
- Consider replacing Haar Cascade with MediaPipe Face Mesh.
- Track eye center instead of full face box center.
- Add a config file for calibration values.
- Add keyboard controls for live calibration.
- Improve behavior when face tracking is lost.
- Add better scaling without distortion.
- Test with higher quality room renders.
- Test with concrete/tile room materials.
- Later calculate distance dynamically using face size or depth estimation.

