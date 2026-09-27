"""Projects on disk: one folder per film under $STOPMOTION_DATA/projects, with a project.json."""

import json
import os
import secrets
import tempfile
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path


@dataclass
class Project:
    id: str
    name: str
    created_at: str  # ISO 8601, UTC
    fps: int = 10
    stabilise: bool = True
    frames: list[str] = field(default_factory=list)


def _write_atomic(path: Path, data: bytes) -> None:
    # Write a temp file next to the target, then swap it in, so a power cut leaves either the
    # old file or the new one, never half of one
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


class ProjectStore:
    """Creates, reads and changes projects under `data_dir`."""

    def __init__(self, data_dir: Path, clock: Callable[[], datetime] = lambda: datetime.now(UTC)):
        self.data_dir = data_dir
        self.projects_dir = data_dir / "projects"
        self.clock = clock

    def create(self, name: str) -> Project:
        project = Project(id=secrets.token_hex(4), name=name, created_at=self.clock().isoformat())
        (self._dir(project.id) / "frames").mkdir(parents=True)
        self._save(project)
        return project

    def list(self) -> list[Project]:
        if not self.projects_dir.is_dir():
            return []
        projects = [self._load(d.name) for d in self.projects_dir.iterdir() if d.is_dir()]
        return sorted(projects, key=lambda p: p.created_at, reverse=True)

    def _dir(self, project_id: str) -> Path:
        return self.projects_dir / project_id

    def _load(self, project_id: str) -> Project:
        return Project(**json.loads((self._dir(project_id) / "project.json").read_text()))

    def _save(self, project: Project) -> None:
        text = json.dumps(asdict(project), indent=2) + "\n"
        _write_atomic(self._dir(project.id) / "project.json", text.encode())
