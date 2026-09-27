"""App settings, read from the environment."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    camera: str
    revision: str
