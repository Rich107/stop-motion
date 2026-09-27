from pathlib import Path

from backend.camera import get_camera
from backend.camera.fake import FakeCamera
from backend.camera.picam import PiCamera
from backend.config import Settings


def test_when_camera_setting_is_fake_the_factory_returns_a_fake_camera(tmp_path: Path):
    settings = Settings(data_dir=tmp_path, camera="fake", revision="dev")

    camera = get_camera(settings)

    assert isinstance(camera, FakeCamera)


def test_when_camera_setting_is_pi_the_factory_returns_a_pi_camera_that_is_not_started(
    tmp_path: Path,
):
    settings = Settings(data_dir=tmp_path, camera="pi", revision="dev")

    camera = get_camera(settings)

    assert isinstance(camera, PiCamera)
    assert not camera.is_open
