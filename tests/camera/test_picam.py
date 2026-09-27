import cv2
import numpy as np
import pytest

from backend.camera.base import CameraNotOpenError
from backend.camera.picam import PiCamera, auto_controls, fixed_controls, lores_to_bgr

# Stand-ins for libcamera's enums, which only exist on the Pi
MANUAL = "AfModeEnum.Manual"
CONTINUOUS = "AfModeEnum.Continuous"


def test_when_metadata_has_exposure_gains_and_lens_they_become_fixed_manual_controls():
    metadata = {
        "ExposureTime": 16000,
        "AnalogueGain": 2.5,
        "ColourGains": (1.9, 1.6),
        "LensPosition": 3.2,
        "Lux": 400.0,
    }

    controls = fixed_controls(metadata, manual_af=MANUAL)

    assert controls == {
        "AeEnable": False,
        "AwbEnable": False,
        "ExposureTime": 16000,
        "AnalogueGain": 2.5,
        "ColourGains": (1.9, 1.6),
        "AfMode": MANUAL,
        "LensPosition": 3.2,
    }


def test_when_metadata_has_no_lens_position_no_focus_controls_are_set():
    metadata = {"ExposureTime": 16000, "AnalogueGain": 2.5, "ColourGains": (1.9, 1.6)}

    controls = fixed_controls(metadata, manual_af=MANUAL)

    assert "AfMode" not in controls
    assert "LensPosition" not in controls


def test_when_settings_are_unlocked_on_an_autofocus_camera_auto_exposure_wb_and_focus_resume():
    controls = auto_controls(continuous_af=CONTINUOUS)

    assert controls == {"AeEnable": True, "AwbEnable": True, "AfMode": CONTINUOUS}


def test_when_settings_are_unlocked_on_a_fixed_focus_camera_no_focus_mode_is_set():
    controls = auto_controls(continuous_af=None)

    assert controls == {"AeEnable": True, "AwbEnable": True}


def test_when_a_padded_yuv420_lores_frame_is_converted_it_is_bgr_of_the_preview_size():
    # picamera2 hands YUV420 back as a (height * 3/2, stride) array, stride padded past the width
    width, height, stride = 160, 90, 192
    bgr = np.full((height, stride, 3), (40, 120, 200), np.uint8)
    bgr[:, width:] = (255, 0, 255)  # padding, which must not show
    yuv = cv2.cvtColor(bgr, cv2.COLOR_BGR2YUV_I420)

    out = lores_to_bgr(yuv, (width, height))

    assert out.shape == (height, width, 3)
    assert np.allclose(out.reshape(-1, 3).mean(axis=0), (40, 120, 200), atol=3)


@pytest.mark.parametrize(
    "use",
    [
        PiCamera.preview_jpeg,
        PiCamera.capture_jpeg,
        PiCamera.lock_settings,
        PiCamera.unlock_settings,
    ],
)
def test_when_a_pi_camera_is_not_started_using_it_raises_camera_not_open(use):
    camera = PiCamera()

    with pytest.raises(CameraNotOpenError):
        use(camera)
