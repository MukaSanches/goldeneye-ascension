# GoldenEye Ascension controls

This note documents the Ascension-specific keyboard control behavior on `ascension-modern-controls-v1`. It does not replace GoldenEye's original controls and does not change save or ROM compatibility.

## Control presets

Ascension exposes three PC-side control presets:

| Preset | Behavior |
|---|---|
| `CLASSIC` | Original GoldenEye PC-port behavior. Ascension's dedicated crouch bridge is disabled. |
| `HYBRID` | Keeps the legacy keyboard fire mapping on `Left Ctrl` and adds dedicated crouch on `C`. |
| `MODERN` | Enables dedicated crouch on `Left Ctrl`, `Right Ctrl`, or `C`. |

`CLASSIC` is the default preset so existing players keep the original behavior unless they explicitly select an Ascension preset.

## Dedicated crouch

`Input.DedicatedCrouch` is an on/off Ascension option. Even when enabled, it has no effect while the `CLASSIC` preset is selected.

For manual regression testing:

1. Select `CLASSIC` and confirm `C`/Ctrl do not invoke the Ascension dedicated-crouch bridge.
2. Select `HYBRID` and confirm `C` crouches while `Left Ctrl` remains available for legacy fire.
3. Select `MODERN` and confirm `C`, `Left Ctrl`, and `Right Ctrl` can invoke dedicated crouch.
4. Disable dedicated crouch and confirm none of the presets invoke the Ascension crouch bridge.

The implementation lives in `port/src/ascension_controls.c`. Static regression checks live in `tools_pc/verify_ascension_contracts.py`.

## Manual `ge007.ini` fallback

If the in-game options overlay is unavailable while testing, the same Ascension controls can be configured directly in `ge007.ini`:

```ini
[Input]
ControlPreset = 0
DedicatedCrouch = 1
```

`ControlPreset` accepts `0 = CLASSIC`, `1 = HYBRID`, or `2 = MODERN`. `DedicatedCrouch` accepts `0 = OFF` or `1 = ON`. These values are registered as bounded integer options, so out-of-range values are clamped when the configuration is loaded.

## Automated verification

Before committing control-related changes, run the ROM-free Ascension checks from the repository root:

```sh
python3 tools_pc/verify_ascension_contracts.py
python3 tools_pc/test_ascension_patchers.py
```

Both commands should finish with `PASS`. These checks do not replace an in-game smoke test, but they catch accidental regressions in the preset ranges, dedicated-crouch mappings, PT-BR control strings, patcher preflight, and repository hygiene without requiring a ROM.

## Compatibility rules

Ascension control options are intentionally PC-side and opt-in. Changes in this area should preserve:

- the requirement for a user-supplied GoldenEye 007 ROM;
- existing save compatibility;
- PT-BR localization work;
- original GoldenEye behavior under `CLASSIC`;
- the legacy `Left Ctrl` fire mapping under `HYBRID`.
