import json
import os
import time
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


def test_when_a_frame_is_added_the_thumbnail_is_a_480_wide_copy_of_it(tmp_path: Path):
    store = ProjectStore(tmp_path)
    project = store.create()
    store.add_frame(project.id, jpeg(1280, 720, brightness=50))

    store.add_frame(project.id, jpeg(1280, 720, brightness=200))

    thumb = cv2.imread(str(tmp_path / "projects" / project.id / "thumb.jpg"))
    assert thumb.shape == (270, 480, 3)
    assert abs(thumb.mean() - 200) < 2


def test_when_a_frame_is_added_last_capture_is_touched(tmp_path: Path):
    store = ProjectStore(tmp_path)
    project = store.create()
    last_capture = tmp_path / "last_capture"
    last_capture.touch()
    an_hour_ago = time.time() - 3600
    os.utime(last_capture, (an_hour_ago, an_hour_ago))

    store.add_frame(project.id, jpeg())

    assert last_capture.stat().st_mtime > time.time() - 60


def test_when_the_last_frame_is_undone_it_is_removed_from_disk_and_the_list(tmp_path: Path):
    store = ProjectStore(tmp_path)
    project = store.create()
    for _ in range(3):
        store.add_frame(project.id, jpeg())

    store.undo_last(project.id)

    frames_dir = tmp_path / "projects" / project.id / "frames"
    assert store.get(project.id).frames == ["00001.jpg", "00002.jpg"]
    assert sorted(p.name for p in frames_dir.iterdir()) == ["00001.jpg", "00002.jpg"]


def test_when_the_last_frame_is_undone_the_thumbnail_shows_the_frame_before_it(tmp_path: Path):
    store = ProjectStore(tmp_path)
    project = store.create()
    for brightness in [50, 200]:
        store.add_frame(project.id, jpeg(brightness=brightness))

    store.undo_last(project.id)

    thumb = cv2.imread(str(tmp_path / "projects" / project.id / "thumb.jpg"))
    assert abs(thumb.mean() - 50) < 2


def test_when_undo_is_called_on_an_empty_project_it_leaves_it_empty_without_error(
    tmp_path: Path,
):
    store = ProjectStore(tmp_path)
    project = store.create()

    store.undo_last(project.id)

    assert store.get(project.id).frames == []


def test_when_the_only_frame_is_undone_the_thumbnail_is_removed(tmp_path: Path):
    store = ProjectStore(tmp_path)
    project = store.create()
    store.add_frame(project.id, jpeg())

    store.undo_last(project.id)

    assert not (tmp_path / "projects" / project.id / "thumb.jpg").exists()


def test_when_a_project_is_renamed_a_new_store_sees_the_new_name(tmp_path: Path):
    project = ProjectStore(tmp_path).create("Film 1")

    ProjectStore(tmp_path).rename(project.id, "Space rocket")

    assert ProjectStore(tmp_path).get(project.id).name == "Space rocket"


def test_when_a_project_is_removed_a_new_store_no_longer_lists_it_or_its_files(tmp_path: Path):
    store = ProjectStore(tmp_path)
    kept, removed = store.create("Kept"), store.create("Removed")
    store.add_frame(removed.id, jpeg())

    store.remove(removed.id)

    assert [p.id for p in ProjectStore(tmp_path).list()] == [kept.id]
    assert not (tmp_path / "projects" / removed.id).exists()


def ticking_clock():
    """A clock that moves on a minute every time it is read, so creation order is certain."""
    times = (datetime(2026, 9, 27, 9, 0, tzinfo=UTC) + timedelta(minutes=i) for i in range(1000))
    return lambda: next(times)


def jpeg(width: int = 640, height: int = 360, brightness: int = 128) -> bytes:
    """A real JPEG, like the camera sends."""
    ok, data = cv2.imencode(".jpg", np.full((height, width, 3), brightness, np.uint8))
    assert ok
    return data.tobytes()
