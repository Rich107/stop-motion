from pathlib import Path

import cv2
import numpy as np

from backend.render.stabilise import common_crop, compute_transforms
from tests.render.scenes import (
    HEIGHT,
    WIDTH,
    camera_view,
    rebuilt_scene,
    textured_scene,
    write_frames,
)


def test_when_frames_are_shifted_by_a_known_amount_reference_mode_recovers_the_shift(
    tmp_path: Path,
):
    scene = textured_scene(seed=1)
    shifts = [(0, 0), (5, -3), (-7, 4), (12.5, 6)]
    images = write_frames([camera_view(scene, s, i) for i, s in enumerate(shifts)], tmp_path)

    alignment = compute_transforms(images, mode="reference")

    recovered = [tuple(m[:2, 2]) for m in alignment.transforms]
    np.testing.assert_allclose(recovered, shifts, atol=1.0)
    assert alignment.failed == []


def test_when_the_scene_changes_gradually_chain_mode_aligns_frames_that_reference_mode_fails_on(
    tmp_path: Path,
):
    # A new background sweeps in from the left, so the last frames share nothing with the first
    before, after = textured_scene(seed=1), textured_scene(seed=2)
    count = 8
    shifts = [(3 * i, -2 * i) for i in range(count)]
    frames = [
        camera_view(rebuilt_scene(before, after, i / (count - 1)), shifts[i], i)
        for i in range(count)
    ]
    images = write_frames(frames, tmp_path)

    reference = compute_transforms(images, mode="reference")
    chain = compute_transforms(images, mode="chain")

    assert reference.failed != []
    assert chain.failed == []
    recovered = [tuple(m[:2, 2]) for m in chain.transforms]
    np.testing.assert_allclose(recovered, shifts, atol=1.0)


def test_when_a_frame_cant_be_matched_it_reuses_the_previous_transform_and_is_reported_failed(
    tmp_path: Path,
):
    scene = textured_scene(seed=1)
    shifts = [(0, 0), (4, 2), (8, 4), (12, 6)]
    frames = [camera_view(scene, s, i) for i, s in enumerate(shifts)]
    frames[2] = np.full_like(frames[2], 128)  # lens cap on: nothing to match
    images = write_frames(frames, tmp_path)

    alignment = compute_transforms(images)

    assert alignment.failed == [2]
    np.testing.assert_array_equal(alignment.transforms[2], alignment.transforms[1])
    # The next photo is matched against the last good one, so the chain carries on
    np.testing.assert_allclose(alignment.transforms[3][:2, 2], shifts[3], atol=1.0)


def test_when_transforms_are_applied_the_common_crop_hides_all_borders():
    size = (WIDTH, HEIGHT)
    rotation = np.vstack([cv2.getRotationMatrix2D((WIDTH / 2, HEIGHT / 2), 2.0, 1.0), [0, 0, 1]])
    transforms = [np.eye(3), shift_matrix(15, -10), shift_matrix(-20, 8), rotation]

    crop = common_crop(transforms, size)

    white = np.full((HEIGHT, WIDTH), 255, np.uint8)
    for M in transforms:
        warped = cv2.warpPerspective(white, M, size, flags=cv2.INTER_NEAREST, borderValue=0)
        cropped = warped[crop.y : crop.y + crop.height, crop.x : crop.x + crop.width]
        assert cropped.min() == 255
    assert crop.width / WIDTH > 0.85
    assert (crop.width, crop.height) == (crop.width & ~1, crop.height & ~1)  # even, for H.264


def shift_matrix(dx: float, dy: float) -> np.ndarray:
    return np.array([[1, 0, dx], [0, 1, dy], [0, 0, 1]], dtype=float)
