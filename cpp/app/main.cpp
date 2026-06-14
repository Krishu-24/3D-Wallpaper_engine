#include <atomic>
#include <chrono>
#include <cmath>
#include <exception>
#include <iostream>
#include <memory>
#include <optional>
#include <stdexcept>
#include <thread>
#include <utility>

#include <opencv2/highgui.hpp>
#include <opencv2/imgproc.hpp>
#include <opencv2/videoio.hpp>

#include "AppConfig.hpp"
#include "ExponentialSmoother2D.hpp"
#include "ImageSequence.hpp"
#include "IndexMapper.hpp"
#include "MediaPipeFaceTracker.hpp"
#include "SequenceCache.hpp"
#include "WallpaperWindow.hpp"

namespace {

struct DebugTrackingState {
    std::atomic<bool> hasMouse{false};
    std::atomic<int> mouseX{0};
    std::atomic<int> mouseY{0};
};

struct DebugTrackingSample {
    cv::Rect faceBox;
    MediaPipeDebugData debugData;
};

const char* trackingBackendName(TrackingBackend backend) {
    switch (backend) {
    case TrackingBackend::DebugMouse:
        return "debug_mouse";
    case TrackingBackend::MediaPipe:
    default:
        return "mediapipe";
    }
}

void onDebugMouse(int event, int x, int y, int, void* userData) {
    if (event != cv::EVENT_MOUSEMOVE && event != cv::EVENT_LBUTTONDOWN && event != cv::EVENT_RBUTTONDOWN) {
        return;
    }

    auto* state = static_cast<DebugTrackingState*>(userData);
    if (!state) {
        return;
    }

    state->mouseX.store(x);
    state->mouseY.store(y);
    state->hasMouse.store(true);
}

DebugTrackingSample makeDebugTrackingSample(
    const cv::Mat& frame,
    const TrackingConfig& tracking,
    const DebugTrackingState& state,
    int frameId) {
    const int frameWidth = frame.cols;
    const int frameHeight = frame.rows;
    int centerX = frameWidth / 2;
    int centerY = frameHeight / 2;

    if (state.hasMouse.load()) {
        centerX = std::max(0, std::min(frameWidth - 1, state.mouseX.load()));
        centerY = std::max(0, std::min(frameHeight - 1, state.mouseY.load()));
    } else {
        const double t = static_cast<double>(frameId) * 0.035;
        centerX = static_cast<int>((frameWidth / 2.0) + std::sin(t) * frameWidth * 0.35);
        centerY = static_cast<int>((frameHeight / 2.0) + std::cos(t * 0.7) * frameHeight * 0.25);
    }

    const int boxWidth = std::max(1, tracking.minFaceSize.first);
    const int boxHeight = std::max(1, tracking.minFaceSize.second);
    cv::Rect faceBox(centerX - boxWidth / 2, centerY - boxHeight / 2, boxWidth, boxHeight);
    faceBox &= cv::Rect(0, 0, frameWidth, frameHeight);

    MediaPipeDebugData debugData;
    debugData.nose = {centerX, centerY};
    debugData.eyeMid = {centerX, centerY};
    debugData.faceCenter = {centerX, centerY};
    debugData.forehead = {centerX, std::max(0, centerY - boxHeight / 2)};
    debugData.chin = {centerX, std::min(frameHeight - 1, centerY + boxHeight / 2)};
    debugData.leftEyeInner = {std::max(0, centerX - boxWidth / 6), std::max(0, centerY - boxHeight / 8)};
    debugData.rightEyeInner = {std::min(frameWidth - 1, centerX + boxWidth / 6), std::max(0, centerY - boxHeight / 8)};
    debugData.leftEyeOuter = {std::max(0, centerX - boxWidth / 3), std::max(0, centerY - boxHeight / 8)};
    debugData.rightEyeOuter = {std::min(frameWidth - 1, centerX + boxWidth / 3), std::max(0, centerY - boxHeight / 8)};
    debugData.trackingPixel = {centerX, centerY};
    debugData.trackingPoint = state.hasMouse.load() ? "debug_mouse" : "debug_synthetic";
    debugData.frameWidth = frameWidth;
    debugData.frameHeight = frameHeight;
    debugData.noseNorm = {static_cast<double>(centerX) / frameWidth, static_cast<double>(centerY) / frameHeight};
    debugData.eyeMidNorm = debugData.noseNorm;
    debugData.faceCenterNorm = debugData.noseNorm;

    return {faceBox, debugData};
}

bool isReasonableFaceBox(
    const std::optional<cv::Rect>& faceBox,
    const std::optional<cv::Rect>& lastValidFaceBox) {
    if (!faceBox.has_value()) {
        return false;
    }
    if (!lastValidFaceBox.has_value()) {
        return true;
    }

    const auto& box = *faceBox;
    const auto& last = *lastValidFaceBox;
    const double cx = box.x + box.width / 2.0;
    const double cy = box.y + box.height / 2.0;
    const double lastCx = last.x + last.width / 2.0;
    const double lastCy = last.y + last.height / 2.0;

    if (std::abs(cx - lastCx) > 180.0 || std::abs(cy - lastCy) > 180.0) {
        return false;
    }

    const double oldArea = static_cast<double>(last.width * last.height);
    const double newArea = static_cast<double>(box.width * box.height);
    if (oldArea <= 0.0) {
        return true;
    }

    const double sizeChange = std::abs(newArea - oldArea) / oldArea;
    return sizeChange <= 0.55;
}

void printStartupConfig(const AppConfig& config) {
    std::cout << "[INFO] Starting MediaPipe wallpaper renderer.\n";
    std::cout << "[INFO] Reusing old camera, cache, indexing, smoothing, threading, and render pipeline semantics.\n";
    std::cout << "[INFO] Tracking backend: " << trackingBackendName(config.tracking.backend) << '\n';
    if (config.tracking.backend == TrackingBackend::MediaPipe) {
        std::cout << "[INFO] MediaPipe tracker selected as the intended final tracking path.\n";
        std::cout << "[INFO] MediaPipe debug view uses landmarks.\n";
    } else {
        std::cout << "[INFO] Debug tracker selected: mouse in debug window, synthetic point until mouse input arrives.\n";
        std::cout << "[INFO] MediaPipeFaceTracker stub remains unused in this temporary mode.\n";
    }
    std::cout << "[INFO] Sequence: " << config.sequence.yViews << " x " << config.sequence.zViews << '\n';
    std::cout << "[INFO] Camera FOV from config: H=" << config.tracking.cameraHorizontalFov()
              << " deg, V=" << config.tracking.cameraVerticalFov() << " deg\n";
    std::cout << "[INFO] Render angle range from config: Y=" << config.tracking.renderYAngleMin
              << " to " << config.tracking.renderYAngleMax << " deg, Z="
              << config.tracking.renderZAngleMin << " to " << config.tracking.renderZAngleMax << " deg\n";
    std::cout << "[INFO] Cache from config: max=" << config.cache.maxCacheSize
              << ", preload_y=" << config.cache.preloadRadiusY
              << ", preload_z=" << config.cache.preloadRadiusZ
              << ", workers=" << config.cache.maxWorkers
              << ", blending=" << (config.cache.enableBlending ? "True" : "False") << '\n';
}

} // namespace

