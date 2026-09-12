# Ascension gameplay smoke test

Run this after any input, F10, video, locale, or gameplay-facing change.

## Boot

- Build completes without linker/compiler errors.
- Game reaches file select.
- F10 opens and closes cleanly.

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

## Front end / overlay

- F10 rows scroll at low resolution.
- Mouse hover/click still selects rows.
- Left/right arrows still change values.
- Closing F10 returns control to the game.
- Settings survive a normal close/relaunch.

## Safety regression

- PT-BR catalog/files are unchanged.
- ROM files are unchanged.
- Save data loads normally.
- Dam can be played for at least two minutes without stuck input or crashes.
