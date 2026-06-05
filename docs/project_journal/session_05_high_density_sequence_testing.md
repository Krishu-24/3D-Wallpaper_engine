# Session 05 - High Density Sequence Testing and Engine Tuning

## Objective

Integrate and test the new high-density render sequence with the real multithreaded wallpaper engine.

The main goal of this session was to move from the older low-count render sequence to the new high-density sequence:

```text
Y_VIEWS = 121
Z_VIEWS = 35
Total frames = 4235
```

This session focused on:

- Running the new `121 x 35` render sequence
- Updating engine configuration for the new sequence
- Testing cache and RAM behavior
- Testing frame blending again
- Tuning smoothing and snap behavior
- Improving tracking-loss behavior
- Reducing false face detection jumps
- Understanding remaining vertical-axis choppiness
- Reviewing earlier OpenCV and PyQt wallpaper-window experiments

---

## Starting Point

Before this session, the engine had already moved beyond the prototype stage.

The real implementation already included:

- Structured `src`-based engine code
- `app/run_wallpaper.py` as the entry point
- LRU image sequence cache
- Background image preloading
- Float indexing
- Optional frame blending
- Exponential smoothing
- Snap threshold
- Axis flip config
- Fullscreen OpenCV display
- Prototype-style debug window
- Multithreaded camera capture
- Multithreaded face tracking
- Thread-safe shared state

At this point, the engine was working with the older low-count rendered sequence.

The next major step was to test the newly rendered high-density sequence.

---

## New Render Sequence

The new render sequence uses:

```python
y_views = 121
z_views = 35
```

Total frame count:

```text
121 x 35 = 4235 frames
```

This was chosen because earlier testing showed that lower horizontal counts still felt slightly laggy or stepped during small head movements.

The expected benefit of this sequence:

- Smoother horizontal motion
- Better view-dependent response
- More realistic screen/window illusion
- Less visible frame stepping during head movement

---

## Code Updates for High-Density Sequence

The main updates were made in:

```text
app/run_wallpaper.py
src/config.py
src/renderer.py
src/smoothing.py
```

The sequence config was updated from:

```python
y_views = 60
z_views = 9
```

to:

```python
y_views = 121
z_views = 35
```

The image sequence path continued to be loaded through:

```env
IMAGE_SEQUENCE_FOLDER=path_to_render_sequence_folder
```

The render folder must contain files matching the configured pattern:

```python
filename_pattern = "view_{frame:04d}.png"
start_frame = 1
```

Expected file examples:

```text
view_0001.png
view_0002.png
view_0003.png
...
view_4235.png
```

---

## Cache and RAM Testing

Initial cache settings were aggressive:

```python
max_cache_size = 400
preload_radius_y = 7
preload_radius_z = 4
max_workers = 4
enable_blending = True
```

This worked, but RAM usage rose to around:

```text
6 GB
```

This was higher than desired.

Target RAM range:

```text
3 GB to 4.7 GB
```

### Finding

The main RAM cost is not the compressed PNG file size on disk.

Once loaded by OpenCV, each image becomes a decoded raw image array in memory.

For example:

```text
1920 x 1080 x 3 bytes ≈ 6 MB per frame
```

So hundreds of cached frames can quickly become several GB of memory usage.

### Conclusion

The most important RAM control is:

```python
max_cache_size
```

Secondary controls:

```python
preload_radius_y
preload_radius_z
max_workers
enable_blending
```

Blending can increase pressure because it needs neighboring frames available for interpolation.

---

## Cache Tuning

The recommended cache direction changed from aggressive caching to more controlled caching.

Suggested tuned values:

```python
max_cache_size = 180
preload_radius_y = 8
preload_radius_z = 2
max_workers = 6
enable_blending = True
```

Reasoning:

- `max_cache_size = 400` was too heavy for RAM.
- `preload_radius_z = 4` loaded too many vertical rows.
- `preload_radius_y = 8` is useful because horizontal movement has 121 views and benefits from wider preloading.
- `preload_radius_z = 2` is a better balance for vertical movement and RAM.
- `max_workers = 6` may help reduce loading delay during faster movements, but should be reduced if CPU usage becomes too high.

If RAM is still too high, future values to test:

```python
max_cache_size = 140
max_cache_size = 160
max_cache_size = 180
```

---

## Blending Test

Frame blending was previously disabled for the old low-count sequence because it looked bad.

Old sequence finding:

```text
Blending caused ghosting or a melted look because the angular gap between adjacent rendered views was too large.
```

With the new `121 x 35` sequence, blending was tested again.

### Finding

Blending looked acceptable with the high-density sequence.

This suggests that blending is only useful when adjacent rendered views are close enough.

### Current Decision

For the high-density sequence:

```python
enable_blending = True
```

is acceptable.

For low-count test sequences:

```python
enable_blending = False
```

is still better.

---

## Horizontal Axis Testing

The horizontal axis now feels smooth.

This is likely because the horizontal render count is high:

```text
Y_VIEWS = 121
```

### Finding

After tuning, there was no noticeable lag or jitter in the horizontal direction.

