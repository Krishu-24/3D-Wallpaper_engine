# 3D Wallpaper Engine

A face-tracked view-dependent wallpaper engine that displays pre-rendered image sequences based on the viewer's head position.

The goal of this project is to create a fake 3D screen/window effect by rendering many camera views of a scene in Blender and switching between those views in real time using webcam-based face tracking.

This repository has now moved beyond prototype testing. The current implementation is the beginning of the real engine architecture.

---

## Current Status

The project has moved from a single prototype script into a structured engine.

The current version includes:

- Webcam-based face tracking
- View-dependent image sequence rendering
- Float-based sequence indexing
- Configurable horizontal and vertical index flipping
- Jitter smoothing
- Snap threshold for fast head movement
- LRU image cache
- Background image preloading
- Optional frame blending
- Multithreaded camera capture
- Multithreaded face tracking
- Main-thread OpenCV display
- Prototype-style debug window
- Fullscreen wallpaper display
- ESC key quit handling

---

## Current Architecture

The engine is split into separate responsibilities.

```text
CameraWorker thread:
Continuously captures the latest webcam frame.

TrackingWorker thread:
Continuously detects the face from the latest camera frame.

Main renderer thread:
Uses the latest known tracking result to choose and display the correct rendered frame.

Image cache thread pool:
Loads and preloads image sequence frames in the background.