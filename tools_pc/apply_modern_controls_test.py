#!/usr/bin/env python3
"""Apply the temporary Ascension Modern Controls v1 integration for local testing.

This patcher is intentionally narrow and idempotent. It touches only
port/src/input.c and refuses to write if the expected upstream anchors are not
present exactly once. The permanent integration can be committed after the
Windows/MSYS2 gameplay test passes.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "port" / "src" / "input.c"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count == 0 and new in text:
        print(f"OK: {label} already applied")
        return text
    if count != 1:
        raise SystemExit(f"ERROR: {label}: expected exactly one anchor, found {count}; no file written")
    print(f"APPLY: {label}")
    return text.replace(old, new, 1)


def main() -> int:
    original = PATH.read_text(encoding="utf-8")
    text = original

    # This is an insertion that deliberately retains its anchor. Test the
    # inserted include itself first, otherwise a second run would duplicate it.
    if '#include "ascension_controls.h"\n' in text:
        print("OK: Ascension controls include already applied")
    else:
        text = replace_once(
            text,
            '#include "optionsoverlay.h"\n',
            '#include "optionsoverlay.h"\n#include "ascension_controls.h"\n',
            "Ascension controls include",
        )

    old = '''        if ((mb & SDL_BUTTON(SDL_BUTTON_LEFT)) || actHeld(ks, IA_FIRE))\n            button |= GE_CONT_G;\n        int aimHeld = (mb & SDL_BUTTON(SDL_BUTTON_RIGHT)) || actHeld(ks, IA_AIM);\n        if (aimHeld)\n            button |= GE_CONT_R;\n'''
    new = '''        /* Ascension Modern Controls v1: dedicated crouch is translated into\n         * GoldenEye's native 1.1 aim+stick-down gesture. This deliberately\n         * keeps bondview2.c as the gameplay authority, so weapon crouch\n         * restrictions and the original crouch state machine remain intact. */\n        int dedicatedCrouch = !menuMode && ascensionControlsDedicatedCrouchHeld();\n\n        /* In Modern, Left Ctrl is a crouch key. Do not also emit the legacy\n         * keyboard-fire binding on the same poll. LMB remains fire. Hybrid's\n         * crouch key is C, therefore legacy Left Ctrl fire is unaffected. */\n        if ((mb & SDL_BUTTON(SDL_BUTTON_LEFT)) ||\n            (actHeld(ks, IA_FIRE) && !dedicatedCrouch))\n            button |= GE_CONT_G;\n\n        int aimHeld = (mb & SDL_BUTTON(SDL_BUTTON_RIGHT)) ||\n                      actHeld(ks, IA_AIM) || dedicatedCrouch;\n        if (aimHeld)\n            button |= GE_CONT_R;\n\n        if (dedicatedCrouch)\n            sy = -STICK_MAX;\n'''
    text = replace_once(text, old, new, "dedicated crouch native-input bridge")

    if text == original:
        print("No changes needed.")
        return 0

    backup = PATH.with_suffix(".c.ascension-before-modern-controls")
    if not backup.exists():
        backup.write_text(original, encoding="utf-8")
        print(f"BACKUP: {backup.relative_to(ROOT)}")

    PATH.write_text(text, encoding="utf-8")
    print("SUCCESS: Ascension Modern Controls v1 test integration applied.")
    print("Modified: port/src/input.c")
    return 0


if __name__ == "__main__":
    sys.exit(main())
