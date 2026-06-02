import threading
import time

import cv2


class CameraWorker:
    """
    Dedicated webcam capture thread.

    This keeps the latest webcam frame updated independently
    from rendering and face detection.
    """

    def __init__(
        self,
        shared_state,
        camera_index=0,
        mirror_camera=True,
        poll_sleep=0.001,
    ):
        self.shared_state = shared_state
        self.camera_index = camera_index
        self.mirror_camera = mirror_camera
        self.poll_sleep = poll_sleep

        self.cap = None
        self.thread = None
        self.running = False

    def start(self):
        self.cap = cv2.VideoCapture(self.camera_index)

        if not self.cap.isOpened():
            raise RuntimeError("Could not open webcam.")

        self.running = True

        self.thread = threading.Thread(
            target=self._run,
            name="CameraWorker",
            daemon=True,
        )
        self.thread.start()

    def _run(self):
        while self.running and self.shared_state.is_running():
            ret, frame = self.cap.read()

            if not ret:
                time.sleep(self.poll_sleep)
                continue

            if self.mirror_camera:
                frame = cv2.flip(frame, 1)

            self.shared_state.set_camera_frame(frame)

            if self.poll_sleep > 0:
                time.sleep(self.poll_sleep)

    def stop(self):
        self.running = False

        if self.thread is not None:
            self.thread.join(timeout=1.0)

        if self.cap is not None:
            self.cap.release()
            self.cap = None