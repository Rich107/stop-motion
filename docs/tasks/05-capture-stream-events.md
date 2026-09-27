# 05: Capture API, MJPEG stream, event bus + SSE

**Goal:** HTTP endpoints the UI and the button use.
**Depends on:** 03, 04.

## Scope

- `GET /stream`: `multipart/x-mixed-replace` MJPEG from `camera.preview_jpeg()`, ~15 fps, stops cleanly
  when the client disconnects. Several viewers share one camera.
- `backend/events.py`: in-process pub/sub (`publish(event, data)`, async subscribe).
- `GET /events`: SSE stream of events (`frame-added`, `frame-removed`, `render-progress`, `render-done`).
- Service function `capture(project_id)` used by both the API and the button (task 09):
  `camera.capture_jpeg()`, then `store.add_frame()`, lock camera settings after the first frame of a
  project, publish `frame-added`.
- `POST /projects/{id}/frames` captures; `DELETE /projects/{id}/frames/last` undoes and publishes
  `frame-removed`.
- `GET /projects/{id}/frames/{n}.jpg` and `GET /projects/{id}/frames/last.jpg` (404 when empty).
- An "active project" (last one opened) kept in app state for the button to target.

## Behaviours to test

- When a frame is captured it is stored and a `frame-added` event is published.
- When the first frame of a project is captured, camera settings are locked.
- When the last frame is undone, it's removed and `frame-removed` is published.
- When the project doesn't exist, capture returns 404.
- When `/stream` is requested it returns multipart JPEG parts.
- When a client subscribes to `/events` and a frame is captured, it receives the event.
- When `last.jpg` is requested for an empty project it returns 404.

## Progress

- [ ] Branch created off fresh `origin/main`
- [ ] Event bus
- [ ] Capture service + locking
- [ ] Capture endpoint
- [ ] Undo endpoint
- [ ] Frame image endpoints
- [ ] MJPEG stream
- [ ] SSE endpoint
- [ ] Active project
- [ ] PR opened
