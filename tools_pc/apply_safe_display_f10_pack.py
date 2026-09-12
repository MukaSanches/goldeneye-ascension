#!/usr/bin/env python3
"""Expose existing low-risk video/input toggles in Ascension's F10 overlay.

UI/config-only: adds rows for options already registered by video.c/input.c.
No ROM, PT-BR assets, gameplay logic, physics, AI, or save format changes.
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

    display_anchor = '''    { .key="Video.TextureFilter",  .label="Texture filter",\n      .help="Texture sharpness and smoothing.", .category=CAT_DISPLAY,\n      .kind=ROW_ENUM, .step=1, .names=kTexFilter, .resetValue=1 },\n'''

    display_replacement = display_anchor + '''\n    { .key="Video.FixMipTextures", .label="Mipmap compatibility fix",\n      .help="Keep the port's mipmapped-texture compatibility fix enabled.", .category=CAT_DISPLAY,\n      .kind=ROW_TOGGLE, .step=1, .names=kOnOff, .resetValue=1 },\n\n    { .key="Video.WrapFix", .label="Texture wrap fix",\n      .help="Optional texture-edge compatibility fix. Leave OFF unless needed.", .category=CAT_DISPLAY,\n      .kind=ROW_TOGGLE, .step=1, .names=kOnOff, .resetValue=0 },\n'''
    text = replace_once(text, display_anchor, display_replacement,
                        "safe display compatibility rows")

    input_anchor = '''    /* INPUT */\n    { .key="Input.MouseAimSpeed",  .label="Mouse aim speed",\n'''
    input_replacement = '''    /* INPUT */\n    { .key="Input.MouseEnabled", .label="Mouse input",\n      .help="Enable or disable mouse input without changing keyboard/gamepad.", .category=CAT_INPUT,\n      .kind=ROW_TOGGLE, .step=1, .names=kOnOff, .resetValue=1 },\n\n    { .key="Input.MouseAimSpeed",  .label="Mouse aim speed",\n'''
    text = replace_once(text, input_anchor, input_replacement,
                        "mouse enabled row")

    if text == original:
        print("No changes needed.")
        return 0

    backup = PATH.with_suffix(".c.ascension-before-safe-display-pack")
    if not backup.exists():
        backup.write_text(original, encoding="utf-8")
        print(f"BACKUP: {backup.relative_to(ROOT)}")

    PATH.write_text(text, encoding="utf-8")
    print("SUCCESS: safe display/input compatibility rows added to F10.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
