#!/usr/bin/env python3
"""Disable Modern mouse-look while GoldenEye menus are active.

This is a narrow, fail-closed hotfix for Ascension Modern Controls V3.
It intentionally leaves Classic/Hybrid menu behavior untouched.

Run after apply_modern_controls_v2.py and apply_modern_controls_v3.py.
The patch is idempotent.
"""
from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "port" / "src" / "input.c"


class PatchError(RuntimeError):
    pass


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        return text
    count = text.count(old)
    if count != 1:
        raise PatchError(f"{label}: expected exactly one anchor, found {count}")
    return text.replace(old, new, 1)


def patch_input(text: str) -> str:
    # V3 must already be present. This prevents accidentally patching a stale
    # or unrelated checkout with a superficially similar mouse block.
    if "ascensionControlsQueueDirectLook(edx, dyLook, aimHeld)" not in text:
        raise PatchError("Modern Controls V3 direct-look bridge is not applied")

    old_reset = """        reconcileGrab(menuMode);\n"""
    new_reset = """        /* Ascension V3 menu guard: Modern mouse-look is gameplay-only.\n         * Entering any GoldenEye menu drops pending/smoothed camera motion so\n         * no look delta can leak into folder/file selection or snap on resume. */\n        if (menuMode && ascensionControlsIsModern()) {\n            ascensionControlsResetTransient();\n            mouseDX = mouseDY = 0.0;\n            mouseSmDX = mouseSmDY = 0.0;\n        }\n\n        reconcileGrab(menuMode);\n"""
    text = replace_once(text, old_reset, new_reset, "Modern menu transient guard")

    old_mouse = """        /* Mouse-look. Mode-dependent (see the tuning-constants comment):\n         *   aim mode  -> push the analog stick past +/-60 for proportional\n         *                yaw + pitch; emit NO C-buttons (they mean crouch here).\n         *   hipfire   -> yaw on analog stick-X; pitch on digital C-up/C-down.\n         * \"look down\" convention: mouse-down looks down by default; GE's\n         * native pitch is inverted so hipfire down = C-up (GE_CONT_E) and\n         * aim-mode down = +stick_y. MouseInvertY flips both. */\n        if (mouseEnabled) {\n"""
    new_mouse = """        /* Mouse-look. Mode-dependent (see the tuning-constants comment):\n         *   aim mode  -> push the analog stick past +/-60 for proportional\n         *                yaw + pitch; emit NO C-buttons (they mean crouch here).\n         *   hipfire   -> yaw on analog stick-X; pitch on digital C-up/C-down.\n         * \"look down\" convention: mouse-down looks down by default; GE's\n         * native pitch is inverted so hipfire down = C-up (GE_CONT_E) and\n         * aim-mode down = +stick_y. MouseInvertY flips both.\n         *\n         * Ascension V3 menu guard: Modern never routes mouse motion through\n         * either the direct-look or legacy-look path while a menu is active.\n         * Keyboard/gamepad menu navigation remains native and unchanged. */\n        if (mouseEnabled && !(menuMode && ascensionControlsIsModern())) {\n"""
    text = replace_once(text, old_mouse, new_mouse, "Modern menu mouse-look guard")

    return text


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="validate without writing")
    args = parser.parse_args()

    original = INPUT.read_text(encoding="utf-8")
    try:
        patched = patch_input(original)
    except PatchError as exc:
        raise SystemExit(f"ERROR: {exc}; no file written")

    required = [
        "Ascension V3 menu guard",
        "mouseEnabled && !(menuMode && ascensionControlsIsModern())",
        "ascensionControlsResetTransient();",
        "mouseDX = mouseDY = 0.0;",
        "mouseSmDX = mouseSmDY = 0.0;",
    ]
    for needle in required:
        if needle not in patched:
            raise SystemExit(f"ERROR: validation failed: missing {needle!r}; no file written")

    if args.check:
        print("Modern Controls V3 menu guard: PASS")
        print("Would update:", INPUT.relative_to(ROOT) if patched != original else "nothing (already applied)")
        return 0

    if patched != original:
        INPUT.write_text(patched, encoding="utf-8")
        print("UPDATED:", INPUT.relative_to(ROOT))
    else:
        print("No changes needed; Modern menu guard already applied.")

    print("Modern mouse-look is now disabled in GoldenEye menus.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
