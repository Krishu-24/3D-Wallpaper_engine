# Research Note - OpenCV, PyQt, and Real Wallpaper Backend Findings

## Purpose

This note summarizes findings from testing and discussing different display approaches for the 3D wallpaper engine.

The project currently uses OpenCV for fast testing, but the final goal is a real desktop wallpaper-like experience.

This research compares:

- OpenCV display windows
- PyQt windows
- True Windows wallpaper integration
- Future C++ / Win32 / DirectX direction

---

## Current Rendering Goal

The project is trying to create a view-dependent wallpaper effect.

The engine takes:

```text
webcam face position
```

maps it to:

```text
rendered view index
```

and displays:

```text
the corresponding pre-rendered image frame
```

The desired illusion is a 3D screen/window that reacts to the viewer's head position.

---

## OpenCV Findings

OpenCV has been the best tool for early testing.

It allowed quick implementation of:

- Webcam capture
- Face detection
- Debug windows
- Fullscreen display
- Image sequence rendering
- ESC quit handling
- Tracking visualization
- Frame index testing

### Advantages

OpenCV is useful because it is simple and fast to iterate with.

It is good for:

```text
tracking -> indexing -> rendering -> display
```

testing.

It also makes it easy to create debug views showing:

- Camera feed
- Face rectangle
- Face center dot
- Guide lines
- Raw index
- Smoothed index
- Cache stats
- Grayscale preview
- Tracked face preview

### Limitations

OpenCV fullscreen display is not a real desktop wallpaper.

It creates a fullscreen application window.

This means:

- It is not behind desktop icons
- It is not integrated with the Windows desktop
- It behaves like an app window
- It is not a long-term polished wallpaper backend

### Conclusion

OpenCV is the correct testing backend for now.

It should continue to be used while tuning:

- Tracking
- Indexing
- Caching
- Smoothing
- Preloading
- High-density render behavior

---

## PyQt Findings

PyQt was considered as a possible display and UI solution.

PyQt provides better app/window control than OpenCV.

It is useful for:

- Borderless windows
- Settings panels
- Debug UI
- Preset selection
- Multi-window layouts
- Future user-facing controls

### Advantages

PyQt is better than OpenCV for a polished Python application interface.

It could be used later for:

```text
settings GUI
render preview
debug controls
cache tuning panel
sequence preset selector
```

### Limitations

PyQt by itself does not solve true desktop wallpaper integration.

A PyQt fullscreen borderless window can look like a wallpaper, but it is still an app window.

It does not automatically render behind icons or integrate with the desktop shell.

### Conclusion

PyQt is useful for a future UI layer, not necessarily the final rendering backend.

Recommended future role:

```text
PyQt = settings/debug/control UI
OpenCV = current testing renderer
Win32/DirectX = future real wallpaper backend
```

---

## Windows Desktop Wallpaper Findings

A real Windows live wallpaper is not just a fullscreen window.

It needs to interact with the Windows desktop shell.

Earlier diagnostics inspected the desktop window hierarchy safely.

Relevant desktop window classes included:

```text
Progman
SHELLDLL_DefView
SysListView32
```

A real implementation may need to work with:

```text
WorkerW
Progman
desktop icon layer
Explorer restarts
window parenting
```

### Important Finding

The wallpaper backend should be separated from the tracking/rendering logic.

The engine should continue to produce the correct frame.

The backend should handle where and how that frame is displayed.

---

## Recommended Architecture Direction

The project should remain split into layers.

```text
Tracking layer:
webcam capture, face detection, smoothing

Indexing layer:
face position to render index

Render sequence layer:
cache, preload, frame selection, blending

Display backend layer:
OpenCV now, real wallpaper later

UI layer:
PyQt later for controls/settings
```

This prevents the project from becoming messy.

---

## Backend Comparison

| Backend | Good For | Weakness |
|---|---|---|
| OpenCV | Fast testing and debug display | Not a real wallpaper backend |
| PyQt | UI, settings, borderless windows | Still not true desktop integration |
| Win32 | Desktop window control | More complex |
| DirectX | High-performance rendering | Requires C++/graphics work |
| Python-only | Fast development | Limited for low-level desktop integration |

---

## Current Decision

For now:

```text
Use OpenCV for engine testing.
Do not switch the renderer yet.
```

Later:

```text
Use PyQt for settings/debug UI.
Use Win32/DirectX for real wallpaper integration.
```

---

## Future Research Tasks

1. Investigate safe WorkerW / Progman wallpaper embedding.
2. Test how Explorer restarts affect the wallpaper window.
3. Compare OpenCV fullscreen vs PyQt borderless fullscreen.
4. Explore DirectX texture streaming for image sequences.
5. Research whether Python can remain the tracking layer while C++ handles display.
6. Test IPC between Python tracking engine and a C++ renderer.
7. Benchmark PNG/JPG/WebP decoding for large image sequences.
8. Evaluate GPU upload cost if moving to DirectX.

---

## Summary

OpenCV is currently the right tool for fast development and testing.

PyQt is useful later for UI and control panels.

A true wallpaper backend should be built separately later, most likely using Win32 and DirectX.

The current priority should remain:

```text
make the tracking, indexing, caching, and high-density sequence playback feel correct
```

before moving into the final desktop integration layer.
