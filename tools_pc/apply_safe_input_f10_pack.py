#!/usr/bin/env python3
"""Expose validated low-risk PC input options in Ascension's F10 overlay.

This patcher is narrow and idempotent. It exposes existing input knobs and adds
one optional mouse-wheel weapon-cycle toggle. No ROM/PT-BR/gameplay state-machine
changes are made.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
OVERLAY = ROOT / "port" / "src" / "optionsoverlay.c"
INPUT = ROOT / "port" / "src" / "input.c"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count == 0 and new in text:
        print(f"OK: {label} already applied")
        return text
    if count != 1:
        raise SystemExit(f"ERROR: {label}: expected exactly one anchor, found {count}; no file written")
    print(f"APPLY: {label}")
    return text.replace(old, new, 1)


def patch_input() -> None:
    original = INPUT.read_text(encoding="utf-8")
    text = original

    text = replace_once(
        text,
        'static int wheelPulse = 0;\n',
        'static int wheelPulse = 0;\nstatic int wheelWeaponCycle = 1;  /* optional PC QoL; default preserves current behaviour */\n',
        "wheel-cycle option storage",
    )

    text = replace_once(
        text,
        '''void inputPostWheel(int notches)\n{\n    if (notches < 0) notches = -notches;   /* both directions cycle forward */\n    if (notches > 0) wheelPulse = WHEEL_PULSE_POLLS;\n}\n''',
        '''void inputPostWheel(int notches)\n{\n    if (!wheelWeaponCycle) return;\n    if (notches < 0) notches = -notches;   /* both directions cycle forward */\n    if (notches > 0) wheelPulse = WHEEL_PULSE_POLLS;\n}\n''',
        "wheel-cycle gate",
    )

    text = replace_once(
        text,
        '    configRegisterInt("Input.PadLookInvertY", &padLookInvertY, 0, 1);\n',
        '    configRegisterInt("Input.PadLookInvertY", &padLookInvertY, 0, 1);\n'
        '    configRegisterInt("Input.MouseWheelWeaponCycle", &wheelWeaponCycle, 0, 1);\n',
        "wheel-cycle config",
    )

    if text != original:
        INPUT.write_text(text, encoding="utf-8")


def patch_overlay() -> None:
    original = OVERLAY.read_text(encoding="utf-8")
    text = original

    anchor = '''    { .key="Input.MouseCaptureMode", .label="Mouse capture",\n      .help="Choose how mouse lock activates.", .category=CAT_INPUT,\n      .kind=ROW_TOGGLE, .step=1, .names=kCapture, .resetValue=1 },\n'''

    replacement = anchor + '''\n    { .key="Input.MouseWheelWeaponCycle", .label="Mouse wheel weapons",\n      .help="Use the mouse wheel to cycle weapons.", .category=CAT_INPUT,\n      .kind=ROW_TOGGLE, .step=1, .names=kOnOff, .resetValue=1 },\n\n    { .key="Input.MouseRawInput", .label="Raw mouse input",\n      .help="Bypass OS pointer acceleration for aiming.", .category=CAT_INPUT,\n      .kind=ROW_TOGGLE, .step=1, .names=kOnOff, .resetValue=0 },\n\n    { .key="Input.MouseSmoothing", .label="Mouse smoothing %",\n      .help="Low-pass mouse smoothing. 0 keeps raw motion.", .category=CAT_INPUT,\n      .kind=ROW_SLIDER, .step=5, .uiMin=0, .uiMax=90, .resetValue=0 },\n\n    { .key="Input.MouseYScale", .label="Mouse Y scale %",\n      .help="Vertical mouse sensitivity relative to horizontal.", .category=CAT_INPUT,\n      .kind=ROW_SLIDER, .step=5, .uiMin=50, .uiMax=150, .resetValue=100 },\n\n    { .key="Input.AimBand", .label="Aim response band",\n      .help="Fine aim response range above GoldenEye's native gate.", .category=CAT_INPUT,\n      .kind=ROW_SLIDER, .step=1, .uiMin=5, .uiMax=40, .resetValue=20 },\n\n    { .key="Input.HipfirePitchSpeed", .label="Hipfire pitch %",\n      .help="Vertical look response outside aim mode.", .category=CAT_INPUT,\n      .kind=ROW_SLIDER, .step=10, .uiMin=50, .uiMax=200, .resetValue=100 },\n\n    { .key="Input.MenuPointerSpeed", .label="Menu pointer speed %",\n      .help="Mouse pointer speed in menus and briefings.", .category=CAT_INPUT,\n      .kind=ROW_SLIDER, .step=10, .uiMin=50, .uiMax=200, .resetValue=100 },\n\n    { .key="Input.MenuPointerMode", .label="Direct menu pointer",\n      .help="Use the modern 1:1 menu-pointer controller.", .category=CAT_INPUT,\n      .kind=ROW_TOGGLE, .step=1, .names=kOnOff, .resetValue=1 },\n\n    { .key="Input.PadDeadzone", .label="Gamepad deadzone",\n      .help="Left-stick deadzone. Lower is more responsive.", .category=CAT_INPUT,\n      .kind=ROW_SLIDER, .step=500, .uiMin=0, .uiMax=16000, .resetValue=7000 },\n\n    { .key="Input.PadTriggerPct", .label="Trigger threshold %",\n      .help="Trigger press point for fire/aim.", .category=CAT_INPUT,\n      .kind=ROW_SLIDER, .step=1, .uiMin=5, .uiMax=60, .resetValue=23 },\n\n    { .key="Input.PadLookInvertY", .label="Gamepad invert Y",\n      .help="Reverse vertical look on the right stick.", .category=CAT_INPUT,\n      .kind=ROW_TOGGLE, .step=1, .names=kOnOff, .resetValue=0 },\n'''

    text = replace_once(text, anchor, replacement, "safe existing input rows + wheel toggle")
    if text != original:
        OVERLAY.write_text(text, encoding="utf-8")


def main() -> int:
    patch_input()
    patch_overlay()
    print("SUCCESS: safe F10 input tuning pack applied.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
