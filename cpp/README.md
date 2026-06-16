# C++ Layout

This directory is split by how the code is built and reused.

- `engine/` contains reusable wallpaper engine code: renderer/window glue,
  image sequence loading, cache/preload behavior, smoothing, tracking config,
  and view-index mapping.
- `runners/debug_mouse_runner.cpp` is the normal CMake runner. It keeps the
  current debug mouse/external UDP/MediaPipe-stub runtime path and links
  against the reusable engine sources.
- `mediapipe_bazel/wallpaper_mediapipe_runner/` is the canonical MediaPipe
  Tasks C++ Bazel app. `scripts/run_mediapipe_cpp.ps1` copies it into the
  external MediaPipe checkout, builds it, and runs it.

Build the CMake debug runner from the repo root:

```powershell
cmake -S cpp -B cpp\build
cmake --build cpp\build --target debug_mouse_runner --config Debug
```

Run the MediaPipe C++ workflow from the repo root:

```powershell
.\run_mediapipe_cpp.bat
```
