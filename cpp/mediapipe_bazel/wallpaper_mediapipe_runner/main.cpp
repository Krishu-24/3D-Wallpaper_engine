#include <algorithm>
#include <chrono>
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <memory>
#include <sstream>
#include <string>
#include <vector>

#include <opencv2/core.hpp>
#include <opencv2/highgui.hpp>
#include <opencv2/imgproc.hpp>
#include <opencv2/videoio.hpp>

#include "absl/status/statusor.h"
#include "mediapipe/tasks/cc/core/base_options.h"
#include "mediapipe/tasks/cc/vision/core/running_mode.h"
#include "mediapipe/tasks/cc/vision/face_landmarker/face_landmarker.h"
#include "mediapipe/tasks/cc/vision/utils/image_utils.h"

namespace {

// Same landmark indices used by src/mediapipe_core/mediapipe_tracking_worker.py.
constexpr int kNoseTip = 1;
constexpr int kForehead = 10;
constexpr int kChin = 152;
constexpr int kLeftEyeOuter = 33;
constexpr int kLeftEyeInner = 133;
constexpr int kRightEyeOuter = 263;
constexpr int kRightEyeInner = 362;

using Landmark = mediapipe::tasks::components::containers::NormalizedLandmark;
using FaceLandmarker = mediapipe::tasks::vision::face_landmarker::FaceLandmarker;
using FaceLandmarkerOptions = mediapipe::tasks::vision::face_landmarker::FaceLandmarkerOptions;
using FaceLandmarkerResult = mediapipe::tasks::vision::face_landmarker::FaceLandmarkerResult;
using RunningMode = mediapipe::tasks::vision::core::RunningMode;

cv::Point LandmarkToPixel(const Landmark& landmark, int width, int height) {
    const int x = std::max(0, std::min(width - 1, static_cast<int>(landmark.x * width)));
    const int y = std::max(0, std::min(height - 1, static_cast<int>(landmark.y * height)));
    return {x, y};
}

bool HasIndex(const std::vector<Landmark>& landmarks, int index) {
    return index >= 0 && static_cast<size_t>(index) < landmarks.size();
}

cv::Point AveragePoint(const cv::Point& a, const cv::Point& b) {
    return {(a.x + b.x) / 2, (a.y + b.y) / 2};
}

std::string Fixed(double value, int precision) {
    std::ostringstream stream;
    stream << std::fixed << std::setprecision(precision) << value;
    return stream.str();
}

int64_t MillisecondsSince(const std::chrono::steady_clock::time_point& start) {
    return std::chrono::duration_cast<std::chrono::milliseconds>(
               std::chrono::steady_clock::now() - start)
        .count();
}

void DrawLabel(cv::Mat& frame, const cv::Point& point, const std::string& label, const cv::Scalar& color) {
    cv::circle(frame, point, 6, color, -1, cv::LINE_AA);
    cv::putText(
        frame,
        label,
        {point.x + 8, point.y - 8},
        cv::FONT_HERSHEY_SIMPLEX,
        0.5,
        color,
        1,
        cv::LINE_AA);
}

void DrawFaceLandmarks(cv::Mat& frame, const FaceLandmarkerResult& result) {
    if (result.face_landmarks.empty()) {
        cv::putText(
            frame,
            "No face detected",
            {20, 35},
            cv::FONT_HERSHEY_SIMPLEX,
            0.8,
            {0, 0, 255},
            2,
            cv::LINE_AA);
        return;
    }

    const int width = frame.cols;
    const int height = frame.rows;
    const auto& landmarks = result.face_landmarks[0].landmarks;

    for (const auto& landmark : landmarks) {
        cv::circle(frame, LandmarkToPixel(landmark, width, height), 1, {180, 255, 180}, -1, cv::LINE_AA);
    }

    if (!HasIndex(landmarks, kLeftEyeInner) || !HasIndex(landmarks, kRightEyeInner) ||
        !HasIndex(landmarks, kNoseTip) || !HasIndex(landmarks, kForehead) ||
        !HasIndex(landmarks, kChin) || !HasIndex(landmarks, kLeftEyeOuter) ||
        !HasIndex(landmarks, kRightEyeOuter)) {
        cv::putText(
            frame,
            "Face detected, but required landmark indices are missing",
            {20, 35},
            cv::FONT_HERSHEY_SIMPLEX,
            0.7,
            {0, 0, 255},
            2,
            cv::LINE_AA);
        return;
    }

    const cv::Point nose = LandmarkToPixel(landmarks[kNoseTip], width, height);
    const cv::Point forehead = LandmarkToPixel(landmarks[kForehead], width, height);
    const cv::Point chin = LandmarkToPixel(landmarks[kChin], width, height);
    const cv::Point leftEyeInner = LandmarkToPixel(landmarks[kLeftEyeInner], width, height);
    const cv::Point rightEyeInner = LandmarkToPixel(landmarks[kRightEyeInner], width, height);
    const cv::Point leftEyeOuter = LandmarkToPixel(landmarks[kLeftEyeOuter], width, height);
    const cv::Point rightEyeOuter = LandmarkToPixel(landmarks[kRightEyeOuter], width, height);

    // This is the point the current Python MediaPipe tracker uses by default.
    const cv::Point eyeMid = AveragePoint(leftEyeInner, rightEyeInner);
    const cv::Point faceCenter = AveragePoint(forehead, chin);

    DrawLabel(frame, nose, "nose", {0, 255, 255});
    DrawLabel(frame, forehead, "forehead", {255, 255, 255});
    DrawLabel(frame, chin, "chin", {255, 255, 255});
    DrawLabel(frame, leftEyeInner, "L inner", {255, 0, 255});
    DrawLabel(frame, rightEyeInner, "R inner", {255, 0, 255});
    DrawLabel(frame, leftEyeOuter, "L outer", {160, 80, 255});
    DrawLabel(frame, rightEyeOuter, "R outer", {160, 80, 255});

    cv::line(frame, leftEyeInner, rightEyeInner, {255, 0, 255}, 2, cv::LINE_AA);
    DrawLabel(frame, faceCenter, "face_center", {0, 180, 255});
    cv::circle(frame, eyeMid, 10, {0, 0, 255}, 2, cv::LINE_AA);
    cv::putText(
        frame,
        "TRACK eye_mid",
        {eyeMid.x + 12, eyeMid.y + 18},
        cv::FONT_HERSHEY_SIMPLEX,
        0.65,
        {0, 0, 255},
        2,
        cv::LINE_AA);
}

void PrintUsage(const char* exe) {
    std::cerr << "Usage: " << exe << " <path/to/face_landmarker.task> [camera_index]\n";
}

} // namespace

