#!/usr/bin/env python3
"""Keep Modern direct-look out of menus without disabling menu pointer input.

V3 already routes menu mouse movement through GoldenEye's front-end cursor before
its direct-look branch. The original hotfix accidentally gated the entire mouse
block in Modern menus, which also removed the absolute pointer path. This
corrected guard is fail-closed and idempotent: it clears gameplay look residue
on menu entry while explicitly restoring the normal `if (mouseEnabled)` block.
"""
from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "port" / "src" / "input.c"


class PatchError(RuntimeError):
    pass


def patch_input(text: str) -> str:
    if "ascensionControlsQueueDirectLook(edx, dyLook, aimHeld)" not in text:
        raise PatchError("Modern Controls V3 direct-look bridge is not applied")

    # Repair checkouts that received the first menu-guard hotfix. The menu
    # branch inside this block is the pointer implementation; never gate it.
    broken = "if (mouseEnabled && !(menuMode && ascensionControlsIsModern())) {"
    if broken in text:
        text = text.replace(broken, "if (mouseEnabled) {", 1)

    # Add the transient reset once. It prevents gameplay look deltas from
    # snapping after leaving a menu but does not consume menu pointer motion.
    marker = "Ascension V3 menu guard: clear gameplay look residue only"
    if marker not in text:
        anchor = "        reconcileGrab(menuMode);\n"
        if text.count(anchor) != 1:
            raise PatchError(f"menu reconcile anchor expected once, found {text.count(anchor)}")
        guard = """        /* Ascension V3 menu guard: clear gameplay look residue only.\n         * Menu mouse movement must continue into the native front-end pointer\n         * branch below; direct-look is already bypassed by menuMode routing. */\n        if (menuMode && ascensionControlsIsModern()) {\n            ascensionControlsResetTransient();\n            mouseSmDX = mouseSmDY = 0.0;\n        }\n\n        reconcileGrab(menuMode);\n"""
        text = text.replace(anchor, guard, 1)

    if broken in text:
        raise PatchError("broken Modern menu-wide mouse gate remains")
    if "if (mouseEnabled) {" not in text:
        raise PatchError("mouse input block missing")
    if marker not in text:
        raise PatchError("transient-only menu guard missing")
    return text


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    original = INPUT.read_text(encoding="utf-8")
    try:
        patched = patch_input(original)
    except PatchError as exc:
        raise SystemExit(f"ERROR: {exc}; no file written")

    if args.check:
        print("Modern Controls V3 menu guard: PASS")
        print("Menu pointer path: ENABLED")
        print("Direct-look residue reset: ENABLED")
        print("Would update:", INPUT.relative_to(ROOT) if patched != original else "nothing")
        return 0

    if patched != original:
        INPUT.write_text(patched, encoding="utf-8")
        print("UPDATED:", INPUT.relative_to(ROOT))
    else:
        print("No changes needed; corrected menu guard already applied.")
    print("GoldenEye menus keep absolute mouse navigation; gameplay look remains isolated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
