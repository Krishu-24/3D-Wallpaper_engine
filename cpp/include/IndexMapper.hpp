#pragma once

#include <utility>

#include <opencv2/core.hpp>

#include "AppConfig.hpp"

class IndexMapper {
public:
    IndexMapper(const SequenceConfig& sequence, const TrackingConfig& tracking);

    std::pair<double, double> faceBoxToSequenceIndices(
        const cv::Rect& faceBox,
        int cameraWidth,
        int cameraHeight) const;

    static double pixelToCameraAngle(
        double pixelValue,
        double imageSize,
        double cameraFovDegrees,
        int centerPositiveDirection);

    static double angleToSequenceIndex(
        double angleDegrees,
        double angleMin,
        double angleMax,
        int totalViews);

private:
    SequenceConfig sequence_;
    TrackingConfig tracking_;
};
