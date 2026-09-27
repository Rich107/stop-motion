"""App settings, read from the environment."""

import os
from dataclasses import dataclass
from pathlib import Path

# Written by the deploy workflow next to backend/ (see docs/deploy-plan.md)
DEFAULT_REVISION_FILE = Path(__file__).resolve().parent.parent / "REVISION"


def _read_revision(revision_file: Path) -> str:
    if "REVISION" in os.environ:
        return os.environ["REVISION"]
    if revision_file.is_file():
        return revision_file.read_text().strip()
    return "dev"


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    camera: str
    revision: str

    @classmethod
    def from_env(cls, revision_file: Path = DEFAULT_REVISION_FILE) -> "Settings":
        return cls(data_dir=Path("./data"), camera="fake", revision=_read_revision(revision_file))
