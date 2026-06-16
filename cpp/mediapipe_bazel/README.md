# MediaPipe Bazel Apps

These folders are standalone MediaPipe Tasks C++ apps. They are kept separate
from the reusable CMake engine because the working MediaPipe C++ path is Bazel
inside an external MediaPipe checkout.

`wallpaper_mediapipe_runner/` is the canonical MediaPipe Bazel app. The wrapper
script copies it into the external MediaPipe source tree under
`mediapipe/experiments/`, builds it, copies available OpenCV DLLs beside the
executable, and runs it with this repo's `models/face_landmarker.task`.

The older `face_landmarker_api_test/` and `face_landmarker_live_test/` folders
are historical probes. Remove them only after the canonical runner has built and
run successfully on the current machine.
