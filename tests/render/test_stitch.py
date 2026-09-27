from pathlib import Path

import pytest

from backend.render.stitch import NoImagesError, build_command, list_images


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


def test_when_building_the_ffmpeg_command_fps_size_hold_last_and_output_are_included(tmp_path: Path):
    output = tmp_path / "film.mp4"

    cmd = build_command(tmp_path / "frames.txt", output, fps=10, width=640, height=360, hold_last=1.5)

    vf = cmd[cmd.index("-vf") + 1]
    assert cmd[0] == "ffmpeg"
    assert cmd[cmd.index("-i") + 1] == str(tmp_path / "frames.txt")
    assert "fps=10" in vf
    assert "scale=640:360" in vf
    assert "pad=640:360" in vf
    assert "stop_duration=1.5" in vf
    assert cmd[-1] == str(output)
