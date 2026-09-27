"""The Pi's Camera Module 3, through picamera2."""

from collections.abc import Mapping
from typing import Any

from backend.camera.fake import Size

# What auto exposure, auto white balance and autofocus settled on, read back from the metadata
_LOCKED = ("ExposureTime", "AnalogueGain", "ColourGains")


def fixed_controls(metadata: Mapping[str, Any], manual_af: Any) -> dict[str, Any]:
    """Controls that hold the camera at the exposure, white balance and focus in `metadata`.

    `manual_af` is libcamera's `controls.AfModeEnum.Manual`, passed in so this runs off the Pi.
    """
    controls: dict[str, Any] = {"AeEnable": False, "AwbEnable": False}
    controls |= {k: metadata[k] for k in _LOCKED if k in metadata}
    # Only autofocus cameras (like the Module 3) report a lens position or accept AF controls
    if "LensPosition" in metadata:
        controls |= {"AfMode": manual_af, "LensPosition": metadata["LensPosition"]}
    return controls


def auto_controls(continuous_af: Any | None) -> dict[str, Any]:
    """Controls that hand exposure, white balance and focus back to the camera.

    `continuous_af` is libcamera's `controls.AfModeEnum.Continuous`, or None without autofocus.
    """
    controls: dict[str, Any] = {"AeEnable": True, "AwbEnable": True}
    if continuous_af is not None:
        controls["AfMode"] = continuous_af
    return controls


class PiCamera:
    def __init__(self, still_size: Size = (4608, 2592), preview_size: Size = (1280, 720)) -> None:
        self.still_size = still_size
        self.preview_size = preview_size
        self._picam2 = None

    @property
    def is_open(self) -> bool:
        return self._picam2 is not None