The X direction felt good and smooth.

### Conclusion

The horizontal render density is sufficient for the current setup.

No additional horizontal render views are needed right now.

---

## Vertical Axis Testing

The vertical axis still felt choppy compared to the horizontal axis.

Current vertical render count:

```text
Z_VIEWS = 35
```

### Finding

The vertical axis is naturally more visible as stepped because it has fewer views than the horizontal axis.

However, this does not automatically mean that more vertical renders are needed.

Possible causes of vertical choppiness:

- Lower vertical frame count
- Same smoothing behavior being used for both axes
- Face detector jitter in the vertical coordinate
- Over-aggressive tracking update rate
- Cache pressure from large vertical preload radius
- Blending between still-not-dense-enough vertical views

### Decision

Do not render more vertical images yet.

First, fix it in software.

---

## Axis-Specific Smoothing

The engine originally used the same smoothing behavior for both horizontal and vertical movement.

That was not ideal.

The high-density sequence has:

```text
Horizontal views = 121
Vertical views = 35
```

So horizontal can respond quickly, while vertical may need stronger smoothing.

The smoother was updated to support separate axis values:

```python
amount_x = 0.60
amount_y = 0.45
```

Meaning:

```text
amount_x -> horizontal responsiveness
amount_y -> vertical responsiveness
```

### Finding

This helped make the vertical movement less unstable without damaging the smooth horizontal feel.

### Current Direction

Keep horizontal faster and vertical slightly smoother.

If vertical feels too delayed:

```python
amount_y = 0.50
```

If vertical feels too jittery:

```python
amount_y = 0.35
```

---

## Tracking-Loss Behavior

The renderer was intended to hold the last valid rendered position when face tracking is lost.

Correct behavior:

```text
face detected -> update render position
face lost     -> keep rendering last_display_y and last_display_z
```

The renderer logic already mostly did this correctly.

However, during testing it still looked like the engine was not holding position.

### Finding

The issue was probably not true tracking loss.

It was likely caused by false Haar Cascade detections.

In other words:

```text
The detector sometimes found a wrong face-like region.
The renderer treated that as a valid face.
The render jumped to the wrong position.
```

This looked like a tracking-loss hold failure, but was actually a false detection problem.

---

## False Detection Rejection

A reasonable-face filter was added to the renderer.

The renderer now compares the new detected face box against the last valid face box.

It rejects detections if:

- The face center jumps too far suddenly
- The detected face size changes too much suddenly
- The face box is missing

Current values:

```python
max_face_jump_px = 180
max_face_size_change_ratio = 0.55
```

### Behavior

If the face detection is reasonable:

```text
accept face box
update render position
store as last valid face
```

If the face detection is unreasonable:

```text
reject face box
hold last render position
do not reset smoother
do not jump to center
```

### Finding

This improved the tracking-loss feel and reduced sudden jumps caused by bad detections.

---

## Tracking FPS Testing

The tracking FPS was initially high:

```python
max_tracking_fps = 55.0
```

Higher tracking FPS is not always better with Haar Cascade.

It can produce more frequent noisy updates.

A more stable value to test is:

```python
max_tracking_fps = 30.0
```

### Finding

For Haar Cascade, lower tracking FPS can sometimes feel more stable because the detection output is less noisy.

### Current Direction

Use:

```python
max_tracking_fps = 30.0
```

for stability testing.

If responsiveness feels too slow, test:

```python
max_tracking_fps = 45.0
```

---

## OpenCV Wallpaper Testing Findings

Earlier testing used OpenCV windows for the visual output.

OpenCV was useful because it allowed quick testing of:

- Image sequence display
- Fullscreen output
- Face tracking debug windows
- Frame switching
- Basic render loop behavior
- ESC quit handling

### Findings

OpenCV is good for prototype and engine testing.

It is simple and fast enough to quickly validate:

```text
tracking -> indexing -> image selection -> display
```

However, OpenCV windows are not a proper desktop wallpaper solution.

OpenCV fullscreen creates a fullscreen application window, not a real desktop background.

### What OpenCV Is Good For

- Fast iteration
- Debug windows
- Displaying the active rendered frame
- Testing face tracking
- Testing frame indexing
- Testing cache behavior
- Testing fullscreen illusion

### What OpenCV Is Not Good For

- True Windows desktop wallpaper integration
- Proper behind-icons rendering
- Robust desktop window parenting
- Long-term app packaging
- Polished user-facing UI

### Conclusion

OpenCV should remain the main testing display backend for now.

It is still the fastest way to tune the engine.

A separate wallpaper integration layer should come later.

---

## PyQt Wallpaper Testing Findings

PyQt was considered and tested as an alternative display/UI route for wallpaper-style behavior.

PyQt is useful because it provides more control over:

- Window creation
- Borderless display
- UI elements
- Settings panels
- Multi-window management
- Future app interface
- Better event handling than raw OpenCV windows

### Findings

PyQt is better suited than OpenCV for a future polished application UI.

However, PyQt still does not automatically solve true desktop wallpaper integration.

