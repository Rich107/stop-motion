from backend.camera.picam import auto_controls, fixed_controls

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
