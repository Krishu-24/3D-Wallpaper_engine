#include "WallpaperWindow.hpp"

#include <algorithm>
#include <cmath>
#include <iomanip>
#include <sstream>
#include <tuple>
#include <utility>

#include <opencv2/highgui.hpp>
#include <opencv2/imgproc.hpp>

namespace {

double clampDouble(double value, double minValue, double maxValue) {
    return std::max(minValue, std::min(maxValue, value));
}

std::string fixed2(double value) {
    std::ostringstream stream;
    stream << std::fixed << std::setprecision(2) << value;
    return stream.str();
}

std::string fixed3(double value) {
    std::ostringstream stream;
    stream << std::fixed << std::setprecision(3) << value;
    return stream.str();
}

} // namespace

WallpaperWindow::WallpaperWindow(WindowConfig config) : config_(std::move(config)) {}

void WallpaperWindow::setup() {
    cv::namedWindow(config_.windowName, cv::WINDOW_NORMAL);
    if (config_.fullscreen) {
        cv::setWindowProperty(config_.windowName, cv::WND_PROP_FULLSCREEN, cv::WINDOW_FULLSCREEN);
    }

    if (config_.showDebugWindow) {
        cv::namedWindow(config_.debugWindowName, cv::WINDOW_NORMAL);
        cv::resizeWindow(config_.debugWindowName, 960, 540);
    }
}

void WallpaperWindow::showWallpaper(const cv::Mat& frame) const {
    cv::imshow(config_.windowName, frame);
}

double WallpaperWindow::indexToAngle(double index, int totalViews, double angleMin, double angleMax) {
    if (totalViews <= 1) {
        return 0.0;
    }
    index = clampDouble(index, 0.0, static_cast<double>(totalViews - 1));
    const double t = index / static_cast<double>(totalViews - 1);
    return angleMin + t * (angleMax - angleMin);
}

std::optional<std::tuple<int, int, int>> WallpaperWindow::indexToSequenceNumber(
    double yIndex,
    double zIndex,
    int yViews,
    int zViews) {
    if (yViews <= 0 || zViews <= 0) {
        return std::nullopt;
    }

    const int yInt = static_cast<int>(std::round(clampDouble(yIndex, 0.0, static_cast<double>(yViews - 1))));
    const int zInt = static_cast<int>(std::round(clampDouble(zIndex, 0.0, static_cast<double>(zViews - 1))));
    const int frameNumber = 1 + zInt * yViews + yInt;
    return std::make_tuple(yInt, zInt, frameNumber);
}

void WallpaperWindow::drawPoint(cv::Mat& frame, const cv::Point& point, const std::string& label, const cv::Scalar& color) {
    cv::circle(frame, point, 5, color, -1);
    cv::putText(
        frame,
        label,
        cv::Point(point.x + 8, point.y - 8),
        cv::FONT_HERSHEY_SIMPLEX,
        0.5,
        color,
        1,
        cv::LINE_AA);
}

