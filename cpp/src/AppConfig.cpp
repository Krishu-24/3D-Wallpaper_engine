#include "AppConfig.hpp"

#include <algorithm>
#include <cctype>
#include <cmath>
#include <cstdlib>
#include <fstream>
#include <sstream>
#include <stdexcept>
#include <unordered_map>

namespace {

constexpr double kPi = 3.14159265358979323846;

std::string trim(std::string value) {
    const auto first = value.find_first_not_of(" \t\r\n");
    if (first == std::string::npos) {
        return "";
    }
    const auto last = value.find_last_not_of(" \t\r\n");
    value = value.substr(first, last - first + 1);
    if (value.size() >= 2 && ((value.front() == '"' && value.back() == '"') ||
                              (value.front() == '\'' && value.back() == '\''))) {
        value = value.substr(1, value.size() - 2);
    }
    return value;
}

std::string lower(std::string value) {
    std::transform(value.begin(), value.end(), value.begin(), [](unsigned char ch) {
        return static_cast<char>(std::tolower(ch));
    });
    return value;
}

std::filesystem::path findProjectRoot() {
    auto current = std::filesystem::current_path();
    for (int i = 0; i < 6; ++i) {
        if (std::filesystem::exists(current / ".env") && std::filesystem::exists(current / "src")) {
            return current;
        }
        if (std::filesystem::exists(current / ".env") && current.filename() == "3D_Wallpaper_engine") {
            return current;
        }
        if (!current.has_parent_path()) {
            break;
        }
        current = current.parent_path();
    }

    current = std::filesystem::current_path();
    if (current.filename() == "cpp" && current.has_parent_path()) {
        return current.parent_path();
    }
    if (current.filename() == "build" && current.parent_path().filename() == "cpp") {
        return current.parent_path().parent_path();
    }
    return std::filesystem::current_path();
}

std::unordered_map<std::string, std::string> loadEnvFile(const std::filesystem::path& path) {
    std::unordered_map<std::string, std::string> env;
    std::ifstream file(path);
    if (!file) {
        return env;
    }

    std::string line;
    while (std::getline(file, line)) {
        line = trim(line);
        if (line.empty() || line.front() == '#') {
            continue;
        }
        const auto equal = line.find('=');
        if (equal == std::string::npos) {
            continue;
        }
        const auto key = trim(line.substr(0, equal));
        auto value = trim(line.substr(equal + 1));
        const auto comment = value.find(" #");
        if (comment != std::string::npos) {
            value = trim(value.substr(0, comment));
        }
        env[key] = value;
    }
    return env;
}

std::string envValue(const std::unordered_map<std::string, std::string>& env, const std::string& key) {
    if (const char* processValue = std::getenv(key.c_str())) {
        if (std::string(processValue).size() > 0) {
            return processValue;
        }
    }
    const auto found = env.find(key);
    if (found != env.end() && !found->second.empty()) {
        return found->second;
    }
    return "";
}

bool envFlagEnabled(const std::unordered_map<std::string, std::string>& env, const std::string& key) {
    const std::string value = lower(trim(envValue(env, key)));
    return value == "1" || value == "true" || value == "yes" || value == "on";
}

int envInt(
    const std::unordered_map<std::string, std::string>& env,
    const std::string& key,
    int defaultValue) {
    const std::string value = trim(envValue(env, key));
    if (value.empty()) {
        return defaultValue;
    }
    try {
        return std::stoi(value);
    } catch (const std::exception&) {
        throw std::runtime_error(key + " must be an integer.");
    }
}

double envDouble(
    const std::unordered_map<std::string, std::string>& env,
    const std::string& key,
    double defaultValue) {
    const std::string value = trim(envValue(env, key));
    if (value.empty()) {
        return defaultValue;
    }
    try {
        return std::stod(value);
    } catch (const std::exception&) {
        throw std::runtime_error(key + " must be a number.");
    }
}

} // namespace

