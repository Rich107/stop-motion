"""A camera that draws a test pattern, for dev, tests and CI."""

import threading


class FakeCamera:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._open = False
        self._locked = False

    @property
    def is_open(self) -> bool:
        return self._open

    @property
    def settings_locked(self) -> bool:
        return self._locked

    def start(self) -> None:
        with self._lock:
            self._open = True

    def stop(self) -> None:
        with self._lock:
            self._open = False

    def preview_jpeg(self) -> bytes:
        raise NotImplementedError

    def capture_jpeg(self) -> bytes:
        raise NotImplementedError

    def lock_settings(self) -> None:
        raise NotImplementedError

    def unlock_settings(self) -> None:
        raise NotImplementedError
