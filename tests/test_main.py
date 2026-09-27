from pathlib import Path

from fastapi.testclient import TestClient

from backend.config import Settings
from backend.main import create_app


def test_when_health_is_called_it_returns_200_with_status_ok(tmp_path: Path):
    client = TestClient(create_app(Settings(data_dir=tmp_path, camera="fake", revision="abc123")))

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_when_revision_env_is_set_health_reports_it(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("REVISION", "abc123")
    client = TestClient(create_app(Settings.from_env(revision_file=tmp_path / "REVISION")))

    response = client.get("/health")

    assert response.json() == {"status": "ok", "revision": "abc123"}


def test_when_no_revision_env_or_file_is_present_health_reports_dev(monkeypatch, tmp_path: Path):
    monkeypatch.delenv("REVISION", raising=False)
    client = TestClient(create_app(Settings.from_env(revision_file=tmp_path / "REVISION")))

    response = client.get("/health")

    assert response.json()["revision"] == "dev"
