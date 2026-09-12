# Ascension Modern Controls v1

Ascension keeps GoldenEye's original gameplay/input path intact and layers a small PC-only control profile on top.

## Presets

`Input.ControlPreset`

- `0` — Classic: preserves the existing PC-port keyboard behaviour and disables dedicated crouch.
- `1` — Hybrid: preserves legacy keyboard fire on Left Ctrl while enabling dedicated crouch on `C`.
- `2` — Modern: enables dedicated crouch on `Left Ctrl`, `Right Ctrl`, or `C`.

`Input.DedicatedCrouch = 1` enables the dedicated crouch action for Hybrid/Modern.

## Design rules

- Original N64 control logic remains the authority for movement, aiming, weapons and crouch restrictions.
- Dedicated crouch is PC-only and still respects `WEAPONSTATBITFLAG_DISABLE_CROUCH`.
- Existing mouse/gamepad/rebinding configuration remains valid.
- No ROM, PT-BR catalogue, graphics sidecar or translated asset is touched by this feature.

## Modern baseline

- WASD: movement/strafe
- Mouse: look
- Left mouse: fire
- Right mouse: aim
- E / Space / Z: action
- R / X / F: cancel/reload behaviour already provided by GoldenEye's control path
- Ctrl or C: dedicated crouch
- Mouse wheel: weapon cycle

The existing `[Input.Bind]` configuration remains the source of keyboard remapping for standard actions.
