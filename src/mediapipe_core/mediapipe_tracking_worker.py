import os
import threading
import time
from pathlib import Path

import cv2
import mediapipe as mp


# =========================
# LANDMARK INDICES
# =========================

NOSE_TIP = 1
FOREHEAD = 10
CHIN = 152

LEFT_EYE_OUTER = 33
LEFT_EYE_INNER = 133

RIGHT_EYE_OUTER = 263
RIGHT_EYE_INNER = 362


# =========================
# SHARED MEDIAPIPE DEBUG DATA
# =========================

_latest_debug_data = None
_debug_lock = threading.Lock()


def set_latest_mediapipe_debug_data(data):
    global _latest_debug_data

    with _debug_lock:
        _latest_debug_data = data


def get_latest_mediapipe_debug_data():
    with _debug_lock:
        if _latest_debug_data is None:
            return None

        # Shallow copy is enough because values are tuples/numbers.
        return dict(_latest_debug_data)


# =========================
# HELPERS
# =========================

def normalized_to_pixel(landmark, width, height):
    x = int(landmark.x * width)
    y = int(landmark.y * height)
    return x, y


def clamp(value, min_value, max_value):
    return max(min_value, min(max_value, value))


# =========================
# TRACKER
# =========================

class MediaPipeFaceTracker:
    """
    MediaPipe FaceLandmarker tracker.

    Important:
    The old renderer maps the CENTER of face_box to sequence indices.

    So instead of returning the full MediaPipe face bounds, this returns a
    synthetic face_box centered on the eye midpoint.

    That makes the old indexing logic behave like your successful MediaPipe
    landmark test.
    """

    def __init__(
        self,
        model_path,
        min_face_size=(60, 60),
        min_face_detection_confidence=0.5,
        min_face_presence_confidence=0.5,
        min_tracking_confidence=0.5,
        tracking_point="eye_mid",
    ):
        self.model_path = Path(model_path)
        self.min_face_size = min_face_size
        self.tracking_point = tracking_point

        self.last_face = None

        if not self.model_path.exists():
            raise FileNotFoundError(
                "MediaPipe model file was not found. Check MEDIAPIPE_MODEL_PATH in .env."
            )

        BaseOptions = mp.tasks.BaseOptions
        FaceLandmarker = mp.tasks.vision.FaceLandmarker
        FaceLandmarkerOptions = mp.tasks.vision.FaceLandmarkerOptions
        VisionRunningMode = mp.tasks.vision.RunningMode

        options = FaceLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=str(self.model_path)),
            running_mode=VisionRunningMode.VIDEO,
            num_faces=1,
            min_face_detection_confidence=min_face_detection_confidence,
            min_face_presence_confidence=min_face_presence_confidence,
            min_tracking_confidence=min_tracking_confidence,
            output_face_blendshapes=False,
            output_facial_transformation_matrixes=False,
        )

        self.landmarker = FaceLandmarker.create_from_options(options)

        self.start_time = time.perf_counter()
        self.last_timestamp_ms = 0

    def detect(self, frame):
        """
        Returns:
            (x, y, w, h) if face found
            None if no face found

        The returned box is centered on the chosen MediaPipe landmark point.
        """

        if frame is None:
            set_latest_mediapipe_debug_data(None)
            return None

        frame_h, frame_w = frame.shape[:2]

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        mp_image = mp.Image(
            image_format=mp.ImageFormat.SRGB,
            data=rgb_frame,
        )

        timestamp_ms = int((time.perf_counter() - self.start_time) * 1000)

        # VIDEO mode needs strictly increasing timestamps.
        if timestamp_ms <= self.last_timestamp_ms:
            timestamp_ms = self.last_timestamp_ms + 1

        self.last_timestamp_ms = timestamp_ms

        result = self.landmarker.detect_for_video(
            mp_image,
            timestamp_ms,
        )

        if not result.face_landmarks:
            set_latest_mediapipe_debug_data(None)
            return None

        landmarks = result.face_landmarks[0]

        nose = normalized_to_pixel(landmarks[NOSE_TIP], frame_w, frame_h)

        left_eye_inner = normalized_to_pixel(landmarks[LEFT_EYE_INNER], frame_w, frame_h)
        right_eye_inner = normalized_to_pixel(landmarks[RIGHT_EYE_INNER], frame_w, frame_h)

        left_eye_outer = normalized_to_pixel(landmarks[LEFT_EYE_OUTER], frame_w, frame_h)
        right_eye_outer = normalized_to_pixel(landmarks[RIGHT_EYE_OUTER], frame_w, frame_h)

        forehead = normalized_to_pixel(landmarks[FOREHEAD], frame_w, frame_h)
        chin = normalized_to_pixel(landmarks[CHIN], frame_w, frame_h)

        eye_mid = (
            (left_eye_inner[0] + right_eye_inner[0]) // 2,
            (left_eye_inner[1] + right_eye_inner[1]) // 2,
        )

        face_center = (
            (forehead[0] + chin[0]) // 2,
            (forehead[1] + chin[1]) // 2,
        )

        if self.tracking_point == "nose":
            tracking_pixel = nose
        elif self.tracking_point == "face_center":
            tracking_pixel = face_center
        else:
            tracking_pixel = eye_mid

        # Use landmark spread only to create a stable fake box size.
        # The old renderer only cares about the box center for indexing.
        xs = [lm.x for lm in landmarks]
        ys = [lm.y for lm in landmarks]

        x_min = int(min(xs) * frame_w)
        x_max = int(max(xs) * frame_w)
        y_min = int(min(ys) * frame_h)
        y_max = int(max(ys) * frame_h)

        landmark_w = max(1, x_max - x_min)
        landmark_h = max(1, y_max - y_min)

        box_w = int(landmark_w * 1.25)
        box_h = int(landmark_h * 1.45)

        min_w, min_h = self.min_face_size
        box_w = max(box_w, min_w)
        box_h = max(box_h, min_h)

        cx, cy = tracking_pixel

        x = int(cx - box_w / 2)
        y = int(cy - box_h / 2)

        x = clamp(x, 0, frame_w - 1)
        y = clamp(y, 0, frame_h - 1)
        box_w = clamp(box_w, 1, frame_w - x)
        box_h = clamp(box_h, 1, frame_h - y)

        face_box = (int(x), int(y), int(box_w), int(box_h))

        debug_data = {
            "nose": nose,
            "eye_mid": eye_mid,
            "face_center": face_center,
            "forehead": forehead,
            "chin": chin,
            "left_eye_inner": left_eye_inner,
            "right_eye_inner": right_eye_inner,
            "left_eye_outer": left_eye_outer,
            "right_eye_outer": right_eye_outer,
            "tracking_pixel": tracking_pixel,
            "tracking_point": self.tracking_point,
            "frame_width": frame_w,
            "frame_height": frame_h,
            "nose_norm": (
                landmarks[NOSE_TIP].x,
                landmarks[NOSE_TIP].y,
            ),
            "eye_mid_norm": (
                eye_mid[0] / frame_w,
                eye_mid[1] / frame_h,
            ),
            "face_center_norm": (
                face_center[0] / frame_w,
                face_center[1] / frame_h,
            ),
        }

        set_latest_mediapipe_debug_data(debug_data)

        self.last_face = face_box
        return self.last_face

    def get_last_face(self):
        return self.last_face

    def close(self):
        if self.landmarker is not None:
            self.landmarker.close()
            self.landmarker = None


