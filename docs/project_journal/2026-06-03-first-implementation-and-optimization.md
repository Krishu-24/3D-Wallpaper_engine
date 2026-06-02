# Session 04 - Real Engine Implementation and Multithreaded Renderer

## Objective

Move the 3D wallpaper project out of the prototype stage and begin the real implementation of the engine.

The main goal of this session was to take the working prototype and restructure it into a cleaner, faster, and more scalable engine architecture.

This session focused on:

- Proper engine structure
- LRU image caching
- Float-based indexing
- Smoothing and snap behavior
- Debug window restoration
- Tracking-loss behavior
- Fullscreen rendering
- ESC quit handling
- Multithreaded camera capture
- Multithreaded face tracking
- Background image preloading

---

## Starting Point

Before this session, the project had a working prototype that could use OpenCV face detection, track the user's face position, map the face position to an image sequence, and display the corresponding rendered frame.

However, the prototype had some major limitations:

- Most logic was inside one prototype script
- Image loading was not scalable
- Too many images could be loaded into RAM
- Face tracking, camera reading, rendering, and display were tightly coupled
- It was not ready for the future high-density render sequence
- It was difficult to expand cleanly
- Debug behavior from the prototype needed to be preserved in the real engine

The main decision was to stop treating the project as a prototype and begin building a proper engine.

---

## New Project Direction

The project has now moved from:

```text
prototype script
```

to:

```text
structured real engine implementation
```

The new real implementation is now placed inside:

```text
src/
```

The runnable entry point is:

```text
app/run_wallpaper.py
```

The prototype folder is now treated as old experimental work.

---

## Current File Structure

```text
3D_Wallpaper_engine/
│
├── app/
│   └── run_wallpaper.py
│
├── src/
│   ├── __init__.py
│   ├── config.py
│   ├── indexing.py
│   ├── smoothing.py
│   ├── sequence_cache.py
│   ├── face_tracker.py
│   ├── shared_state.py
│   ├── camera_worker.py
│   ├── tracking_worker.py
│   ├── debug_view.py
│   └── renderer.py
│
├── prototypes/
│
├── assets/
│
├── docs/
│   └── project_journal/
│
├── tests/
│
├── .env
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

---

# What Was Implemented

## 1. Real Engine Structure

The code was separated into multiple files with clear responsibilities.

Main modules added or updated:

```text
config.py
indexing.py
smoothing.py
sequence_cache.py
face_tracker.py
shared_state.py
camera_worker.py
tracking_worker.py
debug_view.py
renderer.py
```

This makes the project easier to maintain, debug, and expand.

---

## 2. Configuration System

A configuration system was added using Python dataclasses.

Current config sections:

```text
SequenceConfig
CacheConfig
TrackingConfig
ThreadingConfig
WindowConfig
AppConfig
```

This allows important values to be controlled from one place instead of being scattered throughout the code.

Important current values:

```python
y_views = 60
z_views = 9

max_cache_size = 120
preload_radius_y = 3
preload_radius_z = 1
enable_blending = False

smoothing_amount = 0.40
snap_distance = 8.0

flip_x = False
flip_z = True

