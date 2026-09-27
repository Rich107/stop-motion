import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import cv2
import numpy as np

from backend.projects import ProjectStore


def test_when_a_project_is_created_it_appears_in_the_list_with_zero_frames(tmp_path: Path):
    store = ProjectStore(tmp_path)

    project = store.create("Dinosaurs")

    assert [(p.id, p.name, p.frames) for p in store.list()] == [(project.id, "Dinosaurs", [])]


def test_when_projects_are_listed_the_newest_is_first(tmp_path: Path):
    store = ProjectStore(tmp_path, clock=ticking_clock())
    for name in ["First", "Second", "Third"]:
        store.create(name)

    projects = store.list()

    assert [p.name for p in projects] == ["Third", "Second", "First"]


def test_when_no_name_is_given_it_is_named_one_after_the_highest_film_number(tmp_path: Path):
    store = ProjectStore(tmp_path)
    for name in ["Film 1", "Dinosaurs", "Film 5"]:
        store.create(name)

    project = store.create()

    assert project.name == "Film 6"


def test_when_frames_are_added_they_are_saved_with_the_next_number_and_listed_in_project_json(
    tmp_path: Path,
):
    store = ProjectStore(tmp_path)
    project = store.create()
    photos = [jpeg(brightness=50), jpeg(brightness=200)]

    for photo in photos:
        store.add_frame(project.id, photo)

    project_dir = tmp_path / "projects" / project.id
    saved = json.loads((project_dir / "project.json").read_text())
    assert saved["frames"] == ["00001.jpg", "00002.jpg"]
    assert [(project_dir / "frames" / name).read_bytes() for name in saved["frames"]] == photos


def ticking_clock():
    """A clock that moves on a minute every time it is read, so creation order is certain."""
    times = (datetime(2026, 9, 27, 9, 0, tzinfo=UTC) + timedelta(minutes=i) for i in range(1000))
    return lambda: next(times)


def jpeg(width: int = 640, height: int = 360, brightness: int = 128) -> bytes:
    """A real JPEG, like the camera sends."""
    ok, data = cv2.imencode(".jpg", np.full((height, width, 3), brightness, np.uint8))
    assert ok
    return data.tobytes()
