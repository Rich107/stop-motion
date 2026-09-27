#!/usr/bin/env python3
"""Stabilise a folder of stop-motion photos with OpenCV, then stitch them into a video with ffmpeg.

Every photo is aligned to a reference frame (the first, by default) by matching
background features, which undoes bumps to the camera or tripod. The animated
subject moves on purpose; RANSAC treats it as outliers, and --exclude masks it
out completely if it covers a large part of the shot.

Usage:
    python stopmotion_stabilised.py ./frames
    python stopmotion_stabilised.py ./frames -o movie.mp4 --fps 12
    python stopmotion_stabilised.py ./frames --exclude 800,400,1200,900 --keep-frames ./aligned
    python stopmotion_stabilised.py ./frames --model homography   # camera was also tilted

Requires: pip install opencv-python, and ffmpeg on PATH (brew install ffmpeg).
"""

import argparse
import math
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    import cv2
    import numpy as np
except ImportError:
    sys.exit("OpenCV not found. Install with: pip install opencv-python")

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}
MIN_INLIERS = 20
RATIO_TEST = 0.75


def natural_key(path: Path):
    # Sort "img2" before "img10"
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", path.name)]


def parse_rect(text):
    try:
        x, y, w, h = (int(v) for v in text.split(","))
    except ValueError:
        raise argparse.ArgumentTypeError("expected X,Y,W,H in pixels, e.g. 800,400,1200,900")
    return x, y, w, h


def load(path, size):
    img = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if img is None:
        sys.exit(f"Could not read {path}")
    if (img.shape[1], img.shape[0]) != size:
        img = cv2.resize(img, size, interpolation=cv2.INTER_AREA)
    return img


def make_detector(kind):
    if kind == "sift":
        return cv2.SIFT_create(nfeatures=4000), cv2.NORM_L2
    return cv2.ORB_create(nfeatures=5000), cv2.NORM_HAMMING


def detect(detector, img, scale, mask):
    small = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    return detector.detectAndCompute(gray, mask)


def estimate(ref_feats, feats, matcher, model):
    """Return a 3x3 matrix mapping this frame onto the reference (detection scale), plus inlier count."""
    kp_ref, des_ref = ref_feats
    kp, des = feats
    if des is None or des_ref is None or len(kp) < MIN_INLIERS:
        return None, 0

    pairs = matcher.knnMatch(des, des_ref, k=2)
    good = [p[0] for p in pairs if len(p) == 2 and p[0].distance < RATIO_TEST * p[1].distance]
    if len(good) < MIN_INLIERS:
        return None, len(good)

    src = np.float32([kp[m.queryIdx].pt for m in good])
    dst = np.float32([kp_ref[m.trainIdx].pt for m in good])
    if model == "homography":
        M, inliers = cv2.findHomography(src, dst, cv2.RANSAC, 3.0)
    else:
        # Similarity: shift + rotation + uniform zoom, no skew
        M, inliers = cv2.estimateAffinePartial2D(src, dst, method=cv2.RANSAC, ransacReprojThreshold=3.0)
        if M is not None:
            M = np.vstack([M, [0, 0, 1]])

    count = int(inliers.sum()) if inliers is not None else 0
    if M is None or count < MIN_INLIERS:
        return None, count
    return M, count


def common_crop(transforms, w, h):
    """Largest centred rectangle (same aspect ratio) that every aligned frame fully covers."""
    s = 400 / max(w, h)
    sw, sh = round(w * s), round(h * s)
    S = np.diag([s, s, 1.0])
    S_inv = np.linalg.inv(S)

    ones = np.full((sh, sw), 255, np.uint8)
    valid = ones.copy()
    for M in transforms:
        valid &= cv2.warpPerspective(ones, S @ M @ S_inv, (sw, sh), flags=cv2.INTER_NEAREST, borderValue=0)

    lo, hi = 0.0, 1.0
    for _ in range(20):
        mid = (lo + hi) / 2
        cw, ch = int(sw * mid), int(sh * mid)
        x0, y0 = (sw - cw) // 2, (sh - ch) // 2
        region = valid[y0:y0 + ch, x0:x0 + cw]
        if region.size and region.min() == 255:
            lo = mid
        else:
            hi = mid

    frac = lo * 0.99  # small safety margin for rounding at the edges
    cw, ch = int(w * frac) & ~1, int(h * frac) & ~1
    return (w - cw) // 2, (h - ch) // 2, cw, ch, frac


def describe(M):
    angle = math.degrees(math.atan2(M[1, 0], M[0, 0]))
    zoom = math.hypot(M[0, 0], M[1, 0])
    return f"shift ({M[0, 2]:+7.1f}, {M[1, 2]:+7.1f}) px  rot {angle:+5.2f}°  zoom {zoom:.3f}"


