import math
import threading
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import cv2


class ImageSequenceCache:
    """
    Optimized image sequence loader.

    Features:
    - LRU cache
    - Async background preloading
    - Float indexing
    - Optional bilinear frame blending
    - Controllable preload radius
    - Controllable max cached frames
    """

    def __init__(
        self,
        folder,
        y_views,
        z_views,
        filename_pattern="view_{frame:04d}.png",
        start_frame=1,
        max_cache_size=300,
        preload_radius_y=4,
        preload_radius_z=2,
        enable_blending=True,
        max_workers=4,
        resize_to=None,
    ):
        self.folder = Path(folder)
        self.y_views = y_views
        self.z_views = z_views
        self.filename_pattern = filename_pattern
        self.start_frame = start_frame

        self.max_cache_size = max_cache_size
        self.preload_radius_y = preload_radius_y
        self.preload_radius_z = preload_radius_z
        self.enable_blending = enable_blending
        self.resize_to = resize_to

        self.cache = OrderedDict()
        self.loading = set()

        self.lock = threading.Lock()
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

    def clamp(self, value, min_value, max_value):
        return max(min_value, min(max_value, value))

    def grid_to_frame_number(self, y_index, z_index):
        """
        Converts a 2D grid coordinate into the rendered frame number.

        Assumes render order:
        z row first, then y across that row.

        Example:
        z = 0, y = 0 -> frame 1
        z = 0, y = 1 -> frame 2
        z = 1, y = 0 -> frame y_views + 1
        """

        y_index = int(self.clamp(y_index, 0, self.y_views - 1))
        z_index = int(self.clamp(z_index, 0, self.z_views - 1))

        flat_index = z_index * self.y_views + y_index
        return self.start_frame + flat_index

    def frame_path(self, y_index, z_index):
        frame_number = self.grid_to_frame_number(y_index, z_index)
        filename = self.filename_pattern.format(frame=frame_number)
        return self.folder / filename

    def load_frame_from_disk(self, y_index, z_index):
        path = self.frame_path(y_index, z_index)

        img = cv2.imread(str(path), cv2.IMREAD_COLOR)

        if img is None:
            raise FileNotFoundError(f"Could not load image: {path}")

        if self.resize_to is not None:
            img = cv2.resize(img, self.resize_to, interpolation=cv2.INTER_AREA)

        return img

    def get_cached_frame(self, y_index, z_index):
        key = (int(y_index), int(z_index))

        with self.lock:
            if key in self.cache:
                self.cache.move_to_end(key)
                return self.cache[key]

        img = self.load_frame_from_disk(*key)

        with self.lock:
            self.cache[key] = img
            self.cache.move_to_end(key)

            while len(self.cache) > self.max_cache_size:
                self.cache.popitem(last=False)

        return img

    def preload_frame(self, y_index, z_index):
        key = (int(y_index), int(z_index))

        with self.lock:
            if key in self.cache or key in self.loading:
                return

            self.loading.add(key)

        def task():
            try:
                img = self.load_frame_from_disk(*key)

                with self.lock:
                    self.cache[key] = img
                    self.cache.move_to_end(key)

                    while len(self.cache) > self.max_cache_size:
                        self.cache.popitem(last=False)

            except Exception as e:
                print(f"[PRELOAD ERROR] {key}: {e}")

            finally:
                with self.lock:
                    self.loading.discard(key)

        self.executor.submit(task)

    def preload_around(self, y_float, z_float):
        center_y = int(round(y_float))
        center_z = int(round(z_float))

        for dz in range(-self.preload_radius_z, self.preload_radius_z + 1):
            for dy in range(-self.preload_radius_y, self.preload_radius_y + 1):
                y = self.clamp(center_y + dy, 0, self.y_views - 1)
                z = self.clamp(center_z + dz, 0, self.z_views - 1)

                self.preload_frame(y, z)

    def get_frame_nearest(self, y_float, z_float):
        y_index = int(round(y_float))
        z_index = int(round(z_float))

        y_index = self.clamp(y_index, 0, self.y_views - 1)
        z_index = self.clamp(z_index, 0, self.z_views - 1)

        self.preload_around(y_float, z_float)

        return self.get_cached_frame(y_index, z_index)

    def get_frame_blended(self, y_float, z_float):
        """
        Bilinear blend between the 4 neighboring frames.

        This makes movement between rendered views feel smoother.
        """

        y_float = self.clamp(y_float, 0, self.y_views - 1)
        z_float = self.clamp(z_float, 0, self.z_views - 1)

        y0 = int(math.floor(y_float))
        y1 = int(math.ceil(y_float))
        z0 = int(math.floor(z_float))
        z1 = int(math.ceil(z_float))

        y0 = self.clamp(y0, 0, self.y_views - 1)
        y1 = self.clamp(y1, 0, self.y_views - 1)
        z0 = self.clamp(z0, 0, self.z_views - 1)
        z1 = self.clamp(z1, 0, self.z_views - 1)

        wy = y_float - y0
        wz = z_float - z0

        self.preload_around(y_float, z_float)

        img00 = self.get_cached_frame(y0, z0)
        img10 = self.get_cached_frame(y1, z0)
        img01 = self.get_cached_frame(y0, z1)
        img11 = self.get_cached_frame(y1, z1)

        top = cv2.addWeighted(img00, 1.0 - wy, img10, wy, 0)
        bottom = cv2.addWeighted(img01, 1.0 - wy, img11, wy, 0)

        blended = cv2.addWeighted(top, 1.0 - wz, bottom, wz, 0)

        return blended

    def get_frame(self, y_float, z_float):
        if self.enable_blending:
            return self.get_frame_blended(y_float, z_float)

        return self.get_frame_nearest(y_float, z_float)

    def cache_info(self):
        with self.lock:
            return {
                "cached_frames": len(self.cache),
                "loading_frames": len(self.loading),
                "max_cache_size": self.max_cache_size,
            }

    def shutdown(self):
        self.executor.shutdown(wait=False)