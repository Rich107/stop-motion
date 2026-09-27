"""Synthetic stop-motion frames for render tests: a textured scene seen by a wobbly camera."""

from pathlib import Path

import cv2
import numpy as np

WIDTH, HEIGHT = 640, 360
MARGIN = 60  # scene is bigger than a frame so the camera can shift without running off the edge


def textured_scene(seed: int) -> np.ndarray:
    """A background full of random shapes, which gives the feature detector plenty of corners."""
    rng = np.random.default_rng(seed)
    scene = np.full((HEIGHT + 2 * MARGIN, WIDTH + 2 * MARGIN, 3), 128, np.uint8)
    for _ in range(400):
        colour = tuple(int(c) for c in rng.integers(0, 256, 3))
        x = int(rng.integers(0, scene.shape[1]))
        y = int(rng.integers(0, scene.shape[0]))
        size = int(rng.integers(4, 30))
        if rng.random() < 0.5:
            cv2.rectangle(scene, (x, y), (x + size, y + size), colour, thickness=-1)
        else:
            cv2.circle(scene, (x, y), size // 2, colour, thickness=-1)
    return scene


def rebuilt_scene(before: np.ndarray, after: np.ndarray, fraction: float) -> np.ndarray:
    """`before` with its left `fraction` replaced by `after`, like a building going up in shot."""
    scene = before.copy()
    columns = round(scene.shape[1] * fraction)
    scene[:, :columns] = after[:, :columns]
    return scene


def camera_view(scene: np.ndarray, shift: tuple[float, float], frame_index: int = 0) -> np.ndarray:
    """What the camera sees when bumped by `shift` px, with a block (the subject) moving across."""
    dx, dy = shift
    # Camera moved by (dx, dy), so the scene appears moved by (-dx, -dy)
    view_to_scene = np.float32([[1, 0, MARGIN + dx], [0, 1, MARGIN + dy]])
    view = cv2.warpAffine(
        scene, view_to_scene, (WIDTH, HEIGHT), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP
    )
    x = 100 + 40 * frame_index
    cv2.rectangle(view, (x, 150), (x + 80, 230), (0, 0, 255), thickness=-1)
    return view


def write_frames(frames: list[np.ndarray], directory: Path) -> list[Path]:
    directory.mkdir(parents=True, exist_ok=True)
    paths = []
    for i, frame in enumerate(frames):
        path = directory / f"frame{i}.png"
        cv2.imwrite(str(path), frame)
        paths.append(path)
    return paths