fullscreen = True
```

These values are currently tuned for the older low-count rendered sequence.

---

## 3. Environment Variable Path Loading

The image sequence folder is now loaded from `.env`.

Current variable:

```env
IMAGE_SEQUENCE_FOLDER=path_to_rendered_sequence
```

This keeps personal local file paths out of the code.

The engine originally used:

```env
SEQUENCE_FOLDER
```

but this was changed back to:

```env
IMAGE_SEQUENCE_FOLDER
```

to match the existing project environment setup.

---

## 4. LRU Image Cache

An LRU image cache was implemented in:

```text
sequence_cache.py
```

The goal was to avoid loading the entire rendered image sequence into RAM.

Instead of loading every frame, the engine now keeps only a fixed number of recently used frames.

Current old-sequence value:

```python
max_cache_size = 120
```

Future high-density value:

```python
max_cache_size = 300
```

This solves the earlier problem where loading a large image sequence could consume several GB of RAM.

---

## 5. Background Image Preloading

The cache now preloads nearby frames in the background.

Current preload radius:

```python
preload_radius_y = 3
preload_radius_z = 1
```

This means the engine tries to keep nearby horizontal and vertical views ready before they are needed.

Background preloading uses:

```python
ThreadPoolExecutor
```

This was the first use of multithreading in the engine.

---

## 6. Float Indexing

The engine now maps the detected face position to floating-point sequence indices.

Example:

```text
Y = 31.42
Z = 5.80
```

This is better than only using integer frame indices because it represents the user's position between rendered views.

This also makes optional frame blending possible later.

---

## 7. Optional Frame Blending

Frame blending was implemented using the four neighboring frames around a float index.

However, testing showed that blending currently feels bad with the old low-count rendered sequence.

Reason:

```text
The angular gap between rendered views is too large.
```

This causes visual ghosting or a melted look.

Current decision:

```python
enable_blending = False
```

Blending will be tested again after rendering the future high-density `121 x 35` sequence.

---

## 8. Jitter Smoothing

Exponential smoothing was added to reduce jitter from face detection.

The initial smoothing value was too slow and made movement feel delayed.

It was tuned to:

```python
smoothing_amount = 0.40
```

This feels faster and more responsive.

---

## 9. Snap Threshold

A snap threshold was added because smoothing caused large head movements to visually travel through many intermediate rendered frames.

This made the engine feel like it was rendering every image from the old position to the new position.

The fix:

```text
small movements -> smooth
large movements -> snap directly
```

Current value:

```python
snap_distance = 8.0
```

This made movement feel faster and less lazy.

---

## 10. Axis Flip Configuration

The vertical axis was flipped during testing.

Reason:

```text
Webcam y coordinates increase downward.
Rendered vertical view order may be visually opposite.
```

A configurable flip system was added.

Current values:

```python
flip_x = False
flip_z = True
```

This is now controlled through config instead of being hardcoded.

---

## 11. Hold Last Render Position on Tracking Loss

A bug appeared where losing face tracking caused the rendered view to jump suddenly to the bottom-right.

This was incorrect behavior.

The correct behavior from the prototype was:

```text
If tracking is lost, hold the last valid view.
```

The renderer was updated to store:

```python
last_display_y
last_display_z
```

Now the behavior is:

```text
face detected -> update render position
face lost     -> keep showing last rendered position
```

This fixed the sudden jump.

---

## 12. Fullscreen Window Restored

The prototype opened the render view as a fullscreen window.

The new engine initially did not preserve this behavior.

Fullscreen support was restored through:

```text
WindowConfig
```

Current value:

```python
fullscreen = True
```

---

## 13. ESC Quit Restored

The engine now exits using:

```text
ESC
```

instead of:

```text
Q
```

This was added because `Q` was not reliably quitting in the new setup.

---

## 14. Prototype-Style Debug Window Restored

The new engine initially had a simpler debug window, but the prototype debug view was more useful.

A new module was added:

```text
debug_view.py
```

The debug window now includes:

- Camera feed
- Center guide lines
- Quarter guide lines
- Face rectangle
- Face center dot
- Line from screen center to face center
- Raw sequence index
- Smoothed render index
- Cache usage
- Loading frame count
- Grayscale preview
- Tracked face preview
- ESC quit note

This restored the useful visual debugging behavior from the prototype while keeping the new engine architecture.

---

# Multithreading Work

## Earlier Multithreading

Before the final multithreaded update, only image preloading was threaded.

Architecture at that stage:

```text
Main thread:
camera capture
face detection
indexing
rendering
display

Thread pool:
image preloading
```

This helped with image loading, but the main loop was still responsible for too much.

---

## New Multithreaded Architecture

The engine now uses a proper latest-value multithreaded structure.

Current architecture:

```text
CameraWorker thread:
captures the latest webcam frame continuously

TrackingWorker thread:
runs face detection on the latest camera frame

Main renderer thread:
renders and displays the wallpaper using the latest tracking result

