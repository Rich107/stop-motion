from pathlib import Path

import pytest

from backend.render.stitch import NoImagesError, list_images


def test_when_images_are_named_img2_and_img10_they_sort_naturally(tmp_path: Path):
    for name in ["img10.jpg", "img2.jpg", "IMG1.jpg"]:
        (tmp_path / name).write_bytes(b"")

    images = list_images(tmp_path)

    assert [p.name for p in images] == ["IMG1.jpg", "img2.jpg", "img10.jpg"]


def test_when_directory_has_non_image_files_they_are_ignored(tmp_path: Path):
    for name in ["a.jpg", "b.PNG", "notes.txt", ".DS_Store"]:
        (tmp_path / name).write_bytes(b"")
    (tmp_path / "sub.jpg").mkdir()

    images = list_images(tmp_path)

    assert [p.name for p in images] == ["a.jpg", "b.PNG"]


def test_when_no_images_are_found_a_clear_error_is_raised(tmp_path: Path):
    (tmp_path / "notes.txt").write_text("hello")

    with pytest.raises(NoImagesError, match="No images found in"):
        list_images(tmp_path)
