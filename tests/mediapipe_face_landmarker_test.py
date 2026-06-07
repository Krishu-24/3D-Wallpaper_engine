import time
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np


# =========================
# CONFIG
# =========================

MODEL_PATH = Path("models/face_landmarker.task")

CAMERA_INDEX = 0
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480

# Important landmark indices from MediaPipe face mesh topology
NOSE_TIP = 1
FOREHEAD = 10
CHIN = 152

LEFT_EYE_OUTER = 33
LEFT_EYE_INNER = 133

RIGHT_EYE_OUTER = 263
RIGHT_EYE_INNER = 362


# =========================
# HELPERS
# =========================

def normalized_to_pixel(landmark, width, height):
    """
    MediaPipe landmarks are normalized:
    x: 0.0 to 1.0 across image width
    y: 0.0 to 1.0 across image height
    z: relative depth-like value
    """
    x = int(landmark.x * width)
    y = int(landmark.y * height)
    return x, y


def draw_point(frame, point, label, color):
    x, y = point

    cv2.circle(frame, (x, y), 5, color, -1)

    cv2.putText(
        frame,
        label,
        (x + 8, y - 8),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        color,
        1,
        cv2.LINE_AA,
    )


def draw_landmark_subset(frame, landmarks, width, height):
    """
    Draws a small subset of landmarks instead of the full face mesh.
    Full mesh is visually noisy for our wallpaper-tracking test.
    """
    for idx in [NOSE_TIP, FOREHEAD, CHIN, LEFT_EYE_OUTER, LEFT_EYE_INNER, RIGHT_EYE_OUTER, RIGHT_EYE_INNER]:
        point = normalized_to_pixel(landmarks[idx], width, height)
        cv2.circle(frame, point, 2, (255, 255, 255), -1)


def main():
    if not MODEL_PATH.exists():
        print(f"ERROR: Model file not found: {MODEL_PATH}")
        print("Download it first into models/face_landmarker.task")
        return

    # =========================
    # MEDIAPIPE TASK SETUP
    # =========================

    BaseOptions = mp.tasks.BaseOptions
    FaceLandmarker = mp.tasks.vision.FaceLandmarker
    FaceLandmarkerOptions = mp.tasks.vision.FaceLandmarkerOptions
    VisionRunningMode = mp.tasks.vision.RunningMode

    options = FaceLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=str(MODEL_PATH)),
        running_mode=VisionRunningMode.VIDEO,
        num_faces=1,
        min_face_detection_confidence=0.5,
        min_face_presence_confidence=0.5,
        min_tracking_confidence=0.5,
        output_face_blendshapes=False,
        output_facial_transformation_matrixes=False,
    )

    cap = cv2.VideoCapture(CAMERA_INDEX)

    if not cap.isOpened():
        print("ERROR: Could not open webcam.")
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)

    prev_time = time.time()
    start_time = time.time()

    with FaceLandmarker.create_from_options(options) as landmarker:
        while True:
            success, frame = cap.read()

            if not success:
                print("ERROR: Could not read webcam frame.")
                break

            # Mirror preview, same feel as normal webcam apps
            frame = cv2.flip(frame, 1)

            height, width, _ = frame.shape

            # OpenCV gives BGR. MediaPipe wants RGB.
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # MediaPipe Image object
            mp_image = mp.Image(
                image_format=mp.ImageFormat.SRGB,
                data=rgb_frame,
            )

            # VIDEO mode needs increasing timestamp in milliseconds
            timestamp_ms = int((time.time() - start_time) * 1000)

            result = landmarker.detect_for_video(mp_image, timestamp_ms)

            if result.face_landmarks:
                landmarks = result.face_landmarks[0]

                # Main tracking candidates
                nose = normalized_to_pixel(landmarks[NOSE_TIP], width, height)

                left_eye_inner = normalized_to_pixel(landmarks[LEFT_EYE_INNER], width, height)
                right_eye_inner = normalized_to_pixel(landmarks[RIGHT_EYE_INNER], width, height)

                forehead = normalized_to_pixel(landmarks[FOREHEAD], width, height)
                chin = normalized_to_pixel(landmarks[CHIN], width, height)

                # Eye midpoint, probably best for your wallpaper tracker
                eye_mid_x = (left_eye_inner[0] + right_eye_inner[0]) // 2
                eye_mid_y = (left_eye_inner[1] + right_eye_inner[1]) // 2
                eye_mid = (eye_mid_x, eye_mid_y)

                # Rough face center using forehead and chin
                face_center_x = (forehead[0] + chin[0]) // 2
                face_center_y = (forehead[1] + chin[1]) // 2
                face_center = (face_center_x, face_center_y)

                # Normalized tracking values for your renderer
                nose_norm_x = landmarks[NOSE_TIP].x
                nose_norm_y = landmarks[NOSE_TIP].y

                eye_mid_norm_x = eye_mid_x / width
                eye_mid_norm_y = eye_mid_y / height

                face_center_norm_x = face_center_x / width
                face_center_norm_y = face_center_y / height

                # Draw selected landmarks
                draw_landmark_subset(frame, landmarks, width, height)

                draw_point(frame, nose, "nose", (0, 255, 255))
                draw_point(frame, eye_mid, "eye_mid", (255, 0, 255))
                draw_point(frame, face_center, "face_center", (0, 255, 0))

                # Draw center reference lines
                cv2.line(frame, (width // 2, 0), (width // 2, height), (80, 80, 80), 1)
                cv2.line(frame, (0, height // 2), (width, height // 2), (80, 80, 80), 1)

                # Text overlay
                cv2.putText(
                    frame,
                    f"Nose: x={nose_norm_x:.3f}, y={nose_norm_y:.3f}",
                    (20, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 255, 255),
                    2,
                    cv2.LINE_AA,
                )

                cv2.putText(
                    frame,
                    f"Eye mid: x={eye_mid_norm_x:.3f}, y={eye_mid_norm_y:.3f}",
                    (20, 60),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (255, 0, 255),
                    2,
                    cv2.LINE_AA,
                )

                cv2.putText(
                    frame,
                    f"Face center: x={face_center_norm_x:.3f}, y={face_center_norm_y:.3f}",
                    (20, 90),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 255, 0),
                    2,
                    cv2.LINE_AA,
                )

                print(
                    f"eye_mid=({eye_mid_norm_x:.3f}, {eye_mid_norm_y:.3f}) | "
                    f"nose=({nose_norm_x:.3f}, {nose_norm_y:.3f}) | "
                    f"face_center=({face_center_norm_x:.3f}, {face_center_norm_y:.3f})"
                )

            else:
                cv2.putText(
                    frame,
                    "No face detected",
                    (20, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 0, 255),
                    2,
                    cv2.LINE_AA,
                )

            # FPS
            current_time = time.time()
            dt = current_time - prev_time
            prev_time = current_time

            fps = 1.0 / dt if dt > 0 else 0.0

            cv2.putText(
                frame,
                f"FPS: {fps:.1f}",
                (20, height - 20),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 255),
                2,
                cv2.LINE_AA,
            )

            cv2.imshow("MediaPipe Face Landmarker Test", frame)

            key = cv2.waitKey(1) & 0xFF

            if key == ord("q") or key == 27:
                break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()