double TrackingConfig::cameraHorizontalFov() const {
    if (cameraMeasureDistanceCm <= 0.0) {
        return 0.0;
    }
    return 2.0 * 180.0 / kPi *
           std::atan((cameraVisibleWidthCm / 2.0) / cameraMeasureDistanceCm);
}

double TrackingConfig::cameraVerticalFov() const {
    if (cameraMeasureDistanceCm <= 0.0) {
        return 0.0;
    }
    return 2.0 * 180.0 / kPi *
           std::atan((cameraVisibleHeightCm / 2.0) / cameraMeasureDistanceCm);
}

AppConfig AppConfig::load() {
    AppConfig config;
    config.projectRoot = findProjectRoot();

    const auto env = loadEnvFile(config.projectRoot / ".env");
    const auto sequenceFolder = envValue(env, "IMAGE_SEQUENCE_FOLDER");
    if (sequenceFolder.empty()) {
        throw std::runtime_error("IMAGE_SEQUENCE_FOLDER is missing. Add it to your .env file.");
    }
    config.sequence.folder = std::filesystem::path(sequenceFolder);

    const std::string trackingBackend = lower(trim(envValue(env, "TRACKING_BACKEND")));
    if (trackingBackend == "debug_mouse" || envFlagEnabled(env, "DEBUG_TRACKING")) {
        config.tracking.backend = TrackingBackend::DebugMouse;
    } else if (trackingBackend == "external_udp") {
        config.tracking.backend = TrackingBackend::ExternalUdp;
    } else if (trackingBackend.empty() || trackingBackend == "mediapipe") {
        config.tracking.backend = TrackingBackend::MediaPipe;
    } else {
        throw std::runtime_error(
            "Unsupported TRACKING_BACKEND value '" + trackingBackend +
            "'. Use 'mediapipe', 'debug_mouse', or 'external_udp'.");
    }

    config.externalTracking.udpPort = envInt(
        env,
        "EXTERNAL_TRACKING_UDP_PORT",
        config.externalTracking.udpPort);
    config.externalTracking.frameWidth = envInt(
        env,
        "EXTERNAL_TRACKING_FRAME_WIDTH",
        config.externalTracking.frameWidth);
    config.externalTracking.frameHeight = envInt(
        env,
        "EXTERNAL_TRACKING_FRAME_HEIGHT",
        config.externalTracking.frameHeight);
    config.externalTracking.packetTimeoutSeconds = envDouble(
        env,
        "EXTERNAL_TRACKING_PACKET_TIMEOUT_SECONDS",
        config.externalTracking.packetTimeoutSeconds);
    config.externalTracking.minConfidence = envDouble(
        env,
        "EXTERNAL_TRACKING_MIN_CONFIDENCE",
        config.externalTracking.minConfidence);

    if (config.externalTracking.udpPort <= 0 || config.externalTracking.udpPort > 65535) {
        throw std::runtime_error("EXTERNAL_TRACKING_UDP_PORT must be between 1 and 65535.");
    }
    if (config.externalTracking.frameWidth <= 0 || config.externalTracking.frameHeight <= 0) {
        throw std::runtime_error("EXTERNAL_TRACKING_FRAME_WIDTH and EXTERNAL_TRACKING_FRAME_HEIGHT must be positive.");
    }

    auto modelPath = envValue(env, "MEDIAPIPE_MODEL_PATH");
    if (modelPath.empty() && config.tracking.backend == TrackingBackend::MediaPipe) {
        throw std::runtime_error("MEDIAPIPE_MODEL_PATH is missing. Add it to your .env file.");
    }

    config.mediaPipeModelPath = std::filesystem::path(modelPath);
    if (!modelPath.empty() && config.mediaPipeModelPath.is_relative()) {
        config.mediaPipeModelPath = config.projectRoot / config.mediaPipeModelPath;
    }

    return config;
}
