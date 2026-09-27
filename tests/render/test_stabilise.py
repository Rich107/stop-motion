from pathlib import Path

import numpy as np

from backend.render.stabilise import compute_transforms
from tests.render.scenes import camera_view, textured_scene, write_frames


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
