# 11: Deployment

**Goal:** turn `docs/deploy-plan.md` into real files.
**Depends on:** 01 (needs `/health` and `requirements.txt`); best done after 04 so `/health` checks the camera.

## Scope

- Update `docs/deploy-plan.md` for the htmx decision: **no frontend build**. Remove the Node/`npm` steps
  and `frontend/dist/` from the tarball (templates and static files live in `backend/`).
- `.github/workflows/deploy.yml` from the plan (checkout, run tests, Tailscale, tarball, SSH to
  `deploy.sh`, capture-guard wait, `workflow_dispatch` with `force` and `rollback` inputs, concurrency).
  Pin actions to commit SHAs.
- `deploy/stopmotion.service`, `deploy/deploy.sh`, `deploy/sudoers-stopmotion`,
  `deploy/install-pi.sh` (one-time setup the owner runs by hand on the Pi, idempotent).
- `docs/pi-setup.md`: step-by-step owner checklist (Tailscale, keys, secrets, first deploy, test rollback).

## Behaviours to test

Shell and workflow code, so test what can be tested locally (pytest running the script against a temp
base dir, with `systemctl`/`curl`/`sudo` stubbed via `PATH`):

- When `deploy.sh` runs with a fake release tarball, it unpacks it into `releases/<sha>` and switches `current`.
- When the health check fails, it rolls back to the previous release.
- When `requirements.txt` is unchanged, the existing venv is reused.
- When more than 5 releases exist, the oldest are pruned.
- When `last_capture` is recent and `force` isn't set, it exits with the "deferred" code.
- `shellcheck` passes on all scripts; `actionlint` passes on workflows (add both to CI).

## Progress

- [ ] Branch created off fresh `origin/main`
- [ ] Deploy plan updated (no Node)
- [ ] deploy.sh: unpack + switch
- [ ] deploy.sh: rollback on failed health
- [ ] deploy.sh: venv reuse
- [ ] deploy.sh: prune
- [ ] deploy.sh: capture guard
- [ ] systemd unit, sudoers, install-pi.sh
- [ ] deploy.yml
- [ ] shellcheck + actionlint in CI
- [ ] pi-setup.md
- [ ] PR opened
