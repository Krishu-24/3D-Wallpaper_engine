# Research Notes: MediaPipe C++ Windows Build and Runtime Setup

## Overview

This document records the problems faced while trying to build and run a C++ MediaPipe FaceLandmarker experiment on Windows for the 3D wallpaper engine. The purpose was not just to run a demo, but to prove that real MediaPipe C++ tracking can eventually replace the temporary `debug_mouse` backend in the C++ wallpaper runner.

The final result was successful: the C++ FaceLandmarker experiment opened the webcam, drew face landmarks, highlighted the `eye_mid` tracking point, and printed FPS.

## Final Working Direction

The latest MediaPipe checkout caused too many Windows/MSVC problems, mainly around C++20 and newer Protobuf dependencies. The solid solution was to stop using the latest checkout and instead use a clean pinned MediaPipe version:

```text
MediaPipe version: v0.10.20
Location: C:\dev\mediapipe
Fresh Bazel cache: C:\bazel_cache_mp1020
```

This avoided some of the latest C++20/protobuf issues and gave a more stable baseline.

## Important Versions and Tools

| Component | Version / Path Used | Notes |
|---|---|---|
| OS | Windows 11 | Main development machine |
| Visual Studio | Visual Studio Community 2026 / VS 18 | Installed Desktop Development with C++ |
| MSVC | `14.51.36231` | Used by Bazel for C++ compilation |
| Python | Python 3.12 | Used by Bazel/MediaPipe tooling |
| Bazel launcher | Bazelisk | Installed through winget |
| Bazel version | Initially forced `7.4.1`, later allowed pinned repo setup | Forced version was cleared for older MediaPipe |
| MediaPipe | `v0.10.20` final working attempt | Latest checkout caused C++20/protobuf issues |
| OpenCV installed | OpenCV 4.12, `vc16` layout | MediaPipe expected OpenCV 3.4.10 style `vc15` paths |
| Model | `models/face_landmarker.task` | Already present inside project repo |
| Shell dependency | Git Bash | Used for `bash` and `awk` during Bazel genrules |
| Developer Mode | Enabled | Required for symlink creation during Bazel dependency setup |

## Why Bazel Was Needed

MediaPipe C++ is not a normal small CMake library. It is a large Google-style C++ project built around Bazel. Building FaceLandmarker pulls in a large dependency graph:

```text
MediaPipe
TensorFlow Lite
Protobuf
Abseil
XNNPACK
pthreadpool
ruy
Eigen
FlatBuffers
gRPC tools
LLVM-related pieces
OpenCV wrapper rules
Python toolchains
```

This is why builds took a long time. The first clean build had to download, generate, compile, and link many dependencies.

## Problems Faced and Fixes

### 1. CMake and MSVC Setup

The first C++ renderer needed CMake and the MSVC compiler. VS Code alone was not enough because it is only an editor. The actual C++ pipeline was:

```text
VS Code → CMake → MSVC/cl.exe → .exe
```

CMake generated the build files, MSVC compiled the C++ code, and the final program was a Windows `.exe`.

### 2. OpenCV Not Found in CMake

The C++ renderer needed OpenCV. vcpkg was used for the project C++ runner, but the MediaPipe Bazel build used its own OpenCV expectations.

For the normal C++ renderer, CMake was run with the vcpkg toolchain:

```powershell
cmake -S . -B build -DCMAKE_TOOLCHAIN_FILE="C:\dev\vcpkg\scripts\buildsystems\vcpkg.cmake"
cmake --build build --config Release
```

### 3. MediaPipe C++ Stub First

The main C++ runner did not immediately include real MediaPipe. A `MediaPipeFaceTracker` stub was created that clearly failed if real MediaPipe C++ was not configured. This avoided silently falling back to Haar cascade.

### 4. Debug Mouse Backend

A `debug_mouse` backend was added so the C++ renderer could be tested without MediaPipe. Mouse position simulated the face/eye point. This validated the full renderer path:

```text
mouse position → smoothing → angle mapping → image index → cache → display
```

This was useful because it separated renderer problems from tracker problems.

### 5. Python MediaPipe Bridge / Shared-Memory Idea

Since Python MediaPipe already worked, one practical idea was to use Python as a tracking sidecar and feed tracking coordinates to the C++ renderer through shared memory, IPC, or another bridge. This would allow:

```text
Python MediaPipe tracker → shared memory / IPC → C++ renderer
```

This remains a valid fallback if direct MediaPipe C++ integration becomes too expensive to maintain.

### 6. Bazel Symlink Error

Bazel failed with:

```text
WinError 1314: A required privilege is not held by the client
```

This happened because Bazel/LLVM needed to create symlinks. Windows Developer Mode was enabled, and the machine was restarted. After that, symlink creation worked.

### 7. OpenCV Expected Wrong Version Layout

MediaPipe expected files like:

```text
C:\opencv\build\x64\vc15\bin\opencv_world3410.dll
C:\opencv\build\x64\vc15\lib\opencv_world3410.lib
```

But the installed OpenCV was:

```text
C:\opencv\build\x64\vc16\bin\opencv_world4120.dll
C:\opencv\build\x64\vc16\lib\opencv_world4120.lib
```

Temporary workaround:

```powershell
New-Item -ItemType Directory -Force "C:\opencv\build\x64\vc15\bin"
New-Item -ItemType Directory -Force "C:\opencv\build\x64\vc15\lib"

Copy-Item "C:\opencv\build\x64\vc16\bin\opencv_world4120.dll" "C:\opencv\build\x64\vc15\bin\opencv_world3410.dll" -Force
Copy-Item "C:\opencv\build\x64\vc16\lib\opencv_world4120.lib" "C:\opencv\build\x64\vc15\lib\opencv_world3410.lib" -Force
```

