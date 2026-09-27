from pathlib import Path

import numpy as np

from backend.render.stabilise import compute_transforms
from tests.render.scenes import camera_view, rebuilt_scene, textured_scene, write_frames


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
