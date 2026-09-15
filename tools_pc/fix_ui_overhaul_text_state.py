#!/usr/bin/env python3
"""Repair the Ascension UI Overhaul v1 text render state.

The first dossier renderer drew the active Q-Branch sidebar background from
inside drawCategoryTabs(), after the display list had already switched into the
text microcode state. fillRect() changes combine/render state, so subsequent
text glyphs were emitted as solid quads on real hardware/backends even though
headless compile/contracts passed.

This hotfix keeps *all* primitive rectangles in the geometry phase, then calls
microcode_constructor(), and makes drawCategoryTabs() text-only.  It is
fail-closed and idempotent and does not touch gameplay/save/mission logic.
"""
from pathlib import Path
import argparse

ROOT = Path(__file__).resolve().parents[1]
OV = ROOT / "port/src/optionsoverlay.c"


class PatchError(RuntimeError):
    pass


OLD_TABS = '''static Gfx *drawCategoryTabs(Gfx *gdl, int active)
{
    for (int cat = CAT_DISPLAY; cat <= CAT_SYSTEM; ++cat) {
        s32 y = OV_SIDE_Y0 + cat * OV_SIDE_STEP;
        u32 col = cat == active ? ASC_UI_IVORY : ASC_UI_SLATE;
        if (cat == active) {
            gdl = fillRect(gdl, OV_SIDE_X0, y - 4, OV_SIDE_X1, y + 24,
                           25, 25, 22, 232);
            gdl = fillRect(gdl, OV_SIDE_X0, y - 4, OV_SIDE_X0 + 2, y + 24,
                           214, 184, 95, 255);
        }
        gdl = drawText(gdl, OV_SIDE_X0 + 8, y, categoryName(cat), col);
        gdl = drawText(gdl, OV_SIDE_X0 + 8, y + 11,
                       categorySub(cat), cat == active ? ASC_UI_GOLD_DIM : 0x666A67FFu);
    }
    return gdl;
}'''

NEW_TABS = '''static Gfx *drawCategoryTabs(Gfx *gdl, int active)
{
    /* Text-only by design.  All rectangles are emitted before
     * microcode_constructor() so text state can never be dirtied mid-pass. */
    for (int cat = CAT_DISPLAY; cat <= CAT_SYSTEM; ++cat) {
        s32 y = OV_SIDE_Y0 + cat * OV_SIDE_STEP;
        u32 col = cat == active ? ASC_UI_IVORY : ASC_UI_SLATE;
        gdl = drawText(gdl, OV_SIDE_X0 + 8, y, categoryName(cat), col);
        gdl = drawText(gdl, OV_SIDE_X0 + 8, y + 11,
                       categorySub(cat), cat == active ? ASC_UI_GOLD_DIM : 0x666A67FFu);
    }
    return gdl;
}'''

SHAPE_ANCHOR = '''    gdl = microcode_constructor(gdl);

    /* Header. */'''

SHAPE_BLOCK = '''    /* Active Q-Branch department highlight.  Geometry must be complete before
     * the text microcode is restored; never call fillRect() from a text pass. */
    {
        s32 sy = OV_SIDE_Y0 + activeCat * OV_SIDE_STEP;
        gdl = fillRect(gdl, OV_SIDE_X0, sy - 4, OV_SIDE_X1, sy + 24,
                       25, 25, 22, 232);
        gdl = fillRect(gdl, OV_SIDE_X0, sy - 4, OV_SIDE_X0 + 2, sy + 24,
                       214, 184, 95, 255);
    }

    gdl = microcode_constructor(gdl);

    /* Header. */'''

MARKER = "Text-only by design.  All rectangles are emitted before"


def patch(text: str) -> str:
    if "Q BRANCH SYSTEMS" not in text or "CAT_SYSTEM" not in text:
        raise PatchError("Ascension UI Overhaul v1 is not applied")

    # Repair the known bad renderer.  A source already repaired simply skips it.
    if OLD_TABS in text:
        text = text.replace(OLD_TABS, NEW_TABS, 1)
    elif MARKER not in text:
        raise PatchError("unexpected drawCategoryTabs implementation")

    if SHAPE_BLOCK not in text:
        if text.count(SHAPE_ANCHOR) != 1:
            raise PatchError(
                f"text-state insertion anchor expected once, found {text.count(SHAPE_ANCHOR)}"
            )
        text = text.replace(SHAPE_ANCHOR, SHAPE_BLOCK, 1)

    # Strong postconditions: no geometry in category text pass; geometry before
    # header text; only text calls remain inside drawCategoryTabs.
    start = text.find("static Gfx *drawCategoryTabs")
    end = text.find("\n}\n", start)
    if start < 0 or end < 0:
        raise PatchError("drawCategoryTabs not found after repair")
    tabs = text[start:end + 3]
    if "fillRect(" in tabs:
        raise PatchError("fillRect still present inside drawCategoryTabs")
    if MARKER not in tabs:
        raise PatchError("text-only category renderer marker missing")
    if text.find("Active Q-Branch department highlight") > text.find("/* Header. */"):
        raise PatchError("sidebar geometry is not before text header")

    return text


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    original = OV.read_text(encoding="utf-8")
    try:
        repaired = patch(original)
    except PatchError as exc:
        raise SystemExit(f"ERROR: {exc}; no file written")

    if args.check:
        print("Ascension UI text-state repair: PASS")
        print("Sidebar geometry before text microcode: PASS")
        print("Category renderer text-only: PASS")
        print("Would update:", OV.relative_to(ROOT) if repaired != original else "nothing")
        return 0

    if repaired != original:
        OV.write_text(repaired, encoding="utf-8")
        print("UPDATED:", OV.relative_to(ROOT))
    else:
        print("No changes needed; text-state repair already applied.")

    print("Q Branch text rendering state is isolated from rectangle primitives.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
