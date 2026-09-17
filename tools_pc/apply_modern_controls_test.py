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

    old = '''        if ((mb & SDL_BUTTON(SDL_BUTTON_LEFT)) || actHeld(ks, IA_FIRE))
            button |= GE_CONT_G;
        int aimHeld = (mb & SDL_BUTTON(SDL_BUTTON_RIGHT)) || actHeld(ks, IA_AIM);
        if (aimHeld)
            button |= GE_CONT_R;
'''
    new = '''        /* Ascension Modern Controls v1: dedicated crouch is translated into
         * GoldenEye's native 1.1 aim+stick-down gesture. This deliberately
         * keeps bondview2.c as the gameplay authority, so weapon crouch
         * restrictions and the original crouch state machine remain intact. */
        int dedicatedCrouch = !menuMode && ascensionControlsDedicatedCrouchHeld();

        /* In Modern, Left Ctrl is a crouch key. Do not also emit the legacy
         * keyboard-fire binding on the same poll. LMB remains fire. Hybrid's
         * crouch key is C, therefore legacy Left Ctrl fire is unaffected. */
        if ((mb & SDL_BUTTON(SDL_BUTTON_LEFT)) ||
            (actHeld(ks, IA_FIRE) && !dedicatedCrouch))
            button |= GE_CONT_G;

        int aimHeld = (mb & SDL_BUTTON(SDL_BUTTON_RIGHT)) ||
                      actHeld(ks, IA_AIM) || dedicatedCrouch;
        if (aimHeld)
            button |= GE_CONT_R;

        if (dedicatedCrouch)
            sy = -STICK_MAX;
'''
    text = replace_once(text, old, new, "dedicated crouch native-input bridge")

    old = '''                if (fabs(dyLook) >= AIM_MOVE_THRESH) {
                    int m = 61 + (int)gy; if (m > 60 + aimBand) m = 60 + aimBand;
                    sy += (dyLook > 0) ? m : -m;   /* +stick_y = look down */
                }
'''
    new = '''                /* Dedicated crouch owns stick-Y while held: preserve the
                 * native aim+stick-down gesture even if the mouse moves
                 * vertically. Mouse-X remains available for horizontal aim. */
                if (!dedicatedCrouch && fabs(dyLook) >= AIM_MOVE_THRESH) {
                    int m = 61 + (int)gy; if (m > 60 + aimBand) m = 60 + aimBand;
                    sy += (dyLook > 0) ? m : -m;   /* +stick_y = look down */
                }
'''
    text = replace_once(text, old, new, "dedicated crouch mouse-Y isolation")

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
