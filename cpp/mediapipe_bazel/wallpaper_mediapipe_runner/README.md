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

The app currently runs the working live FaceLandmarker webcam flow and uses the
same landmark logic as the earlier live test.
