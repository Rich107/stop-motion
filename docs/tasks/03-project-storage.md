# 03: Project storage

**Goal:** projects on disk that the API and UI build on.
**Depends on:** 01.

## Scope

`backend/projects.py`, a `ProjectStore(data_dir)`:

```
$STOPMOTION_DATA/
  last_capture                 touched on every capture (used by the deploy guard)
  projects/<id>/project.json   {"id", "name", "created_at", "fps", "stabilise", "frames": ["00001.jpg", ...]}
  projects/<id>/frames/00001.jpg
  projects/<id>/thumb.jpg      resized copy of the latest frame
  projects/<id>/film.mp4       written by task 08
```

- `create(name=None)` (default name like "Film 3"), `list()` newest first, `get(id)`, `rename`, `remove`.
- `add_frame(id, jpeg_bytes)`: writes the next numbered file atomically, appends to `frames`, updates the
  thumbnail, touches `last_capture`.
- `undo_last(id)`: removes the last frame (file + list entry), updates the thumbnail.
- `frame_path(id, index)`, `last_frame_path(id)`.
- Writes to `project.json` are atomic (write temp + rename). IDs are safe for paths (no traversal).

## Behaviours to test

- When a project is created it appears in the list with zero frames.
- When no name is given it gets the next "Film N" name.
- When projects are listed the newest is first.
- When a frame is added it is saved with the next number and recorded in project.json.
- When a frame is added the thumbnail and `last_capture` are updated.
- When the last frame is undone it is removed from disk and the list.
- When undo is called on an empty project nothing breaks.
- When a project is renamed or removed the change persists across a new `ProjectStore`.
- When an id contains `..` or `/` it is rejected.

## Progress

- [x] Branch created off fresh `origin/main`
- [x] Create + list
- [x] Default names
- [x] Add frame
- [x] Thumbnail + last_capture
- [x] Undo
- [x] Rename + remove + persistence
- [ ] Path safety
- [ ] PR opened
