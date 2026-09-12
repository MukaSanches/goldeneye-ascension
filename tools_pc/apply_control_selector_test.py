#!/usr/bin/env python3
"""Add the Ascension Modern Controls selector to the F10 control center.

Narrow, idempotent test patcher. It only edits port/src/optionsoverlay.c and
refuses to write if expected anchors are missing or ambiguous.
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

    text = replace_once(
        text,
        'static const char *const kCapture[]   = { "ALWAYS GRAB", "CLICK-TO-LOCK", NULL };\n',
        'static const char *const kCapture[]   = { "ALWAYS GRAB", "CLICK-TO-LOCK", NULL };\n'
        'static const char *const kControlPreset[] = { "CLASSIC", "HYBRID", "MODERN", NULL };\n',
        "control preset names",
    )

    anchor = '''    /* INPUT */\n    { .key="Input.MouseAimSpeed",  .label="Mouse aim speed",\n'''
    replacement = '''    /* INPUT */\n    { .key="Input.ControlPreset", .label="Control preset",\n      .help="Classic, Hybrid or Modern PC controls.", .category=CAT_INPUT,\n      .kind=ROW_ENUM, .step=1, .names=kControlPreset, .resetValue=2 },\n\n    { .key="Input.DedicatedCrouch", .label="Dedicated crouch",\n      .help="Enable the Ascension crouch shortcut for Hybrid/Modern.", .category=CAT_INPUT,\n      .kind=ROW_TOGGLE, .step=1, .names=kOnOff, .resetValue=1 },\n\n    { .key="Input.MouseAimSpeed",  .label="Mouse aim speed",\n'''
    text = replace_once(text, anchor, replacement, "F10 control rows")

    if text == original:
        print("No changes needed.")
        return 0

    backup = PATH.with_suffix(".c.ascension-before-control-selector")
    if not backup.exists():
        backup.write_text(original, encoding="utf-8")
        print(f"BACKUP: {backup.relative_to(ROOT)}")

    PATH.write_text(text, encoding="utf-8")
    print("SUCCESS: in-game control selector added to F10.")
    print("F10 > INPUT > Control preset: CLASSIC / HYBRID / MODERN")
    print("F10 > INPUT > Dedicated crouch: OFF / ON")
    return 0


if __name__ == "__main__":
    sys.exit(main())
