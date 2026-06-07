import math
from dataclasses import dataclass
from pathlib import Path


# =========================
# SEQUENCE CONFIG
# =========================

@dataclass
class SequenceConfig:
    folder: Path

    # Render grid
    y_views: int = 121
    z_views: int = 35

    # File naming
    filename_pattern: str = "view_{frame:04d}.png"
    start_frame: int = 1


# =========================
# CACHE CONFIG
# =========================

@dataclass
class CacheConfig:
    max_cache_size: int = 300
    preload_radius_y: int = 4
    preload_radius_z: int = 2
    max_workers: int = 4
    enable_blending: bool = False
    resize_to: tuple[int, int] | None = None


# =========================
# TRACKING CONFIG
# =========================

@dataclass
class TrackingConfig:
    camera_index: int = 0

    # Smoothing
    smoothing_amount: float = 0.40
    snap_distance: float = 8.0

    # Camera preview behavior
    mirror_camera: bool = True

    # Axis correction
    flip_x: bool = False
    flip_z: bool = True

    # Haar Cascade settings
    # MediaPipe does not use these, but the old Haar tracker does.
    min_face_size: tuple[int, int] = (60, 60)
    scale_factor: float = 1.2
    min_neighbors: int = 5

    # =========================
    # CAMERA FOV MEASUREMENT
    # =========================
    # Measure these physically.
    #
    # camera_measure_distance_cm:
    #     Distance from webcam lens to wall/measurement plane.
    #
    # camera_visible_width_cm:
    #     Real-world width visible in webcam frame at that distance.
    #
    # camera_visible_height_cm:
    #     Real-world height visible in webcam frame at that distance.

    camera_measure_distance_cm: float = 198 #98
    camera_visible_width_cm: float = 204 #203
    camera_visible_height_cm: float = 158 #158

    # =========================
    # RENDER ANGLE RANGE
    # =========================
    # These must match your Blender render script.

    render_y_angle_min: float = -25.0
    render_y_angle_max: float = 25.0

    render_z_angle_min: float = -10.0
    render_z_angle_max: float = 10.0

    @property
    def camera_horizontal_fov(self) -> float:
        """
        Calculates horizontal webcam FOV from physical measurement.

        Formula:
            FOV = 2 * atan((visible_width / 2) / distance)
        """

        if self.camera_measure_distance_cm <= 0:
            return 0.0

        return 2.0 * math.degrees(
            math.atan(
                (self.camera_visible_width_cm / 2.0)
                / self.camera_measure_distance_cm
            )
        )

    @property
    def camera_vertical_fov(self) -> float:
        """
        Calculates vertical webcam FOV from physical measurement.

        Formula:
            FOV = 2 * atan((visible_height / 2) / distance)
        """

        if self.camera_measure_distance_cm <= 0:
            return 0.0

        return 2.0 * math.degrees(
            math.atan(
                (self.camera_visible_height_cm / 2.0)
                / self.camera_measure_distance_cm
            )
        )


# =========================
# THREADING CONFIG
# =========================

@dataclass
class ThreadingConfig:
    camera_poll_sleep: float = 0.001
    tracking_poll_sleep: float = 0.005
    max_tracking_fps: float = 60.0


# =========================
# WINDOW CONFIG
# =========================

@dataclass
class WindowConfig:
    window_name: str = "3D Wallpaper Engine"
    debug_window_name: str = "Face Tracking Debug"
    show_debug_window: bool = True
    fullscreen: bool = True


# =========================
# APP CONFIG
# =========================

@dataclass
class AppConfig:
    sequence: SequenceConfig
    cache: CacheConfig
    tracking: TrackingConfig
    threading: ThreadingConfig
    window: WindowConfig