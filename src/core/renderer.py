import cv2
import time

from .camera_worker import CameraWorker
from .debug_view import create_debug_view
from .indexing import face_box_to_sequence_indices
from .sequence_cache import ImageSequenceCache
from .shared_state import SharedState
from .smoothing import ExponentialSmoother2D
from .tracking_worker import TrackingWorker


class WallpaperRenderer:
    """
    Main renderer.

    Thread structure:
    - CameraWorker thread captures latest webcam frame.
    - TrackingWorker thread detects latest face position.
    - Main thread renders wallpaper and owns OpenCV windows.
    - ImageSequenceCache uses worker threads for frame preloading.
    """

    def __init__(self, app_config):
        self.config = app_config

        self.shared_state = SharedState()

        self.sequence = ImageSequenceCache(
            folder=self.config.sequence.folder,
            y_views=self.config.sequence.y_views,
            z_views=self.config.sequence.z_views,
            filename_pattern=self.config.sequence.filename_pattern,
            start_frame=self.config.sequence.start_frame,
            max_cache_size=self.config.cache.max_cache_size,
            preload_radius_y=self.config.cache.preload_radius_y,
            preload_radius_z=self.config.cache.preload_radius_z,
            enable_blending=self.config.cache.enable_blending,
            max_workers=self.config.cache.max_workers,
            resize_to=self.config.cache.resize_to,
        )

        self.smoother = ExponentialSmoother2D(
            amount=self.config.tracking.smoothing_amount,
            snap_distance=self.config.tracking.snap_distance,

            # X has many views, so it can stay responsive.
            # Z/vertical has fewer views, so smooth it a bit more.
            amount_x=0.60,
            amount_y=0.45,
        )

        self.camera_worker = CameraWorker(
            shared_state=self.shared_state,
            camera_index=self.config.tracking.camera_index,
            mirror_camera=self.config.tracking.mirror_camera,
            poll_sleep=self.config.threading.camera_poll_sleep,
        )

        self.tracking_worker = TrackingWorker(
            shared_state=self.shared_state,
            scale_factor=self.config.tracking.scale_factor,
            min_neighbors=self.config.tracking.min_neighbors,
            min_face_size=self.config.tracking.min_face_size,
            poll_sleep=self.config.threading.tracking_poll_sleep,
            max_tracking_fps=self.config.threading.max_tracking_fps,
        )

        # Start from center view
        self.last_display_y = (self.config.sequence.y_views - 1) / 2
        self.last_display_z = (self.config.sequence.z_views - 1) / 2

        self.raw_y = None
        self.raw_z = None

        # Used to reject false face detections.
        # Without this, Haar Cascade can detect a wrong face-like region and
        # the render appears to "not hold" when tracking is lost.
        self.last_valid_face_box = None
        self.max_face_jump_px = 180
        self.max_face_size_change_ratio = 0.55

    def setup_windows(self):
        cv2.namedWindow(self.config.window.window_name, cv2.WINDOW_NORMAL)

        if self.config.window.fullscreen:
            cv2.setWindowProperty(
                self.config.window.window_name,
                cv2.WND_PROP_FULLSCREEN,
                cv2.WINDOW_FULLSCREEN,
            )

        if self.config.window.show_debug_window:
            cv2.namedWindow(self.config.window.debug_window_name, cv2.WINDOW_NORMAL)
            cv2.resizeWindow(self.config.window.debug_window_name, 960, 540)

    def start_workers(self):
        self.camera_worker.start()
        self.tracking_worker.start()

    def is_reasonable_face_box(self, face_box):
        """
        Rejects sudden false detections.

        The renderer should only update the view if the detected face box is
        close enough to the previous valid face box.

        If detection is lost or becomes unreasonable, the renderer holds the
        last valid render position.
        """

        if face_box is None:
            return False

        if self.last_valid_face_box is None:
            return True

        x, y, w, h = face_box
        lx, ly, lw, lh = self.last_valid_face_box

        cx = x + w / 2
        cy = y + h / 2

        lcx = lx + lw / 2
        lcy = ly + lh / 2

        jump_x = abs(cx - lcx)
        jump_y = abs(cy - lcy)

        if jump_x > self.max_face_jump_px or jump_y > self.max_face_jump_px:
            return False

        old_area = lw * lh
        new_area = w * h

        if old_area <= 0:
            return True

        size_change = abs(new_area - old_area) / old_area

        if size_change > self.max_face_size_change_ratio:
            return False

        return True

    def run(self):
        self.setup_windows()
        self.start_workers()

        print("[INFO] Wallpaper renderer started.")
        print("[INFO] CameraWorker thread active.")
        print("[INFO] TrackingWorker thread active.")
        print("[INFO] Image cache preload thread pool active.")
        print("[INFO] Press ESC to quit.")

        try:
            while True:
                camera_frame, _, camera_frame_id = self.shared_state.get_camera_frame(
                    copy=True
                )

                if camera_frame is None:
                    time.sleep(0.005)

                    key = cv2.waitKey(1) & 0xFF
                    if key == 27:
                        break

                    continue

                camera_height, camera_width = camera_frame.shape[:2]

                face_box, _, tracking_frame_id = self.shared_state.get_face_box()

                # Reject false detections.
                # If face_box is None or unreasonable, hold the last rendered view.
                if not self.is_reasonable_face_box(face_box):
                    face_box = None
                else:
                    self.last_valid_face_box = face_box

                smoothed_y = self.last_display_y
                smoothed_z = self.last_display_z

                if face_box is not None:
                    self.raw_y, self.raw_z = face_box_to_sequence_indices(
                        face_box=face_box,
                        camera_width=camera_width,
                        camera_height=camera_height,
                        y_views=self.config.sequence.y_views,
                        z_views=self.config.sequence.z_views,
                        flip_x=self.config.tracking.flip_x,
                        flip_z=self.config.tracking.flip_z,
                        camera_horizontal_fov=self.config.tracking.camera_horizontal_fov,
                        camera_vertical_fov=self.config.tracking.camera_vertical_fov,
                        render_y_angle_min=self.config.tracking.render_y_angle_min,
                        render_y_angle_max=self.config.tracking.render_y_angle_max,
                        render_z_angle_min=self.config.tracking.render_z_angle_min,
                        render_z_angle_max=self.config.tracking.render_z_angle_max,
                    )

                    smoothed_y, smoothed_z = self.smoother.update(
                        self.raw_y,
                        self.raw_z,
                    )

                    self.last_display_y = smoothed_y
                    self.last_display_z = smoothed_z

                else:
                    # Tracking lost or rejected:
                    # keep last_display_y and last_display_z unchanged.
                    # Do not reset smoother.
                    # Do not jump to center.
                    # Do not use stale false detections.
                    smoothed_y = self.last_display_y
                    smoothed_z = self.last_display_z

                display_frame = self.sequence.get_frame(
                    self.last_display_y,
                    self.last_display_z,
                )

                cv2.imshow(
                    self.config.window.window_name,
                    display_frame,
                )

                if self.config.window.show_debug_window:
                    cache_info = self.sequence.cache_info()

                    debug_frame = create_debug_view(
                        frame=camera_frame,
                        face_box=face_box,
                        raw_y_index=self.raw_y if face_box is not None else None,
                        raw_z_index=self.raw_z if face_box is not None else None,
                        smoothed_y_index=smoothed_y,
                        smoothed_z_index=smoothed_z,
                        cache_info=cache_info,
                        sequence_y_views=self.config.sequence.y_views,
                        sequence_z_views=self.config.sequence.z_views,
                        tracking_frame_id=tracking_frame_id,
                    )

                    cv2.imshow(
                        self.config.window.debug_window_name,
                        debug_frame,
                    )

                key = cv2.waitKey(1) & 0xFF

                if key == 27:
                    break

        finally:
            self.shutdown()

    def shutdown(self):
        print("[INFO] Shutting down renderer.")

        self.shared_state.stop()

        self.tracking_worker.stop()
        self.camera_worker.stop()

        self.sequence.shutdown()

        cv2.destroyAllWindows()
    
    