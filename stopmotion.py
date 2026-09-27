#!/usr/bin/env python3
"""Stitch a directory of images into a stop-motion video using ffmpeg.

Usage:
    python stopmotion.py ./frames
    python stopmotion.py ./frames -o movie.mp4 --fps 12 --width 1920 --height 1080
"""

import argparse
import shutil
import sys
from pathlib import Path

from backend.render.stitch import NoImagesError, StitchError, list_images, stitch


def main() -> None:
    p = argparse.ArgumentParser(description="Turn a folder of images into a stop-motion video.")
    p.add_argument("input_dir", type=Path, help="Folder containing images")
    p.add_argument("-o", "--output", type=Path, default=Path("stopmotion.mp4"))
    p.add_argument("--fps", type=float, default=12, help="Frames per second (stop motion: 8-15)")
    p.add_argument("--width", type=int, default=1920)
    p.add_argument("--height", type=int, default=1080)
    p.add_argument("--hold-last", type=float, default=1.0, help="Seconds to hold final frame")
    args = p.parse_args()

    if not shutil.which("ffmpeg"):
        sys.exit("ffmpeg not found. Install with: brew install ffmpeg")

    try:
        images = list_images(args.input_dir)
        print(f"Stitching {len(images)} frames at {args.fps} fps -> {args.output}")
        stitch(images, args.output, args.fps, args.width, args.height, args.hold_last)
    except (NoImagesError, StitchError) as e:
        sys.exit(str(e))


if __name__ == "__main__":
    main()