def main():
    p = argparse.ArgumentParser(description="Stabilise stop-motion photos, then turn them into a video.")
    p.add_argument("input_dir", type=Path, help="Folder containing images")
    p.add_argument("-o", "--output", type=Path, default=Path("stopmotion_stabilised.mp4"))
    p.add_argument("--fps", type=float, default=12, help="Frames per second (stop motion: 8-15)")
    p.add_argument("--width", type=int, default=1920)
    p.add_argument("--height", type=int, default=1080)
    p.add_argument("--hold-last", type=float, default=1.0, help="Seconds to hold final frame")
    p.add_argument("--ref", type=int, default=0, help="Index of the frame everything aligns to")
    p.add_argument("--model", choices=["similarity", "homography"], default="similarity",
                   help="similarity = shift/rotate/zoom; homography = also corrects tilt")
    p.add_argument("--features", choices=["sift", "orb"], default="sift", help="sift is more robust, orb faster")
    p.add_argument("--exclude", type=parse_rect, action="append", default=[], metavar="X,Y,W,H",
                   help="Ignore this area (e.g. your subject) when matching. Repeatable. Photo pixel coords")
    p.add_argument("--detect-size", type=int, default=1600, help="Longest side used for feature detection")
    p.add_argument("--no-crop", action="store_true",
                   help="Don't zoom in to hide edges; stretch edge pixels instead")
    p.add_argument("--keep-frames", type=Path, help="Also save the aligned frames to this folder")
    p.add_argument("--no-video", action="store_true", help="Only align frames (use with --keep-frames)")
    args = p.parse_args()

    if not args.no_video and not shutil.which("ffmpeg"):
        sys.exit("ffmpeg not found. Install with: brew install ffmpeg")

    images = sorted(
        (f for f in args.input_dir.iterdir() if f.suffix.lower() in IMAGE_EXTS),
        key=natural_key,
    )
    if not images:
        sys.exit(f"No images found in {args.input_dir}")
    if not 0 <= args.ref < len(images):
        sys.exit(f"--ref must be between 0 and {len(images) - 1}")

    first = cv2.imread(str(images[args.ref]), cv2.IMREAD_COLOR)
    if first is None:
        sys.exit(f"Could not read {images[args.ref]}")
    h, w = first.shape[:2]
    size = (w, h)
    scale = min(1.0, args.detect_size / max(w, h))
    S = np.diag([scale, scale, 1.0])
    S_inv = np.linalg.inv(S)

    mask = np.full((round(h * scale), round(w * scale)), 255, np.uint8)
    for x, y, rw, rh in args.exclude:
        cv2.rectangle(mask, (int(x * scale), int(y * scale)),
                      (int((x + rw) * scale), int((y + rh) * scale)), 0, thickness=-1)

    detector, norm = make_detector(args.features)
    matcher = cv2.BFMatcher(norm)
    ref_feats = detect(detector, first, scale, mask)
    if ref_feats[1] is None or len(ref_feats[0]) < MIN_INLIERS:
        sys.exit("Too few features in the reference frame. Try --features orb, a different --ref, "
                 "or a smaller --exclude area")

    # Pass 1: work out how far each photo has moved from the reference
    print(f"Aligning {len(images)} frames to {images[args.ref].name}")
    transforms, failed = [], []
    prev = np.eye(3)
    for i, path in enumerate(images):
        if i == args.ref:
            M, note = np.eye(3), "reference"
        else:
            M_small, inliers = estimate(ref_feats, detect(detector, load(path, size), scale, mask), matcher, args.model)
            if M_small is None:
                # Camera most likely stayed wherever it was for the previous frame
                M, note = prev, f"FAILED ({inliers} matches), reusing previous alignment"
                failed.append(path.name)
            else:
                M, note = S_inv @ M_small @ S, f"{inliers} inliers"
        transforms.append(M)
        prev = M
        print(f"  [{i + 1:>4}/{len(images)}] {path.name:<30} {describe(M)}  {note}")

    if args.no_crop:
        crop = None
    else:
        *crop, frac = common_crop(transforms, w, h)
        print(f"Cropping to {crop[2]}x{crop[3]} ({frac:.0%} of the original) to hide shifted edges")
        if frac < 0.8:
            print("  Warning: large crop. One or more frames moved a lot; check the list above, "
                  "or use --no-crop")

    # Pass 2: warp each photo into place and write it out
    with tempfile.TemporaryDirectory() as tmp:
        out_dir = args.keep_frames or Path(tmp)
        out_dir.mkdir(parents=True, exist_ok=True)
        for i, (path, M) in enumerate(zip(images, transforms)):
            img = load(path, size)
            if args.model == "homography":
                aligned = cv2.warpPerspective(img, M, size, flags=cv2.INTER_LANCZOS4,
                                              borderMode=cv2.BORDER_REPLICATE)
            else:
                aligned = cv2.warpAffine(img, M[:2], size, flags=cv2.INTER_LANCZOS4,
                                         borderMode=cv2.BORDER_REPLICATE)
            if crop:
                x, y, cw, ch = crop
                aligned = aligned[y:y + ch, x:x + cw]
            cv2.imwrite(str(out_dir / f"frame_{i:05d}.jpg"), aligned, [cv2.IMWRITE_JPEG_QUALITY, 95])

        if args.keep_frames:
            print(f"Aligned frames saved to {out_dir}")

        if not args.no_video:
            # Fit every frame into WxH, letterbox if aspect differs, then hold the last frame
            vf = (
                f"scale={args.width}:{args.height}:force_original_aspect_ratio=decrease,"
                f"pad={args.width}:{args.height}:(ow-iw)/2:(oh-ih)/2,setsar=1,"
                f"tpad=stop_mode=clone:stop_duration={args.hold_last},format=yuv420p"
            )
            cmd = [
                "ffmpeg", "-y", "-loglevel", "error", "-stats",
                "-framerate", str(args.fps), "-i", str(out_dir / "frame_%05d.jpg"),
                "-vf", vf,
                "-c:v", "libx264", "-crf", "18", "-preset", "medium",
                "-movflags", "+faststart",
                str(args.output),
            ]
            print(f"Stitching {len(images)} frames at {args.fps} fps -> {args.output}")
            subprocess.run(cmd, check=True)

    if failed:
        print(f"\n{len(failed)} frame(s) couldn't be aligned: {', '.join(failed)}")
        print("Try --features orb, --exclude over your subject, or --ref to a closer frame.")


if __name__ == "__main__":
    main()
