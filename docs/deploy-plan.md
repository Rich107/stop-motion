# Deployment plan: push-to-deploy to the stop-motion Pi

Status: draft plan, nothing implemented. Researched 2026-09-27; links at the bottom.

## 1. Goal and constraints

- Private repo `Rich107/stop-motion`. Push to `main` (or run the workflow by hand) and GitHub Actions deploys to the Pi.
- Target: Raspberry Pi 5, Raspberry Pi OS 64-bit (Bookworm or later). The app runs as `stopmotion.service`: FastAPI + picamera2 + ffmpeg + OpenCV, and it serves a small built web frontend. On the home LAN it is reachable at `http://stopmotion.local`.
- The Pi is behind home NAT. GitHub-hosted runners cannot reach it, and `stopmotion.local` is mDNS, so it only resolves on the LAN.
- A 6-year-old uses it. A deploy must never restart the app during a filming session.

## 2. Reaching a Pi behind NAT: options

| Option                                    | Inbound exposure               | Owner setup effort                                                       | Long-lived secrets in GitHub                  | Main risk / downside                                                                                   | Verdict         |
| ----------------------------------------- | ------------------------------ | ------------------------------------------------------------------------ | --------------------------------------------- | ------------------------------------------------------------------------------------------------------ | --------------- |
| (a) Tailscale + `tailscale/github-action` | None (outbound WireGuard)      | Low: free account, policy tags, one credential                           | None with workload identity (just an SSH key) | Depends on a third-party control plane; the runner is on your tailnet for the length of the job        | **Recommended** |
| (b) Self-hosted runner on the Pi          | None (runner polls GitHub)     | Low: install runner service                                              | None for SSH (no SSH at all)                  | Every workflow in the repo runs code on the camera box; builds compete with the app for CPU/RAM        | Good fallback   |
| (c) Router port-forward + dynamic DNS     | SSH open to the whole internet | Medium: router config, DDNS client, fail2ban                             | SSH key + public hostname                     | Constant brute-force traffic, ISP CGNAT often breaks it, and it exposes your home IP                   | Discouraged     |
| (d) Cloudflare Tunnel (SSH via Access)    | None (outbound tunnel)         | Medium-high: needs a domain on Cloudflare, Zero Trust app, service token | CF Access service token ID + secret + SSH key | More moving parts; `cloudflared` has to be installed on the runner; handshake errors are hard to debug | Viable, heavier |

Notes:

- **(a) Tailscale.** `tailscale/github-action@v4` adds the runner to your tailnet as an **ephemeral, tagged** node and logs it out at the end of the job. Tailscale's docs now **recommend workload identity federation (WIF)**: GitHub's OIDC token is exchanged for tailnet access, so no Tailscale secret is stored in GitHub. WIF requires Tailscale client 1.90.1 or later on the runner. The older OAuth client (client ID + secret with the writable `auth_keys` scope) still works. Plain auth keys expire after at most 90 days, so avoid them.
- **(b) Self-hosted runner.** GitHub says self-hosted runners should only be used with private repos. Even in a private repo, anyone with write access, or a compromised dependency or action, gets code execution on the Pi and access to the job's secrets. It is acceptable for a single-owner repo, but it turns the camera Pi into a CI box. It is the best choice only if you want nothing third-party in the path.
- **(c) Port-forward.** Not recommended. Internet-exposed port 22 attracts scans within minutes. Many ISPs use CGNAT, which makes the Pi unreachable anyway. Dynamic DNS adds a second point of failure.
- **(d) Cloudflare Tunnel.** Good if you already run a domain on Cloudflare. CI connects through `cloudflared access ssh` with a Zero Trust **service token**. Compared with (a), it adds a domain dependency and a third-party action or manual `cloudflared` install.

**Recommendation: (a) Tailscale with workload identity federation, then plain OpenSSH over the tailnet** with a deploy-only SSH key whose command is forced to a single script on the Pi. Fallback: (b), using the same `deploy.sh`, triggered locally.

