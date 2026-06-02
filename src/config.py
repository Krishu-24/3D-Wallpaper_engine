from dataclasses import dataclass
from pathlib import Path


@dataclass
class SequenceConfig:
    folder: Path
    y_views: int = 60
    z_views: int = 9
    filename_pattern: str = "view_{frame:04d}.png"
    start_frame: int = 1


@dataclass
class CacheConfig:
    max_cache_size: int = 120
    preload_radius_y: int = 3
    preload_radius_z: int = 1
    max_workers: int = 4
    enable_blending: bool = False
    resize_to: tuple[int, int] | None = None


@dataclass
class TrackingConfig:
    camera_index: int = 0

    smoothing_amount: float = 0.40
    snap_distance: float = 8.0

    mirror_camera: bool = True

    flip_x: bool = False
    flip_z: bool = True

    min_face_size: tuple[int, int] = (60, 60)
    scale_factor: float = 1.2
    min_neighbors: int = 5


@dataclass
class ThreadingConfig:
    camera_poll_sleep: float = 0.001
    tracking_poll_sleep: float = 0.005
    max_tracking_fps: float = 60.0


@dataclass
class WindowConfig:
    window_name: str = "3D Wallpaper Engine"
    debug_window_name: str = "Face Tracking Debug"
    show_debug_window: bool = True
    fullscreen: bool = True


@dataclass
class AppConfig:
    sequence: SequenceConfig
    cache: CacheConfig
    tracking: TrackingConfig
    threading: ThreadingConfig
    window: WindowConfig