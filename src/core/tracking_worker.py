import threading
import time

from .face_tracker import FaceTracker


class TrackingWorker:
    """
    Dedicated face tracking thread.

    This continuously reads the latest camera frame and updates
    the latest detected face box.

    It does not queue old frames. It always works on the latest frame.
    """

    def __init__(
        self,
        shared_state,
        scale_factor=1.2,
        min_neighbors=5,
        min_face_size=(60, 60),
        poll_sleep=0.005,
        max_tracking_fps=60.0,
    ):
        self.shared_state = shared_state

        self.scale_factor = scale_factor
        self.min_neighbors = min_neighbors
        self.min_face_size = min_face_size

        self.poll_sleep = poll_sleep
        self.max_tracking_fps = max_tracking_fps

        self.face_tracker = None
        self.thread = None
        self.running = False

        self.last_processed_frame_id = -1

    def start(self):
        self.face_tracker = FaceTracker(
            scale_factor=self.scale_factor,
            min_neighbors=self.min_neighbors,
            min_face_size=self.min_face_size,
        )

        self.running = True

        self.thread = threading.Thread(
            target=self._run,
            name="TrackingWorker",
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

            # If no face is detected, store None.
            # Renderer will hold the last valid rendered position.
            self.shared_state.set_face_box(
                face_box=face_box,
                source_frame_id=frame_id,
            )

    def stop(self):
        self.running = False

        if self.thread is not None:
            self.thread.join(timeout=1.0)