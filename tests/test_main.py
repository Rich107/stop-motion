from pathlib import Path

from fastapi.testclient import TestClient

from backend.camera import FakeCamera
from backend.config import Settings
from backend.main import app, create_app


def test_when_health_is_called_it_returns_200_with_status_ok(tmp_path: Path):
    app = create_app(Settings(data_dir=tmp_path, camera="fake", revision="abc123"))

    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_when_revision_env_is_set_health_reports_it(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("REVISION", "abc123")
    app = create_app(Settings.from_env(revision_file=tmp_path / "REVISION"))

    with TestClient(app) as client:
        response = client.get("/health")

    assert response.json() == {"status": "ok", "revision": "abc123"}


def test_when_no_revision_env_or_file_is_present_health_reports_dev(monkeypatch, tmp_path: Path):
    monkeypatch.delenv("REVISION", raising=False)
    app = create_app(Settings.from_env(revision_file=tmp_path / "REVISION"))

    with TestClient(app) as client:
        response = client.get("/health")

    assert response.json()["revision"] == "dev"


def test_when_module_app_is_served_health_returns_200():
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200


def test_when_the_app_starts_the_camera_is_started(tmp_path: Path):
    camera = FakeCamera()
    app = create_app(Settings(data_dir=tmp_path, camera="fake", revision="dev"), camera=camera)

    with TestClient(app):
        is_open = camera.is_open

    assert is_open


def test_when_the_app_shuts_down_the_camera_is_stopped(tmp_path: Path):
    camera = FakeCamera()
    app = create_app(Settings(data_dir=tmp_path, camera="fake", revision="dev"), camera=camera)

    with TestClient(app):
        pass

    assert not camera.is_open


def test_when_the_camera_is_not_open_health_returns_503_saying_so(tmp_path: Path):
    camera = FakeCamera()
    app = create_app(Settings(data_dir=tmp_path, camera="fake", revision="abc123"), camera=camera)

    with TestClient(app) as client:
        camera.stop()
        response = client.get("/health")

    assert response.status_code == 503
    assert response.json() == {
        "status": "error",
        "reason": "camera not open",
        "revision": "abc123",
    }


class UnpluggedCamera(FakeCamera):
    def start(self) -> None:
        raise RuntimeError("Camera __init__ sequence did not complete")


def test_when_the_camera_fails_to_start_the_app_still_serves_health_as_503(tmp_path: Path):
    app = create_app(
        Settings(data_dir=tmp_path, camera="fake", revision="dev"), camera=UnpluggedCamera()
    )

    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 503
    assert response.json()["reason"] == "camera not open"
