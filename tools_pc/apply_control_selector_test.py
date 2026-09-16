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

    # The insertion intentionally keeps kCapture, so key idempotence off the
    # symbol we add rather than off the retained anchor.
    if "static const char *const kControlPreset[]" in text:
        print("OK: control preset names already applied")
    else:
        text = replace_once(
            text,
            'static const char *const kCapture[]   = { "ALWAYS GRAB", "CLICK-TO-LOCK", NULL };\n',
            'static const char *const kCapture[]   = { "ALWAYS GRAB", "CLICK-TO-LOCK", NULL };\n'
            'static const char *const kControlPreset[] = { "CLASSIC", "HYBRID", "MODERN", NULL };\n',
            "control preset names",
        )

    # Later patchers are allowed to insert additional INPUT rows around these
    # entries. Presence of both owned config keys is the stable proof that this
    # patch has already been applied; requiring the original adjacency would
    # make a second pack run fail or duplicate rows.
    if ' .key="Input.ControlPreset"' in text and ' .key="Input.DedicatedCrouch"' in text:
        print("OK: F10 control rows already applied")
    else:
        anchor = '''    /* INPUT */\n    { .key="Input.MouseAimSpeed",  .label="Mouse aim speed",\n'''
        replacement = '''    /* INPUT */\n    { .key="Input.ControlPreset", .label="Control preset",\n      .help="Classic, Hybrid or Modern PC controls.", .category=CAT_INPUT,\n      .kind=ROW_ENUM, .step=1, .names=kControlPreset, .resetValue=0 },\n\n    { .key="Input.DedicatedCrouch", .label="Dedicated crouch",\n      .help="Enable the Ascension crouch shortcut for Hybrid/Modern.", .category=CAT_INPUT,\n      .kind=ROW_TOGGLE, .step=1, .names=kOnOff, .resetValue=1 },\n\n    { .key="Input.MouseAimSpeed",  .label="Mouse aim speed",\n'''
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