Image cache thread pool:
loads and preloads rendered image frames
```

This separates the most important runtime responsibilities.

---

## Why Latest-Value Sharing Was Used

The engine does not use a queue of camera frames.

This was intentional.

A queue would cause old frames to build up if tracking or rendering is slower than camera capture.

That would create lag.

Instead, the system uses latest-value sharing:

```text
camera captures frame 1
camera captures frame 2
camera captures frame 3
renderer uses only latest available frame
old frames are discarded
```

This is better for a real-time wallpaper engine because responsiveness matters more than processing every frame.

---

## Shared State

A new file was added:

```text
shared_state.py
```

It safely stores:

- Latest camera frame
- Latest camera timestamp
- Latest camera frame ID
- Latest face box
- Latest face timestamp
- Latest face frame ID
- Running state

Thread safety is handled using:

```python
threading.Lock()
```

---

## Camera Worker

A new file was added:

```text
camera_worker.py
```

Responsibilities:

- Open webcam
- Continuously read frames
- Mirror camera frame if enabled
- Store latest frame in `SharedState`
- Release webcam on shutdown

This prevents the renderer from being blocked by camera capture.

---

## Tracking Worker

A new file was added:

```text
tracking_worker.py
```

Responsibilities:

- Read latest camera frame from `SharedState`
- Run face detection
- Store latest detected face box in `SharedState`
- Avoid reprocessing the same frame ID
- Limit tracking FPS if needed

Current value:

```python
max_tracking_fps = 60.0
```

This prevents face detection from blocking rendering.

---

## Renderer Thread

The main thread now owns:

- OpenCV windows
- Wallpaper display
- Debug display
- ESC quit handling
- Render frame selection

This is important because OpenCV display windows should stay in the main thread, especially on Windows.

---

# Current Behavior

The engine currently:

- Starts the camera thread
- Starts the tracking thread
- Starts the cache preload thread pool
- Opens the wallpaper window fullscreen
- Opens the debug window
- Uses the latest detected face position
- Holds the last render view when face tracking is lost
- Uses ESC to quit
- Shuts everything down safely

---

# Current Known Issues

## 1. Blending Feels Bad on Old Sequence

Frame blending feels bad right now.

Likely reason:

```text
The old sequence has too few rendered views.
```

Current decision:

```python
enable_blending = False
```

Blending will be tested again after rendering the high-density sequence.

---

## 2. Haar Cascade Tracking Is Limited

The current face tracker still uses OpenCV Haar Cascade.

It is simple and fast, but it can lose tracking with:

- Face angles
- Lighting changes
- Partial face visibility
- Fast movement

Future tracking options:

- MediaPipe Face Detection
- MediaPipe Face Mesh
- Head pose estimation
- Eye tracking

---

## 3. No FPS or Timing Debug Yet

The engine does not yet show separate performance numbers.

Needed stats:

- Camera FPS
- Tracking FPS
- Render FPS
- Cache hit rate
- Cache misses
- Disk load time
- Preload load count

This should be added soon.

---

## 4. Preloading Is Radius-Based Only

Current preloading loads frames around the current index.

Future improvement:

```text
movement-direction preloading
```

Example:

```text
head moving right -> preload more frames to the right
head moving up    -> preload more frames upward
```

---

# Current Recommended Config

## Old Sequence

```python
y_views = 60
z_views = 9

max_cache_size = 120
preload_radius_y = 3
preload_radius_z = 1
enable_blending = False

smoothing_amount = 0.40
snap_distance = 8.0

flip_x = False
flip_z = True
```

## Future High-Density Sequence

```python
y_views = 121
z_views = 35

max_cache_size = 300
preload_radius_y = 4
preload_radius_z = 2

enable_blending = False
```

For the high-density sequence, blending should remain disabled for the first test.

After confirming performance, blending can be tested again.

---

# Testing Notes

The latest version should be run from the project root:

```bash
python app/run_wallpaper.py
```

The `.env` file must contain:

```env
IMAGE_SEQUENCE_FOLDER=path_to_rendered_sequence
```

Press:

```text
ESC
```

to quit.

---

# Next Steps

## Immediate Next Steps

- Add FPS and timing overlay
- Add cache hit and miss statistics
- Add direct disk load timing
- Add separate camera FPS, tracking FPS, and render FPS
- Add config presets for old sequence and high-density sequence

---

## Next Optimization Steps

- Add movement-direction based preloading
- Add velocity-aware prediction
- Test larger cache sizes
- Render the final `121 x 35` image sequence
- Test high-density sequence with blending disabled first
- Re-test blending after high-density render
- Compare PNG, JPG, and WebP loading performance

---

## Future Engine Steps

- Replace Haar Cascade with better face tracking
- Add head pose estimation
- Add GUI/settings panel
- Add real desktop wallpaper integration
- Package the engine cleanly

---

# Summary

This session converted the project from a working prototype into the first real version of the engine.

The main achievements were:

- Structured `src`-based implementation
- Config system
- LRU image cache
- Background image preloading
- Float indexing
- Smoothing
- Snap threshold
- Axis flip config
- Tracking-loss hold behavior
- Fullscreen display
- Prototype-style debug window
- Multithreaded camera capture
- Multithreaded face tracking
- Thread-safe shared state

This is now a proper base for the future high-density `121 x 35` rendered sequence.
