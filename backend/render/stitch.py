"""Stitch a list of images into a stop-motion video using ffmpeg."""

import re
import subprocess
import tempfile
from collections.abc import Sequence
from pathlib import Path

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}


class NoImagesError(ValueError):
    """The folder has no photos in it."""


class StitchError(RuntimeError):
    """ffmpeg failed; the message ends with what it printed."""


def natural_key(path: Path) -> list[int | str]:
    # Sort "img2" before "img10"
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", path.name)]


def list_images(directory: Path) -> list[Path]:
    """Images in `directory`, in natural name order."""
    images = (f for f in directory.iterdir() if f.is_file() and f.suffix.lower() in IMAGE_EXTS)
    images = sorted(images, key=natural_key)
    if not images:
        raise NoImagesError(f"No images found in {directory}")
    return images


def concat_list(frames: Sequence[Path]) -> str:
    """Contents of an ffmpeg concat-demuxer list file naming each frame."""
    lines = []
    for frame in frames:
        # Inside single quotes, a quote is written as '\''
        quoted = frame.resolve().as_posix().replace("'", "'\\''")
        lines.append(f"file '{quoted}'\n")
    return "".join(lines)


def build_command(
    list_file: Path, output: Path, fps: float, width: int, height: int, hold_last: float
) -> list[str]:
    """ffmpeg arguments that turn a concat list of photos into an H.264 MP4."""
    # Each photo becomes one frame at `fps`; fit it into WxH (letterbox if the aspect differs),
    # then hold the last frame for `hold_last` seconds
    vf = (
        f"setpts=N/({fps}*TB),fps={fps},"
        f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1,"
        f"tpad=stop_mode=clone:stop_duration={hold_last},format=yuv420p"
    )
    return [
        "ffmpeg",
        "-y",
        "-nostdin",
        "-loglevel",
        "error",
        "-nostats",
        "-progress",
        "pipe:1",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(list_file),
        "-vf",
        vf,
        "-c:v",
        "libx264",
        "-crf",
        "18",
        "-preset",
        "medium",
        "-movflags",
        "+faststart",
        str(output),
    ]


def stitch(
    frames: Sequence[Path],
    output: Path,
    fps: float,
    width: int,
    height: int,
    hold_last: float,
) -> None:
    """Turn `frames` into an MP4 at `output`, one frame per photo, holding the last one."""
    if not frames:
        raise NoImagesError("No frames to stitch")
    with tempfile.TemporaryDirectory() as tmp:
        list_file = Path(tmp) / "frames.txt"
        list_file.write_text(concat_list(frames))
        cmd = build_command(list_file, output, fps, width, height, hold_last)
        with (
            tempfile.TemporaryFile("w+") as errors,
            subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=errors, text=True) as proc,
        ):
            proc.stdout.read()
            if proc.wait() != 0:
                errors.seek(0)
                raise StitchError(f"ffmpeg failed making {output}:\n{errors.read()[-2000:]}")
