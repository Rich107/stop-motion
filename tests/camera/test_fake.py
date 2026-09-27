import cv2
import numpy as np

from backend.camera.base import Camera
from backend.camera.fake import FakeCamera


def test_when_a_fake_camera_is_started_it_is_an_open_camera():
    camera = FakeCamera()

    camera.start()

    assert isinstance(camera, Camera)
    assert camera.is_open


def test_when_a_fake_camera_is_stopped_it_is_not_open():
    camera = FakeCamera()
    camera.start()

    camera.stop()

    assert not camera.is_open


def test_when_a_fake_camera_captures_it_returns_a_jpeg_of_the_still_size():
    camera = FakeCamera(still_size=(320, 180), preview_size=(160, 90))
    camera.start()

    jpeg = camera.capture_jpeg()

    assert jpeg[:2] == b"\xff\xd8"
    assert decode(jpeg).shape == (180, 320, 3)


def decode(jpeg: bytes) -> np.ndarray:
    return cv2.imdecode(np.frombuffer(jpeg, np.uint8), cv2.IMREAD_COLOR)
