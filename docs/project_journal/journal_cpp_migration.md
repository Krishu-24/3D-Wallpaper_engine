# Journal: C++ Migration Progress for 3D Wallpaper Engine

## Purpose

The goal of this migration was to move the performance-heavy parts of the 3D wallpaper engine from Python to C++, while keeping the same behavior that already worked in the Python version. The main motivation was smoother rendering, lower latency, and a cleaner path toward a proper desktop application later.

The Python version was already useful because it proved the core idea: track the user's face or eye position, map that position into a render angle, and display the correct pre-rendered frame from the image sequence. The problem was that the full Python pipeline was becoming heavy, especially with large image sequences like `121 x 35`, caching, smoothing, and real-time webcam tracking.

## Python Baseline

Before starting C++, the Python version had these working pieces:

- OpenCV camera capture
- Haar cascade tracking first, then MediaPipe face tracking
- Eye-center or face-center extraction
- Exponential smoothing
- Angle mapping using camera/render config values
- Image-sequence indexing
- LRU image cache and preloading
- Wallpaper/debug display using OpenCV/PyQt style experiments

This version proved the math and the user experience, but the next target was speed and cleaner runtime behavior.

## Initial C++ Migration

The first C++ version was created under the project’s `cpp/` folder. The structure separated headers, source files, and app entry point:

```text
cpp/
├── CMakeLists.txt
├── runners/debug_mouse_runner.cpp
├── engine/include/wallpaper_engine/
│   ├── AppConfig.hpp
│   ├── IndexMapper.hpp
│   ├── ExponentialSmoother2D.hpp
│   ├── ImageSequence.hpp
│   ├── SequenceCache.hpp
│   ├── MediaPipeFaceTracker.hpp
│   └── WallpaperWindow.hpp
└── engine/src/
    ├── AppConfig.cpp
    ├── IndexMapper.cpp
    ├── ExponentialSmoother2D.cpp
    ├── ImageSequence.cpp
    ├── SequenceCache.cpp
    ├── MediaPipeFaceTracker.cpp
    └── WallpaperWindow.cpp
```

The C++ runner ported the important logic from Python:

- `.env` based config loading
- camera/render FOV values
- render-angle mapping
- smoothing
- image-sequence indexing
- LRU-style cache
- debug display window
- preload behavior
- frame display loop

CMake was used because the C++ project has many files and dependencies. VS Code is only the editor, while CMake creates the build plan, MSVC compiles the code, and the final result is a `.exe`.

## Debug Mouse Backend

Before MediaPipe C++ was available, a `debug_mouse` backend was added. This was important because it let us test the whole C++ render pipeline without depending on face tracking yet.

The mouse position acted like a fake face/eye landmark. It passed through the same downstream path:

```text
mouse position → smoothing → angle mapping → image index → cache → display
```

This proved that the renderer, smoother, index mapper, and cache were working in C++. It also showed that the C++ version felt much smoother than the Python version when moving around quickly. The loading value increased on big jumps because the cache had to catch up, but this was expected behavior.

## Python-to-C++ Bridge / Shared-Memory Idea

A bridge idea was also considered where Python MediaPipe tracking could feed the C++ renderer. The reason was practical: Python MediaPipe already worked, while C++ MediaPipe was difficult to build on Windows.

The idea was:

```text
Python MediaPipe tracker → shared memory / IPC / external bridge → C++ renderer
```

This would let Python handle tracking while C++ handled the fast rendering pipeline. It is still a useful fallback strategy because it avoids fighting MediaPipe C++ during early development. However, the long-term cleaner plan is still to get real C++ tracking working directly.

## MediaPipe C++ Experiment

After the debug mouse backend worked, the next step was an isolated MediaPipe C++ FaceLandmarker experiment. This was intentionally kept separate from the main wallpaper runner so that build issues would not break the working project.

Experiment path in the project repo:

```text
cpp/mediapipe_bazel/face_landmarker_live_test/
```

The experiment used:

- OpenCV webcam capture
- MediaPipe FaceLandmarker C++ API
- `face_landmarker.task`
- live landmark drawing
- highlighted `eye_mid` tracking point
- FPS/frame-time printing

After a long Windows/Bazel setup process, the experiment finally built and ran successfully. The webcam opened, landmarks were drawn, the `eye_mid` point was highlighted, and FPS was printed.

## Current Status

The current state is:

- Python MediaPipe wallpaper runner works.
- C++ renderer pipeline works.
- `debug_mouse` backend works and validates the C++ renderer path.
- MediaPipe C++ FaceLandmarker experiment builds and runs.
- The main C++ wallpaper runner still needs real MediaPipe tracking integrated into it.

## Why This Matters

This milestone proves that the project can move toward a real C++ desktop engine. The debug mouse backend proved the renderer side, and the isolated MediaPipe C++ experiment proved the tracking side. The next step is to combine them carefully.

## Next Work

The next engineering steps are:

1. Save and document the successful MediaPipe build setup.
2. Keep MediaPipe source external, not inside the project repo.
3. Port the working FaceLandmarker logic into `MediaPipeFaceTracker.cpp`.
4. Replace the `debug_mouse` backend with real `eye_mid` output.
5. Keep `debug_mouse` as a fallback testing backend.
6. Package DLLs and model files properly before any public release.
7. Test the final app on a clean Windows install with no dev tools.


