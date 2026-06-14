#include "ImageSequence.hpp"

#include <algorithm>
#include <iomanip>
#include <sstream>
#include <stdexcept>
#include <utility>

#include <opencv2/imgcodecs.hpp>
#include <opencv2/imgproc.hpp>

namespace {

int clampInt(int value, int minValue, int maxValue) {
    return std::max(minValue, std::min(maxValue, value));
}

std::string formatFilename(const std::string& pattern, int frameNumber) {
    const std::string token = "{frame:04d}";
    const auto pos = pattern.find(token);
    if (pos == std::string::npos) {
        return pattern;
    }

    std::ostringstream frame;
    frame << std::setw(4) << std::setfill('0') << frameNumber;

    std::string filename = pattern;
    filename.replace(pos, token.size(), frame.str());
    return filename;
}

} // namespace

ImageSequence::ImageSequence(
    std::filesystem::path folder,
    int yViews,
    int zViews,
    std::string filenamePattern,
    int startFrame,
    std::optional<std::pair<int, int>> resizeTo)
    : folder_(std::move(folder)),
      yViews_(yViews),
      zViews_(zViews),
      filenamePattern_(std::move(filenamePattern)),
      startFrame_(startFrame),
      resizeTo_(resizeTo) {}

int ImageSequence::yViews() const {
    return yViews_;
}

int ImageSequence::zViews() const {
    return zViews_;
}

int ImageSequence::startFrame() const {
    return startFrame_;
}

int ImageSequence::gridToFrameNumber(int yIndex, int zIndex) const {
    yIndex = clampInt(yIndex, 0, yViews_ - 1);
    zIndex = clampInt(zIndex, 0, zViews_ - 1);
    const int flatIndex = zIndex * yViews_ + yIndex;
    return startFrame_ + flatIndex;
}

std::filesystem::path ImageSequence::framePath(int yIndex, int zIndex) const {
    const int frameNumber = gridToFrameNumber(yIndex, zIndex);
    return folder_ / formatFilename(filenamePattern_, frameNumber);
}

cv::Mat ImageSequence::loadFrameFromDisk(int yIndex, int zIndex) const {
    const auto path = framePath(yIndex, zIndex);
    cv::Mat image = cv::imread(path.string(), cv::IMREAD_COLOR);
    if (image.empty()) {
        throw std::runtime_error("Could not load image: " + path.string());
    }

    if (resizeTo_.has_value()) {
        cv::Mat resized;
        cv::resize(
            image,
            resized,
            cv::Size(resizeTo_->first, resizeTo_->second),
            0.0,
            0.0,
            cv::INTER_AREA);
        return resized;
    }

    return image;
}
