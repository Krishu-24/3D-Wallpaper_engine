# Prototype 01 - Face Tracked 3D Wallpaper

This prototype displays a pre rendered Blender image sequence as a fullscreen wallpaper and changes the displayed view based on the user's webcam tracked face position.

The goal is to create a **screen-as-window** effect, where moving your head changes the perspective of the rendered scene.

## Features

- Loads a 540 image Blender render sequence
- Tracks face position using OpenCV
- Converts face position into real viewing angles
- Maps viewing angles to rendered camera angles
- Displays the matching render fullscreen
- Shows a debug tracking window
- Supports x axis flip correction
- Uses smoothing to reduce jitter

## Prototype File

```text
prototypes/prototype_01_face_tracked_wallpaper.py
```

## Assets Required

The prototype expects a rendered image sequence in this format:

```text
assets/screen_as_window/renders/off_axis_sequence/
```

Filename format:

```text
view_0001.png
view_0002.png
...
view_0540.png
```

Current sequence layout:

```text
x steps: 60
y steps: 9
total images: 540
```

Render order:

```text
view_0001 = bottom-left
view_0060 = bottom-right
view_0540 = top-right
```

## Current Calibration

The current prototype uses manually measured webcam calibration values:

```python
distance_from_camera_cm = 45.8

camera_x_range_cm = 47.0
camera_y_range_cm = 34.0
```

Rendered FOV range:

```python
rendered_x_fov_min = -30.0
rendered_x_fov_max = 30.0

rendered_y_fov_min = -10.0
rendered_y_fov_max = 10.0
```

Other important settings:

```python
x_steps = 60
y_steps = 9

reverse_x = True
reverse_y = False

smooth_strength = 0.25
```

## How It Works

The prototype maps the user's head position like this:

```text
webcam face center
→ real world x/y offset
→ viewing angle
→ rendered x/y angle index
→ image sequence index
```

The final image index is calculated using:

```python
image_index = y_index * x_steps + x_index
```

The x axis is flipped in code using:

```python
reverse_x = True
```

The full image list should not be reversed, because that breaks the 2D render sequence order.

## Debug Window

The program opens two windows:

```text
wallpaper
tracking
```

`wallpaper` shows the fullscreen rendered view.

`tracking` shows the webcam feed with face box, center point, current angles, current indices, and current image number.

## Dependencies

Install OpenCV:

```bash
pip install opencv-python
```

Tkinter is also used for screen size detection and is usually included with Python on Windows.

## Run

From the project root:

```bash
python prototypes/prototype_01_face_tracked_wallpaper.py
```

Press `Esc` to exit.

## Known Limitations

- Haar Cascade tracking can jitter.
- Face tracking can fail at extreme head angles.
- Distance from camera is currently fixed.
- Calibration values are manually measured.
- Image resizing may distort if render aspect ratio and screen aspect ratio do not match.

## Future Improvements

- Replace Haar Cascade with MediaPipe Face Mesh.
- Add dynamic distance estimation.
- Move calibration values into a config file.
- Add live calibration controls.
- Improve lost face behavior.
- Add aspect ratio correct scaling.
- Test with final room scene renders.