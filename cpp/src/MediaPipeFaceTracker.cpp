#include "MediaPipeFaceTracker.hpp"

#include <algorithm>
#include <filesystem>
#include <stdexcept>
#include <utility>

MediaPipeFaceTracker::MediaPipeFaceTracker(
    std::string modelPath,
    cv::Size minFaceSize,
    double minFaceDetectionConfidence,
    double minFacePresenceConfidence,
    double minTrackingConfidence,
    std::string trackingPoint)
    : modelPath_(std::move(modelPath)),
      minFaceSize_(minFaceSize),
      minFaceDetectionConfidence_(minFaceDetectionConfidence),
      minFacePresenceConfidence_(minFacePresenceConfidence),
      minTrackingConfidence_(minTrackingConfidence),
      trackingPoint_(std::move(trackingPoint)),
      startTime_(std::chrono::steady_clock::now()) {
    if (!std::filesystem::exists(modelPath_)) {
        throw std::runtime_error("MediaPipe model file was not found. Check MEDIAPIPE_MODEL_PATH in .env.");
    }

#ifndef HAVE_MEDIAPIPE_CPP
    throw std::runtime_error(
        "MediaPipe C++ is not installed/configured for this build. "
        "Install/configure MediaPipe Tasks C++ and build with HAVE_MEDIAPIPE_CPP support; "
        "the C++ runner will not fall back to Haar cascade.");
#else
    throw std::runtime_error(
        "HAVE_MEDIAPIPE_CPP was enabled, but this project still needs the local MediaPipe Tasks C++ "
        "wiring for FaceLandmarker. No Haar cascade fallback is available.");
#endif
}

MediaPipeFaceTracker::~MediaPipeFaceTracker() {
    close();
}

std::optional<cv::Rect> MediaPipeFaceTracker::detect(const cv::Mat& frame) {
    if (frame.empty()) {
        latestDebugData_.reset();
        return std::nullopt;
    }

#ifndef HAVE_MEDIAPIPE_CPP
    throw std::runtime_error("MediaPipe C++ tracker is unavailable in this build.");
#else
    (void)frame;
    throw std::runtime_error("MediaPipe C++ FaceLandmarker integration is not wired in this build.");
#endif
}

std::optional<cv::Rect> MediaPipeFaceTracker::lastFace() const {
    return lastFace_;
}

std::optional<MediaPipeDebugData> MediaPipeFaceTracker::latestDebugData() const {
    return latestDebugData_;
}

void MediaPipeFaceTracker::close() {
#ifdef HAVE_MEDIAPIPE_CPP
    delete impl_;
    impl_ = nullptr;
#endif
}
