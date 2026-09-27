# Stop motion

A Raspberry Pi stop-motion camera for a child. Take photos from a tablet or a big button, see an
onion-skin preview of the last shot, play the film back and turn it into a stabilised MP4.
See `docs/plan.md` for the plan and `docs/tasks/` for the work, task by task.

## Run locally

Needs Python 3.11+ and ffmpeg (`brew install ffmpeg`).

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/uvicorn backend.main:app --reload
```

Then open <http://127.0.0.1:8000/health>.

Settings come from the environment:

| Variable            | Default                           | Meaning                       |
| ------------------- | --------------------------------- | ----------------------------- |
| `STOPMOTION_DATA`   | `./data`                          | Where projects are stored     |
| `STOPMOTION_CAMERA` | `fake`                            | `fake` or `pi`                |
| `REVISION`          | contents of `REVISION`, or `dev`  | Reported by `/health`         |

## Run tests

```sh
.venv/bin/ruff check
.venv/bin/ruff format --check
.venv/bin/pytest
```

## CLI scripts

`stopmotion.py` and `stopmotion_stabilised.py` turn a folder of photos into a video from the command
line. Run either with `--help`. Both are thin wrappers over `backend/render/`.

`stopmotion_stabilised.py` lines the photos up first. By default it matches each photo to the one
before it (`--mode chain`), which copes with a scene that changes a lot during the shoot;
`--mode reference` matches every photo to one frame (`--ref`), which doesn't drift but fails when
the scene has changed too much.
