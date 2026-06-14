#pragma once

#include <condition_variable>
#include <list>
#include <map>
#include <mutex>
#include <optional>
#include <queue>
#include <set>
#include <thread>
#include <vector>

#include <opencv2/core.hpp>

#include "ImageSequence.hpp"

struct CacheInfo {
    int cachedFrames = 0;
    int loadingFrames = 0;
    int maxCacheSize = 0;
};

class SequenceCache {
public:
    SequenceCache(
        ImageSequence sequence,
        int maxCacheSize = 300,
        int preloadRadiusY = 4,
        int preloadRadiusZ = 2,
        bool enableBlending = false,
        int maxWorkers = 4);

    ~SequenceCache();

    SequenceCache(const SequenceCache&) = delete;
    SequenceCache& operator=(const SequenceCache&) = delete;

    cv::Mat getFrame(double yFloat, double zFloat);
    CacheInfo cacheInfo() const;
    void shutdown();

private:
    using Key = std::pair<int, int>;

    struct Entry {
        cv::Mat image;
        std::list<Key>::iterator lruIt;
    };

    int clampInt(int value, int minValue, int maxValue) const;
    cv::Mat getFrameNearest(double yFloat, double zFloat);
    cv::Mat getFrameBlended(double yFloat, double zFloat);
    cv::Mat getCachedFrame(int yIndex, int zIndex);
    void preloadAround(double yFloat, double zFloat);
    void preloadFrame(int yIndex, int zIndex);
    void insertLoadedFrame(const Key& key, const cv::Mat& image);
    void workerLoop();

    ImageSequence sequence_;
    int maxCacheSize_;
    int preloadRadiusY_;
    int preloadRadiusZ_;
    bool enableBlending_;

    mutable std::mutex mutex_;
    std::condition_variable cv_;
    std::map<Key, Entry> cache_;
    std::list<Key> lru_;
    std::set<Key> loading_;
    std::queue<Key> jobs_;
    std::vector<std::thread> workers_;
    bool stopping_ = false;
};
