import os
import socket
import sys
import time
from pathlib import Path

import cv2
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"

if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from core.config import TrackingConfig, ThreadingConfig
from mediapipe_core.mediapipe_tracking_worker import (
    MediaPipeFaceTracker,
    get_latest_mediapipe_debug_data,
)


def env_int(name, default):
    value = os.getenv(name)
    if not value:
        return default
    return int(value)


def get_mediapipe_model_path():
    model_path = os.getenv("MEDIAPIPE_MODEL_PATH")
    if not model_path:
        raise RuntimeError(
            "MEDIAPIPE_MODEL_PATH is missing. Add it to your .env file."
        )

    model_path = Path(model_path)
    if not model_path.is_absolute():
        model_path = PROJECT_ROOT / model_path
    return model_path


def main():
    load_dotenv(PROJECT_ROOT / ".env")

    tracking = TrackingConfig()
    threading = ThreadingConfig()

    udp_host = os.getenv("EXTERNAL_TRACKING_UDP_HOST", "127.0.0.1")
    udp_port = env_int("EXTERNAL_TRACKING_UDP_PORT", 5055)
    frame_width = env_int("EXTERNAL_TRACKING_FRAME_WIDTH", 640)
    frame_height = env_int("EXTERNAL_TRACKING_FRAME_HEIGHT", 480)

    model_path = get_mediapipe_model_path()

    cap = cv2.VideoCapture(tracking.camera_index)
    if not cap.isOpened():
        raise RuntimeError("Could not open webcam.")

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, frame_width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, frame_height)

    tracker = MediaPipeFaceTracker(
        model_path=model_path,
        min_face_size=tracking.min_face_size,
        min_face_detection_confidence=0.5,
        min_face_presence_confidence=0.5,
        min_tracking_confidence=0.5,
        tracking_point="eye_mid",
    )

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    target = (udp_host, udp_port)
    min_frame_time = (
        1.0 / threading.max_tracking_fps
        if threading.max_tracking_fps > 0
        else 0.0
    )
    last_send_time = 0.0

    print("[INFO] Python MediaPipe UDP sender started.")
    print(f"[INFO] Sending x,y,confidence to {udp_host}:{udp_port}.")
    print(f"[INFO] Requested camera frame size: {frame_width}x{frame_height}.")
    print(
        "[INFO] Actual camera frame size: "
        f"{int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))}x"
        f"{int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))}."
    )
    print("[INFO] Press Ctrl+C to stop.")

    try:
        while True:
            now = time.perf_counter()
            if min_frame_time > 0 and now - last_send_time < min_frame_time:
                time.sleep(threading.tracking_poll_sleep)
                continue

            ok, frame = cap.read()
            if not ok or frame is None:
                time.sleep(threading.tracking_poll_sleep)
                continue

            if tracking.mirror_camera:
                frame = cv2.flip(frame, 1)

            face_box = tracker.detect(frame)
            if face_box is not None:
                debug_data = get_latest_mediapipe_debug_data()
                if debug_data and "tracking_pixel" in debug_data:
                    x, y = debug_data["tracking_pixel"]
                else:
                    bx, by, bw, bh = face_box
                    x = bx + bw / 2.0
                    y = by + bh / 2.0

                message = f"{float(x):.2f},{float(y):.2f},1.0"
                sock.sendto(message.encode("utf-8"), target)

            last_send_time = now

    except KeyboardInterrupt:
        print("\n[INFO] Stopping Python MediaPipe UDP sender.")
    finally:
        tracker.close()
        cap.release()
        sock.close()


if __name__ == "__main__":
    main()
