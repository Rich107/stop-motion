# 07: Playback and speed picker

**Goal:** ▶️ plays the film so far in the browser, looping, at the chosen speed.
**Depends on:** 06.

## Scope

- `GET /projects/{id}/frames.json` returns ordered frame URLs + fps.
- Speed picker: 🐢 6 fps, 🐇 10 fps, 🚀 15 fps, stored in `project.json` (`PATCH /projects/{id}` or form post).
- Player overlay (Alpine): preloads frames, loops at fps, ✖ closes back to the camera. Shows a friendly
  empty state when there are no frames.
- Smaller playback frames (generate `frames/small/` on add, or resize on request and cache) so playback is
  smooth over wifi.

## Behaviours to test

- When frames.json is requested it lists frames in order with the project's fps.
- When a speed is chosen it is saved and returned by frames.json.
- When an invalid speed is sent it is rejected.
- When a small frame is requested it is smaller than the original and cached.
- When the camera page loads it includes the play button and speed picker with the current speed selected.

## Progress

- [ ] Branch created off fresh `origin/main`
- [ ] frames.json
- [ ] Speed setting
- [ ] Validation
- [ ] Small frames
- [ ] Player overlay + speed picker UI
- [ ] PR opened
