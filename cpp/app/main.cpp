#include <algorithm>
#include <atomic>
#include <chrono>
#include <cmath>
#include <exception>
#include <iostream>
#include <memory>
#include <optional>
#include <stdexcept>
#include <sstream>
#include <string>
#include <thread>
#include <utility>

#ifdef _WIN32
#define NOMINMAX
#include <winsock2.h>
#include <ws2tcpip.h>
#else
#include <arpa/inet.h>
#include <fcntl.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <unistd.h>
#endif

#include <opencv2/highgui.hpp>
#include <opencv2/imgproc.hpp>
#include <opencv2/videoio.hpp>

#include "AppConfig.hpp"
#include "ExponentialSmoother2D.hpp"
#include "ImageSequence.hpp"
#include "IndexMapper.hpp"
#include "MediaPipeFaceTracker.hpp"
#include "SequenceCache.hpp"
#include "WallpaperWindow.hpp"

namespace {

struct DebugTrackingState {
    std::atomic<bool> hasMouse{false};
    std::atomic<int> mouseX{0};
    std::atomic<int> mouseY{0};
};

struct DebugTrackingSample {
    cv::Rect faceBox;
    MediaPipeDebugData debugData;
};

struct ExternalTrackingPoint {
    double x = 0.0;
    double y = 0.0;
    double confidence = 0.0;
};

#ifdef _WIN32
using UdpSocketHandle = SOCKET;
constexpr UdpSocketHandle kInvalidUdpSocket = INVALID_SOCKET;
#else
using UdpSocketHandle = int;
constexpr UdpSocketHandle kInvalidUdpSocket = -1;
#endif

const char* trackingBackendName(TrackingBackend backend) {
    switch (backend) {
    case TrackingBackend::ExternalUdp:
        return "external_udp";
    case TrackingBackend::DebugMouse:
        return "debug_mouse";
    case TrackingBackend::MediaPipe:
    default:
        return "mediapipe";
    }
}

void onDebugMouse(int event, int x, int y, int, void* userData) {
    if (event != cv::EVENT_MOUSEMOVE && event != cv::EVENT_LBUTTONDOWN && event != cv::EVENT_RBUTTONDOWN) {
        return;
    }

    auto* state = static_cast<DebugTrackingState*>(userData);
    if (!state) {
        return;
    }

    state->mouseX.store(x);
    state->mouseY.store(y);
    state->hasMouse.store(true);
}

void closeUdpSocket(UdpSocketHandle socketHandle) {
    if (socketHandle == kInvalidUdpSocket) {
        return;
    }
#ifdef _WIN32
    closesocket(socketHandle);
#else
    close(socketHandle);
#endif
}

bool setNonBlocking(UdpSocketHandle socketHandle) {
#ifdef _WIN32
    u_long mode = 1;
    return ioctlsocket(socketHandle, FIONBIO, &mode) == 0;
#else
    const int flags = fcntl(socketHandle, F_GETFL, 0);
    return flags >= 0 && fcntl(socketHandle, F_SETFL, flags | O_NONBLOCK) == 0;
#endif
}

std::optional<ExternalTrackingPoint> parseExternalTrackingMessage(
    std::string message,
    double minConfidence) {
    std::replace(message.begin(), message.end(), ',', ' ');

    ExternalTrackingPoint point;
    std::istringstream stream(message);
    if (!(stream >> point.x >> point.y >> point.confidence)) {
        return std::nullopt;
    }
    if (point.confidence < minConfidence) {
        return std::nullopt;
    }
    return point;
}

class ExternalUdpTracker {
public:
    explicit ExternalUdpTracker(const ExternalTrackingConfig& config)
        : config_(config) {
#ifdef _WIN32
        WSADATA wsaData{};
        if (WSAStartup(MAKEWORD(2, 2), &wsaData) != 0) {
            throw std::runtime_error("WSAStartup failed for external_udp tracker.");
        }
        wsaStarted_ = true;
#endif

        socket_ = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
        if (socket_ == kInvalidUdpSocket) {
            throw std::runtime_error("Could not create UDP socket for external_udp tracker.");
        }

        sockaddr_in address{};
        address.sin_family = AF_INET;
        address.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
        address.sin_port = htons(static_cast<unsigned short>(config_.udpPort));

        if (bind(socket_, reinterpret_cast<sockaddr*>(&address), sizeof(address)) != 0) {
            throw std::runtime_error("Could not bind external_udp tracker to localhost UDP port " +
                                     std::to_string(config_.udpPort) + ".");
        }

        if (!setNonBlocking(socket_)) {
            throw std::runtime_error("Could not set external_udp socket to nonblocking mode.");
        }
    }

