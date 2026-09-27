# 08: Make film: render jobs, progress, download

**Goal:** 🎬 turns the photos into `film.mp4` (stabilised by default), with a progress bar, then plays it.
**Depends on:** 02, 07.

## Scope

- `backend/render/jobs.py`: one render at a time (queue/lock), runs in a background thread or process so
  the stream stays responsive. Stages: aligning, then stitching. Publishes `render-progress` (percent,
  stage) and `render-done` / `render-failed` events.
- `POST /projects/{id}/film` starts a job (409 if one is running for that project); uses the project's
  fps and `stabilise` flag, chain mode.
- `GET /projects/{id}/film.mp4` (supports range requests so iPad Safari can play it), 404 if not rendered.
- UI: 🎬 button, progress bar via SSE, then a `<video>` player and a ⬇️ download button. Mark the film
  stale when frames change after rendering.

## Behaviours to test

- When a film is requested a job runs and `film.mp4` is created (tiny frames; integration test with
  real ffmpeg, skipped if missing).
- When a job runs, progress events are published in increasing order and a done event at the end.
- When a job is already running for a project, a second request returns 409.
- When rendering fails, a failed event is published and the old film is kept.
- When stabilise is off, the stabilisation step is skipped.
- When frames change after a render, the film is reported as stale.
- When film.mp4 is requested with a Range header, it returns 206.

## Progress

- [ ] Branch created off fresh `origin/main`
- [ ] Job runner + single-job lock
- [ ] Progress events
- [ ] Film endpoint + 409
- [ ] Failure handling
- [ ] Stabilise toggle
- [ ] Stale detection
- [ ] Range requests
- [ ] UI: button, progress, player, download
- [ ] PR opened
