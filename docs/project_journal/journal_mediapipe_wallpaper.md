# june 7 2026, session 1: MediaPipe Wallpaper Runner Integration

## Session Focus

This session focused on restarting the MediaPipe-based face tracking path for the 3D wallpaper engine without breaking the already-working Haar Cascade wallpaper runner.

The main goal was to create a clean MediaPipe runner that reuses the existing project structure, existing renderer logic, existing configuration system, and old working values wherever possible.

The approach was:

1. Do not modify old working files unless absolutely necessary.
2. Keep the Haar Cascade runner stable.
3. Add MediaPipe support through new files.
4. Fetch all important values from config instead of hardcoding them in runner files.
5. Make the MediaPipe runner work first, then polish and optimize later.

---

## New MediaPipe Work Completed

### 1. MediaPipe runner created

A new MediaPipe runner file was created for launching the wallpaper using MediaPipe face tracking.

New file:

```text
app/run_wallpaper_mediapipe.py
```

This file is responsible for starting the wallpaper engine with MediaPipe tracking instead of Haar Cascade tracking.

The runner now:

- Loads project paths correctly.
- Reads required settings from the existing config system.
- Uses `.env` for the image sequence folder path.
- Uses the existing renderer and sequence pipeline as much as possible.
- Avoids duplicating old working logic unnecessarily.
- Keeps MediaPipe work isolated from the original Haar Cascade path.

The MediaPipe runner is now working.

---

### 2. MediaPipe core/tracking file created

A new MediaPipe tracking/core file was created to handle MediaPipe-specific face tracking logic.

New file:

```text
src/tracking/mediapipe_face_tracker.py
```

This file separates MediaPipe detection logic from the rest of the wallpaper engine.

Its role is to:

- Initialize MediaPipe face detection or face tracking.
- Read frames from the webcam.
- Detect the face position.
- Output a usable face center or normalized tracking coordinate.
- Keep MediaPipe-specific logic out of the renderer.

This keeps the project modular and avoids mixing Haar Cascade and MediaPipe logic in the same file.

---

## Existing Haar Cascade Runner Cleanup

The Haar Cascade wallpaper runner was also adjusted so that it uses values fetched from config instead of setting important values directly inside the runner.

This means the Haar Cascade runner is cleaner now and more consistent with the MediaPipe runner.

The runner now follows the project configuration more closely instead of relying on scattered hardcoded values.

This is important because both tracking systems should eventually use the same shared configuration for:

- Screen/window size
- Rendered angle ranges
- Number of image views
- Smoothing settings
- Tracking calibration values
- Cache settings
- Sequence folder path
- Threading options

The Haar Cascade runner remains the stable baseline.

---

## Configuration Work

A major part of this work was making sure values come from the config system instead of being randomly set inside runner files.

The project now relies more cleanly on config objects such as:

```text
AppConfig
WindowConfig
SequenceConfig
TrackingConfig
CacheConfig
ThreadingConfig
```

This helps keep the system consistent between runners.

Instead of having different values in different files, the goal is now:

```text
config.py is the source of truth
runner files only assemble and launch the app
core files do the actual work
```

This will make optimization easier later.

---

## Webcam FOV Calibration Discussion

During this session, the webcam calibration values were reviewed.

The values being discussed were:

```text
camera_visible_width_cm = 203
camera_visible_height_cm = 158
camera_measure_distance_cm = 198
```

There was initially confusion because the distance was thought to be:

```text
98 cm
```

But it was later corrected to:

```text
198 cm
```

This correction matters a lot.

With the wrong value:

```text
distance = 98 cm
width = 203 cm
height = 158 cm
```

The calculated webcam FOV becomes very wide:

```text
horizontal FOV ≈ 92.0 degrees
vertical FOV ≈ 77.8 degrees
```

This makes the wallpaper angle mapping feel much too aggressive and unrealistic.

With the corrected value:

```text
distance = 198 cm
width = 203 cm
height = 158 cm
```

The calculated webcam FOV becomes:

```text
horizontal FOV ≈ 54.26 degrees
vertical FOV ≈ 43.53 degrees
```

This is much more reasonable and much closer to the older working behavior.

The important conclusion was:

```text
Measured webcam width and height are not screen dimensions.
They are only used to calculate webcam FOV.
```

The correct formula is:

```python
horizontal_fov = 2 * atan((visible_width_cm / 2) / measurement_distance_cm)
vertical_fov = 2 * atan((visible_height_cm / 2) / measurement_distance_cm)
```

After the FOV is calculated, the calibration distance should not directly control render mapping.

---

## Mapping Understanding Confirmed

The tracking and render mapping pipeline should remain conceptually separated.

### Webcam tracking space

This includes:

```text
webcam frame width in pixels
webcam frame height in pixels
face center x in pixels
face center y in pixels
webcam horizontal FOV
webcam vertical FOV
```

The webcam tracking system estimates where the face is in the camera frame.

---

### Render sequence space

This includes:

```text
Y_VIEWS
Z_VIEWS
Y_ANGLE_MIN
Y_ANGLE_MAX
Z_ANGLE_MIN
Z_ANGLE_MAX
image index
```

The render system decides which pre-rendered view should be shown.

---

### Important rule

The webcam FOV calibration should not overwrite screen size, render distance, or Blender scene values.

The measured webcam dimensions are only for converting face pixel position into a viewing angle.

The rendered image sequence should still be mapped using the render angle range and image count.

---

## Gain Discussion

A possible tuning idea called `gain` was discussed, but it was clarified that gain is not currently required and probably does not exist in the project yet.

Gain simply means a sensitivity multiplier:

```python
render_angle = camera_angle * gain
```

For now, gain should not be added unless needed later.

The cleaner current approach is:

```text
face pixel position
→ webcam FOV
→ camera/viewing angle
→ clamp to rendered angle range
→ map to image index
```

Since the main issue was likely the mistaken `98 cm` measurement instead of `198 cm`, the first step is to use the correct calibration values and test the behavior before adding any artificial sensitivity multiplier.

---

## Current Status

### Working now

- The original Haar Cascade wallpaper runner still works.
- The new MediaPipe wallpaper runner now works.
- MediaPipe has been added without destroying the old working pipeline.
- MediaPipe logic is separated into its own tracking/core file.
- The Haar Cascade runner has also been cleaned to fetch values from config.
- Important values are moving toward config-based control.
- The image sequence folder is fetched from `.env`.
- The project is now in a better state for comparing Haar Cascade and MediaPipe behavior.

---

## Current Design Direction

The project should keep this structure:

```text
app/
  run_wallpaper.py
  run_wallpaper_mediapipe.py

src/
  core/
    config.py
    renderer.py
    indexing.py

  tracking/
    haar_face_tracker.py
    mediapipe_face_tracker.py

  sequence/
    lru_image_sequence.py

  smoothing/
    exponential_smoother_2d.py
```

The exact file names may differ slightly, but the design idea is clear:

```text
runner files launch the app
tracking files detect the face
core files map tracking to render views
sequence files load images efficiently
smoothing files stabilize motion
config controls all important values
```

---

## Testing and Findings

### MediaPipe testing

MediaPipe tracking was tested as a replacement for Haar Cascade.

Findings:

- MediaPipe runner now starts and runs.
- MediaPipe can use the existing wallpaper renderer pipeline.
- The runner mostly works with old known-good values.
- MediaPipe integration should now be polished rather than rebuilt from scratch.

---

### Haar Cascade testing

The Haar Cascade runner remains important as the working baseline.

Findings:

- Haar Cascade runner still works.
- It has now been adjusted to fetch more values from config.
- It remains useful for comparing whether MediaPipe tracking is actually improving the illusion or just changing the motion feel.

---

### Angle mapping testing

The biggest mapping issue discovered was the webcam measurement distance mistake.

Using:

```text
98 cm
```

made the webcam FOV much too wide.

Using:

```text
198 cm
```

gives much more realistic FOV values.

This explains why the mapping changed drastically earlier.

---

## Work To Do Next

The next phase is polish and optimization of the Python implementation.

### 1. Polish MediaPipe runner

Clean up:

- Imports
- Config usage
- Debug prints
- Error handling
- Naming
- Comments
- Startup flow

The MediaPipe runner should become as clean and stable as the original runner.

---

### 2. Polish MediaPipe tracking file

Improve:

- Face center extraction
- Confidence handling
- Lost face behavior
- Frame flipping consistency
- Normalized coordinate output
- Optional eye-based tracking if useful later

The tracker should output clean tracking data and not handle render logic directly.

---

### 3. Verify indexing

Double-check that runtime image index flattening matches the Blender render order.

If Blender renders using:

```python
for z in range(Z_VIEWS):
    for y in range(Y_VIEWS):
        frame_index = z * Y_VIEWS + y
```

then runtime should use:

```python
image_index = z_index * Y_VIEWS + y_index
```

If Blender renders using:

```python
for y in range(Y_VIEWS):
    for z in range(Z_VIEWS):
        frame_index = y * Z_VIEWS + z
```

then runtime should use:

```python
image_index = y_index * Z_VIEWS + z_index
```

This must be confirmed before rendering a large final sequence.

---

### 4. Tune variables

Now that the runner works, the next job is to play with values and optimize the feel.

Variables to tune:

```text
camera_measure_distance_cm
camera_visible_width_cm
camera_visible_height_cm
render_y_angle_min
render_y_angle_max
render_z_angle_min
render_z_angle_max
smoothing alpha
lost face behavior
cache size
window update timing
threading settings
```

The goal is to make the wallpaper feel:

```text
smooth
responsive
not over-sensitive
not laggy
not jumpy
realistic to the eye
```

---

### 5. Add useful debug mode

A debug mode should print or overlay:

```text
face center x/y
normalized x/y
webcam FOV x/y
mapped render angle y/z
y_index
z_index
final image index
FPS
cache hits/misses
```

This will make it easier to understand whether problems are coming from tracking, mapping, smoothing, indexing, or image loading.

---

### 6. Compare Haar Cascade vs MediaPipe

Before moving to C++, compare both systems:

```text
Haar Cascade stability
MediaPipe stability
latency
jitter
lost face recovery
CPU usage
angle smoothness
visual realism
```

The goal is not just to use MediaPipe because it is newer.

The goal is to use whichever tracker gives the best wallpaper illusion.

---

### 7. Prepare for C++/DirectX move

Once the Python version is polished, the project can move toward C++/DirectX.

Before moving, the Python version should clearly define:

```text
final tracking math
final angle mapping
final render order
final image naming convention
final config values
final smoothing behavior
final cache strategy
```

C++ should not begin while the Python logic is still unclear.

The Python version is the prototype and reference implementation.

---

## Final Session Conclusion

This session successfully restarted the MediaPipe journey without breaking the old working Haar Cascade path.

The project now has:

```text
working Haar Cascade runner
working MediaPipe runner
new MediaPipe tracking/core file
cleaner config-based runners
better understanding of webcam FOV calibration
corrected measurement distance from 98 cm to 198 cm
clear next steps for polishing Python before moving to C++
```

The immediate next step is not C++ yet.

The immediate next step is to polish the Python files, tune the variables, confirm the image indexing, and compare Haar Cascade vs MediaPipe behavior.

After that, the project can move to the C++/DirectX implementation with a much clearer reference design.
