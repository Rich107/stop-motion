# 10: Parent area

**Goal:** grown-up controls, out of reach of accidental taps.
**Depends on:** 08.

## Scope

- Entry via a 3-second long-press on a small ⚙️ corner icon, then a 4-digit PIN (`STOPMOTION_PIN`, default
  `1234`) that sets a signed session cookie for 30 minutes.
- `/parent`: rename/remove projects, toggle stabilise per project, download films, re-lock camera
  settings, show disk free, CPU temperature (read `/sys/class/thermal/thermal_zone0/temp`, "n/a" if
  missing), app revision.
- All parent routes return 403 without the cookie.

## Behaviours to test

- When the correct PIN is posted, a session cookie is set and `/parent` loads.
- When a wrong PIN is posted, access is refused.
- When a parent route is called without the cookie it returns 403.
- When a project is removed from the parent area it's gone from the projects page.
- When the thermal file is missing the temperature shows "n/a".
- When the session is older than 30 minutes it's rejected.

## Progress

- [ ] Branch created off fresh `origin/main`
- [ ] PIN login + cookie
- [ ] Route protection
- [ ] Project management
- [ ] System info
- [ ] Session expiry
- [ ] Long-press entry UI
- [ ] PR opened
