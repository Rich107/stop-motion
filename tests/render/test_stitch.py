from pathlib import Path

from backend.render.stitch import list_images


def test_when_images_are_named_img2_and_img10_they_sort_naturally(tmp_path: Path):
    for name in ["img10.jpg", "img2.jpg", "IMG1.jpg"]:
        (tmp_path / name).write_bytes(b"")

    images = list_images(tmp_path)

    assert [p.name for p in images] == ["IMG1.jpg", "img2.jpg", "img10.jpg"]
