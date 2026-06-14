cmake_minimum_required(VERSION 3.20)

project(ThreeDWallpaperEngineCpp LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

option(HAVE_MEDIAPIPE_CPP "Build with a configured MediaPipe C++ FaceLandmarker integration" OFF)

find_package(OpenCV REQUIRED COMPONENTS core imgproc highgui videoio imgcodecs)

add_executable(wallpaper_mediapipe
    app/main.cpp
    src/AppConfig.cpp
    src/ExponentialSmoother2D.cpp
    src/ImageSequence.cpp
    src/IndexMapper.cpp
    src/MediaPipeFaceTracker.cpp
    src/SequenceCache.cpp
    src/WallpaperWindow.cpp
)

target_include_directories(wallpaper_mediapipe
    PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/include
)

target_link_libraries(wallpaper_mediapipe PRIVATE ${OpenCV_LIBS})

if(HAVE_MEDIAPIPE_CPP)
    target_compile_definitions(wallpaper_mediapipe PRIVATE HAVE_MEDIAPIPE_CPP)
endif()