void WallpaperWindow::showDebug(
    const cv::Mat& cameraFrame,
    const std::optional<cv::Rect>& faceBox,
    const std::optional<MediaPipeDebugData>& debugData,
    std::optional<double> rawYIndex,
    std::optional<double> rawZIndex,
    double smoothedYIndex,
    double smoothedZIndex,
    const CacheInfo& cacheInfo,
    int sequenceYViews,
    int sequenceZViews,
    int trackingFrameId) const {
    if (!config_.showDebugWindow) {
        return;
    }

    cv::Mat debugFrame = cameraFrame.clone();
    const int h = debugFrame.rows;
    const int w = debugFrame.cols;
    const int screenCenterX = w / 2;
    const int screenCenterY = h / 2;

    cv::line(debugFrame, {screenCenterX, 0}, {screenCenterX, h}, {80, 80, 80}, 1);
    cv::line(debugFrame, {0, screenCenterY}, {w, screenCenterY}, {80, 80, 80}, 1);
    cv::line(debugFrame, {w / 4, 0}, {w / 4, h}, {45, 45, 45}, 1);
    cv::line(debugFrame, {(3 * w) / 4, 0}, {(3 * w) / 4, h}, {45, 45, 45}, 1);
    cv::line(debugFrame, {0, h / 4}, {w, h / 4}, {45, 45, 45}, 1);
    cv::line(debugFrame, {0, (3 * h) / 4}, {w, (3 * h) / 4}, {45, 45, 45}, 1);
    cv::circle(debugFrame, {screenCenterX, screenCenterY}, 5, {0, 255, 255}, -1);

    if (debugData.has_value() && faceBox.has_value()) {
        const auto& data = *debugData;
        drawPoint(debugFrame, data.nose, "nose", {0, 255, 255});
        drawPoint(debugFrame, data.eyeMid, "eye_mid", {255, 0, 255});
        drawPoint(debugFrame, data.faceCenter, "face_center", {0, 255, 0});

        for (const auto& point : {
                 data.forehead,
                 data.chin,
                 data.leftEyeInner,
                 data.rightEyeInner,
                 data.leftEyeOuter,
                 data.rightEyeOuter}) {
            cv::circle(debugFrame, point, 2, {255, 255, 255}, -1);
        }

        cv::circle(debugFrame, data.trackingPixel, 8, {0, 0, 255}, 2);
        cv::line(debugFrame, {screenCenterX, screenCenterY}, data.trackingPixel, {0, 255, 0}, 2);

        cv::putText(debugFrame, "Tracking point: " + data.trackingPoint, {20, 35}, cv::FONT_HERSHEY_SIMPLEX, 0.65, {0, 255, 0}, 2);
        cv::putText(debugFrame, "Eye mid: x=" + fixed3(data.eyeMidNorm.x) + ", y=" + fixed3(data.eyeMidNorm.y), {20, 65}, cv::FONT_HERSHEY_SIMPLEX, 0.65, {255, 0, 255}, 2);
        cv::putText(debugFrame, "Nose: x=" + fixed3(data.noseNorm.x) + ", y=" + fixed3(data.noseNorm.y), {20, 95}, cv::FONT_HERSHEY_SIMPLEX, 0.65, {0, 255, 255}, 2);
        cv::putText(debugFrame, "Face center: x=" + fixed3(data.faceCenterNorm.x) + ", y=" + fixed3(data.faceCenterNorm.y), {20, 125}, cv::FONT_HERSHEY_SIMPLEX, 0.65, {0, 255, 0}, 2);
    } else {
        cv::putText(debugFrame, "No face detected - holding last render position", {20, 35}, cv::FONT_HERSHEY_SIMPLEX, 0.7, {0, 0, 255}, 2);
    }

    int textY = 160;
    if (rawYIndex.has_value() && rawZIndex.has_value()) {
        const double rawYAngle = indexToAngle(*rawYIndex, sequenceYViews, -25.0, 25.0);
        const double rawZAngle = indexToAngle(*rawZIndex, sequenceZViews, -10.0, 10.0);
        cv::putText(debugFrame, "Raw index: Y=" + fixed2(*rawYIndex) + ", Z=" + fixed2(*rawZIndex), {20, textY}, cv::FONT_HERSHEY_SIMPLEX, 0.65, {255, 255, 255}, 2);
        textY += 30;
        cv::putText(debugFrame, "Raw angle: Y=" + fixed2(rawYAngle) + " deg, Z=" + fixed2(rawZAngle) + " deg", {20, textY}, cv::FONT_HERSHEY_SIMPLEX, 0.65, {255, 255, 255}, 2);
        textY += 30;
        if (const auto info = indexToSequenceNumber(*rawYIndex, *rawZIndex, sequenceYViews, sequenceZViews)) {
            const auto [yNo, zNo, frameNo] = *info;
            cv::putText(debugFrame, "Raw image: Y#" + std::to_string(yNo + 1) + "/" + std::to_string(sequenceYViews) + ", Z#" + std::to_string(zNo + 1) + "/" + std::to_string(sequenceZViews) + ", frame=" + std::to_string(frameNo), {20, textY}, cv::FONT_HERSHEY_SIMPLEX, 0.65, {255, 255, 255}, 2);
            textY += 30;
        }
    }

    const double renderYAngle = indexToAngle(smoothedYIndex, sequenceYViews, -25.0, 25.0);
    const double renderZAngle = indexToAngle(smoothedZIndex, sequenceZViews, -10.0, 10.0);
    cv::putText(debugFrame, "Render index: Y=" + fixed2(smoothedYIndex) + ", Z=" + fixed2(smoothedZIndex), {20, textY}, cv::FONT_HERSHEY_SIMPLEX, 0.65, {0, 255, 255}, 2);
    textY += 30;
    cv::putText(debugFrame, "Render angle: Y=" + fixed2(renderYAngle) + " deg, Z=" + fixed2(renderZAngle) + " deg", {20, textY}, cv::FONT_HERSHEY_SIMPLEX, 0.65, {0, 255, 255}, 2);
    textY += 30;
    if (const auto info = indexToSequenceNumber(smoothedYIndex, smoothedZIndex, sequenceYViews, sequenceZViews)) {
        const auto [yNo, zNo, frameNo] = *info;
        cv::putText(debugFrame, "Render image: Y#" + std::to_string(yNo + 1) + "/" + std::to_string(sequenceYViews) + ", Z#" + std::to_string(zNo + 1) + "/" + std::to_string(sequenceZViews) + ", frame=" + std::to_string(frameNo), {20, textY}, cv::FONT_HERSHEY_SIMPLEX, 0.65, {0, 255, 255}, 2);
        textY += 30;
    }

    cv::putText(debugFrame, "Sequence grid: " + std::to_string(sequenceYViews) + " x " + std::to_string(sequenceZViews), {20, textY}, cv::FONT_HERSHEY_SIMPLEX, 0.65, {255, 255, 255}, 2);
    textY += 30;
    cv::putText(debugFrame, "Cache: " + std::to_string(cacheInfo.cachedFrames) + "/" + std::to_string(cacheInfo.maxCacheSize), {20, textY}, cv::FONT_HERSHEY_SIMPLEX, 0.65, {0, 255, 0}, 2);
    textY += 30;
    cv::putText(debugFrame, "Loading: " + std::to_string(cacheInfo.loadingFrames), {20, textY}, cv::FONT_HERSHEY_SIMPLEX, 0.65, {0, 255, 0}, 2);
    textY += 30;
    cv::putText(debugFrame, "Tracking frame id: " + std::to_string(trackingFrameId), {20, textY}, cv::FONT_HERSHEY_SIMPLEX, 0.65, {255, 255, 255}, 2);

    cv::putText(debugFrame, "ESC: quit", {20, h - 25}, cv::FONT_HERSHEY_SIMPLEX, 0.7, {0, 255, 255}, 2);
    cv::imshow(config_.debugWindowName, debugFrame);
}

int WallpaperWindow::waitKey(int delayMs) const {
    return cv::waitKey(delayMs) & 0xFF;
}

void WallpaperWindow::destroyAll() const {
    cv::destroyAllWindows();
}
