"""Projects on disk: one folder per film under $STOPMOTION_DATA/projects, with a project.json."""

import json
import os
import re
import secrets
import shutil
import tempfile
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import cv2
import numpy as np

DEFAULT_NAME = re.compile(r"Film (\d+)")
THUMB_WIDTH = 480
# An allowlist rather than looking for "..": nothing that can name another folder gets through
VALID_ID = re.compile(r"[A-Za-z0-9_-]{1,64}")


class InvalidProjectIdError(ValueError):
    """The id could point outside the projects folder, so it's never used as a path."""


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


def _thumbnail(jpeg: bytes) -> bytes:
    """A small copy of a photo for the projects page."""
    img = cv2.imdecode(np.frombuffer(jpeg, np.uint8), cv2.IMREAD_COLOR)
    h, w = img.shape[:2]
    if w > THUMB_WIDTH:
        img = cv2.resize(
            img, (THUMB_WIDTH, round(h * THUMB_WIDTH / w)), interpolation=cv2.INTER_AREA
        )
    ok, data = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 80])
    if not ok:
        raise OSError("Could not encode the thumbnail")
    return data.tobytes()


class ProjectStore:
    """Creates, reads and changes projects under `data_dir`."""

    def __init__(self, data_dir: Path, clock: Callable[[], datetime] = lambda: datetime.now(UTC)):
        self.data_dir = data_dir
        self.projects_dir = data_dir / "projects"
        self.clock = clock

    def create(self, name: str | None = None) -> Project:
        if name is None:
            name = self._next_default_name()
        project = Project(id=secrets.token_hex(4), name=name, created_at=self.clock().isoformat())
        (self._dir(project.id) / "frames").mkdir(parents=True)
        self._save(project)
        return project

    def list(self) -> list[Project]:
        if not self.projects_dir.is_dir():
            return []
        projects = [
            self._load(d.name)
            for d in self.projects_dir.iterdir()
            if d.is_dir() and VALID_ID.fullmatch(d.name)
        ]
        return sorted(projects, key=lambda p: p.created_at, reverse=True)

    def get(self, project_id: str) -> Project:
        return self._load(project_id)

    def rename(self, project_id: str, name: str) -> Project:
        project = self.get(project_id)
        project.name = name
        self._save(project)
        return project

    def remove(self, project_id: str) -> None:
        """Delete the project and everything in its folder."""
        project_dir = self._dir(project_id)
        # Move it aside in one step first, so a power cut mid-delete can't leave half a project
        # in the list (list() skips folders whose names aren't ids)
        doomed = self.projects_dir / f".removing-{project_id}"
        os.replace(project_dir, doomed)
        shutil.rmtree(doomed)

    def add_frame(self, project_id: str, jpeg: bytes) -> Project:
        """Save `jpeg` as the project's next frame and record it."""
        project = self.get(project_id)
        # Number on from the last frame, not the count, which clashes if one goes from the middle
        number = int(Path(project.frames[-1]).stem) + 1 if project.frames else 1
        name = f"{number:05d}.jpg"
        thumb = _thumbnail(jpeg)
        # Photo first, then the list: a power cut in between only leaves an unlisted file
        _write_atomic(self._dir(project_id) / "frames" / name, jpeg)
        _write_atomic(self._dir(project_id) / "thumb.jpg", thumb)
        project.frames.append(name)
        self._save(project)
        # The deploy guard reads this file's mtime so it never restarts the app mid-shoot
        (self.data_dir / "last_capture").touch()
        return project

    def undo_last(self, project_id: str) -> Project:
        """Forget the project's last frame and delete its photo."""
        project = self.get(project_id)
        if not project.frames:
            return project
        name = project.frames.pop()
        # List first, then the photo: a power cut in between only leaves an unlisted file
        self._save(project)
        (self._dir(project_id) / "frames" / name).unlink(missing_ok=True)
        thumb = self._dir(project_id) / "thumb.jpg"
        if project.frames:
            latest = self._dir(project_id) / "frames" / project.frames[-1]
            _write_atomic(thumb, _thumbnail(latest.read_bytes()))
        else:
            thumb.unlink(missing_ok=True)
        return project

    def _next_default_name(self) -> str:
        # One more than the highest rather than count + 1, which can repeat a name after a removal
        numbers = [int(m[1]) for p in self.list() if (m := DEFAULT_NAME.fullmatch(p.name))]
        return f"Film {max(numbers, default=0) + 1}"

    def _dir(self, project_id: str) -> Path:
        if not VALID_ID.fullmatch(project_id):
            raise InvalidProjectIdError(f"Not a valid project id: {project_id!r}")
        return self.projects_dir / project_id

    def _load(self, project_id: str) -> Project:
        return Project(**json.loads((self._dir(project_id) / "project.json").read_text()))

    def _save(self, project: Project) -> None:
        text = json.dumps(asdict(project), indent=2) + "\n"
        _write_atomic(self._dir(project.id) / "project.json", text.encode())
