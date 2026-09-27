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
