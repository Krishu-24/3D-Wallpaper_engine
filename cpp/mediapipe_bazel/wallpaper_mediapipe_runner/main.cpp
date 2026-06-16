#include <algorithm>
#include <atomic>
#include <chrono>
#include <cstdint>
#include <cstdlib>
#include <exception>
#include <iomanip>
#include <iostream>
#include <memory>
#include <mutex>
#include <optional>
#include <sstream>
#include <stdexcept>
#include <string>
#include <thread>
#include <utility>
#include <vector>

#include <opencv2/core.hpp>
#include <opencv2/imgproc.hpp>
#include <opencv2/videoio.hpp>

#include "absl/status/statusor.h"
#include "mediapipe/tasks/cc/core/base_options.h"
#include "mediapipe/tasks/cc/vision/core/running_mode.h"
#include "mediapipe/tasks/cc/vision/face_landmarker/face_landmarker.h"
#include "mediapipe/tasks/cc/vision/utils/image_utils.h"
#include "wallpaper_engine/AppConfig.hpp"
#include "wallpaper_engine/ExponentialSmoother2D.hpp"
#include "wallpaper_engine/ImageSequence.hpp"
#include "wallpaper_engine/IndexMapper.hpp"
#include "wallpaper_engine/MediaPipeFaceTracker.hpp"
#include "wallpaper_engine/SequenceCache.hpp"
#include "wallpaper_engine/WallpaperWindow.hpp"

namespace {

// Same landmark indices used by src/mediapipe_core/mediapipe_tracking_worker.py.
constexpr int kNoseTip = 1;
constexpr int kForehead = 10;
constexpr int kChin = 152;
constexpr int kLeftEyeOuter = 33;
constexpr int kLeftEyeInner = 133;
constexpr int kRightEyeOuter = 263;
constexpr int kRightEyeInner = 362;
constexpr int kLogEveryFrames = 60;

using Landmark = mediapipe::tasks::components::containers::NormalizedLandmark;
using FaceLandmarker = mediapipe::tasks::vision::face_landmarker::FaceLandmarker;
using FaceLandmarkerOptions = mediapipe::tasks::vision::face_landmarker::FaceLandmarkerOptions;
using FaceLandmarkerResult = mediapipe::tasks::vision::face_landmarker::FaceLandmarkerResult;
using RunningMode = mediapipe::tasks::vision::core::RunningMode;

struct TrackingSample {
    cv::Rect faceBox;
    MediaPipeDebugData debugData;
};

struct TimingStats {
    double mappingMs = 0.0;
    double cacheMs = 0.0;
    double displayMs = 0.0;
    double totalMs = 0.0;
    double maxTotalMs = 0.0;
    int samples = 0;

    void add(
        double mapping,
        double cache,
        double display,
        double total) {
        mappingMs += mapping;
        cacheMs += cache;
        displayMs += display;
        totalMs += total;
        maxTotalMs = std::max(maxTotalMs, total);
        ++samples;
    }

    void reset() {
        *this = {};
    }
};

struct SharedTrackingState {
    std::mutex mutex;
    std::optional<TrackingSample> latestSample;
    cv::Mat latestCameraFrame;
    std::chrono::steady_clock::time_point latestTrackingTime{};
    std::uint64_t trackingUpdateCounter = 0;
    int latestFaceCount = 0;
    double latestInferenceMs = 0.0;
    std::string error;
};

struct ThreadStopper {
    std::atomic<bool>& stop;
    std::thread& worker;

