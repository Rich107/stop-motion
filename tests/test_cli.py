import subprocess
import sys
from pathlib import Path

from tests.render.scenes import camera_view, textured_scene, write_frames
from tests.render.video import needs_ffmpeg, probe

ROOT = Path(__file__).resolve().parent.parent


def run_script(name: str, *args: str | Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(ROOT / name), *map(str, args)],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )


def small_folder(directory: Path) -> Path:
    scene = textured_scene(seed=1)
    write_frames([camera_view(scene, (2 * i, -i), i) for i in range(4)], directory)
    return directory


@needs_ffmpeg
def test_when_stopmotion_runs_on_a_small_folder_it_produces_a_video(tmp_path: Path):
    frames = small_folder(tmp_path / "frames")
    output = tmp_path / "film.mp4"

    result = run_script(
        "stopmotion.py",
        frames,
        "-o",
        output,
        "--fps",
        "10",
        "--width",
        "320",
        "--height",
        "180",
        "--hold-last",
        "0.5",
    )

    assert result.returncode == 0, result.stderr
    info = probe(output)
    assert (info["width"], info["height"]) == (320, 180)
    assert int(info["nb_read_frames"]) == 4 + 5
