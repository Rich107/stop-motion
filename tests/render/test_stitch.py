import time
from pathlib import Path

import numpy as np
import pytest

from backend.render.stitch import NoImagesError, build_command, concat_list, list_images, stitch
from tests.render.scenes import write_frames
from tests.render.video import needs_ffmpeg, probe


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


def test_when_building_the_ffmpeg_command_fps_size_hold_last_and_output_are_included(
    tmp_path: Path,
):
    output = tmp_path / "film.mp4"

    cmd = build_command(
        tmp_path / "frames.txt", output, fps=10, width=640, height=360, hold_last=1.5
    )

    vf = cmd[cmd.index("-vf") + 1]
    assert cmd[0] == "ffmpeg"
    assert cmd[cmd.index("-i") + 1] == str(tmp_path / "frames.txt")
    assert "fps=10" in vf
    assert "scale=640:360" in vf
    assert "pad=640:360" in vf
    assert "stop_duration=1.5" in vf
    assert cmd[-1] == str(output)


def test_when_a_frame_path_has_a_quote_the_concat_list_escapes_it(tmp_path: Path):
    frames = [tmp_path / "a.jpg", tmp_path / "Sam's film" / "b.jpg"]

    text = concat_list(frames)

    assert text.splitlines() == [
        f"file '{tmp_path}/a.jpg'",
        f"file '{tmp_path}/Sam'\\''s film/b.jpg'",
    ]


@needs_ffmpeg
def test_when_frames_are_stitched_the_h264_mp4_has_every_frame_then_the_held_last_one(
    tmp_path: Path,
):
    frames = write_frames(
        [np.full((180, 320, 3), 40 * i, np.uint8) for i in range(5)], tmp_path / "Sam's film"
    )
    output = tmp_path / "film.mp4"

    stitch(frames, output, fps=10, width=320, height=180, hold_last=0.5)

    info = probe(output)
    assert info["codec_name"] == "h264"
    assert (info["width"], info["height"]) == (320, 180)
    assert info["r_frame_rate"] == "10/1"
    assert int(info["nb_read_frames"]) == 5 + 5  # every photo, then half a second of the last


@needs_ffmpeg
def test_when_progress_is_given_stitching_reports_up_to_the_total_frame_count(tmp_path: Path):
    frames = write_frames([np.full((180, 320, 3), 40 * i, np.uint8) for i in range(5)], tmp_path)
    calls = []

    stitch(
        frames,
        tmp_path / "film.mp4",
        fps=10,
        width=320,
        height=180,
        hold_last=0.5,
        progress=lambda done, total, stage: calls.append((done, total, stage)),
    )

    assert calls[-1] == (10, 10, "stitch")
    assert all(total == 10 and stage == "stitch" for _, total, stage in calls)


class Cancelled(Exception):
    pass


@needs_ffmpeg
def test_when_progress_raises_ffmpeg_is_stopped_and_no_film_is_left(tmp_path: Path):
    noise = np.random.default_rng(0).integers(0, 256, (720, 1280, 3), np.uint8)
    frames = write_frames([noise] * 3, tmp_path)
    output = tmp_path / "film.mp4"

    def cancel(done: int, total: int, stage: str) -> None:
        raise Cancelled

    started = time.monotonic()
    with pytest.raises(Cancelled):
        # Ten minutes of held noise: far longer to encode than the time allowed below
        stitch(frames, output, fps=30, width=1280, height=720, hold_last=600, progress=cancel)
    elapsed = time.monotonic() - started

    assert elapsed < 10
    assert not output.exists()
