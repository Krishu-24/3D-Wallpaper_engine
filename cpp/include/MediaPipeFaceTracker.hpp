#pragma once

#include <chrono>
#include <cstdint>
#include <optional>
#include <string>

#include <opencv2/core.hpp>

struct MediaPipeDebugData {
    cv::Point nose{};
    cv::Point eyeMid{};
    cv::Point faceCenter{};
    cv::Point forehead{};
    cv::Point chin{};
    cv::Point leftEyeInner{};
    cv::Point rightEyeInner{};
    cv::Point leftEyeOuter{};
    cv::Point rightEyeOuter{};
    cv::Point trackingPixel{};
    std::string trackingPoint = "eye_mid";
    int frameWidth = 0;
    int frameHeight = 0;
    cv::Point2d noseNorm{};
    cv::Point2d eyeMidNorm{};
    cv::Point2d faceCenterNorm{};
};

class MediaPipeFaceTracker {
public:
    MediaPipeFaceTracker(
        std::string modelPath,
        cv::Size minFaceSize = {60, 60},
        double minFaceDetectionConfidence = 0.5,
        double minFacePresenceConfidence = 0.5,
        double minTrackingConfidence = 0.5,
        std::string trackingPoint = "eye_mid");

    ~MediaPipeFaceTracker();

    MediaPipeFaceTracker(const MediaPipeFaceTracker&) = delete;
    MediaPipeFaceTracker& operator=(const MediaPipeFaceTracker&) = delete;

    std::optional<cv::Rect> detect(const cv::Mat& frame);
    std::optional<cv::Rect> lastFace() const;
    std::optional<MediaPipeDebugData> latestDebugData() const;
    void close();

private:
    std::string modelPath_;
    cv::Size minFaceSize_;
    double minFaceDetectionConfidence_;
    double minFacePresenceConfidence_;
    double minTrackingConfidence_;
    std::string trackingPoint_;
    std::optional<cv::Rect> lastFace_;
    std::optional<MediaPipeDebugData> latestDebugData_;
    std::chrono::steady_clock::time_point startTime_;
    int64_t lastTimestampMs_ = 0;

#ifdef HAVE_MEDIAPIPE_CPP
    struct Impl;
    Impl* impl_ = nullptr;
#endif
};
