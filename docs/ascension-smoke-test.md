# Ascension gameplay smoke test

Run this after any input, F10, video, locale, or gameplay-facing change.

## Boot

- Build completes without linker/compiler errors.
- Game reaches file select.
- F10 opens and closes cleanly.

## Automated preflight / build verification

Before a gameplay-facing test, run:

```bash
ASCENSION_NO_LAUNCH=1 ./tools_pc/run_ascension_safe_test.sh
```

Expected results:

- The Ascension patcher preflight reports that all child patchers parse cleanly before any patcher runs.
- The NTSC-final PC target builds successfully.
- The runner finds the generated `ge007` executable for the current platform.
- The run ends with `ASCENSION_NO_LAUNCH=1; skipping game launch.` rather than trying to open an SDL window.
- A normal run without `ASCENSION_NO_LAUNCH=1` still launches the game after the same patch/build path.

## Keyboard / mouse

- WASD movement works.
- Mouse look works.
- Left mouse fires.
- Right mouse aims.
- E/Space action works.
- R/X/F cancel/reload path works.
- Mouse wheel cycles weapon once per notch.

## Ascension controls

- F10 > INPUT > Control preset shows CLASSIC / HYBRID / MODERN.
- A fresh configuration starts on CLASSIC, preserving the original PC-port control behaviour by default.
- Resetting Control preset returns it to CLASSIC.
- An already-saved HYBRID or MODERN selection remains selected after relaunch; the new default must not overwrite existing user configuration.
- F10 > INPUT > Dedicated crouch shows OFF / ON.
- Modern: C / Left Ctrl / Right Ctrl crouch; Left Ctrl must not fire simultaneously.
- Hybrid: C crouches; legacy Left Ctrl fire remains available.
- Classic: dedicated crouch shortcut is disabled.
- Weapon-specific crouch restrictions still behave like GoldenEye.

## Input tuning

- Raw mouse input toggle changes only the existing raw-input option.
- Mouse smoothing at 0 preserves unsmoothed behavior.
- Mouse Y scale returns to 100 cleanly.
- Hipfire pitch returns to 100 cleanly.
- Gamepad deadzone returns to 7000 cleanly.
- Trigger threshold returns to 23 cleanly.
- Gamepad invert Y toggles correctly.

## PC polish presets

- F10 > DISPLAY > FOV preset shows ORIGINAL / MODERN / WIDE / CUSTOM.
- ORIGINAL sets FOV scale to 100; MODERN sets 105; WIDE sets 115.
- Choosing CUSTOM leaves the manually selected FOV value unchanged.
- F10 > INPUT > Mouse feel shows CLASSIC / SMOOTH / MODERN / RAW / CUSTOM.
- RAW enables raw mouse input and disables smoothing; SMOOTH applies smoothing without enabling raw input.
- Choosing CUSTOM leaves manually tuned mouse options unchanged.
- F10 > INPUT > Gamepad preset shows CLASSIC / MODERN / INVERT Y / CUSTOM.
- CLASSIC restores deadzone 7000, trigger threshold 23 and normal look Y.
- MODERN applies deadzone 5000, trigger threshold 18 and normal look Y.
- INVERT Y keeps the modern deadzone/trigger values and only inverts the look Y axis.
- Choosing CUSTOM leaves manually tuned gamepad options unchanged.
- After a normal close/relaunch, the selected preset and resulting values persist.

## Display / quality

- Alt+Enter toggles fullscreen once per key press.
- F11 toggles fullscreen once per key press.
- F10 > DISPLAY > Quality preset: Performance applies 1x MSAA, bilinear filtering, and 2x anisotropic filtering.
- F10 > DISPLAY > Quality preset: Balanced applies 2x MSAA, 3-point filtering, and 4x anisotropic filtering.
- F10 > DISPLAY > Quality preset: Quality applies 4x MSAA, 3-point filtering, and 8x anisotropic filtering.
- Applying any quality preset reports that MSAA requires a restart.
- After restart, the selected preset values persist.

## Front end / overlay

- F10 rows scroll at low resolution.
- Mouse hover/click still selects rows.
- Left/right arrows still change values.
- Rows that require a restart show an explicit restart-required hint.
- F10 > GAMEPLAY > Ascension front-end brand can hide/show the Ascension signature and F10 hint on file select.
- Closing F10 returns control to the game.
- Settings survive a normal close/relaunch.

## Screenshot UX

- F12 captures exactly one screenshot per key press.
- Screenshot is written under `./screenshots/`.
- Filename uses the `ascension_YYYYMMDD_HHMMSS_NNN.ppm` pattern.
- Capturing multiple screenshots in one session does not overwrite an earlier capture.

## Safety regression

- PT-BR catalog/files are unchanged.
- ROM files are unchanged.
- Save data loads normally.
- Original mission behavior remains unchanged when Ascension options are left at their defaults.
- Dam can be played for at least two minutes without stuck input or crashes.
