from pathlib import Path

from backend.camera import get_camera
from backend.camera.fake import FakeCamera
from backend.config import Settings


def test_when_camera_setting_is_fake_the_factory_returns_a_fake_camera(tmp_path: Path):
    settings = Settings(data_dir=tmp_path, camera="fake", revision="dev")

    camera = get_camera(settings)

    assert isinstance(camera, FakeCamera)
