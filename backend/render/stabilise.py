"""Stabilise stop-motion photos with OpenCV by matching background features.

Each photo gets a 3x3 matrix that maps it onto the reference frame, which undoes bumps to the
camera or tripod. The animated subject moves on purpose; RANSAC treats it as outliers, and
`exclude` masks it out completely if it covers a large part of the shot.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import cv2
import numpy as np

MIN_INLIERS = 20
RATIO_TEST = 0.75

Mode = Literal["reference", "chain"]
Model = Literal["similarity", "homography"]
Features = Literal["sift", "orb"]
Rect = tuple[int, int, int, int]


class AlignmentError(ValueError):
    """The photos can't be aligned at all (unreadable, or no features in the reference)."""


@dataclass
class Alignment:
    """Per-frame matrices mapping each photo onto the reference frame."""

    transforms: list[np.ndarray]
    size: tuple[int, int]
    failed: list[int] = field(default_factory=list)
    inliers: list[int | None] = field(default_factory=list)


def load(path: Path, size: tuple[int, int] | None = None) -> np.ndarray:
    img = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if img is None:
        raise AlignmentError(f"Could not read {path}")
    if size is not None and (img.shape[1], img.shape[0]) != size:
        img = cv2.resize(img, size, interpolation=cv2.INTER_AREA)
    return img


def _make_detector(kind: Features):
    if kind == "sift":
        return cv2.SIFT_create(nfeatures=4000), cv2.NORM_L2
    return cv2.ORB_create(nfeatures=5000), cv2.NORM_HAMMING


class _Matcher:
    """Detects features at a reduced scale and estimates the matrix between two photos."""

    def __init__(
        self, size: tuple[int, int], model: Model, features: Features, exclude, detect_size: int
    ):
        w, h = size
        self.size = size
        self.model = model
        self.scale = min(1.0, detect_size / max(w, h))
        self.S = np.diag([self.scale, self.scale, 1.0])
        self.S_inv = np.linalg.inv(self.S)
        self.mask = np.full((round(h * self.scale), round(w * self.scale)), 255, np.uint8)
        for x, y, rw, rh in exclude:
            s = self.scale
            corner1, corner2 = (int(x * s), int(y * s)), (int((x + rw) * s), int((y + rh) * s))
            cv2.rectangle(self.mask, corner1, corner2, 0, thickness=-1)
        self.detector, norm = _make_detector(features)
        self.matcher = cv2.BFMatcher(norm)

    def detect(self, img: np.ndarray):
        small = cv2.resize(img, None, fx=self.scale, fy=self.scale, interpolation=cv2.INTER_AREA)
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        return self.detector.detectAndCompute(gray, self.mask)

    def estimate(self, feats, target_feats) -> tuple[np.ndarray | None, int]:
        """Full-resolution matrix mapping one photo's features onto another's, plus inliers."""
        kp, des = feats
        kp_t, des_t = target_feats
        if des is None or des_t is None or len(kp) < MIN_INLIERS or len(kp_t) < 2:
            return None, 0

        pairs = self.matcher.knnMatch(des, des_t, k=2)
        good = [p[0] for p in pairs if len(p) == 2 and p[0].distance < RATIO_TEST * p[1].distance]
        if len(good) < MIN_INLIERS:
            return None, len(good)

        src = np.float32([kp[m.queryIdx].pt for m in good])
        dst = np.float32([kp_t[m.trainIdx].pt for m in good])
        if self.model == "homography":
            M, inliers = cv2.findHomography(src, dst, cv2.RANSAC, 3.0)
        else:
            # Similarity: shift + rotation + uniform zoom, no skew
            M, inliers = cv2.estimateAffinePartial2D(
                src, dst, method=cv2.RANSAC, ransacReprojThreshold=3.0
            )
            if M is not None:
                M = np.vstack([M, [0, 0, 1]])

        count = int(inliers.sum()) if inliers is not None else 0
        if M is None or count < MIN_INLIERS:
            return None, count
        return self.S_inv @ M @ self.S, count


def compute_transforms(
    images: Sequence[Path],
    mode: Mode = "reference",
    model: Model = "similarity",
    features: Features = "sift",
    exclude: Sequence[Rect] = (),
    ref_index: int = 0,
    detect_size: int = 1600,
) -> Alignment:
    """Work out how far each photo has moved from the reference frame."""
    if not 0 <= ref_index < len(images):
        raise AlignmentError(f"ref_index must be between 0 and {len(images) - 1}")

    first = load(images[ref_index])
    size = (first.shape[1], first.shape[0])
    matcher = _Matcher(size, model, features, exclude, detect_size)
    ref_feats = matcher.detect(first)
    if ref_feats[1] is None or len(ref_feats[0]) < MIN_INLIERS:
        raise AlignmentError("Too few features in the reference frame")

    alignment = Alignment(transforms=[], size=size)
    prev = np.eye(3)
    for i, path in enumerate(images):
        if i == ref_index:
            M, inliers = np.eye(3), None
        else:
            M, inliers = matcher.estimate(matcher.detect(load(path, size)), ref_feats)
            if M is None:
                # Camera most likely stayed wherever it was for the previous frame
                M = prev
                alignment.failed.append(i)
        alignment.transforms.append(M)
        alignment.inliers.append(inliers)
        prev = M
    return alignment
