from concurrent.futures import ThreadPoolExecutor

import cv2
import numpy as np
import pytest

from backend.camera.base import Camera, CameraNotOpenError
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


def test_when_a_fake_camera_previews_it_returns_a_jpeg_of_the_preview_size():
    camera = FakeCamera(still_size=(320, 180), preview_size=(160, 90))
    camera.start()

    jpeg = camera.preview_jpeg()

    assert decode(jpeg).shape == (90, 160, 3)


def test_when_a_fake_camera_previews_twice_the_frames_differ():
    camera = FakeCamera(still_size=(320, 180), preview_size=(160, 90))
    camera.start()
    first = camera.preview_jpeg()

    second = camera.preview_jpeg()

    assert not np.array_equal(decode(first), decode(second))


def test_when_two_fake_cameras_share_a_seed_their_frames_match():
    cameras = [FakeCamera(still_size=(320, 180), preview_size=(160, 90), seed=7) for _ in range(2)]
    for camera in cameras:
        camera.start()

    first, second = (camera.preview_jpeg() for camera in cameras)

    assert first == second


def test_when_two_fake_cameras_have_different_seeds_their_frames_differ():
    cameras = [FakeCamera(still_size=(320, 180), preview_size=(160, 90), seed=s) for s in (1, 2)]
    for camera in cameras:
        camera.start()

    first, second = (camera.preview_jpeg() for camera in cameras)

    assert first != second


def test_when_many_threads_preview_at_once_every_frame_is_different():
    camera = FakeCamera(still_size=(320, 180), preview_size=(160, 90))
    camera.start()

    with ThreadPoolExecutor(max_workers=8) as pool:
        frames = list(pool.map(lambda _: camera.preview_jpeg(), range(64)))

    assert len(set(frames)) == 64


def test_when_settings_are_locked_the_fake_camera_reports_them_locked():
    camera = FakeCamera()
    camera.start()

    camera.lock_settings()

    assert camera.settings_locked


def test_when_locked_settings_are_unlocked_the_fake_camera_reports_them_unlocked():
    camera = FakeCamera()
    camera.start()
    camera.lock_settings()

    camera.unlock_settings()

    assert not camera.settings_locked


def test_when_a_locked_fake_camera_is_stopped_and_restarted_its_settings_are_unlocked():
    camera = FakeCamera()
    camera.start()
    camera.lock_settings()

    camera.stop()
    camera.start()

    assert not camera.settings_locked


@pytest.mark.parametrize("take", [FakeCamera.preview_jpeg, FakeCamera.capture_jpeg])
def test_when_a_fake_camera_is_not_started_taking_a_picture_raises_camera_not_open(take):
    camera = FakeCamera()

    with pytest.raises(CameraNotOpenError):
        take(camera)


@pytest.mark.parametrize("use", [FakeCamera.lock_settings, FakeCamera.unlock_settings])
def test_when_a_fake_camera_is_not_started_changing_settings_raises_camera_not_open(use):
    camera = FakeCamera()

    with pytest.raises(CameraNotOpenError):
        use(camera)


def decode(jpeg: bytes) -> np.ndarray:
    return cv2.imdecode(np.frombuffer(jpeg, np.uint8), cv2.IMREAD_COLOR)
