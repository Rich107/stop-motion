#!/usr/bin/env python3
"""Stabilise a folder of stop-motion photos with OpenCV, then stitch them into a video with ffmpeg.

Every photo is aligned to a reference frame (the first, by default) by matching
background features, which undoes bumps to the camera or tripod. The animated
subject moves on purpose; RANSAC treats it as outliers, and --exclude masks it
out completely if it covers a large part of the shot.

By default each photo is matched against the one before it and the moves are
added up (--mode chain), which copes with a scene that changes a lot over the
shoot. --mode reference matches every photo straight against the reference.

Usage:
    python stopmotion_stabilised.py ./frames
    python stopmotion_stabilised.py ./frames -o movie.mp4 --fps 12
    python stopmotion_stabilised.py ./frames --exclude 800,400,1200,900 --keep-frames ./aligned
    python stopmotion_stabilised.py ./frames --model homography   # camera was also tilted
    python stopmotion_stabilised.py ./frames --mode reference     # align everything to --ref

Requires: pip install opencv-python, and ffmpeg on PATH (brew install ffmpeg).
"""

import argparse
import math
import shutil
import sys
import tempfile
from pathlib import Path

try:
    import cv2  # noqa: F401  (imported early for a friendlier error)
except ImportError:
    sys.exit("OpenCV not found. Install with: pip install opencv-python")

import numpy as np

from backend.render.stabilise import AlignmentError, common_crop, compute_transforms, write_aligned
from backend.render.stitch import NoImagesError, StitchError, list_images, stitch


def parse_rect(text: str) -> tuple[int, int, int, int]:
    try:
        x, y, w, h = (int(v) for v in text.split(","))
    except ValueError:
        raise argparse.ArgumentTypeError(
            "expected X,Y,W,H in pixels, e.g. 800,400,1200,900"
        ) from None
    return x, y, w, h


def describe(M: np.ndarray) -> str:
    angle = math.degrees(math.atan2(M[1, 0], M[0, 0]))
    zoom = math.hypot(M[0, 0], M[1, 0])
    return f"shift ({M[0, 2]:+7.1f}, {M[1, 2]:+7.1f}) px  rot {angle:+5.2f}°  zoom {zoom:.3f}"


def show_progress(done: int, total: int, stage: str) -> None:
    end = "\n" if done == total else ""
    print(f"\r  {stage} {done}/{total}", end=end, flush=True)


def main() -> None:
    p = argparse.ArgumentParser(
        description="Stabilise stop-motion photos, then turn them into a video."
    )
    p.add_argument("input_dir", type=Path, help="Folder containing images")
    p.add_argument("-o", "--output", type=Path, default=Path("stopmotion_stabilised.mp4"))
    p.add_argument("--fps", type=float, default=12, help="Frames per second (stop motion: 8-15)")
    p.add_argument("--width", type=int, default=1920)
    p.add_argument("--height", type=int, default=1080)
    p.add_argument("--hold-last", type=float, default=1.0, help="Seconds to hold final frame")
    p.add_argument("--ref", type=int, default=0, help="Index of the frame everything aligns to")
    p.add_argument(
        "--mode",
        choices=["chain", "reference"],
        default="chain",
        help="chain = match each photo to its neighbour (copes with a changing scene); "
        "reference = match every photo to --ref",
    )
    p.add_argument(
        "--model",
        choices=["similarity", "homography"],
        default="similarity",
        help="similarity = shift/rotate/zoom; homography = also corrects tilt",
    )
    p.add_argument(
        "--features",
        choices=["sift", "orb"],
        default="sift",
        help="sift is more robust, orb faster",
    )
    p.add_argument(
        "--exclude",
        type=parse_rect,
        action="append",
        default=[],
        metavar="X,Y,W,H",
        help="Ignore this area (e.g. your subject) when matching. Repeatable. Photo pixel coords",
    )
    p.add_argument(
        "--detect-size", type=int, default=1600, help="Longest side used for feature detection"
    )
    p.add_argument(
        "--no-crop",
        action="store_true",
        help="Don't zoom in to hide edges; stretch edge pixels instead",
    )
    p.add_argument("--keep-frames", type=Path, help="Also save the aligned frames to this folder")
    p.add_argument(
        "--no-video", action="store_true", help="Only align frames (use with --keep-frames)"
    )
    args = p.parse_args()

    if not args.no_video and not shutil.which("ffmpeg"):
        sys.exit("ffmpeg not found. Install with: brew install ffmpeg")

    try:
        images = list_images(args.input_dir)
        if not 0 <= args.ref < len(images):
            sys.exit(f"--ref must be between 0 and {len(images) - 1}")

        # Pass 1: work out how far each photo has moved from the reference
        how = " (each matched to its neighbour)" if args.mode == "chain" else ""
        print(f"Aligning {len(images)} frames to {images[args.ref].name}{how}")
        alignment = compute_transforms(
            images,
            mode=args.mode,
            model=args.model,
            features=args.features,
            exclude=args.exclude,
            ref_index=args.ref,
            detect_size=args.detect_size,
            progress=show_progress,
        )
        for i, (path, M) in enumerate(zip(images, alignment.transforms, strict=True)):
            if i == args.ref:
                note = "reference"
            elif i in alignment.failed:
                note = f"FAILED ({alignment.inliers[i]} matches), reusing previous alignment"
            else:
                note = f"{alignment.inliers[i]} inliers"
            print(f"  [{i + 1:>4}/{len(images)}] {path.name:<30} {describe(M)}  {note}")

        if args.no_crop:
            crop = None
        else:
            crop = common_crop(alignment.transforms, alignment.size)
            print(
                f"Cropping to {crop.width}x{crop.height} ({crop.fraction:.0%} of the original) "
                "to hide shifted edges"
            )
            if crop.fraction < 0.8:
                print(
                    "  Warning: large crop. One or more frames moved a lot; check the list above, "
                    "or use --no-crop"
                )

        # Pass 2: warp each photo into place and write it out
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = args.keep_frames or Path(tmp)
            frames = write_aligned(
                images, alignment.transforms, crop, out_dir, alignment.size, show_progress
            )
            if args.keep_frames:
                print(f"Aligned frames saved to {out_dir}")

            if not args.no_video:
                print(f"Stitching {len(frames)} frames at {args.fps} fps -> {args.output}")
                stitch(
                    frames,
                    args.output,
                    args.fps,
                    args.width,
                    args.height,
                    args.hold_last,
                    show_progress,
                )
    except (NoImagesError, AlignmentError, StitchError, OSError) as e:
        sys.exit(str(e))

    if alignment.failed:
        names = ", ".join(images[i].name for i in alignment.failed)
        print(f"\n{len(alignment.failed)} frame(s) couldn't be aligned: {names}")
        tips = "Try --features orb, --exclude over your subject"
        if args.mode == "reference":
            tips += ", --ref to a closer frame, or --mode chain."
        else:
            tips += ", or --mode reference if the scene hardly changed."
        print(tips)


if __name__ == "__main__":
    main()
