#!/usr/bin/env python3
"""Expose existing low-risk PC input tuning options in Ascension's F10 overlay.

This patch is intentionally UI/config-only. It does not change GoldenEye gameplay
logic, ROM data, PT-BR assets, or the underlying input algorithms. It only adds
rows for options already registered by port/src/input.c.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "port" / "src" / "optionsoverlay.c"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count == 0 and new in text:
        print(f"OK: {label} already applied")
        return text
    if count != 1:
        raise SystemExit(
            f"ERROR: {label}: expected exactly one anchor, found {count}; no file written"
        )
    print(f"APPLY: {label}")
    return text.replace(old, new, 1)


def main() -> int:
    original = PATH.read_text(encoding="utf-8")
    text = original

    anchor = '''    { .key="Input.MouseCaptureMode", .label="Mouse capture",\n      .help="Choose how mouse lock activates.", .category=CAT_INPUT,\n      .kind=ROW_TOGGLE, .step=1, .names=kCapture, .resetValue=1 },\n'''

    replacement = anchor + '''\n    { .key="Input.MouseRawInput", .label="Raw mouse input",\n      .help="Bypass OS pointer acceleration for aiming.", .category=CAT_INPUT,\n      .kind=ROW_TOGGLE, .step=1, .names=kOnOff, .resetValue=0 },\n\n    { .key="Input.MouseSmoothing", .label="Mouse smoothing %",\n      .help="Low-pass mouse smoothing. 0 keeps raw motion.", .category=CAT_INPUT,\n      .kind=ROW_SLIDER, .step=5, .uiMin=0, .uiMax=90, .resetValue=0 },\n\n    { .key="Input.MouseYScale", .label="Mouse Y scale %",\n      .help="Vertical mouse sensitivity relative to horizontal.", .category=CAT_INPUT,\n      .kind=ROW_SLIDER, .step=5, .uiMin=50, .uiMax=150, .resetValue=100 },\n\n    { .key="Input.HipfirePitchSpeed", .label="Hipfire pitch %",\n      .help="Vertical look response outside aim mode.", .category=CAT_INPUT,\n      .kind=ROW_SLIDER, .step=10, .uiMin=50, .uiMax=200, .resetValue=100 },\n\n    { .key="Input.PadDeadzone", .label="Gamepad deadzone",\n      .help="Left-stick deadzone. Lower is more responsive.", .category=CAT_INPUT,\n      .kind=ROW_SLIDER, .step=500, .uiMin=0, .uiMax=16000, .resetValue=7000 },\n\n    { .key="Input.PadTriggerPct", .label="Trigger threshold %",\n      .help="Trigger press point for fire/aim.", .category=CAT_INPUT,\n      .kind=ROW_SLIDER, .step=1, .uiMin=5, .uiMax=60, .resetValue=23 },\n\n    { .key="Input.PadLookInvertY", .label="Gamepad invert Y",\n      .help="Reverse vertical look on the right stick.", .category=CAT_INPUT,\n      .kind=ROW_TOGGLE, .step=1, .names=kOnOff, .resetValue=0 },\n'''

    text = replace_once(text, anchor, replacement, "safe existing input rows")

    if text == original:
        print("No changes needed.")
        return 0

    backup = PATH.with_suffix(".c.ascension-before-safe-input-pack")
    if not backup.exists():
        backup.write_text(original, encoding="utf-8")
        print(f"BACKUP: {backup.relative_to(ROOT)}")

    PATH.write_text(text, encoding="utf-8")
    print("SUCCESS: safe F10 input tuning pack applied.")
    print("No gameplay logic or ROM data changed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
