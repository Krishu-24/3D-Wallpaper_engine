import sys
from pathlib import Path
import os

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"

if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from config import (
    AppConfig,
    CacheConfig,
    SequenceConfig,
    TrackingConfig,
    ThreadingConfig,
    WindowConfig,
)
from renderer import WallpaperRenderer


def build_config():
    load_dotenv(PROJECT_ROOT / ".env")

    sequence_folder = os.getenv("IMAGE_SEQUENCE_FOLDER")

    if not sequence_folder:
        raise RuntimeError(
            "IMAGE_SEQUENCE_FOLDER is missing. Add it to your .env file."
        )

    return AppConfig(
        sequence=SequenceConfig(
            folder=Path(sequence_folder),

            # Current old rendered sequence
            y_views=60,
            z_views=9,

            # Use this if files are view_0001.png, view_0002.png...
            filename_pattern="view_{frame:04d}.png",

            # Change this if your sequence starts from a different frame number
            start_frame=1,
        ),
        cache=CacheConfig(
            max_cache_size=120,
            preload_radius_y=3,
            preload_radius_z=1,
            max_workers=4,

            # Keep this off for the low-count old sequence.
            enable_blending=False,

            resize_to=None,
        ),
        tracking=TrackingConfig(
            camera_index=0,

            smoothing_amount=0.40,
            snap_distance=8.0,

            mirror_camera=True,

            flip_x=False,
            flip_z=True,

            min_face_size=(60, 60),
            scale_factor=1.2,
            min_neighbors=5,
        ),
        threading=ThreadingConfig(
            camera_poll_sleep=0.001,
            tracking_poll_sleep=0.005,
            max_tracking_fps=60.0,
        ),
        window=WindowConfig(
            window_name="3D Wallpaper Engine",
            debug_window_name="Face Tracking Debug",
            show_debug_window=True,
            fullscreen=True,
        ),
    )


def main():
    config = build_config()
    renderer = WallpaperRenderer(config)
    renderer.run()


if __name__ == "__main__":
    main()