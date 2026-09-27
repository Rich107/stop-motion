from pathlib import Path

from backend.config import Settings


def test_when_revision_file_is_present_and_env_is_unset_revision_is_read_from_file(
    monkeypatch, tmp_path: Path
):
    monkeypatch.delenv("REVISION", raising=False)
    revision_file = tmp_path / "REVISION"
    revision_file.write_text("deadbeef\n")

    settings = Settings.from_env(revision_file=revision_file)

    assert settings.revision == "deadbeef"


def test_when_data_env_is_set_data_dir_uses_it(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("STOPMOTION_DATA", str(tmp_path / "films"))

    settings = Settings.from_env()

    assert settings.data_dir == tmp_path / "films"


def test_when_data_env_is_unset_data_dir_defaults_to_data(monkeypatch):
    monkeypatch.delenv("STOPMOTION_DATA", raising=False)

    settings = Settings.from_env()

    assert settings.data_dir == Path("./data")


def test_when_camera_env_is_pi_settings_use_pi_camera(monkeypatch):
    monkeypatch.setenv("STOPMOTION_CAMERA", "pi")

    settings = Settings.from_env()

    assert settings.camera == "pi"


def test_when_camera_env_is_unset_camera_defaults_to_fake(monkeypatch):
    monkeypatch.delenv("STOPMOTION_CAMERA", raising=False)

    settings = Settings.from_env()

    assert settings.camera == "fake"
