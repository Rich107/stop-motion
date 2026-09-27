from pathlib import Path

from backend.projects import ProjectStore


def test_when_a_project_is_created_it_appears_in_the_list_with_zero_frames(tmp_path: Path):
    store = ProjectStore(tmp_path)

    project = store.create("Dinosaurs")

    assert [(p.id, p.name, p.frames) for p in store.list()] == [(project.id, "Dinosaurs", [])]
