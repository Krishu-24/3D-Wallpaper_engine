#pragma once

#include <filesystem>
#include <optional>
#include <string>
#include <utility>

enum class TrackingBackend {
    MediaPipe,
    DebugMouse,
    ExternalUdp,
};

struct SequenceConfig {
    std::filesystem::path folder;
    int yViews = 121;
    int zViews = 35;
    std::string filenamePattern = "view_{frame:04d}.png";
    int startFrame = 1;
};

struct CacheConfig {
    int maxCacheSize = 300;
    int preloadRadiusY = 4;
    int preloadRadiusZ = 2;
    int maxWorkers = 4;
    bool enableBlending = false;
    std::optional<std::pair<int, int>> resizeTo;
};

struct TrackingConfig {
    TrackingBackend backend = TrackingBackend::MediaPipe;
    int cameraIndex = 0;
    double smoothingAmount = 0.40;
    double snapDistance = 8.0;
    bool mirrorCamera = true;
    bool flipX = false;
    bool flipZ = true;
    std::pair<int, int> minFaceSize = {60, 60};
    double scaleFactor = 1.2;
    int minNeighbors = 5;
    double cameraMeasureDistanceCm = 198.0;
    double cameraVisibleWidthCm = 204.0;
    double cameraVisibleHeightCm = 158.0;
    double renderYAngleMin = -25.0;
    double renderYAngleMax = 25.0;
    double renderZAngleMin = -10.0;
    double renderZAngleMax = 10.0;

    double cameraHorizontalFov() const;
    double cameraVerticalFov() const;
};

struct ThreadingConfig {
    double cameraPollSleep = 0.001;
    double trackingPollSleep = 0.005;
    double maxTrackingFps = 60.0;
};

struct ExternalTrackingConfig {
    int udpPort = 5055;
    int frameWidth = 640;
    int frameHeight = 480;
    double packetTimeoutSeconds = 0.50;
    double minConfidence = 0.0;
};

struct WindowConfig {
    std::string windowName = "3D Wallpaper Engine - MediaPipe";
    std::string debugWindowName = "MediaPipe Landmark Debug";
    bool showDebugWindow = true;
    bool fullscreen = true;
};

struct AppConfig {
    SequenceConfig sequence;
    CacheConfig cache;
    TrackingConfig tracking;
    ThreadingConfig threading;
    ExternalTrackingConfig externalTracking;
    WindowConfig window;
    std::filesystem::path mediaPipeModelPath;
    std::filesystem::path projectRoot;

    static AppConfig load();
};