A PyQt window can behave like:

```text
borderless fullscreen overlay
```

but that is still different from:

```text
real wallpaper behind desktop icons
```

### What PyQt Is Good For

- Settings GUI
- Preset selector
- Debug panels
- Borderless fullscreen window
- Better app controls
- Future packaged application

### What PyQt Is Not Enough For By Itself

- True desktop embedding behind icons
- Direct desktop compositor integration
- Low-level wallpaper parenting
- DirectX-level rendering performance

### Conclusion

PyQt is a good future UI layer, but not the core rendering solution yet.

For now:

```text
OpenCV = fast render/debug testing
PyQt = future GUI/settings layer
DirectX/C++/Win32 = future real wallpaper backend
```

---

## Desktop Wallpaper Backend Findings

Earlier desktop wallpaper testing showed that making a real live wallpaper on Windows is different from simply opening a fullscreen window.

A true wallpaper backend likely needs to interact with Windows desktop windows such as:

```text
Progman
SHELLDLL_DefView
WorkerW
SysListView32
```

A safe diagnostic was used earlier to inspect the desktop window tree without modifying Explorer.

The result showed the relevant desktop hierarchy, including:

```text
Progman
SHELLDLL_DefView
SysListView32
```

### Finding

A proper wallpaper implementation will likely require a separate backend that handles:

- Window parenting
- WorkerW / Progman behavior
- Desktop icon layer preservation
- Rendering behind icons
- Safe recovery if Explorer restarts

### Conclusion

The current OpenCV renderer is still the correct testing backend.

A real wallpaper backend should be implemented later, probably with:

```text
C++ / Win32 / DirectX
```

This should be separate from the Python tracking and engine experimentation.

---

## Current Recommended High-Density Config

Recommended current direction:

```python
y_views = 121
z_views = 35

max_cache_size = 180
preload_radius_y = 8
preload_radius_z = 2
max_workers = 6
enable_blending = True

smoothing_amount = 0.55
snap_distance = 6.0

amount_x = 0.60
amount_y = 0.45

flip_x = False
flip_z = True

max_tracking_fps = 30.0
```

If RAM is still too high:

```python
max_cache_size = 140
```

or:

```python
max_cache_size = 160
```

If fast movement still lags:

```python
preload_radius_y = 9
max_workers = 6
```

If CPU usage becomes too high:

```python
max_workers = 4
```

If vertical movement is too jittery:

```python
amount_y = 0.35
```

If vertical movement is too delayed:

```python
amount_y = 0.50
```

---

## Current Known Issues

### 1. Vertical Axis Still Feels Choppier Than Horizontal

This is expected because the vertical sequence has fewer views:

```text
Z_VIEWS = 35
```

Software smoothing should be tuned further before rendering more vertical frames.

### 2. RAM Usage Needs Tuning

The sequence can still use a lot of memory depending on:

- Image resolution
- Cache size
- Preload radius
- Blending
- Worker count
- OpenCV buffers

The main knob is:

```python
max_cache_size
```

### 3. Haar Cascade Is Still Limited

Haar Cascade is simple and fast, but not very robust.

It can still lose track or detect false positives.

Future replacement options:

- MediaPipe Face Detection
- MediaPipe Face Mesh
- Head pose estimation
- Eye tracking

### 4. No Performance Stats Yet

The engine still needs proper runtime stats:

- Camera FPS
- Tracking FPS
- Render FPS
- Cache hit rate
- Cache misses
- Disk load time
- Preload load count
- RAM estimate

---

## Next Steps

Immediate next steps:

1. Add FPS and timing overlay
2. Add cache hit/miss statistics
3. Add direct disk load timing
4. Add RAM-aware cache tuning
5. Add config presets for old sequence and high-density sequence

Next optimization steps:

1. Add movement-direction based preloading
2. Add velocity-aware prediction
3. Tune vertical smoothing further
4. Test cache sizes between 140 and 220
5. Test tracking FPS values between 30 and 45
6. Compare PNG, JPG, and WebP loading performance

Future engine steps:

1. Replace Haar Cascade with better tracking
2. Add head pose estimation
3. Create a PyQt settings/debug UI
4. Create a proper Windows wallpaper backend
5. Explore C++ / Win32 / DirectX for real wallpaper rendering
6. Package the engine cleanly

---

## Summary

This session successfully integrated the high-density `121 x 35` render sequence into the real multithreaded wallpaper engine.

Major findings:

- The horizontal axis feels smooth with 121 views.
- The vertical axis still feels choppier and needs software smoothing before more renders are considered.
- Blending looks better with the high-density sequence than it did with the old low-count sequence.
- RAM usage is mostly controlled by decoded image cache size.
- False detections can look like tracking-loss failure.
- The renderer should reject unreasonable face jumps and hold the last valid render position.
- OpenCV remains the best testing backend for now.
- PyQt is useful later for UI, but not enough by itself for a real wallpaper backend.
- True wallpaper integration should be handled separately later, likely with Win32 / DirectX.

The engine is now good enough to commit as the first high-density render sequence testing milestone.