    ~ExternalUdpTracker() {
        closeUdpSocket(socket_);
        socket_ = kInvalidUdpSocket;
#ifdef _WIN32
        if (wsaStarted_) {
            WSACleanup();
        }
#endif
    }

    ExternalUdpTracker(const ExternalUdpTracker&) = delete;
    ExternalUdpTracker& operator=(const ExternalUdpTracker&) = delete;

    std::optional<ExternalTrackingPoint> receiveLatest() const {
        std::optional<ExternalTrackingPoint> latest;
        char buffer[256]{};

        while (true) {
            sockaddr_in sender{};
#ifdef _WIN32
            int senderSize = sizeof(sender);
            const int received = recvfrom(
                socket_,
                buffer,
                static_cast<int>(sizeof(buffer) - 1),
                0,
                reinterpret_cast<sockaddr*>(&sender),
                &senderSize);
            if (received == SOCKET_ERROR) {
                const int error = WSAGetLastError();
                if (error == WSAEWOULDBLOCK) {
                    break;
                }
                break;
            }
#else
            socklen_t senderSize = sizeof(sender);
            const int received = static_cast<int>(recvfrom(
                socket_,
                buffer,
                sizeof(buffer) - 1,
                0,
                reinterpret_cast<sockaddr*>(&sender),
                &senderSize));
            if (received < 0) {
                break;
            }
#endif
            buffer[received] = '\0';
            if (auto parsed = parseExternalTrackingMessage(buffer, config_.minConfidence)) {
                latest = parsed;
            }
        }

        return latest;
    }

private:
    ExternalTrackingConfig config_;
    UdpSocketHandle socket_ = kInvalidUdpSocket;
#ifdef _WIN32
    bool wsaStarted_ = false;
#endif
};

DebugTrackingSample makePointTrackingSample(
    const cv::Mat& frame,
    const TrackingConfig& tracking,
    double pointX,
    double pointY,
    const std::string& trackingPointLabel) {
    const int frameWidth = frame.cols;
    const int frameHeight = frame.rows;
    const int centerX = std::max(0, std::min(frameWidth - 1, static_cast<int>(std::round(pointX))));
    const int centerY = std::max(0, std::min(frameHeight - 1, static_cast<int>(std::round(pointY))));

    const int boxWidth = std::max(1, tracking.minFaceSize.first);
    const int boxHeight = std::max(1, tracking.minFaceSize.second);
    cv::Rect faceBox(centerX - boxWidth / 2, centerY - boxHeight / 2, boxWidth, boxHeight);
    faceBox &= cv::Rect(0, 0, frameWidth, frameHeight);

    MediaPipeDebugData debugData;
    debugData.nose = {centerX, centerY};
    debugData.eyeMid = {centerX, centerY};
    debugData.faceCenter = {centerX, centerY};
    debugData.forehead = {centerX, std::max(0, centerY - boxHeight / 2)};
    debugData.chin = {centerX, std::min(frameHeight - 1, centerY + boxHeight / 2)};
    debugData.leftEyeInner = {std::max(0, centerX - boxWidth / 6), std::max(0, centerY - boxHeight / 8)};
    debugData.rightEyeInner = {std::min(frameWidth - 1, centerX + boxWidth / 6), std::max(0, centerY - boxHeight / 8)};
    debugData.leftEyeOuter = {std::max(0, centerX - boxWidth / 3), std::max(0, centerY - boxHeight / 8)};
    debugData.rightEyeOuter = {std::min(frameWidth - 1, centerX + boxWidth / 3), std::max(0, centerY - boxHeight / 8)};
    debugData.trackingPixel = {centerX, centerY};
    debugData.trackingPoint = trackingPointLabel;
    debugData.frameWidth = frameWidth;
    debugData.frameHeight = frameHeight;
    debugData.noseNorm = {static_cast<double>(centerX) / frameWidth, static_cast<double>(centerY) / frameHeight};
    debugData.eyeMidNorm = debugData.noseNorm;
    debugData.faceCenterNorm = debugData.noseNorm;

    return {faceBox, debugData};
}

DebugTrackingSample makeDebugTrackingSample(
    const cv::Mat& frame,
    const TrackingConfig& tracking,
    const DebugTrackingState& state,
    int frameId) {
    const int frameWidth = frame.cols;
    const int frameHeight = frame.rows;
    int centerX = frameWidth / 2;
    int centerY = frameHeight / 2;

    if (state.hasMouse.load()) {
        centerX = std::max(0, std::min(frameWidth - 1, state.mouseX.load()));
        centerY = std::max(0, std::min(frameHeight - 1, state.mouseY.load()));
    } else {
        const double t = static_cast<double>(frameId) * 0.035;
        centerX = static_cast<int>((frameWidth / 2.0) + std::sin(t) * frameWidth * 0.35);
        centerY = static_cast<int>((frameHeight / 2.0) + std::cos(t * 0.7) * frameHeight * 0.25);
    }

    return makePointTrackingSample(
        frame,
        tracking,
        centerX,
        centerY,
        state.hasMouse.load() ? "debug_mouse" : "debug_synthetic");
}

bool isReasonableFaceBox(
    const std::optional<cv::Rect>& faceBox,
    const std::optional<cv::Rect>& lastValidFaceBox) {
    if (!faceBox.has_value()) {
        return false;
    }
    if (!lastValidFaceBox.has_value()) {
        return true;
    }

    const auto& box = *faceBox;
    const auto& last = *lastValidFaceBox;
    const double cx = box.x + box.width / 2.0;
    const double cy = box.y + box.height / 2.0;
    const double lastCx = last.x + last.width / 2.0;
    const double lastCy = last.y + last.height / 2.0;

    if (std::abs(cx - lastCx) > 180.0 || std::abs(cy - lastCy) > 180.0) {
        return false;
    }

    const double oldArea = static_cast<double>(last.width * last.height);
    const double newArea = static_cast<double>(box.width * box.height);
    if (oldArea <= 0.0) {
        return true;
    }

    const double sizeChange = std::abs(newArea - oldArea) / oldArea;
    return sizeChange <= 0.55;
}

void printStartupConfig(const AppConfig& config) {
    std::cout << "[INFO] Starting MediaPipe wallpaper renderer.\n";
    std::cout << "[INFO] Reusing old camera, cache, indexing, smoothing, threading, and render pipeline semantics.\n";
    std::cout << "[INFO] Tracking backend: " << trackingBackendName(config.tracking.backend) << '\n';
    if (config.tracking.backend == TrackingBackend::MediaPipe) {
        std::cout << "[INFO] MediaPipe tracker selected as the intended final tracking path.\n";
        std::cout << "[INFO] MediaPipe debug view uses landmarks.\n";
    } else if (config.tracking.backend == TrackingBackend::DebugMouse) {
        std::cout << "[INFO] Debug tracker selected: mouse in debug window, synthetic point until mouse input arrives.\n";
        std::cout << "[INFO] MediaPipeFaceTracker stub remains unused in this temporary mode.\n";
    } else if (config.tracking.backend == TrackingBackend::ExternalUdp) {
        std::cout << "[INFO] External UDP tracker selected: Python MediaPipe sends x,y,confidence to C++.\n";
        std::cout << "[INFO] MediaPipeFaceTracker stub remains unused in this temporary mode.\n";
        std::cout << "[INFO] Listening on localhost UDP port " << config.externalTracking.udpPort
                  << " with tracking frame " << config.externalTracking.frameWidth
                  << "x" << config.externalTracking.frameHeight << ".\n";
    }
    std::cout << "[INFO] Sequence: " << config.sequence.yViews << " x " << config.sequence.zViews << '\n';
    std::cout << "[INFO] Camera FOV from config: H=" << config.tracking.cameraHorizontalFov()
              << " deg, V=" << config.tracking.cameraVerticalFov() << " deg\n";
    std::cout << "[INFO] Render angle range from config: Y=" << config.tracking.renderYAngleMin
              << " to " << config.tracking.renderYAngleMax << " deg, Z="
              << config.tracking.renderZAngleMin << " to " << config.tracking.renderZAngleMax << " deg\n";
    std::cout << "[INFO] Cache from config: max=" << config.cache.maxCacheSize
              << ", preload_y=" << config.cache.preloadRadiusY
              << ", preload_z=" << config.cache.preloadRadiusZ
              << ", workers=" << config.cache.maxWorkers
              << ", blending=" << (config.cache.enableBlending ? "True" : "False") << '\n';
}

} // namespace

