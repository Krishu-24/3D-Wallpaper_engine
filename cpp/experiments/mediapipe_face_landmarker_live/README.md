# MediaPipe FaceLandmarker Live C++ Experiment

This is a standalone dependency and webcam experiment. It does not modify or
connect to the wallpaper renderer.

Untouched by this experiment:

- `cpp/app/main.cpp`
- existing C++ wallpaper runner
- `debug_mouse` backend
- `external_udp` backend
- Python files
- current `MediaPipeFaceTracker` stub

## Goal

Run real MediaPipe Tasks C++ FaceLandmarker on live webcam frames and display an
OpenCV debug window similar to the Python MediaPipe debug view.

The demo:

- opens the webcam with OpenCV `VideoCapture`
- reads frames continuously
- converts OpenCV BGR frames to RGB MediaPipe `Image` input
- runs `FaceLandmarker::DetectForVideo` in `RunningMode::VIDEO`
- draws all detected landmarks
- draws the same default tracking point used by the Python tracker:
  `eye_mid = midpoint(LEFT_EYE_INNER[133], RIGHT_EYE_INNER[362])`
- also labels nose, forehead, chin, eye inner/outer points, and face center
- prints FPS/frame time once per second
- shows a normal OpenCV window
- quits on `q` or `Esc`

## Landmark Logic

The landmark indices match `src/mediapipe_core/mediapipe_tracking_worker.py`:

```text
NOSE_TIP = 1
FOREHEAD = 10
CHIN = 152
LEFT_EYE_OUTER = 33
LEFT_EYE_INNER = 133
RIGHT_EYE_OUTER = 263
RIGHT_EYE_INNER = 362
```

The wallpaper tracker currently uses `eye_mid` by default, so this demo draws
that point as `TRACK eye_mid`.

## Why This Likely Cannot Build With Current vcpkg/CMake

The local vcpkg install used by the current C++ wallpaper runner does not appear
to include MediaPipe Tasks C++:

- `C:/dev/vcpkg/installed/x64-windows/include/mediapipe` is absent.
- No `face_landmarker.h` was found under
  `C:/dev/vcpkg/installed/x64-windows`.
- The current CMake project finds OpenCV, but not a MediaPipe C++ package or
  import library.

MediaPipe Tasks C++ exists in the upstream source tree, but it is not exposed in
this repo as a simple vcpkg/CMake dependency. The FaceLandmarker target depends
on a large Bazel graph: MediaPipe framework code, task graph code, calculators,
protobuf-generated targets, Abseil, TensorFlow Lite, and related support code.

The included `CMakeLists.txt` is therefore only a feasibility probe. It fails
honestly unless you provide both MediaPipe headers and compatible prebuilt
libraries.

## Required MediaPipe API

This experiment uses the real C++ Tasks header:

```cpp
#include "mediapipe/tasks/cc/vision/face_landmarker/face_landmarker.h"
```

It also uses:

```cpp
#include "mediapipe/tasks/cc/vision/utils/image_utils.h"
```

for `CreateImageFromBuffer`, which converts the RGB OpenCV frame into a
MediaPipe `Image`.

## Recommended Bazel Build Route

Clone MediaPipe:

```powershell
git clone https://github.com/google-ai-edge/mediapipe.git
cd mediapipe
```

Copy this experiment folder into the MediaPipe checkout at:

```text
mediapipe/experiments/mediapipe_face_landmarker_live/
```

That means the copied files should live at:

```text
<mediapipe repo root>/mediapipe/experiments/mediapipe_face_landmarker_live/main.cpp
<mediapipe repo root>/mediapipe/experiments/mediapipe_face_landmarker_live/BUILD.bazel
```

Build from the MediaPipe repo root:

```powershell
bazel build --define MEDIAPIPE_DISABLE_GPU=1 //mediapipe/experiments/mediapipe_face_landmarker_live:mediapipe_face_landmarker_live
```

Depending on your MediaPipe checkout and platform, you may need to adjust
OpenCV configuration in MediaPipe's Bazel setup. The target depends on:

```text
//third_party:opencv
//mediapipe/tasks/cc/vision/face_landmarker:face_landmarker
//mediapipe/tasks/cc/vision/utils:image_utils
```

## Model File

Use the same model bundle already used by this project, for example:

```text
models/face_landmarker.task
```

When running inside the MediaPipe checkout, either:

- pass an absolute path to this repo's `models/face_landmarker.task`, or
- copy the model into the MediaPipe checkout and pass that path.

## Run Command

From the MediaPipe repo root after a successful Bazel build:

```powershell
bazel-bin\mediapipe\experiments\mediapipe_face_landmarker_live\mediapipe_face_landmarker_live.exe ^
  C:\path\to\3D_Wallpaper_engine\models\face_landmarker.task
```

Optional camera index:

```powershell
bazel-bin\mediapipe\experiments\mediapipe_face_landmarker_live\mediapipe_face_landmarker_live.exe ^
  C:\path\to\face_landmarker.task ^
  1
```

## Expected Behavior

Console:

```text
[INFO] MediaPipe C++ FaceLandmarker live experiment started.
[INFO] Model: ...
[INFO] Camera index: 0
[INFO] Press q or ESC in the OpenCV window to quit.
[INFO] FPS=..., frame_ms=..., faces=...
```

Window:

- webcam feed
- small green dots for all face landmarks
- labels for nose, forehead, chin, eye points, and face center
- red `TRACK eye_mid` point matching the Python tracker's default point
- FPS/frame-time overlay at the bottom

Quit with `q` or `Esc`.

## CMake Feasibility Probe

From this repo root:

```powershell
cmake -S cpp\experiments\mediapipe_face_landmarker_live ^
  -B cpp\experiments\mediapipe_face_landmarker_live\build
```

Expected current result: configuration fails because MediaPipe Tasks C++ headers
and link libraries are not present in the current vcpkg/CMake setup.

If you later produce compatible MediaPipe C++ libraries yourself:

```powershell
cmake -S cpp\experiments\mediapipe_face_landmarker_live ^
  -B cpp\experiments\mediapipe_face_landmarker_live\build ^
  -DMEDIAPIPE_SOURCE_DIR=C:\path\to\mediapipe ^
  -DMEDIAPIPE_FACE_LANDMARKER_LIBS="path\to\your\mediapipe_face_landmarker.lib;..."
```

Headers alone are not enough; the link libraries must come from a compatible
MediaPipe build graph.

## References

- FaceLandmarker C++ API:
  https://github.com/google-ai-edge/mediapipe/blob/master/mediapipe/tasks/cc/vision/face_landmarker/face_landmarker.h
- FaceLandmarker Bazel target:
  https://github.com/google-ai-edge/mediapipe/blob/master/mediapipe/tasks/cc/vision/face_landmarker/BUILD
- MediaPipe framework installation/build docs:
  https://developers.google.com/edge/mediapipe/framework/getting_started/install
