"""The camera interface the rest of the app uses."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class Camera(Protocol):
    """A camera with a low-res live preview and full-res stills.

    Methods may be called from different threads (HTTP requests, the GPIO button).
    """

    @property
    def is_open(self) -> bool: ...

    @property
    def settings_locked(self) -> bool: ...

    def start(self) -> None: ...

    def stop(self) -> None: ...

    def preview_jpeg(self) -> bytes:
        """A low-res frame for the MJPEG stream."""
        ...

    def capture_jpeg(self) -> bytes:
        """A full-res still; the preview keeps running."""
        ...

    def lock_settings(self) -> None:
        """Fix exposure, white balance and focus, so frames of a film match."""
        ...

    def unlock_settings(self) -> None:
        """Go back to automatic exposure, white balance and focus."""
        ...