This was a workaround, not the cleanest long-term solution. For a production build, the correct OpenCV version should be pinned properly.

### 8. Missing Bash / AWK

Bazel needed a Unix-like shell for genrules. It looked for `bash.exe`. Git Bash was already installed, so this was used:

```powershell
$env:BAZEL_SH = "C:\Program Files\Git\bin\bash.exe"
```

### 9. C11 Atomics Error

`pthreadpool` failed with C11 atomics errors such as:

```text
"C atomics require C11 or later"
"C atomic support is not enabled"
```

MSVC needed these C-only flags:

```powershell
--conlyopt=/std:c11
--conlyopt=/experimental:c11atomics
```

### 10. Protobuf MSVC Guard

Protobuf required explicit permission to build with MSVC:

```powershell
--define=protobuf_allow_msvc=true
```

### 11. MediaPipe Macro Error

Newer MediaPipe builds hit:

```text
MP_STATUS_MACROS_IMPL_REM undeclared identifier
```

This came from complicated `MP_ASSIGN_OR_RETURN` macro expansion on MSVC. The workaround was either using:

```powershell
--cxxopt=/Zc:preprocessor
--host_cxxopt=/Zc:preprocessor
```

or manually rewriting certain macro calls. In `v0.10.20`, the main manual patch needed was in `task_api_factory.h`.

### 12. C++20 / Protobuf UntypedMessage Error

The latest MediaPipe checkout pushed C++20, and Protobuf failed with `UntypedMessage` errors under MSVC. This was a major reason to stop using the latest MediaPipe checkout.

The fix was not to keep patching endlessly. The better approach was:

```text
Use pinned MediaPipe v0.10.20
Use fresh Bazel cache
Avoid latest C++20 dependency graph
```

### 13. BUILD.bazel Compatibility Issue

The copied experiment `BUILD.bazel` used newer syntax:

```python
load("@rules_cc//cc:cc_binary.bzl", "cc_binary")
```

Older MediaPipe did not have that file. The fix was to remove the load line and use native `cc_binary`.

### 14. task_api_factory.h Patch

`v0.10.20` had an `#if/#else/#endif` inside an `MP_ASSIGN_OR_RETURN` macro call. MSVC did not handle this correctly with the preprocessor settings.

Original pattern:

```cpp
MP_ASSIGN_OR_RETURN(
    auto runner,
#if !MEDIAPIPE_DISABLE_GPU
    core::TaskRunner::Create(...));
#else
    core::TaskRunner::Create(...));
#endif
```

Rewritten as normal code:

```cpp
#if !MEDIAPIPE_DISABLE_GPU
    auto runner_or = core::TaskRunner::Create(
        std::move(graph_config), std::move(resolver),
        std::move(packets_callback), std::move(default_executor),
        std::move(input_side_packets),
        /*resources=*/nullptr, std::move(error_fn));
#else
    auto runner_or = core::TaskRunner::Create(
        std::move(graph_config), std::move(resolver),
        std::move(packets_callback), std::move(default_executor),
        std::move(input_side_packets), std::move(error_fn));
#endif

    MP_RETURN_IF_ERROR(runner_or.status());
    auto runner = std::move(runner_or.value());

    return std::make_unique<T>(std::move(runner));
```

### 15. Runtime DLL Error

After build success, the exe first exited with:

```text
-1073741515
```

This means:

```text
0xC0000135 = STATUS_DLL_NOT_FOUND
```

The OpenCV DLL was copied beside the built executable:

```powershell
$exeDir = "C:\dev\mediapipe\bazel-bin\mediapipe\experiments\mediapipe_face_landmarker_live"

Copy-Item "C:\opencv\build\x64\vc16\bin\opencv_world4120.dll" $exeDir -Force
Copy-Item "C:\opencv\build\x64\vc15\bin\opencv_world3410.dll" $exeDir -Force
```

After this, the experiment ran successfully.

## Final Successful Run Command

```powershell
cd "C:\dev\mediapipe"

.\bazel-bin\mediapipe\experiments\mediapipe_face_landmarker_live\mediapipe_face_landmarker_live.exe "C:\Users\Arnav Sinha\Desktop\krishu\codes_projects\3D_Wallpaper_engine\models\face_landmarker.task"
```

Successful behavior:

```text
Webcam window opened
Face landmarks were drawn
eye_mid point was highlighted
FPS/debug output printed
```



## Main Lessons

1. MediaPipe C++ on Windows is possible, but setup is fragile.
2. Latest MediaPipe caused C++20 and Protobuf problems with MSVC.
3. Pinning to `v0.10.20` was a better approach than endlessly patching latest.
4. The C++ renderer should keep `debug_mouse` as a fallback backend.
5. Python MediaPipe bridge/shared memory remains a valid fallback if direct C++ integration becomes too expensive.
6. For release, users should never build MediaPipe. They should only receive the compiled `.exe`, required DLLs, model file, and assets.
7. Before any Steam-style release, the app must be tested on a clean Windows machine with no dev tools installed.

## Current Next Step

The immediate next step is to move the successful FaceLandmarker logic into the actual C++ wallpaper runner:

```text
MediaPipe FaceLandmarker experiment → MediaPipeFaceTracker.cpp → real eye_mid tracking → C++ renderer
```

The final architecture should keep three tracking modes:

```text
debug_mouse       for testing renderer
mediapipe_cpp     for final native tracking
python_bridge     optional fallback if needed
```
