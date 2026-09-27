"""A camera that draws a test pattern, for dev, tests and CI."""

import threading

import cv2
import numpy as np

from backend.camera.base import CameraNotOpenError, encode_jpeg

Size = tuple[int, int]  # (width, height)


class FakeCamera:
    """Draws colour bars with a ball that moves and a counter that goes up each frame.

    The colours come from `seed`, so two cameras with the same seed draw the same frames.
    """

    def __init__(
        self, still_size: Size = (1920, 1080), preview_size: Size = (640, 360), seed: int = 0
    ) -> None:
        self.still_size = still_size
        self.preview_size = preview_size
        self._colours = np.random.default_rng(seed).integers(0, 256, size=(8, 3), dtype=np.uint8)
        self._lock = threading.Lock()
        self._open = False
        self._locked = False
        self._frame = 0

    @property
    def is_open(self) -> bool:
        return self._open

    @property
    def settings_locked(self) -> bool:
        return self._locked

    def start(self) -> None:
        with self._lock:
            self._open = True

    def stop(self) -> None:
        with self._lock:
            self._open = False

    def preview_jpeg(self) -> bytes:
        return encode_jpeg(self._draw(self.preview_size), quality=70)

    def capture_jpeg(self) -> bytes:
        return encode_jpeg(self._draw(self.still_size))

    def lock_settings(self) -> None:
        with self._lock:
            self._locked = True

    def unlock_settings(self) -> None:
        raise NotImplementedError

    def _draw(self, size: Size) -> np.ndarray:
        with self._lock:
            if not self._open:
                raise CameraNotOpenError("The camera is not started")
            self._frame += 1
            frame = self._frame
        width, height = size
        bars = np.repeat(self._colours, -(-width // len(self._colours)), axis=0)[:width]
        img = np.ascontiguousarray(np.broadcast_to(bars, (height, width, 3)))
        # The ball crosses the frame every 60 frames, so consecutive frames always differ
        x = round((frame % 60) / 60 * width)
        radius = max(2, height // 8)
        cv2.circle(img, (x, height // 2), radius, (255, 255, 255), -1)
        scale = height / 360
        cv2.putText(
            img,
            str(frame),
            (round(10 * scale), round(40 * scale)),
            cv2.FONT_HERSHEY_SIMPLEX,
            scale,
            (0, 0, 0),
            max(1, round(2 * scale)),
        )
        return img