## 3. GitHub secrets

Set these in repo **Settings → Secrets and variables → Actions → Repository secrets**. Repository-level secrets are used because environments on a *private* repo need GitHub Pro or Team (see section 8).

| Secret               | Contents                                                                                                                               |
| -------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| `PI_HOST`            | Pi's tailnet MagicDNS name, e.g. `stopmotion.tailXXXX.ts.net` (or its `100.x.y.z` IP). **Not** `stopmotion.local`.                     |
| `PI_USER`            | `deploy`                                                                                                                               |
| `PI_SSH_KEY`         | Private half of a new ed25519 key used only for this deploy (`ssh-keygen -t ed25519 -C gha-deploy -N ""`).                             |
| `PI_KNOWN_HOSTS`     | The Pi's host key line(s), e.g. `stopmotion.tailXXXX.ts.net ssh-ed25519 AAAA...`. Pins the host and prevents MITM.                     |
| `TS_OAUTH_CLIENT_ID` | Client ID of the Tailscale **federated identity** (WIF) credential. Tailscale says this isn't secret; stored as a secret for tidiness. |
| `TS_AUDIENCE`        | The audience Tailscale generates for that credential (`api.tailscale.com/<client-id>`). Not secret either.                             |
| `TS_OAUTH_SECRET`    | *Only if you use an OAuth client instead of WIF*: the OAuth client secret (scope `auth_keys` write, tag `tag:ci`).                     |

## 4. One-time setup (owner, by hand)

### 4.1 Tailscale

1. Create a Tailscale account (the free Personal plan is enough). Install Tailscale on the Pi and on your laptop.
2. In **Access controls**, add tags and a grant that lets CI reach **only** SSH on the Pi. Keep a rule for your own devices so you don't lock yourself out:

   ```jsonc
   "tagOwners": {
     "tag:ci":         ["autogroup:admin"],
     "tag:stopmotion": ["autogroup:admin"]
   },
   "grants": [
     { "src": ["autogroup:member"], "dst": ["*"],              "ip": ["*"] },
     { "src": ["tag:ci"],           "dst": ["tag:stopmotion"], "ip": ["tcp:22"] }
   ]
   ```
3. Tag the Pi: `sudo tailscale up --advertise-tags=tag:stopmotion` (or set the tag in the admin console). Tagged nodes have key expiry disabled by default, so the Pi won't silently drop off.
4. Create the CI credential at **Settings → Trust credentials → Credential → OpenID Connect → Issuer: GitHub Actions**:
   - Subject: `repo:Rich107/stop-motion:ref:refs/heads/main`. This matches pushes to main and manual runs from main.
   - Scope: `auth_keys` (write). Tag: `tag:ci`.
   - Copy the **Client ID** and **Audience** into the GitHub secrets.

### 4.2 Pi OS

```bash
# hostname -> stopmotion.local via avahi (installed by default)
sudo hostnamectl set-hostname stopmotion
sudo apt update && sudo apt install -y python3-picamera2 python3-venv ffmpeg rsync curl

# service account (runs the app) and deploy account (receives releases)
sudo adduser --system --group --home /var/lib/stopmotion stopmotion
sudo usermod -aG video stopmotion
sudo adduser --disabled-password --gecos "" deploy

# layout
sudo mkdir -p /opt/stopmotion/{releases,venvs,bin}
sudo chown -R deploy:deploy /opt/stopmotion/releases /opt/stopmotion/venvs
sudo chown root:root /opt/stopmotion/bin     # deploy.sh is root-owned, so the deploy user can't edit it
```

Directory layout:

```
/opt/stopmotion/
  bin/deploy.sh                  # root-owned, forced SSH command (section 6)
  releases/20260927T1200-ab12cd3/
    backend/  frontend/dist/  requirements.txt  REVISION
    .venv -> /opt/stopmotion/venvs/<sha256-of-requirements>
  venvs/<sha256-of-requirements>/ # shared by releases with identical deps
  current -> releases/20260927T1200-ab12cd3
/var/lib/stopmotion/             # photos, movies, last_capture (NOT in releases)
```

