cmake_minimum_required(VERSION 3.20)

project(ThreeDWallpaperEngineCpp LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

option(HAVE_MEDIAPIPE_CPP "Build with a configured MediaPipe C++ FaceLandmarker integration" OFF)

find_package(OpenCV REQUIRED COMPONENTS core imgproc highgui videoio imgcodecs)

add_executable(debug_mouse_runner
    runners/debug_mouse_runner.cpp
    engine/src/AppConfig.cpp
    engine/src/ExponentialSmoother2D.cpp
    engine/src/ImageSequence.cpp
    engine/src/IndexMapper.cpp
    engine/src/MediaPipeFaceTracker.cpp
    engine/src/SequenceCache.cpp
    engine/src/WallpaperWindow.cpp
)

add_custom_target(wallpaper_mediapipe DEPENDS debug_mouse_runner)

target_include_directories(debug_mouse_runner
    PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/engine/include
)

target_link_libraries(debug_mouse_runner PRIVATE ${OpenCV_LIBS})

if(WIN32)
    target_link_libraries(debug_mouse_runner PRIVATE ws2_32)
endif()

if(HAVE_MEDIAPIPE_CPP)
    target_compile_definitions(debug_mouse_runner PRIVATE HAVE_MEDIAPIPE_CPP)
endif()
