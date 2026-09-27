# 06: Kid UI: projects, viewfinder, onion skin

**Goal:** the first version a 6-year-old can use: pick or start a film, see the camera with an onion
skin, take photos, undo.
**Depends on:** 05.

## Scope

- Jinja2 templates + vendored `htmx.min.js`, the htmx `sse` extension and `alpine.min.js` in
  `backend/static/` (no CDN: the Pi may be offline).
- `/` projects page: big thumbnail tiles (newest first) and a big ➕ tile. Tapping opens the camera page.
- `/projects/{id}` camera page: full-screen viewfinder `<img src="/stream">` (with `hx-preserve`, outside
  swap targets) and the last frame on top at ~30% opacity (onion skin). Onion skin toggle.
- Big buttons: 📸 take photo (`hx-post`), 🗑️ undo (with a simple confirm), frame counter, 🏠 home.
- Screen flash + shutter sound on `frame-added` (Alpine, via SSE), so button presses show up too.
- PWA: `manifest.webmanifest`, icons, `apple-mobile-web-app-capable`, full screen, landscape.
- CSS: touch targets at least 88 px, high contrast, no text needed to operate.

## Behaviours to test

Server-side with `TestClient` (HTML content), no browser automation needed:

- When the projects page loads it lists projects with thumbnails and a new-project tile.
- When the new-project tile is used a project is created and the camera page is shown.
- When the camera page loads it contains the stream, the onion-skin image and the capture button.
- When a photo is taken via the page's endpoint the frame counter partial shows the new count.
- When undo is used the counter decreases.
- When the manifest is requested it's valid JSON with name, icons and `display: fullscreen`.
- When templates render, all static assets are local (no external URLs).

## Manual checks (list in PR)

iPad Safari and Android Chrome: add to home screen, onion skin lines up, stream doesn't restart on tap.

## Progress

- [ ] Branch created off fresh `origin/main`
- [ ] Base template + static assets
- [ ] Projects page
- [ ] New project
- [ ] Camera page + onion skin
- [ ] Capture + counter
- [ ] Undo
- [ ] Flash + sound via SSE
- [ ] Manifest + icons
- [ ] PR opened
