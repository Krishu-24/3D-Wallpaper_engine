#include "IndexMapper.hpp"

#include <algorithm>
#include <cmath>

namespace {

constexpr double kPi = 3.14159265358979323846;

double clampDouble(double value, double minValue, double maxValue) {
    return std::max(minValue, std::min(maxValue, value));
}

double mapRange(double value, double inMin, double inMax, double outMin, double outMax) {
    if (inMax == inMin) {
        return outMin;
    }
    value = clampDouble(value, inMin, inMax);
    const double t = (value - inMin) / (inMax - inMin);
    return outMin + t * (outMax - outMin);
}

} // namespace

IndexMapper::IndexMapper(const SequenceConfig& sequence, const TrackingConfig& tracking)
    : sequence_(sequence), tracking_(tracking) {}

double IndexMapper::pixelToCameraAngle(
    double pixelValue,
    double imageSize,
    double cameraFovDegrees,
    int centerPositiveDirection) {
    if (imageSize <= 0.0) {
        return 0.0;
    }

    const double halfSize = imageSize / 2.0;
    if (halfSize == 0.0) {
        return 0.0;
    }

    double normalizedOffset = (pixelValue - halfSize) / halfSize;
    normalizedOffset *= static_cast<double>(centerPositiveDirection);

    const double halfFovRad = (cameraFovDegrees / 2.0) * kPi / 180.0;
    const double angleRad = std::atan(normalizedOffset * std::tan(halfFovRad));
    return angleRad * 180.0 / kPi;
}

double IndexMapper::angleToSequenceIndex(
    double angleDegrees,
    double angleMin,
    double angleMax,
    int totalViews) {
    if (totalViews <= 1) {
        return 0.0;
    }
    return mapRange(angleDegrees, angleMin, angleMax, 0.0, static_cast<double>(totalViews - 1));
}

std::pair<double, double> IndexMapper::faceBoxToSequenceIndices(
    const cv::Rect& faceBox,
    int cameraWidth,
    int cameraHeight) const {
    const double faceCenterX = faceBox.x + faceBox.width / 2.0;
    const double faceCenterY = faceBox.y + faceBox.height / 2.0;

    double cameraYAngle = pixelToCameraAngle(
        faceCenterX,
        static_cast<double>(cameraWidth),
        tracking_.cameraHorizontalFov(),
        1);

    double cameraZAngle = pixelToCameraAngle(
        faceCenterY,
        static_cast<double>(cameraHeight),
        tracking_.cameraVerticalFov(),
        -1);

    if (tracking_.flipX) {
        cameraYAngle *= -1.0;
    }
    if (!tracking_.flipZ) {
        cameraZAngle *= -1.0;
    }

    const double yFloat = angleToSequenceIndex(
        cameraYAngle,
        tracking_.renderYAngleMin,
        tracking_.renderYAngleMax,
        sequence_.yViews);

    const double zFloat = angleToSequenceIndex(
        cameraZAngle,
        tracking_.renderZAngleMin,
        tracking_.renderZAngleMax,
        sequence_.zViews);

    return {yFloat, zFloat};
}
