#pragma once

#include <filesystem>
#include <optional>
#include <string>
#include <utility>

#include <opencv2/core.hpp>

class ImageSequence {
public:
    ImageSequence(
        std::filesystem::path folder,
        int yViews,
        int zViews,
        std::string filenamePattern = "view_{frame:04d}.png",
        int startFrame = 1,
        std::optional<std::pair<int, int>> resizeTo = std::nullopt);

    int yViews() const;
    int zViews() const;
    int startFrame() const;
    int gridToFrameNumber(int yIndex, int zIndex) const;
    std::filesystem::path framePath(int yIndex, int zIndex) const;
    cv::Mat loadFrameFromDisk(int yIndex, int zIndex) const;

private:
    std::filesystem::path folder_;
    int yViews_;
    int zViews_;
    std::string filenamePattern_;
    int startFrame_;
    std::optional<std::pair<int, int>> resizeTo_;
};
