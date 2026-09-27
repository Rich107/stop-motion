"""Stitch a list of images into a stop-motion video using ffmpeg."""

import re
from pathlib import Path

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}


def natural_key(path: Path) -> list[int | str]:
    # Sort "img2" before "img10"
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", path.name)]


def list_images(directory: Path) -> list[Path]:
    """Images in `directory`, in natural name order."""
    images = (f for f in directory.iterdir() if f.is_file() and f.suffix.lower() in IMAGE_EXTS)
    return sorted(images, key=natural_key)
