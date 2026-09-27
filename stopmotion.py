#!/usr/bin/env python3
"""Stitch a directory of images into a stop-motion video using ffmpeg.

Usage:
    python stopmotion.py ./frames
    python stopmotion.py ./frames -o movie.mp4 --fps 12 --width 1920 --height 1080
"""

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}


def natural_key(path: Path):
    # Sort "img2" before "img10"
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", path.name)]


def main():
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

    images = sorted(
        (f for f in args.input_dir.iterdir() if f.suffix.lower() in IMAGE_EXTS),
        key=natural_key,
    )
    if not images:
        sys.exit(f"No images found in {args.input_dir}")

    frame_dur = 1 / args.fps
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        for img in images:
            f.write(f"file '{img.resolve().as_posix()}'\nduration {frame_dur}\n")
        # Concat demuxer ignores the last duration unless the file is repeated
        f.write(f"file '{images[-1].resolve().as_posix()}'\nduration {args.hold_last}\n")
        f.write(f"file '{images[-1].resolve().as_posix()}'\n")
        list_file = f.name

    # Fit every frame into WxH, letterbox if aspect differs
    vf = (
        f"scale={args.width}:{args.height}:force_original_aspect_ratio=decrease,"
        f"pad={args.width}:{args.height}:(ow-iw)/2:(oh-ih)/2,setsar=1,format=yuv420p"
    )
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", list_file,
        "-vf", vf,
        "-r", str(args.fps),
        "-c:v", "libx264", "-crf", "18", "-preset", "medium",
        "-movflags", "+faststart",
        str(args.output),
    ]
    print(f"Stitching {len(images)} frames at {args.fps} fps -> {args.output}")
    try:
        subprocess.run(cmd, check=True)
    finally:
        Path(list_file).unlink(missing_ok=True)


if __name__ == "__main__":
    main()
