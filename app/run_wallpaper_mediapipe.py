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

import core.renderer as renderer_module

from core.renderer import WallpaperRenderer
from mediapipe_core.mediapipe_tracking_worker import MediaPipeTrackingWorker
from mediapipe_core.mediapipe_debug_view import create_mediapipe_debug_view


def build_config():
    load_dotenv(PROJECT_ROOT / ".env")

    sequence_folder = os.getenv("IMAGE_SEQUENCE_FOLDER")

    if not sequence_folder:
        raise RuntimeError(
            "IMAGE_SEQUENCE_FOLDER is missing. Add it to your .env file."
        )

    return AppConfig(
        # Only the local/private sequence path comes from .env.
        # All other sequence values come from SequenceConfig defaults.
        sequence=SequenceConfig(
            folder=Path(sequence_folder),
        ),

        # Use defaults from src/core/config.py
        cache=CacheConfig(),
        tracking=TrackingConfig(),
        threading=ThreadingConfig(),

        # Only change names for the MediaPipe app window.
        # All other window values come from WindowConfig defaults.
        window=WindowConfig(
            window_name="3D Wallpaper Engine - MediaPipe",
            debug_window_name="MediaPipe Landmark Debug",
        ),
    )


def get_mediapipe_model_path():
    load_dotenv(PROJECT_ROOT / ".env")

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
    config = build_config()
    mediapipe_model_path = get_mediapipe_model_path()

    # Replace only the debug view used by renderer.py during this app run.
    # This does not edit src/core/renderer.py.
    renderer_module.create_debug_view = create_mediapipe_debug_view

    renderer = WallpaperRenderer(config)

    # Replace only the old Haar tracking worker.
    # CameraWorker, SharedState, ImageSequenceCache, smoothing, indexing,
    # threading, windows, and render loop still come from the old engine.
    renderer.tracking_worker = MediaPipeTrackingWorker(
        shared_state=renderer.shared_state,
        model_path=mediapipe_model_path,
        min_face_size=config.tracking.min_face_size,
        poll_sleep=config.threading.tracking_poll_sleep,
        max_tracking_fps=config.threading.max_tracking_fps,
        min_face_detection_confidence=0.5,
        min_face_presence_confidence=0.5,
        min_tracking_confidence=0.5,
        tracking_point="eye_mid",
    )

    print("[INFO] Starting MediaPipe wallpaper renderer.")
    print("[INFO] Reusing old camera, cache, indexing, smoothing, threading, and render pipeline.")
    print("[INFO] MediaPipe replaces only the tracking worker.")
    print("[INFO] MediaPipe debug view uses landmarks.")

    print(
        "[INFO] Sequence: "
        f"{config.sequence.y_views} x {config.sequence.z_views}"
    )

    print(
        "[INFO] Camera FOV from config: "
        f"H={config.tracking.camera_horizontal_fov:.2f} deg, "
        f"V={config.tracking.camera_vertical_fov:.2f} deg"
    )

    print(
        "[INFO] Render angle range from config: "
        f"Y={config.tracking.render_y_angle_min:.2f} to "
        f"{config.tracking.render_y_angle_max:.2f} deg, "
        f"Z={config.tracking.render_z_angle_min:.2f} to "
        f"{config.tracking.render_z_angle_max:.2f} deg"
    )

    print(
        "[INFO] Cache from config: "
        f"max={config.cache.max_cache_size}, "
        f"preload_y={config.cache.preload_radius_y}, "
        f"preload_z={config.cache.preload_radius_z}, "
        f"workers={config.cache.max_workers}, "
        f"blending={config.cache.enable_blending}"
    )

    renderer.run()


if __name__ == "__main__":
    main()