#include "SequenceCache.hpp"

#include <algorithm>
#include <cmath>
#include <iostream>
#include <utility>

#include <opencv2/imgproc.hpp>

SequenceCache::SequenceCache(
    ImageSequence sequence,
    int maxCacheSize,
    int preloadRadiusY,
    int preloadRadiusZ,
    bool enableBlending,
    int maxWorkers)
    : sequence_(std::move(sequence)),
      maxCacheSize_(maxCacheSize),
      preloadRadiusY_(preloadRadiusY),
      preloadRadiusZ_(preloadRadiusZ),
      enableBlending_(enableBlending) {
    const int workerCount = std::max(1, maxWorkers);
    workers_.reserve(workerCount);
    for (int i = 0; i < workerCount; ++i) {
        workers_.emplace_back(&SequenceCache::workerLoop, this);
    }
}

SequenceCache::~SequenceCache() {
    shutdown();
}

int SequenceCache::clampInt(int value, int minValue, int maxValue) const {
    return std::max(minValue, std::min(maxValue, value));
}

cv::Mat SequenceCache::getFrame(double yFloat, double zFloat) {
    if (enableBlending_) {
        return getFrameBlended(yFloat, zFloat);
    }
    return getFrameNearest(yFloat, zFloat);
}

cv::Mat SequenceCache::getFrameNearest(double yFloat, double zFloat) {
    int yIndex = static_cast<int>(std::round(yFloat));
    int zIndex = static_cast<int>(std::round(zFloat));
    yIndex = clampInt(yIndex, 0, sequence_.yViews() - 1);
    zIndex = clampInt(zIndex, 0, sequence_.zViews() - 1);

    preloadAround(yFloat, zFloat);
    return getCachedFrame(yIndex, zIndex);
}

cv::Mat SequenceCache::getFrameBlended(double yFloat, double zFloat) {
    yFloat = std::clamp(yFloat, 0.0, static_cast<double>(sequence_.yViews() - 1));
    zFloat = std::clamp(zFloat, 0.0, static_cast<double>(sequence_.zViews() - 1));

    int y0 = clampInt(static_cast<int>(std::floor(yFloat)), 0, sequence_.yViews() - 1);
    int y1 = clampInt(static_cast<int>(std::ceil(yFloat)), 0, sequence_.yViews() - 1);
    int z0 = clampInt(static_cast<int>(std::floor(zFloat)), 0, sequence_.zViews() - 1);
    int z1 = clampInt(static_cast<int>(std::ceil(zFloat)), 0, sequence_.zViews() - 1);

    const double wy = yFloat - y0;
    const double wz = zFloat - z0;

    preloadAround(yFloat, zFloat);

    const cv::Mat img00 = getCachedFrame(y0, z0);
    const cv::Mat img10 = getCachedFrame(y1, z0);
    const cv::Mat img01 = getCachedFrame(y0, z1);
    const cv::Mat img11 = getCachedFrame(y1, z1);

    cv::Mat top;
    cv::Mat bottom;
    cv::Mat blended;
    cv::addWeighted(img00, 1.0 - wy, img10, wy, 0.0, top);
    cv::addWeighted(img01, 1.0 - wy, img11, wy, 0.0, bottom);
    cv::addWeighted(top, 1.0 - wz, bottom, wz, 0.0, blended);
    return blended;
}

cv::Mat SequenceCache::getCachedFrame(int yIndex, int zIndex) {
    const Key key{static_cast<int>(yIndex), static_cast<int>(zIndex)};

    {
        std::lock_guard<std::mutex> lock(mutex_);
        const auto found = cache_.find(key);
        if (found != cache_.end()) {
            lru_.erase(found->second.lruIt);
            lru_.push_back(key);
            found->second.lruIt = std::prev(lru_.end());
            return found->second.image;
        }
    }

    cv::Mat image = sequence_.loadFrameFromDisk(key.first, key.second);
    insertLoadedFrame(key, image);
    return image;
}

void SequenceCache::preloadAround(double yFloat, double zFloat) {
    const int centerY = static_cast<int>(std::round(yFloat));
    const int centerZ = static_cast<int>(std::round(zFloat));

    for (int dz = -preloadRadiusZ_; dz <= preloadRadiusZ_; ++dz) {
        for (int dy = -preloadRadiusY_; dy <= preloadRadiusY_; ++dy) {
            const int y = clampInt(centerY + dy, 0, sequence_.yViews() - 1);
            const int z = clampInt(centerZ + dz, 0, sequence_.zViews() - 1);
            preloadFrame(y, z);
        }
    }
}

void SequenceCache::preloadFrame(int yIndex, int zIndex) {
    const Key key{yIndex, zIndex};
    {
        std::lock_guard<std::mutex> lock(mutex_);
        if (stopping_ || cache_.count(key) > 0 || loading_.count(key) > 0) {
            return;
        }
        loading_.insert(key);
        jobs_.push(key);
    }
    cv_.notify_one();
}

void SequenceCache::insertLoadedFrame(const Key& key, const cv::Mat& image) {
    std::lock_guard<std::mutex> lock(mutex_);

    auto found = cache_.find(key);
    if (found != cache_.end()) {
        lru_.erase(found->second.lruIt);
        cache_.erase(found);
    }

    lru_.push_back(key);
    cache_[key] = Entry{image, std::prev(lru_.end())};

    while (static_cast<int>(cache_.size()) > maxCacheSize_ && !lru_.empty()) {
        const Key old = lru_.front();
        lru_.pop_front();
        cache_.erase(old);
    }
}

void SequenceCache::workerLoop() {
    while (true) {
        Key key;
        {
            std::unique_lock<std::mutex> lock(mutex_);
            cv_.wait(lock, [&] { return stopping_ || !jobs_.empty(); });
            if (stopping_) {
                return;
            }
            key = jobs_.front();
            jobs_.pop();
        }

        try {
            cv::Mat image = sequence_.loadFrameFromDisk(key.first, key.second);
            insertLoadedFrame(key, image);
        } catch (const std::exception& e) {
            std::cerr << "[PRELOAD ERROR] (" << key.first << ", " << key.second << "): "
                      << e.what() << '\n';
        }

        {
            std::lock_guard<std::mutex> lock(mutex_);
            loading_.erase(key);
        }
    }
}

CacheInfo SequenceCache::cacheInfo() const {
    std::lock_guard<std::mutex> lock(mutex_);
    return CacheInfo{
        static_cast<int>(cache_.size()),
        static_cast<int>(loading_.size()),
        maxCacheSize_};
}

void SequenceCache::shutdown() {
    {
        std::lock_guard<std::mutex> lock(mutex_);
        if (stopping_) {
            return;
        }
        stopping_ = true;
        std::queue<Key> empty;
        jobs_.swap(empty);
        loading_.clear();
    }
    cv_.notify_all();
    for (auto& worker : workers_) {
        if (worker.joinable()) {
            worker.join();
        }
    }
    workers_.clear();
}
