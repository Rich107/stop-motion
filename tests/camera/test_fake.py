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
