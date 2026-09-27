from pathlib import Path

from fastapi.testclient import TestClient

from backend.config import Settings
from backend.main import create_app


def test_when_health_is_called_it_returns_200_with_status_ok(tmp_path: Path):
    client = TestClient(create_app(Settings(data_dir=tmp_path, camera="fake", revision="abc123")))

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
