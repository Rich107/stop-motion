# 09: GPIO clicker

**Goal:** a big arcade button on the Pi takes a photo for the active project.
**Depends on:** 05.

## Scope

- `backend/button.py`: gpiozero `Button` on a configurable pin (`STOPMOTION_BUTTON_PIN`, default GPIO 17,
  pull-up), with debounce and a cooldown (~0.7 s) so a held or double press takes one photo.
- On press: call the task 05 `capture(active_project)`. No active project: create one.
- A long press (2 s) undoes the last frame.
- Started in the app lifespan only when `STOPMOTION_BUTTON=1` (off in dev/CI).
- Document wiring in the README: button between GPIO 17 (pin 11) and GND (pin 9).

## Behaviours to test

Use gpiozero's `MockFactory` (real gpiozero, simulated pins).

- When the button is pressed, a frame is captured for the active project.
- When it is pressed twice within the cooldown, only one frame is captured.
- When there is no active project, one is created and captured into.
- When it is held for 2 s, the last frame is undone and no frame is captured.
- When `STOPMOTION_BUTTON` is not set, no button is started.

## Progress

- [ ] Branch created off fresh `origin/main`
- [ ] Press captures
- [ ] Cooldown
- [ ] No active project
- [ ] Long-press undo
- [ ] Lifespan toggle
- [ ] README wiring
- [ ] PR opened