### 4.3 Restricted SSH key and host-key pinning

In `/home/deploy/.ssh/authorized_keys` (mode 600, owned by `deploy`), one line:

```
restrict,from="100.64.0.0/10,fd7a:115c:a1e0::/48",command="/opt/stopmotion/bin/deploy.sh" ssh-ed25519 AAAA... gha-deploy
```

- `restrict` turns off port forwarding, PTY, agent and X11 forwarding. `command=` means the key can **only** run `deploy.sh`. The script reads the requested action from `$SSH_ORIGINAL_COMMAND`. `from=` accepts the key only from Tailscale addresses.
- Build `PI_KNOWN_HOSTS` from a machine already on the tailnet: `ssh-keyscan -t ed25519 stopmotion.tailXXXX.ts.net`. Check the fingerprint against `ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub`, run on the Pi itself.
- Optionally harden sshd with `PasswordAuthentication no`.

### 4.4 sudoers: restart one service only

`sudo visudo -f /etc/sudoers.d/stopmotion-deploy`:

```
deploy ALL=(root) NOPASSWD: /usr/bin/systemctl restart stopmotion.service
```

(`systemctl is-active` and reading logs with `journalctl -u` need no root. To allow the latter, add `deploy` to the `systemd-journal` group.)

### 4.5 systemd unit (draft) at `/etc/systemd/system/stopmotion.service`

```ini
[Unit]
Description=Stop-motion camera app
After=network-online.target
Wants=network-online.target

[Service]
User=stopmotion
Group=stopmotion
SupplementaryGroups=video
WorkingDirectory=/opt/stopmotion/current
Environment=STOPMOTION_DATA=/var/lib/stopmotion
Environment=PYTHONUNBUFFERED=1
ExecStart=/opt/stopmotion/current/.venv/bin/uvicorn backend.main:app --host 0.0.0.0 --port 80
# port 80 so the kid-friendly URL is just http://stopmotion.local
AmbientCapabilities=CAP_NET_BIND_SERVICE
Restart=on-failure
RestartSec=3
StateDirectory=stopmotion
NoNewPrivileges=yes
ProtectSystem=full
ProtectHome=yes
PrivateTmp=yes
# no PrivateDevices: picamera2 needs /dev/video*, /dev/media*, /dev/dma_heap

[Install]
WantedBy=multi-user.target
```

`sudo systemctl daemon-reload && sudo systemctl enable stopmotion.service` (the first real deploy starts it).

## 5. Deploy mechanism

**Choice: CI builds a release tarball and pipes it over SSH to the forced command.** Alternatives considered:

| Mechanism                | Pros                                                                              | Cons                                                                                                            |
| ------------------------ | --------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| Release tarball over SSH | Immutable per-SHA releases; frontend pre-built in CI; works with a forced command | A bit more scripting                                                                                            |
| rsync into release dir   | Fast incremental copies                                                           | Needs an rsync-capable shell or `rrsync`, which clashes with a single forced command                            |
| `git pull` on the Pi     | Simple                                                                            | Needs a GitHub deploy key on the Pi, a Node toolchain on the Pi, and a mutable working tree (no clean rollback) |

What happens:

1. **CI**: checkout, `npm ci && npm run build` in `frontend/`, a quick `python -m compileall backend` sanity check, then `tar` of `backend/`, `frontend/dist/`, `requirements.txt` and `REVISION` (the commit SHA).
2. **Idle guard** (section 7): `ssh ... idle-check`. It waits while a session is in progress.
3. **Upload + switch**: `ssh ... "deploy <sha>" < release.tar.gz`. `deploy.sh` then:
   - takes a `flock` so two deploys can't overlap on the Pi;
   - unpacks into `releases/<ts>-<sha>/`;
   - **Python deps**: hashes `requirements.txt`. If `venvs/<hash>` exists, it is reused (no pip run). Otherwise the script builds it in `venvs/<hash>.tmp` with `python3 -m venv --system-site-packages` (so the apt-installed `picamera2`/`libcamera` are visible) and `pip install -r`, then renames it into place. Deps are therefore installed only when `requirements.txt` changes;
   - symlinks `release/.venv -> venvs/<hash>`;
   - switches `current` **atomically**: `ln -sfn` is not atomic, so it runs `ln -s <release> current.new && mv -T current.new current` instead;
   - runs `sudo systemctl restart stopmotion.service`;
   - **health check**: polls `curl -fsS http://127.0.0.1/health` for up to 30 s;
   - **on failure, it rolls back automatically**: repoints `current` at the previous release, restarts, re-checks, and exits non-zero so the workflow goes red;
   - **prunes**: keeps the newest 5 releases (and never the current or previous one), then deletes venvs that no remaining release links to.
4. **Manual rollback**: `workflow_dispatch` with `action: rollback` runs `ssh ... rollback`, which switches `current` to the previous release and restarts.

`/health` should return 200 only when the app is up **and** the camera opened, e.g. `{"status":"ok","revision":"<sha>"}`. `deploy.sh` checks that `revision` matches the SHA it just deployed.

## 6. Draft `/opt/stopmotion/bin/deploy.sh` (installed by hand, root-owned 0755)

```bash
#!/usr/bin/env bash
set -euo pipefail
BASE=/opt/stopmotion; DATA=/var/lib/stopmotion; KEEP=5; IDLE_MIN=${IDLE_MIN:-15}
exec 9>"$BASE/releases/.deploy.lock"; flock -n 9 || { echo "another deploy running"; exit 73; }
read -r ACTION ARG1 ARG2 <<<"${SSH_ORIGINAL_COMMAND:-}"

health() {  # $1 = expected revision (optional)
  for _ in $(seq 30); do
    out=$(curl -fsS --max-time 2 http://127.0.0.1/health 2>/dev/null) && \
      { [[ -z "${1:-}" || "$out" == *"$1"* ]] && return 0; }
    sleep 1
  done; return 1
}
switch_to() { ln -sfn "$1" "$BASE/current.new" && mv -T "$BASE/current.new" "$BASE/current"; }
previous() { ls -1dt "$BASE"/releases/*/ | sed 's:/$::' | grep -vx "$(readlink -f "$BASE/current")" | head -1; }
restart() { sudo /usr/bin/systemctl restart stopmotion.service; }

case "$ACTION" in
  idle-check)
    f="$DATA/last_capture"
    if [[ -f $f ]] && (( $(date +%s) - $(stat -c %Y "$f") < IDLE_MIN*60 )); then
      echo "busy: capture within last ${IDLE_MIN} min"; exit 75; fi
    echo idle ;;
  deploy)
    [[ "$ARG1" =~ ^[0-9a-f]{40}$ ]] || { echo "bad sha"; exit 64; }
    rel="$BASE/releases/$(date -u +%Y%m%dT%H%M%S)-${ARG1:0:7}"
    mkdir -p "$rel" && tar -xz -C "$rel" --no-same-owner   # tarball on stdin
    h=$(sha256sum "$rel/requirements.txt" | cut -c1-16); venv="$BASE/venvs/$h"
    if [[ ! -x "$venv/bin/python" ]]; then
      rm -rf "$venv.tmp"; python3 -m venv --system-site-packages "$venv.tmp"
      "$venv.tmp/bin/pip" install --no-cache-dir -r "$rel/requirements.txt"
      mv -T "$venv.tmp" "$venv"
    fi
    ln -s "$venv" "$rel/.venv"
    prev=$(readlink -f "$BASE/current" || true)
    switch_to "$rel"; restart
    if ! health "$ARG1"; then
      echo "health check FAILED, rolling back to ${prev:-<none>}"
      journalctl -u stopmotion.service -n 50 --no-pager || true
      [[ -n "$prev" ]] && { switch_to "$prev"; restart; health || echo "rollback also unhealthy!"; }
      exit 1
    fi
    # prune: keep newest $KEEP releases, then remove unreferenced venvs
    ls -1dt "$BASE"/releases/*/ | tail -n +$((KEEP+1)) | while read -r d; do
      [[ "$(readlink -f "$d")" == "$prev" ]] || rm -rf "$d"; done
    used=$(for l in "$BASE"/releases/*/.venv; do readlink -f "$l"; done | sort -u)
    for v in "$BASE"/venvs/*/; do grep -qx "${v%/}" <<<"$used" || rm -rf "$v"; done
    echo "deployed $ARG1" ;;
  rollback)
    p=$(previous); [[ -n "$p" ]] || { echo "no previous release"; exit 1; }
    switch_to "$p"; restart; health && echo "rolled back to $p" ;;
  *) echo "usage: idle-check | deploy <sha> | rollback"; exit 64 ;;
esac
```

