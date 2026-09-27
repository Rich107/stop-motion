"""Stitch a list of images into a stop-motion video using ffmpeg."""

import re
from pathlib import Path

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}


def natural_key(path: Path) -> list[int | str]:
    # Sort "img2" before "img10"
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", path.name)]


def list_images(directory: Path) -> list[Path]:
    """Images in `directory`, in natural name order."""
    return sorted(directory.iterdir(), key=natural_key)
