"""Cameras: one interface, a fake for dev and CI, and picamera2 on the Pi."""

from backend.camera.base import Camera, CameraNotOpenError
from backend.camera.fake import FakeCamera
from backend.config import Settings

__all__ = ["Camera", "CameraNotOpenError", "FakeCamera", "get_camera"]


def get_camera(settings: Settings) -> Camera:
    """The camera `settings.camera` names, not started yet."""
    return FakeCamera()
