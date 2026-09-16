#!/usr/bin/env python3
"""Keep Modern direct-look out of menus without disabling menu pointer input.

V3 routes menu mouse movement through GoldenEye's native front-end cursor before
the direct-look branch. The first hotfix accidentally gated that entire block.
This corrected migration removes the old guard, restores menu pointer input and
keeps only a transient gameplay-look reset. Fail-closed and idempotent.
"""
from __future__ import annotations
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "port/src/input.c"

class PatchError(RuntimeError): pass

def patch_input(text: str) -> str:
    if "ascensionControlsQueueDirectLook(edx, dyLook, aimHeld)" not in text:
        raise PatchError("Modern Controls V3 direct-look bridge is not applied")

    broken_gate = "if (mouseEnabled && !(menuMode && ascensionControlsIsModern())) {"
    if broken_gate in text:
        text = text.replace(broken_gate, "if (mouseEnabled) {", 1)

    # Remove the first-generation transient block if a local checkout already
    # applied it. It zeroed raw menu deltas and its wording incorrectly implied
    # all Modern mouse routing should be disabled in menus.
    old_guard = '''        /* Ascension V3 menu guard: Modern mouse-look is gameplay-only.
         * Entering any GoldenEye menu drops pending/smoothed camera motion so
         * no look delta can leak into folder/file selection or snap on resume. */
        if (menuMode && ascensionControlsIsModern()) {
            ascensionControlsResetTransient();
            mouseDX = mouseDY = 0.0;
            mouseSmDX = mouseSmDY = 0.0;
        }

'''
    if old_guard in text:
        text = text.replace(old_guard, "", 1)

    marker = "Ascension V3 menu guard: clear gameplay look residue only"
    if marker not in text:
        anchor = "        reconcileGrab(menuMode);\n"
        if text.count(anchor) != 1:
            raise PatchError(f"menu reconcile anchor expected once, found {text.count(anchor)}")
        guard = '''        /* Ascension V3 menu guard: clear gameplay look residue only.
         * Menu mouse movement continues into the native front-end pointer
         * branch below; direct-look is bypassed naturally by menuMode routing. */
        if (menuMode && ascensionControlsIsModern()) {
            ascensionControlsResetTransient();
            mouseSmDX = mouseSmDY = 0.0;
        }

        reconcileGrab(menuMode);
'''
        text = text.replace(anchor, guard, 1)

    if broken_gate in text or old_guard in text:
        raise PatchError("first-generation menu guard remains")
    if "if (mouseEnabled) {" not in text:
        raise PatchError("mouse block missing")
    if marker not in text:
        raise PatchError("corrected transient guard missing")
    return text

def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    original = INPUT.read_text(encoding="utf-8")
    try: patched = patch_input(original)
    except PatchError as exc: raise SystemExit(f"ERROR: {exc}; no file written")
    if args.check:
        print("Modern Controls V3 menu guard: PASS")
        print("Native absolute menu pointer: ENABLED")
        print("Gameplay direct-look residue isolation: ENABLED")
        print("Would update:", INPUT.relative_to(ROOT) if patched != original else "nothing")
        return 0
    if patched != original:
        INPUT.write_text(patched, encoding="utf-8"); print("UPDATED:", INPUT.relative_to(ROOT))
    else: print("No changes needed; corrected menu guard already applied.")
    print("Menus use mouse pointer; gameplay retains V3 direct look.")
    return 0

if __name__ == "__main__": raise SystemExit(main())