int main() {
    try {
        AppConfig config = AppConfig::load();
        printStartupConfig(config);

        const bool useDebugTracker = config.tracking.backend == TrackingBackend::DebugMouse;

        cv::VideoCapture camera;
        if (!useDebugTracker) {
            camera.open(config.tracking.cameraIndex);
            if (!camera.isOpened()) {
                throw std::runtime_error("Could not open webcam.");
            }
        }

        std::unique_ptr<MediaPipeFaceTracker> tracker;
        if (!useDebugTracker) {
            tracker = std::make_unique<MediaPipeFaceTracker>(
                config.mediaPipeModelPath.string(),
                cv::Size(config.tracking.minFaceSize.first, config.tracking.minFaceSize.second),
                0.5,
                0.5,
                0.5,
                "eye_mid");
        }

        ExponentialSmoother2D smoother(
            config.tracking.smoothingAmount,
            config.tracking.snapDistance,
            0.60,
            0.45);

        IndexMapper mapper(config.sequence, config.tracking);
        ImageSequence imageSequence(
            config.sequence.folder,
            config.sequence.yViews,
            config.sequence.zViews,
            config.sequence.filenamePattern,
            config.sequence.startFrame,
            config.cache.resizeTo);
        SequenceCache sequenceCache(
            std::move(imageSequence),
            config.cache.maxCacheSize,
            config.cache.preloadRadiusY,
            config.cache.preloadRadiusZ,
            config.cache.enableBlending,
            config.cache.maxWorkers);
        WallpaperWindow window(config.window);

        double lastDisplayY = (config.sequence.yViews - 1) / 2.0;
        double lastDisplayZ = (config.sequence.zViews - 1) / 2.0;
        std::optional<double> rawY;
        std::optional<double> rawZ;
        std::optional<cv::Rect> lastValidFaceBox;
        DebugTrackingState debugTrackingState;

        window.setup();
        if (useDebugTracker && config.window.showDebugWindow) {
            cv::setMouseCallback(config.window.debugWindowName, onDebugMouse, &debugTrackingState);
        }

        std::cout << "[INFO] Wallpaper renderer started.\n";
        if (useDebugTracker) {
            std::cout << "[INFO] Debug tracker active. Move the mouse inside the debug window to drive the viewpoint.\n";
        } else {
            std::cout << "[INFO] Camera capture active.\n";
            std::cout << "[INFO] MediaPipe tracking active.\n";
        }
        std::cout << "[INFO] Image cache preload thread pool active.\n";
        std::cout << "[INFO] Press ESC to quit.\n";

        int frameId = 0;
        while (true) {
            cv::Mat cameraFrame;
            if (useDebugTracker) {
                cameraFrame = cv::Mat(540, 960, CV_8UC3, cv::Scalar(18, 18, 18));
            } else {
                const bool ok = camera.read(cameraFrame);
                if (!ok || cameraFrame.empty()) {
                    std::this_thread::sleep_for(std::chrono::milliseconds(5));
                    if (window.waitKey(1) == 27) {
                        break;
                    }
                    continue;
                }
            }

            ++frameId;
            if (!useDebugTracker && config.tracking.mirrorCamera) {
                cv::flip(cameraFrame, cameraFrame, 1);
            }

            std::optional<cv::Rect> faceBox;
            std::optional<MediaPipeDebugData> debugData;
            if (useDebugTracker) {
                const auto sample = makeDebugTrackingSample(
                    cameraFrame,
                    config.tracking,
                    debugTrackingState,
                    frameId);
                faceBox = sample.faceBox;
                debugData = sample.debugData;
            } else {
                faceBox = tracker->detect(cameraFrame);
                debugData = tracker->latestDebugData();
                if (!isReasonableFaceBox(faceBox, lastValidFaceBox)) {
                    faceBox.reset();
                    debugData.reset();
                } else {
                    lastValidFaceBox = faceBox;
                }
            }

            double smoothedY = lastDisplayY;
            double smoothedZ = lastDisplayZ;
            if (faceBox.has_value()) {
                const auto [mappedY, mappedZ] = mapper.faceBoxToSequenceIndices(
                    *faceBox,
                    cameraFrame.cols,
                    cameraFrame.rows);
                rawY = mappedY;
                rawZ = mappedZ;

                const auto smoothed = smoother.update(mappedY, mappedZ);
                smoothedY = smoothed.first;
                smoothedZ = smoothed.second;
                lastDisplayY = smoothedY;
                lastDisplayZ = smoothedZ;
            }

            cv::Mat displayFrame = sequenceCache.getFrame(lastDisplayY, lastDisplayZ);
            window.showWallpaper(displayFrame);
            window.showDebug(
                cameraFrame,
                faceBox,
                debugData,
                faceBox.has_value() ? rawY : std::nullopt,
                faceBox.has_value() ? rawZ : std::nullopt,
                smoothedY,
                smoothedZ,
                sequenceCache.cacheInfo(),
                config.sequence.yViews,
                config.sequence.zViews,
                frameId);

            if (window.waitKey(1) == 27) {
                break;
            }
        }

        sequenceCache.shutdown();
        if (tracker) {
            tracker->close();
        }
        if (camera.isOpened()) {
            camera.release();
        }
        window.destroyAll();
        return 0;
    } catch (const std::exception& e) {
        std::cerr << "[ERROR] " << e.what() << '\n';
        return 1;
    }
}
