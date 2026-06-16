# Wallpaper MediaPipe Runner

Canonical Bazel-compatible MediaPipe C++ app for this repo.

This folder is copied by `cpp/scripts/run_mediapipe_cpp.ps1` into the external
MediaPipe checkout at:

```text
C:\dev\mediapipe\mediapipe\experiments\wallpaper_mediapipe_runner
```

The Bazel target is:

```text
//mediapipe/experiments/wallpaper_mediapipe_runner:wallpaper_mediapipe_runner
```

The app runs the working live FaceLandmarker webcam flow, extracts `eye_mid`,
then feeds that point through the existing C++ engine classes:

```text
webcam -> FaceLandmarker -> eye_mid -> IndexMapper -> ExponentialSmoother2D -> SequenceCache -> WallpaperWindow
```

The wrapper script also copies `cpp/engine/` beside this app before building so
Bazel compiles the reusable engine sources directly.