Changes to `deploy.sh` itself are deliberately **not** shipped by CI. The script stays root-owned so a leaked deploy key can't rewrite it. Keep a copy in the repo at `deploy/pi/deploy.sh` and reinstall it by hand when it changes.

## 7. Don't deploy mid-session (the 6-year-old guard)

- The app runs `touch /var/lib/stopmotion/last_capture` on every captured frame. This is a small requirement on the app code.
- `idle-check` returns exit 75 if a frame was captured in the last **15 minutes**. The workflow polls it every 60 s for up to 30 min. If the Pi is still busy after that, the job **fails with a clear "deferred" message** and you re-run it later. A manual run with `force: true` skips the guard.
- Optional extra: have the frontend show a small "updating…" overlay when `/health`'s `revision` changes, so the child sees why the screen blinked.
- Alternative: a GitHub **environment with required reviewers** (manual approval). For a private repo this needs GitHub Pro. It also puts the approval tap on the owner, which the idle guard avoids.

## 8. Concurrency, triggers, notes

- `concurrency: { group: deploy-pi, cancel-in-progress: false }` queues deploys instead of cancelling a half-done switch. The Pi-side `flock` is the second line of defence.
- Triggers: `push` to `main` plus `workflow_dispatch`, which takes `action` (deploy/rollback) and `force`.
- The WIF subject `ref:refs/heads/main` means manual runs must use the main branch. If you later add a GitHub environment, the OIDC `sub` changes to `repo:Rich107/stop-motion:environment:<name>`, so update the Tailscale credential to match.
- Pin third-party actions to a commit SHA once things work. Tags are used below for readability.

## 9. Draft `.github/workflows/deploy.yml`

