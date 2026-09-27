"""Stitch a list of images into a stop-motion video using ffmpeg."""

import re
from pathlib import Path

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}


class NoImagesError(ValueError):
    """The folder has no photos in it."""


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