int main(int argc, char** argv) {
    if (argc < 2 || argc > 3) {
        PrintUsage(argv[0]);
        return EXIT_FAILURE;
    }

    const std::string modelPath = argv[1];
    const int cameraIndex = argc == 3 ? std::atoi(argv[2]) : 0;

    cv::VideoCapture camera(cameraIndex);
    if (!camera.isOpened()) {
        std::cerr << "Could not open webcam index " << cameraIndex << ".\n";
        return EXIT_FAILURE;
    }

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
        std::cerr << "Failed to create FaceLandmarker: "
                  << landmarkerOr.status() << '\n';
        return EXIT_FAILURE;
    }
    std::unique_ptr<FaceLandmarker> landmarker = std::move(landmarkerOr.value());

    const std::string windowName = "MediaPipe C++ FaceLandmarker Live";
    cv::namedWindow(windowName, cv::WINDOW_NORMAL);

    const auto startTime = std::chrono::steady_clock::now();
    auto lastFpsPrint = std::chrono::steady_clock::now();
    int framesSincePrint = 0;
    double displayedFps = 0.0;
    double lastFrameMs = 0.0;
    int64_t lastTimestampMs = -1;

    std::cout << "[INFO] MediaPipe C++ FaceLandmarker live experiment started.\n";
    std::cout << "[INFO] Model: " << modelPath << '\n';
    std::cout << "[INFO] Camera index: " << cameraIndex << '\n';
    std::cout << "[INFO] Press q or ESC in the OpenCV window to quit.\n";

    while (true) {
        cv::Mat bgrFrame;
        if (!camera.read(bgrFrame) || bgrFrame.empty()) {
            std::cerr << "[WARN] Empty webcam frame.\n";
            continue;
        }

        const auto frameStart = std::chrono::steady_clock::now();

        cv::Mat rgbFrame;
        cv::cvtColor(bgrFrame, rgbFrame, cv::COLOR_BGR2RGB);
        if (!rgbFrame.isContinuous()) {
            rgbFrame = rgbFrame.clone();
        }

        auto imageOr = mediapipe::tasks::vision::CreateImageFromBuffer(
            mediapipe::ImageFormat::SRGB,
            rgbFrame.data,
            rgbFrame.cols,
            rgbFrame.rows);
        if (!imageOr.ok()) {
            std::cerr << "Failed to create MediaPipe image: " << imageOr.status() << '\n';
            break;
        }

        int64_t timestampMs = MillisecondsSince(startTime);
        if (timestampMs <= lastTimestampMs) {
            timestampMs = lastTimestampMs + 1;
        }
        lastTimestampMs = timestampMs;

        auto resultOr = landmarker->DetectForVideo(std::move(imageOr.value()), timestampMs);
        if (!resultOr.ok()) {
            std::cerr << "FaceLandmarker DetectForVideo failed: " << resultOr.status() << '\n';
            break;
        }

        DrawFaceLandmarks(bgrFrame, resultOr.value());

        lastFrameMs = std::chrono::duration<double, std::milli>(
                          std::chrono::steady_clock::now() - frameStart)
                          .count();
        ++framesSincePrint;

        const auto now = std::chrono::steady_clock::now();
        const double printElapsed = std::chrono::duration<double>(now - lastFpsPrint).count();
        if (printElapsed >= 1.0) {
            displayedFps = framesSincePrint / printElapsed;
            std::cout << "[INFO] FPS=" << Fixed(displayedFps, 1)
                      << ", frame_ms=" << Fixed(lastFrameMs, 2)
                      << ", faces=" << resultOr.value().face_landmarks.size() << '\n';
            framesSincePrint = 0;
            lastFpsPrint = now;
        }

        cv::putText(
            bgrFrame,
            "FPS " + Fixed(displayedFps, 1) + " | frame " + Fixed(lastFrameMs, 1) + " ms | q/ESC quit",
            {20, bgrFrame.rows - 20},
            cv::FONT_HERSHEY_SIMPLEX,
            0.65,
            {0, 255, 255},
            2,
            cv::LINE_AA);

        cv::imshow(windowName, bgrFrame);
        const int key = cv::waitKey(1) & 0xFF;
        if (key == 27 || key == 'q' || key == 'Q') {
            break;
        }
    }

    const auto closeStatus = landmarker->Close();
    if (!closeStatus.ok()) {
        std::cerr << "FaceLandmarker Close failed: " << closeStatus << '\n';
        return EXIT_FAILURE;
    }

    camera.release();
    cv::destroyAllWindows();
    return EXIT_SUCCESS;
}
