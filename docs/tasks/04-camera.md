# 04: Camera interface, fake and Pi cameras

**Goal:** one camera API the app uses everywhere, with a fake for dev/CI and a picamera2 version for the Pi.
**Depends on:** 01.

## Scope

- `backend/camera/base.py`: `Camera` protocol: `start()`, `stop()`, `preview_jpeg() -> bytes`
  (low-res, for MJPEG), `capture_jpeg() -> bytes` (full-res still, preview keeps running),
  `lock_settings()` / `unlock_settings()` (exposure, white balance, focus), `is_open`.
- `backend/camera/fake.py`: `FakeCamera` draws a moving test pattern with a frame counter (OpenCV/numpy),
  deterministic with a seed. Configurable sizes.
- `backend/camera/picam.py`: `PiCamera` with picamera2: main (full-res still) + lores (1280x720) streams,
  software JPEG for the preview (Pi 5 has no hardware JPEG encoder), `lock_settings` reads current
  AE/AWB/lens metadata and sets them as fixed controls. Import picamera2 lazily so the module imports
  without it.
- `get_camera(settings)` factory; wire into the `create_app` lifespan (start on startup, stop on shutdown).
- `/health` returns 503 if the camera isn't open (as `docs/deploy-plan.md` expects).

## Behaviours to test

- When the fake camera captures, it returns a valid JPEG of the configured still size.
- When the fake camera previews, it returns a JPEG of the preview size, and consecutive previews differ.
- When settings are locked then unlocked the fake camera reports it.
- When `STOPMOTION_CAMERA=fake` the factory returns a FakeCamera; `pi` returns a PiCamera (constructed
  lazily, not started).
- When the app starts the camera is started, and it is stopped on shutdown.
- When the camera isn't open `/health` returns 503.
- `PiCamera` logic that doesn't need hardware (e.g. building fixed controls from metadata) is a pure
  function and tested; the rest is listed as manual Pi checks in the PR.

## Progress

- [x] Branch created off fresh `origin/main`
- [x] Camera protocol
- [x] FakeCamera capture
- [x] FakeCamera preview
- [x] Lock/unlock
- [x] Factory
- [ ] App lifespan
- [ ] Health 503
- [ ] PiCamera + pure control-building helper
- [ ] Manual Pi checks listed in PR
- [ ] PR opened
