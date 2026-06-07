import sys
from pathlib import Path
import os

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"

if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from core.config import (
    AppConfig,
    CacheConfig,
    SequenceConfig,
    TrackingConfig,
    ThreadingConfig,
    WindowConfig,
)

from core.renderer import WallpaperRenderer


def build_config():
    load_dotenv(PROJECT_ROOT / ".env")

    sequence_folder = os.getenv("IMAGE_SEQUENCE_FOLDER")

    if not sequence_folder:
        raise RuntimeError(
            "IMAGE_SEQUENCE_FOLDER is missing. Add it to your .env file."
        )

    return AppConfig(
        # Only folder is passed here because it is local/private.
        # y_views, z_views, filename_pattern, and start_frame come from SequenceConfig.
        sequence=SequenceConfig(
            folder=Path(sequence_folder),
        ),

        # All values come from src/core/config.py defaults.
        cache=CacheConfig(),
        tracking=TrackingConfig(),
        threading=ThreadingConfig(),
        window=WindowConfig(),
    )


def main():
    config = build_config()

    print("[INFO] Starting Haar Cascade wallpaper renderer.")
    print("[INFO] Using config defaults from src/core/config.py.")

    print(
        "[INFO] Sequence: "
        f"{config.sequence.y_views} x {config.sequence.z_views}, "
        f"pattern={config.sequence.filename_pattern}, "
        f"start_frame={config.sequence.start_frame}"
    )

    print(
        "[INFO] Cache: "
        f"max={config.cache.max_cache_size}, "
        f"preload_y={config.cache.preload_radius_y}, "
        f"preload_z={config.cache.preload_radius_z}, "
        f"workers={config.cache.max_workers}, "
        f"blending={config.cache.enable_blending}"
    )

    print(
        "[INFO] Tracking: "
        f"smoothing={config.tracking.smoothing_amount}, "
        f"snap={config.tracking.snap_distance}, "
        f"camera={config.tracking.camera_index}, "
        f"mirror={config.tracking.mirror_camera}"
    )

    print(
        "[INFO] Threading: "
        f"camera_sleep={config.threading.camera_poll_sleep}, "
        f"tracking_sleep={config.threading.tracking_poll_sleep}, "
        f"tracking_fps={config.threading.max_tracking_fps}"
    )

    renderer = WallpaperRenderer(config)
    renderer.run()


if __name__ == "__main__":
    main()