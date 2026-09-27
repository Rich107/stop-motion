"""Cameras: one interface, a fake for dev and CI, and picamera2 on the Pi."""

from backend.camera.base import Camera, CameraNotOpenError
from backend.camera.fake import FakeCamera
from backend.camera.picam import PiCamera
from backend.config import Settings

__all__ = ["Camera", "CameraNotOpenError", "FakeCamera", "PiCamera", "get_camera"]


def get_camera(settings: Settings) -> Camera:
    """The camera `settings.camera` names, not started yet."""
    if settings.camera == "pi":
        return PiCamera()
    return FakeCamera()
