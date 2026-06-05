from dataclasses import dataclass
from pathlib import Path


@dataclass
class SequenceConfig:
    folder: Path
    y_views: int = 121
    z_views: int = 35
    filename_pattern: str = "view_{frame:04d}.png"
    start_frame: int = 1

@dataclass
@dataclass
class CacheConfig:
    max_cache_size: int = 180
    preload_radius_y: int = 8
    preload_radius_z: int = 2
    max_workers: int = 6
    enable_blending: bool = True
    resize_to: tuple[int, int] | None = None


@dataclass
class TrackingConfig:
    camera_index: int = 0

    smoothing_amount: float = 0.55
    snap_distance: float = 6.0

    mirror_camera: bool = True

    flip_x: bool = False
    flip_z: bool = True

    min_face_size: tuple[int, int] = (60, 60)
    scale_factor: float = 1.2
    min_neighbors: int = 5


@dataclass
@dataclass
class ThreadingConfig:
    camera_poll_sleep: float = 0.001
    tracking_poll_sleep: float = 0.005
    max_tracking_fps: float = 30.0


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