int main() {
    try {
        AppConfig config = AppConfig::load();
        printStartupConfig(config);

        const bool useDebugTracker = config.tracking.backend == TrackingBackend::DebugMouse;
        const bool useExternalUdpTracker = config.tracking.backend == TrackingBackend::ExternalUdp;
        const bool useMediaPipeTracker = config.tracking.backend == TrackingBackend::MediaPipe;

        cv::VideoCapture camera;
        if (useMediaPipeTracker) {
            camera.open(config.tracking.cameraIndex);
            if (!camera.isOpened()) {
                throw std::runtime_error("Could not open webcam.");
            }
        }

        std::unique_ptr<MediaPipeFaceTracker> tracker;
        if (useMediaPipeTracker) {
            tracker = std::make_unique<MediaPipeFaceTracker>(
                config.mediaPipeModelPath.string(),
                cv::Size(config.tracking.minFaceSize.first, config.tracking.minFaceSize.second),
                0.5,
                0.5,
                0.5,
                "eye_mid");
        }

        std::unique_ptr<ExternalUdpTracker> externalUdpTracker;
        if (useExternalUdpTracker) {
            externalUdpTracker = std::make_unique<ExternalUdpTracker>(config.externalTracking);
        }

        ExponentialSmoother2D smoother(
            config.tracking.smoothingAmount,
            config.tracking.snapDistance,
            0.60,
            0.45);

        IndexMapper mapper(config.sequence, config.tracking);
        ImageSequence imageSequence(
            config.sequence.folder,
            config.sequence.yViews,
            config.sequence.zViews,
            config.sequence.filenamePattern,
            config.sequence.startFrame,
            config.cache.resizeTo);
        SequenceCache sequenceCache(
            std::move(imageSequence),
            config.cache.maxCacheSize,
            config.cache.preloadRadiusY,
            config.cache.preloadRadiusZ,
            config.cache.enableBlending,
            config.cache.maxWorkers);
        WallpaperWindow window(config.window);

        double lastDisplayY = (config.sequence.yViews - 1) / 2.0;
        double lastDisplayZ = (config.sequence.zViews - 1) / 2.0;
        std::optional<double> rawY;
        std::optional<double> rawZ;
        std::optional<cv::Rect> lastValidFaceBox;
        DebugTrackingState debugTrackingState;
        std::optional<ExternalTrackingPoint> lastExternalPoint;
        std::chrono::steady_clock::time_point lastExternalPacketTime{};

        window.setup();
        if (useDebugTracker && config.window.showDebugWindow) {
            cv::setMouseCallback(config.window.debugWindowName, onDebugMouse, &debugTrackingState);
        }

        std::cout << "[INFO] Wallpaper renderer started.\n";
        if (useDebugTracker) {
            std::cout << "[INFO] Debug tracker active. Move the mouse inside the debug window to drive the viewpoint.\n";
        } else if (useExternalUdpTracker) {
            std::cout << "[INFO] external_udp active. Waiting for UDP packets shaped as x,y,confidence.\n";
            std::cout << "[INFO] Holding last valid external point when packets pause; using center until first packet arrives.\n";
        } else {
            std::cout << "[INFO] Camera capture active.\n";
            std::cout << "[INFO] MediaPipe tracking active.\n";
        }
        std::cout << "[INFO] Image cache preload thread pool active.\n";
        std::cout << "[INFO] Press ESC to quit.\n";

        int frameId = 0;
        while (true) {
            cv::Mat cameraFrame;
            if (useDebugTracker) {
                cameraFrame = cv::Mat(540, 960, CV_8UC3, cv::Scalar(18, 18, 18));
            } else if (useExternalUdpTracker) {
                cameraFrame = cv::Mat(
                    config.externalTracking.frameHeight,
                    config.externalTracking.frameWidth,
                    CV_8UC3,
                    cv::Scalar(18, 18, 18));
            } else {
                const bool ok = camera.read(cameraFrame);
                if (!ok || cameraFrame.empty()) {
                    std::this_thread::sleep_for(std::chrono::milliseconds(5));
                    if (window.waitKey(1) == 27) {
                        break;
                    }
                    continue;
                }
            }

            ++frameId;
            if (useMediaPipeTracker && config.tracking.mirrorCamera) {
                cv::flip(cameraFrame, cameraFrame, 1);
            }

            std::optional<cv::Rect> faceBox;
            std::optional<MediaPipeDebugData> debugData;
            if (useDebugTracker) {
                const auto sample = makeDebugTrackingSample(
                    cameraFrame,
                    config.tracking,
                    debugTrackingState,
                    frameId);
                faceBox = sample.faceBox;
                debugData = sample.debugData;
            } else if (useExternalUdpTracker) {
                if (const auto received = externalUdpTracker->receiveLatest()) {
                    lastExternalPoint = received;
                    lastExternalPacketTime = std::chrono::steady_clock::now();
                }

                ExternalTrackingPoint point;
                std::string trackingPointLabel = "external_udp_center";
                if (lastExternalPoint.has_value()) {
                    point = *lastExternalPoint;
                    const auto age = std::chrono::duration<double>(
                        std::chrono::steady_clock::now() - lastExternalPacketTime);
                    trackingPointLabel = age.count() <= config.externalTracking.packetTimeoutSeconds
                                             ? "external_udp"
                                             : "external_udp_hold";
                } else {
                    point.x = cameraFrame.cols / 2.0;
                    point.y = cameraFrame.rows / 2.0;
                    point.confidence = 0.0;
                }

                const auto sample = makePointTrackingSample(
                    cameraFrame,
                    config.tracking,
                    point.x,
                    point.y,
                    trackingPointLabel);
                faceBox = sample.faceBox;
                debugData = sample.debugData;
            } else {
                faceBox = tracker->detect(cameraFrame);
                debugData = tracker->latestDebugData();
                if (!isReasonableFaceBox(faceBox, lastValidFaceBox)) {
                    faceBox.reset();
                    debugData.reset();
                } else {
                    lastValidFaceBox = faceBox;
                }
            }

            double smoothedY = lastDisplayY;
            double smoothedZ = lastDisplayZ;
            if (faceBox.has_value()) {
                const auto [mappedY, mappedZ] = mapper.faceBoxToSequenceIndices(
                    *faceBox,
                    cameraFrame.cols,
                    cameraFrame.rows);
                rawY = mappedY;
                rawZ = mappedZ;

                const auto smoothed = smoother.update(mappedY, mappedZ);
                smoothedY = smoothed.first;
                smoothedZ = smoothed.second;
                lastDisplayY = smoothedY;
                lastDisplayZ = smoothedZ;
            }

            cv::Mat displayFrame = sequenceCache.getFrame(lastDisplayY, lastDisplayZ);
            window.showWallpaper(displayFrame);
            window.showDebug(
                cameraFrame,
                faceBox,
                debugData,
                faceBox.has_value() ? rawY : std::nullopt,
                faceBox.has_value() ? rawZ : std::nullopt,
                smoothedY,
                smoothedZ,
                sequenceCache.cacheInfo(),
                config.sequence.yViews,
                config.sequence.zViews,
                frameId);

            if (window.waitKey(1) == 27) {
                break;
            }
        }

        sequenceCache.shutdown();
        if (tracker) {
            tracker->close();
        }
        if (camera.isOpened()) {
            camera.release();
        }
        window.destroyAll();
        return 0;
    } catch (const std::exception& e) {
        std::cerr << "[ERROR] " << e.what() << '\n';
        return 1;
    }
}
