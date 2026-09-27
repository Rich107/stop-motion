"""The Pi's Camera Module 3, through picamera2."""

import threading
from collections.abc import Mapping
from typing import Any

import cv2
import numpy as np

from backend.camera.base import CameraNotOpenError, encode_jpeg
from backend.camera.fake import Size

MAX_FRAME_US = 100_000  # longest frame (and so exposure) the preview may slow to: 10 fps
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


def lores_to_bgr(yuv420: np.ndarray, size: Size) -> np.ndarray:
    """The lores stream's YUV420 array as a BGR image of `size`.

    picamera2 returns it as (height * 3/2, stride) with any row padding left in; OpenCV converts
    the whole stride's width, then the padding is cut off.
    """
    width, height = size
    return cv2.cvtColor(yuv420, cv2.COLOR_YUV2BGR_I420)[:height, :width]


class PiCamera:
    """Camera Module 3: a full-res main stream for stills, a lores stream for the preview.

    picamera2 is only imported by `start()`, so this module loads off the Pi. One lock keeps
    HTTP requests and the button from using the camera while another thread stops it.
    """

    def __init__(self, still_size: Size = (4608, 2592), preview_size: Size = (1280, 720)) -> None:
        self.still_size = still_size
        self.preview_size = preview_size
        self._lock = threading.Lock()
        self._picam2: Any = None
        self._lores_size = preview_size
        self._locked = False
        # libcamera's (Manual, Continuous) AfModeEnum values, or None if the camera can't focus
        self._af_modes: tuple[Any, Any] | None = None

    @property
    def is_open(self) -> bool:
        return self._picam2 is not None

    @property
    def settings_locked(self) -> bool:
        return self._locked

    def start(self) -> None:
        with self._lock:
            if self._picam2 is not None:
                return
            # Only on the Pi: installed with apt, seen through --system-site-packages
            from libcamera import controls
            from picamera2 import Picamera2

            picam2 = Picamera2()
            try:
                if "AfMode" in picam2.camera_controls:
                    self._af_modes = (controls.AfModeEnum.Manual, controls.AfModeEnum.Continuous)
                config = picam2.create_still_configuration(
                    # RGB888 comes out in OpenCV's BGR order. The Pi 4 only allows a YUV lores
                    # stream; the Pi 5 could do RGB, but converting 720p costs about a millisecond
                    main={"size": self.still_size, "format": "RGB888"},
                    lores={"size": self.preview_size, "format": "YUV420"},
                    # Two full-res buffers so the preview keeps flowing (the default is one)
                    buffer_count=2,
                    # At least 10 fps in a dim room, rather than the stills default of 1000 s
                    controls={"FrameDurationLimits": (100, MAX_FRAME_US)}
                    | auto_controls(self._af_modes[1] if self._af_modes else None),
                )
                picam2.configure(config)
                self._lores_size = picam2.stream_configuration("lores")["size"]
                picam2.start()
            except BaseException:
                picam2.close()
                raise
            self._picam2 = picam2
            self._locked = False

    def stop(self) -> None:
        with self._lock:
            picam2, self._picam2 = self._picam2, None
            self._locked = False
            if picam2 is not None:
                picam2.close()  # stops it first

    def preview_jpeg(self) -> bytes:
        with self._lock:
            yuv = self._open().capture_array("lores")
        # Encode outside the lock so a still capture doesn't wait on it
        return encode_jpeg(lores_to_bgr(yuv, self._lores_size), quality=70)

    def capture_jpeg(self) -> bytes:
        # A frame from the running main stream, so the preview doesn't stop or change mode
        with self._lock:
            bgr = self._open().capture_array("main")
        return encode_jpeg(bgr, quality=92)

    def lock_settings(self) -> None:
        with self._lock:
            picam2 = self._open()
            metadata = picam2.capture_metadata()
            manual = self._af_modes[0] if self._af_modes else None
            picam2.set_controls(fixed_controls(metadata, manual_af=manual))
            self._locked = True

    def unlock_settings(self) -> None:
        with self._lock:
            continuous = self._af_modes[1] if self._af_modes else None
            self._open().set_controls(auto_controls(continuous_af=continuous))
            self._locked = False

    def _open(self) -> Any:
        if self._picam2 is None:
            raise CameraNotOpenError("The camera is not started")
        return self._picam2