```yaml
name: Deploy to Pi

on:
  push:
    branches: [main]
  workflow_dispatch:
    inputs:
      action:
        description: "deploy or rollback"
        type: choice
        options: [deploy, rollback]
        default: deploy
      force:
        description: "Deploy even if the camera was used in the last 15 min"
        type: boolean
        default: false

permissions:
  contents: read
  id-token: write          # OIDC token for Tailscale workload identity federation

concurrency:
  group: deploy-pi
  cancel-in-progress: false

jobs:
  deploy:
    runs-on: ubuntu-latest
    timeout-minutes: 45
    env:
      ACTION: ${{ inputs.action || 'deploy' }}
      FORCE: ${{ inputs.force || false }}
    steps:
      - uses: actions/checkout@v7
        if: env.ACTION == 'deploy'

      - uses: actions/setup-node@v7
        if: env.ACTION == 'deploy'
        with:
          node-version: 22
          cache: npm
          cache-dependency-path: frontend/package-lock.json

      - name: Build frontend + package release
        if: env.ACTION == 'deploy'
        run: |
          (cd frontend && npm ci && npm run build)
          python3 -m compileall -q backend
          echo "$GITHUB_SHA" > REVISION
          tar -czf release.tar.gz backend frontend/dist requirements.txt REVISION

      - name: Join tailnet
        uses: tailscale/github-action@v4
        with:
          oauth-client-id: ${{ secrets.TS_OAUTH_CLIENT_ID }}
          audience: ${{ secrets.TS_AUDIENCE }}
          # OAuth-client alternative: replace `audience` with
          # oauth-secret: ${{ secrets.TS_OAUTH_SECRET }}
          tags: tag:ci
          ping: ${{ secrets.PI_HOST }}

      - name: Configure SSH
        run: |
          install -m 700 -d ~/.ssh
          printf '%s\n' "${{ secrets.PI_SSH_KEY }}" > ~/.ssh/id_ed25519 && chmod 600 ~/.ssh/id_ed25519
          printf '%s\n' "${{ secrets.PI_KNOWN_HOSTS }}" > ~/.ssh/known_hosts
          cat > ~/.ssh/config <<EOF
          Host pi
            HostName ${{ secrets.PI_HOST }}
            User ${{ secrets.PI_USER }}
            IdentityFile ~/.ssh/id_ed25519
            StrictHostKeyChecking yes
            ServerAliveInterval 15
          EOF

      - name: Wait until nobody is filming
        if: env.ACTION == 'deploy' && env.FORCE != 'true'
        run: |
          for i in $(seq 30); do
            rc=0; ssh pi idle-check || rc=$?
            [ $rc -eq 0 ] && exit 0
            [ $rc -ne 75 ] && exit $rc
            echo "Camera in use, waiting ($i/30)..."; sleep 60
          done
          echo "::error::Deferred: camera in use for 30+ min. Re-run later or use force."
          exit 1

      - name: Deploy
        if: env.ACTION == 'deploy'
        run: ssh pi "deploy $GITHUB_SHA" < release.tar.gz

      - name: Rollback
        if: env.ACTION == 'rollback'
        run: ssh pi rollback
```

## 10. Owner checklist (manual steps)

1. Create the Tailscale account, install Tailscale on the Pi and laptop, edit the policy file (tags + grants), and tag the Pi `tag:stopmotion`.
2. Create the Tailscale OIDC trust credential for GitHub Actions (subject `repo:Rich107/stop-motion:ref:refs/heads/main`, scope `auth_keys`, tag `tag:ci`). If you prefer an OAuth client, create that instead.
3. Pi OS setup: hostname, apt packages, users, directories, sudoers, systemd unit, and a hand-installed `deploy.sh`.
4. Generate the deploy SSH key and install the public half with `restrict,from=,command=`. Capture and verify the host key.
5. Add the GitHub secrets in section 3. Make sure Actions is enabled on the private repo. Private repos use free-plan Actions minutes; this job is about 2–3 min per deploy.
6. App-side prerequisites: a `/health` endpoint that reports the revision, the `last_capture` touch, a data dir taken from `STOPMOTION_DATA`, and `requirements.txt` at the repo root.
7. First run: trigger `workflow_dispatch` by hand and watch it. Then test a rollback, and a deliberately broken `/health` to confirm the automatic rollback works.

## Sources

- Tailscale GitHub Action (v4, inputs, WIF needs 1.90.1+): https://github.com/tailscale/github-action
- Tailscale KB, GitHub Action (WIF recommended, ephemeral nodes, tags): https://tailscale.com/kb/1276/tailscale-github-action
- Tailscale KB, Workload identity federation (Trust credentials page, audience): https://tailscale.com/kb/1581/workload-identity-federation
- Tailscale grants syntax: https://tailscale.com/kb/1537/grants-syntax
- GitHub OIDC subject claim formats: https://docs.github.com/en/actions/concepts/security/openid-connect
- GitHub environments plan availability for private repos: https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments
- GitHub secure use of self-hosted runners: https://docs.github.com/en/actions/reference/security/secure-use
- Cloudflare Tunnel SSH from Actions (community action, service tokens): https://github.com/NX1X/cloudflare-tunnel-ssh-action
- actions/checkout releases (v7): https://github.com/actions/checkout/releases
- actions/setup-node releases (v7): https://github.com/actions/setup-node/releases
