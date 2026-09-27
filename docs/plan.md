# Stop-motion Pi: app plan

Status: draft, in review (PR). Implement task by task once merged. Written 2026-09-27.

## What we're building

A Raspberry Pi with a camera on a 3D-printed stand. A 6-year-old uses a tablet (over home wifi) or a big
physical button to take photos, sees a live preview with an onion-skin ghost of the last photo, plays the
film back, and turns it into a stabilised MP4.

## Decisions

| Area         | Decision                                                                                          |
| ------------ | ------------------------------------------------------------------------------------------------- |
| Hardware     | Raspberry Pi 5 (4 GB), Camera Module 3, 60 mm arcade button on GPIO                               |
| Backend      | Python 3.11+, FastAPI, Jinja2 templates, uvicorn                                                   |
| Frontend     | htmx + Alpine.js, served by the backend. No build step, no Node                                   |
| Live preview | MJPEG stream from picamera2 low-res stream at `/stream`, shown with `<img>`                        |
| Push updates | Server-sent events (htmx `sse` extension) for button presses and render progress                  |
| Camera       | `Camera` interface with `FakeCamera` (dev, tests, CI) and `PiCamera` (picamera2, Pi only)          |
| Button       | gpiozero; tests use gpiozero's `MockFactory`                                                      |
| Rendering    | ffmpeg + OpenCV stabilisation (existing scripts, refactored into `backend/render/`, plus chain mode) |
| Storage      | One folder per project under `$STOPMOTION_DATA` with a `project.json`. No database                |
| Install      | Tablet adds the site to its home screen (PWA manifest). Pi reachable at `http://stopmotion.local` |
| Deploy       | See `docs/deploy-plan.md` (Tailscale + SSH from GitHub Actions)                                   |

Assumptions (change the relevant task if wrong): Pi 5, tablet could be iPad or Android (web app works on
both), arcade button rather than a Bluetooth remote.

## Code layout

Matches `docs/deploy-plan.md` (`backend.main:app`, `requirements.txt` at the root).

```
backend/
  main.py            FastAPI app factory (create_app) and `app`
  config.py          Settings from env (STOPMOTION_DATA, STOPMOTION_CAMERA=fake|pi, REVISION)
  camera/            base.py (Camera protocol), fake.py, picam.py
  projects.py        Project storage
  events.py          In-process event bus -> SSE
  render/            stitch.py, stabilise.py, jobs.py
  button.py          GPIO clicker
  templates/         Jinja2 pages and partials
  static/            htmx, alpine, css, icons, sounds, manifest
tests/               pytest, mirrors backend/
stopmotion.py, stopmotion_stabilised.py   CLI scripts, kept working (become thin wrappers)
requirements.txt, requirements-dev.txt, pyproject.toml (pytest + ruff config)
```

## Conventions (every task)

- **Workflow**: branch off fresh `origin/main`, one PR per task, strict TDD: one failing test, commit it
  (`test: ...`), minimal implementation, commit it (`feat: ...` / `fix: ...`), repeat. Done when all tests
  pass. Then open the PR.
- **Progress**: tick the task file's `## Progress` checklist and commit it as you go.
- **Tests**: pytest. Arrange / Act / Assert with a blank line between sections (`# Arrange` comments only
  when a section isn't obvious). Names use "when": `test_when_last_frame_is_undone_it_is_deleted`.
  Prefer real objects (`FakeCamera`, `tmp_path` data dirs, FastAPI `TestClient`, gpiozero `MockFactory`)
  over mocks. Mock only process boundaries you can't run (picamera2, ffmpeg in unit tests).
- **Style**: ruff (lint + format), type hints on public functions, small modules, comments only where the
  "why" isn't obvious. Match the existing scripts' tone.
- **Kid-first UI**: icons over words, touch targets at least 88 px, nothing destructive without a
  confirm, parent-only actions behind a long-press.
- **Hardware code** (`picam.py`, real GPIO) can't run in CI: keep it thin, put logic in testable code,
  and list manual Pi checks in the PR description.
- **Runtime**: no containers. The app runs as a systemd service in a venv created with
  `--system-site-packages`, so the apt-installed picamera2/libcamera are visible (see `docs/deploy-plan.md`).

## Per-task workflow

One task at a time, in order. For each task a subagent:

1. Branches off fresh `origin/main` (`git fetch origin`, then branch from `origin/main`).
2. Works in strict TDD as described under Conventions, updating the task's `## Progress` checklist.
3. Is done when all tests pass locally and in CI. Then it opens the PR.
4. Then separate review subagents run locally in the Claude Code session (no review runs in GitHub
   Actions), each fixing what it finds and pushing to the PR branch:
   1. Every test follows Arrange / Act / Assert.
   2. Every test name uses the "when" convention.
   3. No over-mocked tests.
   4. The PR description matches the actual changes.
   5. Code review: runs `/code-review` locally against the PR, posts the findings as a markdown PR
      comment with `gh pr comment`, then fixes the confirmed ones.
5. **Auto-merge**: once CI is green and all review subagents are done, squash-merge the PR, delete the
   branch, and start the next task. Stop and report instead of merging if CI stays red, a review finding
   needs a decision from the owner, or the task needs something only the owner can do.

## Tasks

Run in order. Each depends on the ones before it being merged.

| #  | Task                                            | File                                   |
| -- | ----------------------------------------------- | -------------------------------------- |
| 01 | Scaffold, `/health`, CI test workflow           | `docs/tasks/01-scaffold.md`            |
| 02 | Render library + chain-mode stabilisation       | `docs/tasks/02-render-library.md`      |
| 03 | Project storage                                 | `docs/tasks/03-project-storage.md`     |
| 04 | Camera interface, fake and Pi cameras           | `docs/tasks/04-camera.md`              |
| 05 | Capture API, MJPEG stream, event bus + SSE      | `docs/tasks/05-capture-stream-events.md` |
| 06 | Kid UI: projects, viewfinder, onion skin        | `docs/tasks/06-ui-capture.md`          |
| 07 | Playback and speed picker                       | `docs/tasks/07-playback.md`            |
| 08 | Make film: render jobs, progress, download      | `docs/tasks/08-make-film.md`           |
| 09 | GPIO clicker                                    | `docs/tasks/09-clicker.md`             |
| 10 | Parent area                                     | `docs/tasks/10-parent-area.md`         |
| 11 | Deployment (workflow, systemd, Pi scripts)      | `docs/tasks/11-deployment.md`          |

Out of scope for agents: the 3D-printed stand and button box, buying hardware, Tailscale/GitHub secret setup.
