from backend.camera.picam import fixed_controls

MANUAL = "AfModeEnum.Manual"  # stands in for libcamera's enum, which only exists on the Pi


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
