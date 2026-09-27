# 02: Render library + chain-mode stabilisation

**Goal:** move the stitching and stabilisation logic from the two root scripts into importable,
tested code in `backend/render/`, and add chain mode (align each frame to the previous one) to fix the
"second go" footage, where the scene changed too much for reference mode.
**Depends on:** 01.

## Scope

- `backend/render/stitch.py`: `list_images(dir)` (natural sort, image extensions),
  `stitch(frames, output, fps, width, height, hold_last, progress=None)` building the ffmpeg command.
  Split command building (pure, unit-tested) from running it.
- `backend/render/stabilise.py`: `compute_transforms(images, mode="reference"|"chain", model, features,
  exclude, ref_index)` returning per-frame 3x3 matrices plus failures; `common_crop(...)`;
  `write_aligned(images, transforms, crop, out_dir, progress=None)`.
- Chain mode: match frame i to frame i-1, compose with frame i-1's transform. On failure, reuse the
  previous transform (same as reference mode today). Make chain the default.
- `progress` callback `(done, total, stage)` so task 08 can report progress.
- Root `stopmotion.py` and `stopmotion_stabilised.py` keep the same CLI flags and become thin wrappers.
  Add `--mode reference|chain` to the stabilised script.

## Behaviours to test

Use synthetic frames generated in tests (textured background, moving block, known shifts/rotations).
Keep images small (e.g. 640x360) so tests are fast.

- When images are named img2/img10 they sort naturally.
- When the directory has non-image files they are ignored.
- When no images are found a clear error is raised.
- When building the ffmpeg command, fps, size, hold-last and output path are included.
- When frames are shifted by a known amount, reference mode recovers the shift within 1 px.
- When the scene changes gradually (content added over time) chain mode aligns frames that reference
  mode fails on.
- When a frame can't be matched, its transform reuses the previous one and it is reported as failed.
- When transforms are applied, the common crop hides all borders.
- When progress is given, it is called for every frame.
- When ffmpeg is available, stitching produces a playable MP4 with the expected frame count
  (integration test with `ffprobe`; skip if ffmpeg is missing).
- When the CLI scripts run on a small folder they still produce a video (smoke test).

## Out of scope

HTTP endpoints, background jobs.

## Progress

- [x] Branch created off fresh `origin/main`
- [x] Natural sort + image listing
- [x] ffmpeg command builder
- [x] Reference-mode alignment
- [x] Chain-mode alignment
- [ ] Failure fallback
- [ ] Common crop
- [ ] Progress callback
- [ ] Stitch integration test
- [ ] CLI wrappers + smoke tests
- [ ] PR opened
