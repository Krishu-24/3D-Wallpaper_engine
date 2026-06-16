# MediaPipe FaceLandmarker C++ Feasibility Test

This folder is intentionally isolated from the wallpaper runner. It does not
modify `cpp/app/main.cpp`, the `debug_mouse` backend, Python files, or the
current `MediaPipeFaceTracker` stub.

## Goal

Build the smallest useful C++ probe for MediaPipe Tasks FaceLandmarker before
integrating anything into the wallpaper engine.

The test accepts:

```text
mediapipe_face_landmarker_test <path/to/face_landmarker.task> <path/to/image>
```

It prints:

- number of detected faces
- first face landmark count
- selected landmark coordinates needed by the wallpaper tracker:
  - nose tip `1`
  - forehead `10`
  - chin `152`
  - left eye outer `33`
  - left eye inner `133`
  - right eye outer `263`
  - right eye inner `362`
  - derived `eye_mid`
  - derived `face_center`

## Local feasibility result

Current local vcpkg/CMake setup does **not** appear to include MediaPipe Tasks
C++:

- `C:/dev/vcpkg/installed/x64-windows/include/mediapipe` is absent.
- No `face_landmarker.h` was found under
  `C:/dev/vcpkg/installed/x64-windows`.
- The existing project CMake setup only finds OpenCV and related dependencies;
  it does not expose a MediaPipe C++ package or import library.

So this cannot honestly be linked from the current vcpkg setup as-is.

## Dependency reality

The FaceLandmarker Tasks C++ header exists in the MediaPipe source tree at:

```text
mediapipe/tasks/cc/vision/face_landmarker/face_landmarker.h
```

That header exposes `FaceLandmarkerOptions`, `FaceLandmarker::Create`, and
`Detect`/`DetectForVideo`/`DetectAsync` APIs. The upstream Bazel target is:

```text
//mediapipe/tasks/cc/vision/face_landmarker:face_landmarker
```

However, MediaPipe Tasks C++ is not distributed here as a simple vcpkg/CMake
package. The upstream build graph is Bazel-based and pulls in MediaPipe
framework targets, calculators, protobuf-generated targets, Abseil, TensorFlow
Lite, and model/task graph support.

Practical options:

1. Build this experiment inside a `google-ai-edge/mediapipe` source checkout
   with Bazel.
2. Build MediaPipe from source and produce compatible C++ libraries yourself,
   then point the CMake probe at those headers and libraries.
3. Keep using the existing `external_udp` bridge while this dependency work is
   unresolved.

## Bazel route

From a MediaPipe source checkout, copy or sync this folder into:

```text
mediapipe/experiments/mediapipe_face_landmarker_test/
```

Then run something like:

```powershell
bazel build //mediapipe/experiments/mediapipe_face_landmarker_test:mediapipe_face_landmarker_test
```

Then run:

```powershell
bazel-bin/mediapipe/experiments/mediapipe_face_landmarker_test/mediapipe_face_landmarker_test.exe ^
  path\to\face_landmarker.task ^
  path\to\image.jpg
```

Exact Bazel flags may depend on your MediaPipe checkout, OS, compiler, and
whether GPU support is enabled. On desktop CPU builds, MediaPipe examples often
use a CPU-only build define such as `--define MEDIAPIPE_DISABLE_GPU=1`.

## CMake probe

The included `CMakeLists.txt` is a feasibility check, not a promise that
MediaPipe can be consumed as a normal CMake dependency.

Try:

```powershell
cmake -S cpp\experiments\mediapipe_face_landmarker_test ^
  -B cpp\experiments\mediapipe_face_landmarker_test\build
```

Expected result in the current repo: configuration fails because the MediaPipe
Tasks C++ header and link libraries are not present.

If you later have a MediaPipe source checkout and compatible prebuilt
libraries, configure with:

```powershell
cmake -S cpp\experiments\mediapipe_face_landmarker_test ^
  -B cpp\experiments\mediapipe_face_landmarker_test\build ^
  -DMEDIAPIPE_SOURCE_DIR=C:\path\to\mediapipe ^
  -DMEDIAPIPE_FACE_LANDMARKER_LIBS="path\to\your\mediapipe_face_landmarker.lib;..."
```

Do not set `MEDIAPIPE_FACE_LANDMARKER_LIBS` unless the libraries were built
from the same compatible MediaPipe dependency graph. Headers alone are not
enough.

## Sources checked

- Google AI Edge Face Landmarker guide documents the task behavior and model
  bundle contents, including 478 face landmarks.
- MediaPipe framework install docs describe a Bazel-based source checkout and
  build flow.
- MediaPipe source contains the C++ Tasks FaceLandmarker header and Bazel
  target under `mediapipe/tasks/cc/vision/face_landmarker`.
