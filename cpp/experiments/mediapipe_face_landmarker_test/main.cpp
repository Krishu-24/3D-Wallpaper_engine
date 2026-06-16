#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <memory>
#include <string>
#include <vector>

#include "absl/status/statusor.h"
#include "mediapipe/tasks/cc/core/base_options.h"
#include "mediapipe/tasks/cc/vision/core/running_mode.h"
#include "mediapipe/tasks/cc/vision/face_landmarker/face_landmarker.h"
#include "mediapipe/tasks/cc/vision/utils/image_utils.h"

namespace {

constexpr int kNoseTip = 1;
constexpr int kForehead = 10;
constexpr int kChin = 152;
constexpr int kLeftEyeOuter = 33;
constexpr int kLeftEyeInner = 133;
constexpr int kRightEyeOuter = 263;
constexpr int kRightEyeInner = 362;

using mediapipe::tasks::components::containers::NormalizedLandmark;
using mediapipe::tasks::vision::core::RunningMode;
using mediapipe::tasks::vision::face_landmarker::FaceLandmarker;
using mediapipe::tasks::vision::face_landmarker::FaceLandmarkerOptions;

void PrintLandmark(
    const std::string& name,
    const NormalizedLandmark& landmark) {
    std::cout << "  " << name << ": "
              << "x=" << std::fixed << std::setprecision(6) << landmark.x
              << ", y=" << landmark.y
              << ", z=" << landmark.z << '\n';
}

NormalizedLandmark Average(
    const NormalizedLandmark& a,
    const NormalizedLandmark& b) {
    NormalizedLandmark out;
    out.x = (a.x + b.x) * 0.5f;
    out.y = (a.y + b.y) * 0.5f;
    out.z = (a.z + b.z) * 0.5f;
    return out;
}

bool HasIndex(const std::vector<NormalizedLandmark>& landmarks, int index) {
    return index >= 0 && static_cast<size_t>(index) < landmarks.size();
}

} // namespace

int main(int argc, char** argv) {
    if (argc != 3) {
        std::cerr << "Usage: " << argv[0]
                  << " <path/to/face_landmarker.task> <path/to/image>\n";
        return EXIT_FAILURE;
    }

    const std::string modelPath = argv[1];
    const std::string imagePath = argv[2];

    auto imageOr = mediapipe::tasks::vision::DecodeImageFromFile(imagePath);
    if (!imageOr.ok()) {
        std::cerr << "Failed to decode image: " << imageOr.status() << '\n';
        return EXIT_FAILURE;
    }

    auto options = std::make_unique<FaceLandmarkerOptions>();
    options->base_options.model_asset_path = modelPath;
    options->running_mode = RunningMode::IMAGE;
    options->num_faces = 1;
    options->min_face_detection_confidence = 0.5f;
    options->min_face_presence_confidence = 0.5f;
    options->min_tracking_confidence = 0.5f;
    options->output_face_blendshapes = false;
    options->output_facial_transformation_matrixes = false;

    absl::StatusOr<std::unique_ptr<FaceLandmarker>> landmarkerOr =
        FaceLandmarker::Create(std::move(options));
    if (!landmarkerOr.ok()) {
        std::cerr << "Failed to create FaceLandmarker: "
                  << landmarkerOr.status() << '\n';
        return EXIT_FAILURE;
    }
    std::unique_ptr<FaceLandmarker> landmarker = std::move(landmarkerOr.value());

    absl::StatusOr<mediapipe::tasks::vision::face_landmarker::FaceLandmarkerResult> resultOr =
        landmarker->Detect(std::move(imageOr.value()));
    if (!resultOr.ok()) {
        std::cerr << "FaceLandmarker Detect failed: " << resultOr.status() << '\n';
        return EXIT_FAILURE;
    }

    const auto& result = resultOr.value();
    std::cout << "faces: " << result.face_landmarks.size() << '\n';

    if (result.face_landmarks.empty()) {
        (void)landmarker->Close();
        return EXIT_SUCCESS;
    }

    const auto& landmarks = result.face_landmarks[0].landmarks;
    std::cout << "first_face_landmark_count: " << landmarks.size() << '\n';

    const int required[] = {
        kNoseTip,
        kForehead,
        kChin,
        kLeftEyeOuter,
        kLeftEyeInner,
        kRightEyeOuter,
        kRightEyeInner,
    };
    for (int index : required) {
        if (!HasIndex(landmarks, index)) {
            std::cerr << "Missing required landmark index " << index
                      << " from first face.\n";
            (void)landmarker->Close();
            return EXIT_FAILURE;
        }
    }

    const auto eyeMid = Average(landmarks[kLeftEyeInner], landmarks[kRightEyeInner]);
    const auto faceCenter = Average(landmarks[kForehead], landmarks[kChin]);

    PrintLandmark("nose_tip[1]", landmarks[kNoseTip]);
    PrintLandmark("forehead[10]", landmarks[kForehead]);
    PrintLandmark("chin[152]", landmarks[kChin]);
    PrintLandmark("left_eye_outer[33]", landmarks[kLeftEyeOuter]);
    PrintLandmark("left_eye_inner[133]", landmarks[kLeftEyeInner]);
    PrintLandmark("right_eye_outer[263]", landmarks[kRightEyeOuter]);
    PrintLandmark("right_eye_inner[362]", landmarks[kRightEyeInner]);
    PrintLandmark("eye_mid[133+362]/2", eyeMid);
    PrintLandmark("face_center[10+152]/2", faceCenter);

    auto closeStatus = landmarker->Close();
    if (!closeStatus.ok()) {
        std::cerr << "FaceLandmarker Close failed: " << closeStatus << '\n';
        return EXIT_FAILURE;
    }

    return EXIT_SUCCESS;
}
