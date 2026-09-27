# 01: Scaffold, `/health`, CI test workflow

**Goal:** empty but runnable FastAPI app, test tooling, and CI that runs tests on every PR.
**Depends on:** nothing.

## Scope

- `backend/` package with `create_app(settings)` factory in `backend/main.py` and module-level `app`.
- `backend/config.py`: `Settings` read from env: `STOPMOTION_DATA` (default `./data`),
  `STOPMOTION_CAMERA` (`fake` default, or `pi`), `REVISION` (default: contents of a `REVISION` file if
  present, else `"dev"`).
- `GET /health` returns `200 {"status": "ok", "revision": "<revision>"}`.
- `requirements.txt` (fastapi, uvicorn, jinja2, opencv-python-headless, numpy),
  `requirements-dev.txt` (pytest, httpx, ruff), `pyproject.toml` with pytest and ruff config.
- `.github/workflows/test.yml`: on PR and push to main; ubuntu-latest; Python 3.11; apt install ffmpeg;
  `ruff check`, `ruff format --check`, `pytest`.
- Short `README.md`: what it is, run locally (`uvicorn backend.main:app --reload`), run tests.
- Add `data/` to `.gitignore`.

## Behaviours to test

- When `/health` is called it returns 200 with status ok.
- When `REVISION` env is set, `/health` reports it.
- When no `REVISION` env or file is present, revision is `"dev"`.
- When `STOPMOTION_DATA` is set, settings use it; when unset, defaults to `./data`.

## Out of scope

Any camera, UI or project logic.

## Progress

- [x] Branch created off fresh `origin/main`
- [x] Tooling files (requirements, pyproject) in place
- [x] Health: status ok
- [x] Health: revision from env
- [x] Health: revision default
- [x] Settings: revision from REVISION file
- [x] Settings: data dir env and default
- [x] Settings: camera env and default
- [x] CI workflow added and green on the PR
- [x] README
- [x] PR opened
