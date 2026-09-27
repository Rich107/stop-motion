"""The Pi's Camera Module 3, through picamera2."""

from backend.camera.fake import Size


class PiCamera:
    def __init__(self, still_size: Size = (4608, 2592), preview_size: Size = (1280, 720)) -> None:
        self.still_size = still_size
        self.preview_size = preview_size
        self._picam2 = None

    @property
    def is_open(self) -> bool:
        return self._picam2 is not None
