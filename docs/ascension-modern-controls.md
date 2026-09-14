# Ascension Modern Controls v1

Ascension keeps GoldenEye's original gameplay/input path intact and layers a small PC-only control profile on top.

## Presets

`Input.ControlPreset`

- `0` — Classic: preserves the existing PC-port keyboard behaviour and disables dedicated crouch.
- `1` — Hybrid: preserves legacy keyboard fire on Left Ctrl while enabling dedicated crouch on `C`.
- `2` — Modern: enables dedicated crouch on `Left Ctrl`, `Right Ctrl`, or `C`.

The default for a new configuration is `0` (Classic). Existing saved `Input.ControlPreset` values are preserved.

`Input.DedicatedCrouch = 1` enables the dedicated crouch action for Hybrid/Modern.

## Compatibility contract

- Classic must remain behaviour-compatible with the existing PC-port controls; Ascension-specific crouch translation is inactive in this preset.
- Hybrid must keep legacy Left Ctrl fire intact; only `C` is interpreted as dedicated crouch.
- Modern may reinterpret Ctrl as dedicated crouch, but suppresses the legacy Ctrl-fire action on the same input poll so one key press cannot crouch and fire simultaneously.
- Dedicated crouch is translated back through GoldenEye's native aim-plus-stick-down gesture rather than bypassing the original crouch state machine.
- Changing presets must not alter ROM data, EEPROM/save format, mission logic, or PT-BR assets.
- Standard keyboard remapping remains owned by the existing `[Input.Bind]` configuration; Ascension does not replace that system.

Any change to this contract should pass the regression checklist in [`ascension-smoke-test.md`](ascension-smoke-test.md) before it is treated as validated.

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
