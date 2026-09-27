"""App settings, read from the environment."""

import os
from dataclasses import dataclass
from pathlib import Path

# Written by the deploy workflow next to backend/ (see docs/deploy-plan.md)
DEFAULT_REVISION_FILE = Path(__file__).resolve().parent.parent / "REVISION"


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    camera: str
    revision: str

    @classmethod
    def from_env(cls, revision_file: Path = DEFAULT_REVISION_FILE) -> "Settings":
        return cls(
            data_dir=Path("./data"), camera="fake", revision=os.environ.get("REVISION", "dev")
        )
