#pragma once

#include <optional>
#include <string>

#include <opencv2/core.hpp>

#include "AppConfig.hpp"
#include "MediaPipeFaceTracker.hpp"
#include "SequenceCache.hpp"

class WallpaperWindow {
public:
    explicit WallpaperWindow(WindowConfig config);

    void setup();
    void showWallpaper(const cv::Mat& frame) const;
    void showDebug(
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
        int trackingFrameId) const;
    int waitKey(int delayMs) const;
    void destroyAll() const;

private:
    static double indexToAngle(double index, int totalViews, double angleMin, double angleMax);
    static std::optional<std::tuple<int, int, int>> indexToSequenceNumber(
        double yIndex,
        double zIndex,
        int yViews,
        int zViews);
    static void drawPoint(cv::Mat& frame, const cv::Point& point, const std::string& label, const cv::Scalar& color);

    WindowConfig config_;
};
