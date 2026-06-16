cmake_minimum_required(VERSION 3.20)

project(MediaPipeFaceLandmarkerLiveFeasibility LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

set(MEDIAPIPE_SOURCE_DIR "" CACHE PATH "Path to a google-ai-edge/mediapipe source checkout")
set(MEDIAPIPE_FACE_LANDMARKER_LIBS "" CACHE STRING "Prebuilt MediaPipe Tasks C++ libraries needed for FaceLandmarker")

find_path(
    MEDIAPIPE_INCLUDE_DIR
    NAMES mediapipe/tasks/cc/vision/face_landmarker/face_landmarker.h
    HINTS
        "${MEDIAPIPE_SOURCE_DIR}"
        "${MEDIAPIPE_SOURCE_DIR}/.."
        "C:/dev/vcpkg/installed/x64-windows/include"
    PATH_SUFFIXES include
)

if(NOT MEDIAPIPE_INCLUDE_DIR)
    message(FATAL_ERROR
        "MediaPipe Tasks C++ headers were not found. The current vcpkg/CMake "
        "setup does not appear to provide mediapipe/tasks/cc headers. "
        "Set MEDIAPIPE_SOURCE_DIR to a google-ai-edge/mediapipe source checkout, "
        "or build this experiment with Bazel from inside a MediaPipe checkout."
    )
endif()

if(MEDIAPIPE_FACE_LANDMARKER_LIBS STREQUAL "")
    message(FATAL_ERROR
        "MediaPipe Tasks C++ headers were found, but no link libraries were "
        "provided. MediaPipe Tasks C++ is not currently available here as a "
        "normal CMake/vcpkg package. Provide MEDIAPIPE_FACE_LANDMARKER_LIBS "
        "only if you have produced compatible prebuilt MediaPipe libraries, "
        "otherwise use the BUILD.bazel file from inside a MediaPipe source tree."
    )
endif()

find_package(OpenCV REQUIRED COMPONENTS core imgproc highgui videoio)

add_executable(mediapipe_face_landmarker_live main.cpp)

target_include_directories(
    mediapipe_face_landmarker_live
    PRIVATE
        "${MEDIAPIPE_INCLUDE_DIR}"
)

target_link_libraries(
    mediapipe_face_landmarker_live
    PRIVATE
        ${OpenCV_LIBS}
        ${MEDIAPIPE_FACE_LANDMARKER_LIBS}
)
