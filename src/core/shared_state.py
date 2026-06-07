import threading
import time


class SharedState:
    """
    Thread-safe latest-value storage.

    Important:
    This is not a queue.

    The camera thread keeps replacing the latest frame.
    The tracking thread always reads the latest frame.
    The renderer always reads the latest tracking result.

    Old frames are intentionally discarded to avoid lag.
    """

    def __init__(self):
        self.lock = threading.Lock()

        self.camera_frame = None
        self.camera_timestamp = None
        self.camera_frame_id = 0

        self.face_box = None
        self.face_timestamp = None
        self.face_frame_id = 0

        self.running = True

    def stop(self):
        with self.lock:
            self.running = False

    def is_running(self):
        with self.lock:
            return self.running

    def set_camera_frame(self, frame):
        with self.lock:
            self.camera_frame = frame
            self.camera_timestamp = time.perf_counter()
            self.camera_frame_id += 1

    def get_camera_frame(self, copy=True):
        with self.lock:
            if self.camera_frame is None:
                return None, None, None

            frame = self.camera_frame.copy() if copy else self.camera_frame
            return frame, self.camera_timestamp, self.camera_frame_id

    def set_face_box(self, face_box, source_frame_id=None):
        with self.lock:
            self.face_box = face_box
            self.face_timestamp = time.perf_counter()
            self.face_frame_id = source_frame_id if source_frame_id is not None else self.camera_frame_id

    def get_face_box(self):
        with self.lock:
            return self.face_box, self.face_timestamp, self.face_frame_id