    ~ThreadStopper() {
        stop.store(true);
        if (worker.joinable()) {
            worker.join();
        }
    }
};

cv::Point landmarkToPixel(const Landmark& landmark, int width, int height) {
    const int x = std::clamp(static_cast<int>(landmark.x * width), 0, width - 1);
    const int y = std::clamp(static_cast<int>(landmark.y * height), 0, height - 1);
    return {x, y};
}

bool hasIndex(const std::vector<Landmark>& landmarks, int index) {
    return index >= 0 && static_cast<size_t>(index) < landmarks.size();
}

cv::Point averagePoint(const cv::Point& a, const cv::Point& b) {
    return {(a.x + b.x) / 2, (a.y + b.y) / 2};
}

cv::Point2d averagePoint(const cv::Point2d& a, const cv::Point2d& b) {
    return {(a.x + b.x) / 2.0, (a.y + b.y) / 2.0};
}

std::string fixed(double value, int precision) {
    std::ostringstream stream;
    stream << std::fixed << std::setprecision(precision) << value;
    return stream.str();
}

int64_t millisecondsSince(const std::chrono::steady_clock::time_point& start) {
    return std::chrono::duration_cast<std::chrono::milliseconds>(
               std::chrono::steady_clock::now() - start)
        .count();
}

double elapsedMs(
    const std::chrono::steady_clock::time_point& start,
    const std::chrono::steady_clock::time_point& end) {
    return std::chrono::duration<double, std::milli>(end - start).count();
}

cv::Rect makeTrackingBox(const cv::Point& center, const TrackingConfig& tracking, int frameWidth, int frameHeight) {
    const int boxWidth = std::max(1, tracking.minFaceSize.first);
    const int boxHeight = std::max(1, tracking.minFaceSize.second);
    cv::Rect box(center.x - boxWidth / 2, center.y - boxHeight / 2, boxWidth, boxHeight);
    box &= cv::Rect(0, 0, frameWidth, frameHeight);
    return box;
}

std::optional<TrackingSample> makeTrackingSample(
    const FaceLandmarkerResult& result,
    const TrackingConfig& tracking,
    int frameWidth,
    int frameHeight) {
    if (result.face_landmarks.empty()) {
        return std::nullopt;
    }

    const auto& landmarks = result.face_landmarks[0].landmarks;
    if (!hasIndex(landmarks, kLeftEyeInner) || !hasIndex(landmarks, kRightEyeInner) ||
        !hasIndex(landmarks, kNoseTip) || !hasIndex(landmarks, kForehead) ||
        !hasIndex(landmarks, kChin) || !hasIndex(landmarks, kLeftEyeOuter) ||
        !hasIndex(landmarks, kRightEyeOuter)) {
        return std::nullopt;
    }

    MediaPipeDebugData debugData;
    debugData.nose = landmarkToPixel(landmarks[kNoseTip], frameWidth, frameHeight);
    debugData.forehead = landmarkToPixel(landmarks[kForehead], frameWidth, frameHeight);
    debugData.chin = landmarkToPixel(landmarks[kChin], frameWidth, frameHeight);
    debugData.leftEyeInner = landmarkToPixel(landmarks[kLeftEyeInner], frameWidth, frameHeight);
    debugData.rightEyeInner = landmarkToPixel(landmarks[kRightEyeInner], frameWidth, frameHeight);
    debugData.leftEyeOuter = landmarkToPixel(landmarks[kLeftEyeOuter], frameWidth, frameHeight);
    debugData.rightEyeOuter = landmarkToPixel(landmarks[kRightEyeOuter], frameWidth, frameHeight);
    debugData.eyeMid = averagePoint(debugData.leftEyeInner, debugData.rightEyeInner);
    debugData.faceCenter = averagePoint(debugData.forehead, debugData.chin);
    debugData.trackingPixel = debugData.eyeMid;
    debugData.trackingPoint = "eye_mid";
    debugData.frameWidth = frameWidth;
    debugData.frameHeight = frameHeight;
    debugData.noseNorm = {landmarks[kNoseTip].x, landmarks[kNoseTip].y};
    debugData.eyeMidNorm = averagePoint(
        cv::Point2d{landmarks[kLeftEyeInner].x, landmarks[kLeftEyeInner].y},
        cv::Point2d{landmarks[kRightEyeInner].x, landmarks[kRightEyeInner].y});
    debugData.faceCenterNorm = averagePoint(
        cv::Point2d{landmarks[kForehead].x, landmarks[kForehead].y},
        cv::Point2d{landmarks[kChin].x, landmarks[kChin].y});

    return TrackingSample{
        makeTrackingBox(debugData.eyeMid, tracking, frameWidth, frameHeight),
        debugData};
}

void printStartupConfig(const AppConfig& config, const std::string& modelPath) {
    std::cout << "[INFO] Starting Bazel MediaPipe wallpaper runner.\n";
    std::cout << "[INFO] Model: " << modelPath << '\n';
    std::cout << "[INFO] Camera index: " << config.tracking.cameraIndex << '\n';
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

void printUsage(const char* exe) {
    std::cerr << "Usage: " << exe << " [path/to/face_landmarker.task] [camera_index]\n";
}

std::unique_ptr<FaceLandmarker> createFaceLandmarker(const std::string& modelPath) {
    auto options = std::make_unique<FaceLandmarkerOptions>();
    options->base_options.model_asset_path = modelPath;
    options->running_mode = RunningMode::VIDEO;
    options->num_faces = 1;
    options->min_face_detection_confidence = 0.5f;
    options->min_face_presence_confidence = 0.5f;
    options->min_tracking_confidence = 0.5f;
    options->output_face_blendshapes = false;
    options->output_facial_transformation_matrixes = false;

    absl::StatusOr<std::unique_ptr<FaceLandmarker>> landmarkerOr =
        FaceLandmarker::Create(std::move(options));
    if (!landmarkerOr.ok()) {
        throw std::runtime_error("Failed to create FaceLandmarker: " + landmarkerOr.status().ToString());
    }
    return std::move(landmarkerOr.value());
}

void trackingLoop(
    SharedTrackingState& state,
    std::atomic<bool>& stop,
    AppConfig config,
    std::string modelPath) {
    try {
        cv::VideoCapture camera(config.tracking.cameraIndex);
        if (!camera.isOpened()) {
            throw std::runtime_error("Could not open webcam index " + std::to_string(config.tracking.cameraIndex) + ".");
        }

        std::unique_ptr<FaceLandmarker> landmarker = createFaceLandmarker(modelPath);
        const auto startTime = std::chrono::steady_clock::now();
        int64_t lastTimestampMs = -1;

        while (!stop.load()) {
            cv::Mat cameraFrame;
            if (!camera.read(cameraFrame) || cameraFrame.empty()) {
                std::this_thread::sleep_for(std::chrono::milliseconds(2));
                continue;
            }

            if (config.tracking.mirrorCamera) {
                cv::flip(cameraFrame, cameraFrame, 1);
            }

            cv::Mat rgbFrame;
            cv::cvtColor(cameraFrame, rgbFrame, cv::COLOR_BGR2RGB);
            if (!rgbFrame.isContinuous()) {
                rgbFrame = rgbFrame.clone();
            }

            auto imageOr = mediapipe::tasks::vision::CreateImageFromBuffer(
                mediapipe::ImageFormat::SRGB,
                rgbFrame.data,
                rgbFrame.cols,
                rgbFrame.rows);
            if (!imageOr.ok()) {
                throw std::runtime_error("Failed to create MediaPipe image: " + imageOr.status().ToString());
            }

            int64_t timestampMs = millisecondsSince(startTime);
            if (timestampMs <= lastTimestampMs) {
                timestampMs = lastTimestampMs + 1;
            }
            lastTimestampMs = timestampMs;

            const auto inferenceStart = std::chrono::steady_clock::now();
            auto resultOr = landmarker->DetectForVideo(std::move(imageOr.value()), timestampMs);
            const auto inferenceEnd = std::chrono::steady_clock::now();
            if (!resultOr.ok()) {
                throw std::runtime_error("FaceLandmarker DetectForVideo failed: " + resultOr.status().ToString());
            }

            const auto sample = makeTrackingSample(
                resultOr.value(),
                config.tracking,
                cameraFrame.cols,
                cameraFrame.rows);

            {
                std::lock_guard<std::mutex> lock(state.mutex);
                state.latestCameraFrame = cameraFrame.clone();
                state.latestFaceCount = static_cast<int>(resultOr.value().face_landmarks.size());
                state.latestInferenceMs = elapsedMs(inferenceStart, inferenceEnd);
                if (sample.has_value()) {
                    state.latestSample = sample;
                    state.latestTrackingTime = inferenceEnd;
                    ++state.trackingUpdateCounter;
                }
            }
        }

        const auto closeStatus = landmarker->Close();
        if (!closeStatus.ok()) {
            std::lock_guard<std::mutex> lock(state.mutex);
            state.error = "FaceLandmarker Close failed: " + closeStatus.ToString();
        }
        camera.release();
    } catch (const std::exception& e) {
        std::lock_guard<std::mutex> lock(state.mutex);
        state.error = e.what();
    }
}

} // namespace

int main(int argc, char** argv) {
    if (argc > 3) {
        printUsage(argv[0]);
        return EXIT_FAILURE;
    }

    try {
        AppConfig config = AppConfig::load();

        const std::string modelPath = argc >= 2
                                          ? argv[1]
                                          : config.mediaPipeModelPath.string();
        if (modelPath.empty()) {
            throw std::runtime_error("MediaPipe model path is empty.");
        }
        if (argc == 3) {
            config.tracking.cameraIndex = std::atoi(argv[2]);
        }

        printStartupConfig(config, modelPath);

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

        window.setup();

        SharedTrackingState trackingState;
        std::atomic<bool> stopTracking{false};
        std::thread trackerThread(trackingLoop, std::ref(trackingState), std::ref(stopTracking), config, modelPath);
        ThreadStopper trackerStopper{stopTracking, trackerThread};

        auto fpsWindowStart = std::chrono::steady_clock::now();
        int framesSincePrint = 0;
        double displayedFps = 0.0;
        double lastFrameMs = 0.0;
        int frameId = 0;
        TimingStats timingStats;
        std::uint64_t lastLoggedTrackingCounter = 0;

        std::cout << "[INFO] MediaPipe C++ wallpaper runner started.\n";
        std::cout << "[INFO] Tracking point: eye_mid.\n";
        std::cout << "[INFO] Press q or ESC to quit.\n";

        while (true) {
            const auto frameStart = std::chrono::steady_clock::now();
            ++frameId;

            std::optional<TrackingSample> latestSample;
            cv::Mat cameraFrame;
            std::chrono::steady_clock::time_point latestTrackingTime{};
            std::uint64_t trackingCounter = 0;
            int latestFaceCount = 0;
            double latestInferenceMs = 0.0;
            std::string trackingError;
            {
                std::lock_guard<std::mutex> lock(trackingState.mutex);
                latestSample = trackingState.latestSample;
                if (!trackingState.latestCameraFrame.empty()) {
                    cameraFrame = trackingState.latestCameraFrame.clone();
                }
                latestTrackingTime = trackingState.latestTrackingTime;
                trackingCounter = trackingState.trackingUpdateCounter;
                latestFaceCount = trackingState.latestFaceCount;
                latestInferenceMs = trackingState.latestInferenceMs;
                trackingError = trackingState.error;
            }

            if (!trackingError.empty()) {
                throw std::runtime_error("Tracking thread failed: " + trackingError);
            }
            if (cameraFrame.empty()) {
                cameraFrame = cv::Mat(540, 960, CV_8UC3, cv::Scalar(18, 18, 18));
            }

            const auto mappingStart = std::chrono::steady_clock::now();
            std::optional<cv::Rect> faceBox;
            std::optional<MediaPipeDebugData> debugData;
            if (latestSample.has_value()) {
                faceBox = latestSample->faceBox;
                debugData = latestSample->debugData;
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
            const auto mappingEnd = std::chrono::steady_clock::now();

            const auto cacheStart = std::chrono::steady_clock::now();
            cv::Mat displayFrame = sequenceCache.getFrame(lastDisplayY, lastDisplayZ);
            const auto cacheEnd = std::chrono::steady_clock::now();

            const CacheInfo cacheInfo = sequenceCache.cacheInfo();
            const auto displayStart = std::chrono::steady_clock::now();
            cv::putText(
                cameraFrame,
                "FPS " + fixed(displayedFps, 1) + " | frame " + fixed(lastFrameMs, 1) + " ms | q/ESC quit",
                {20, cameraFrame.rows - 20},
                cv::FONT_HERSHEY_SIMPLEX,
                0.65,
                {0, 255, 255},
                2,
                cv::LINE_AA);

            window.showWallpaper(displayFrame);
            window.showDebug(
                cameraFrame,
                faceBox,
                debugData,
                faceBox.has_value() ? rawY : std::nullopt,
                faceBox.has_value() ? rawZ : std::nullopt,
                smoothedY,
                smoothedZ,
                cacheInfo,
                config.sequence.yViews,
                config.sequence.zViews,
                frameId);

            const int key = window.waitKey(1);
            const auto displayEnd = std::chrono::steady_clock::now();
            const auto frameEnd = displayEnd;

            lastFrameMs = elapsedMs(frameStart, frameEnd);
            ++framesSincePrint;
            timingStats.add(
                elapsedMs(mappingStart, mappingEnd),
                elapsedMs(cacheStart, cacheEnd),
                elapsedMs(displayStart, displayEnd),
                lastFrameMs);

            if (framesSincePrint >= kLogEveryFrames) {
                const double printElapsed = std::chrono::duration<double>(frameEnd - fpsWindowStart).count();
                displayedFps = printElapsed > 0.0 ? framesSincePrint / printElapsed : 0.0;
                const double sampleCount = std::max(1, timingStats.samples);
                std::cout << "[INFO] FPS=" << fixed(displayedFps, 1)
                          << ", tracker_fps=" << fixed((trackingCounter - lastLoggedTrackingCounter) / std::max(0.001, printElapsed), 1)
                          << ", tracking_age_ms="
                          << (trackingCounter > 0 ? fixed(elapsedMs(latestTrackingTime, frameEnd), 1) : "none")
                          << ", tracker_ms=" << fixed(latestInferenceMs, 2)
                          << ", avg_ms={map:" << fixed(timingStats.mappingMs / sampleCount, 2)
                          << ", cache:" << fixed(timingStats.cacheMs / sampleCount, 2)
                          << ", display:" << fixed(timingStats.displayMs / sampleCount, 2)
                          << ", total:" << fixed(timingStats.totalMs / sampleCount, 2)
                          << ", max_total:" << fixed(timingStats.maxTotalMs, 2)
                          << "}"
                          << ", faces=" << latestFaceCount
                          << ", raw_y=" << (rawY.has_value() ? fixed(*rawY, 2) : "none")
                          << ", raw_z=" << (rawZ.has_value() ? fixed(*rawZ, 2) : "none")
                          << ", render_y=" << fixed(lastDisplayY, 2)
                          << ", render_z=" << fixed(lastDisplayZ, 2)
                          << ", cache=" << cacheInfo.cachedFrames << "/" << cacheInfo.maxCacheSize
                          << ", loading=" << cacheInfo.loadingFrames << '\n';
                framesSincePrint = 0;
                fpsWindowStart = frameEnd;
                lastLoggedTrackingCounter = trackingCounter;
                timingStats.reset();
            }

            if (key == 27 || key == 'q' || key == 'Q') {
                break;
            }
        }

        sequenceCache.shutdown();
        window.destroyAll();
        return EXIT_SUCCESS;
    } catch (const std::exception& e) {
        std::cerr << "[ERROR] " << e.what() << '\n';
        return EXIT_FAILURE;
    }
}