# =========================
# WORKER
# =========================

class MediaPipeTrackingWorker:
    """
    Drop-in replacement for the old Haar TrackingWorker.

    Reads camera frames from SharedState and writes face_box back to SharedState.
    """

    def __init__(
        self,
        shared_state,
        model_path,
        min_face_size=(60, 60),
        poll_sleep=0.005,
        max_tracking_fps=30.0,
        min_face_detection_confidence=0.5,
        min_face_presence_confidence=0.5,
        min_tracking_confidence=0.5,
        tracking_point="eye_mid",
    ):
        self.shared_state = shared_state

        self.model_path = model_path
        self.min_face_size = min_face_size
        self.poll_sleep = poll_sleep
        self.max_tracking_fps = max_tracking_fps

        self.min_face_detection_confidence = min_face_detection_confidence
        self.min_face_presence_confidence = min_face_presence_confidence
        self.min_tracking_confidence = min_tracking_confidence
        self.tracking_point = tracking_point

        self.face_tracker = None
        self.thread = None
        self.running = False

        self.last_processed_frame_id = -1

    def start(self):
        self.face_tracker = MediaPipeFaceTracker(
            model_path=self.model_path,
            min_face_size=self.min_face_size,
            min_face_detection_confidence=self.min_face_detection_confidence,
            min_face_presence_confidence=self.min_face_presence_confidence,
            min_tracking_confidence=self.min_tracking_confidence,
            tracking_point=self.tracking_point,
        )

        self.running = True

        self.thread = threading.Thread(
            target=self._run,
            name="MediaPipeTrackingWorker",
            daemon=True,
        )
        self.thread.start()

    def _run(self):
        min_frame_time = 1.0 / self.max_tracking_fps if self.max_tracking_fps > 0 else 0.0
        last_tracking_time = 0.0

        while self.running and self.shared_state.is_running():
            now = time.perf_counter()

            if min_frame_time > 0 and now - last_tracking_time < min_frame_time:
                time.sleep(self.poll_sleep)
                continue

            frame, _, frame_id = self.shared_state.get_camera_frame(copy=True)

            if frame is None:
                time.sleep(self.poll_sleep)
                continue

            if frame_id == self.last_processed_frame_id:
                time.sleep(self.poll_sleep)
                continue

            self.last_processed_frame_id = frame_id
            last_tracking_time = now

            face_box = self.face_tracker.detect(frame)

            self.shared_state.set_face_box(
                face_box=face_box,
                source_frame_id=frame_id,
            )

    def stop(self):
        self.running = False

        if self.thread is not None:
            self.thread.join(timeout=1.0)

        if self.face_tracker is not None:
            self.face_tracker.close()
            self.face_tracker = None