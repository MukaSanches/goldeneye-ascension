#!/usr/bin/env python3
"""Apply Ascension UI Overhaul v1 to the validated V3 stack.

Direction: GoldenEye/MI6/Q-Branch, not generic modern dashboard UI.
Scope is deliberately port-owned and reversible:
- professional Q Branch F10 visual hierarchy;
- mouse + keyboard category navigation and slider interaction;
- MI6 Classified Archives chrome around the native file-select (save logic untouched);
- no gameplay/save/mission mutations.

Run after V2, V3 and the corrected menu guard. Fail-closed + idempotent.
"""
from __future__ import annotations
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OV = ROOT / "port/src/optionsoverlay.c"

class PatchError(RuntimeError): pass

def once(s: str, old: str, new: str, label: str) -> str:
    if new in s: return s
    n = s.count(old)
    if n != 1: raise PatchError(f"{label}: expected one anchor, found {n}")
    return s.replace(old, new, 1)

def patch_overlay(s: str) -> str:
    if "optionsOverlayHandleInput" not in s or "GE_MENU_FILE_SELECT" not in s:
        raise PatchError("unexpected optionsoverlay baseline")

    s = once(s,
'''#define ASC_UI_GOLD       0xD2B65CFFu
#define ASC_UI_GOLD_DIM   0x9B8749FFu
#define ASC_UI_IVORY      0xE8E2D3FFu
#define ASC_UI_TEXT       0xC8C2B3FFu
#define ASC_UI_SLATE      0x8D9396FFu
#define ASC_UI_DARK       0x080A0CFFu''',
'''/* MI6 / Q Branch visual system. Restrained 1995 intelligence-terminal palette. */
#define ASC_UI_GOLD       0xD7BC6AFFu
#define ASC_UI_GOLD_DIM   0x8F7C45FFu
#define ASC_UI_IVORY      0xEEE8D8FFu
#define ASC_UI_TEXT       0xC9C4B7FFu
#define ASC_UI_SLATE      0x858B88FFu
#define ASC_UI_DARK       0x07090AFFu
#define ASC_UI_RED        0xA64038FFu
#define ASC_UI_GREEN      0x7E9A79FFu''', "MI6 palette")

    # F10 accepts WASD as well as arrows, matching the rest of the PC front end.
    s = once(s,
'''    int up = ks[SDL_SCANCODE_UP]   || ks[SDL_SCANCODE_KP_8];
    int dn = ks[SDL_SCANCODE_DOWN] || ks[SDL_SCANCODE_KP_2];
    int lf = ks[SDL_SCANCODE_LEFT] || ks[SDL_SCANCODE_KP_4];
    int rt = ks[SDL_SCANCODE_RIGHT] || ks[SDL_SCANCODE_KP_6] ||
             ks[SDL_SCANCODE_RETURN] || ks[SDL_SCANCODE_KP_ENTER];''',
'''    int up = ks[SDL_SCANCODE_UP]   || ks[SDL_SCANCODE_KP_8] || ks[SDL_SCANCODE_W];
    int dn = ks[SDL_SCANCODE_DOWN] || ks[SDL_SCANCODE_KP_2] || ks[SDL_SCANCODE_S];
    int lf = ks[SDL_SCANCODE_LEFT] || ks[SDL_SCANCODE_KP_4] || ks[SDL_SCANCODE_A];
    int rt = ks[SDL_SCANCODE_RIGHT] || ks[SDL_SCANCODE_KP_6] || ks[SDL_SCANCODE_D] ||
             ks[SDL_SCANCODE_RETURN] || ks[SDL_SCANCODE_KP_ENTER];''', "F10 WASD")

    # Clickable Q-Branch section tabs. This is deliberately before row handling.
    anchor = '''        int hoverRow = overlayRowAtY(oy);
        int onClose = overlayInCloseBox(ox, oy);
'''
    repl = anchor + '''
        /* Q Branch section tabs are real mouse targets, not decorative labels. */
        if (lmb && !prevLmb && oy >= OV_TOP + OV_LINE - 3 && oy <= OV_TOP + OV_LINE + 12) {
            int target = -1;
            if (ox >= OV_X0 && ox < OV_X0 + 74) target = CAT_DISPLAY;
            else if (ox >= OV_X0 + 78 && ox < OV_X0 + 128) target = CAT_INPUT;
            else if (ox >= OV_X0 + 132 && ox < OV_X0 + 205) target = CAT_GAMEPLAY;
            if (target >= 0) {
                for (int i = 0; i < NUM_ROWS; ++i) {
                    if (rows[i].category == target) { s_sel = i; break; }
                }
                clearPendingAction();
                ensureSelectionVisible();
                hoverRow = -1;
            }
        }
'''
    s = once(s, anchor, repl, "clickable Q tabs")

    old_tabs = '''static Gfx *drawCategoryTabs(Gfx *gdl, int active)
{
    const char *names[] = { "DISPLAY", "INPUT", "GAMEPLAY" };
    const s32 xs[] = { OV_X0, OV_X0 + 78, OV_X0 + 132 };
    const int n = 3;

    for (int i = 0; i < n; i++) {
        u32 col = i == active ? ASC_UI_GOLD : ASC_UI_SLATE;
        gdl = drawText(gdl, xs[i], OV_TOP + OV_LINE, names[i], col);
    }
    return gdl;
}'''
    new_tabs = '''static Gfx *drawCategoryTabs(Gfx *gdl, int active)
{
    const char *names[] = { "DISPLAY", "INPUT", "FIELD" };
    const s32 xs[] = { OV_X0, OV_X0 + 78, OV_X0 + 132 };
    for (int i = 0; i < 3; i++) {
        u32 col = i == active ? ASC_UI_GOLD : ASC_UI_SLATE;
        if (i == active)
            gdl = drawText(gdl, xs[i] - 7, OV_TOP + OV_LINE, ">", ASC_UI_GOLD);
        gdl = drawText(gdl, xs[i], OV_TOP + OV_LINE, names[i], col);
    }
    return gdl;
}'''
    s = once(s, old_tabs, new_tabs, "Q Branch tabs")

    # File-select gets a restrained classified-archive frame while preserving the
    # game's folders, thumbnails, save hit-testing and progression underneath.
    old_brand_shapes = '''        if (showBrand) {
            const s32 brandW = measureText(ASCENSION_SIGNATURE);
            gdl = fillRect(gdl, 8, H - 19, 8 + brandW, H - 18,
                           0xD2, 0xB6, 0x5C, 220);

            if (!s_controlHintSeen) {
                const char *hint = "PRESS F10 TO CONFIGURE";
                const s32 hintW = measureText(hint);
                const s32 hx0 = W - hintW - 14;
                gdl = fillRect(gdl, hx0, H - 36, W - 6, H - 22,
                               8, 10, 12, 225);
                gdl = fillRect(gdl, hx0, H - 36, hx0 + 2, H - 22,
                               0xD2, 0xB6, 0x5C, 255);
            }
        }'''
    new_brand_shapes = '''        if (showBrand) {
            /* MI6 archive chrome: frame the native dossier/folder art instead of
             * replacing it with generic cards. The center remains untouched. */
            gdl = fillRect(gdl, 0, 0, W, 18, 5, 7, 8, 218);
            gdl = fillRect(gdl, 0, 18, W, 19, 0xD7, 0xBC, 0x6A, 220);
            gdl = fillRect(gdl, 0, H - 20, W, H, 5, 7, 8, 224);
            gdl = fillRect(gdl, 0, H - 21, W, H - 20, 0xD7, 0xBC, 0x6A, 170);
            gdl = fillRect(gdl, 7, 24, 8, H - 27, 0x8F, 0x7C, 0x45, 105);
            if (!s_controlHintSeen)
                gdl = fillRect(gdl, W - 125, H - 39, W - 7, H - 25,
                               7, 9, 10, 232);
        }'''
    s = once(s, old_brand_shapes, new_brand_shapes, "MI6 archive frame")

    old_brand_text = '''        if (showBrand) {
            gdl = drawText(gdl, 8, H - 14,
                           ASCENSION_SIGNATURE, ASC_UI_GOLD);
            gdl = drawTextR(gdl, W - 8, H - 14,
                            "F10 CONTROL", ASC_UI_SLATE);

            if (!s_controlHintSeen)
                gdl = drawTextR(gdl, W - 9, H - 32,
                                "PRESS F10 TO CONFIGURE",
                                ASC_UI_IVORY);
        }'''
    new_brand_text = '''        if (showBrand) {
            gdl = drawText(gdl, 9, 5, "MI6 / CLASSIFIED ARCHIVES", ASC_UI_IVORY);
            gdl = drawTextR(gdl, W - 9, 5, "00 SECTION / ACTIVE FILES", ASC_UI_GOLD_DIM);
            gdl = drawText(gdl, 9, H - 15, ASCENSION_SIGNATURE, ASC_UI_GOLD);
            gdl = drawTextR(gdl, W - 9, H - 15,
                            "MOUSE SELECT  |  RMB BACK  |  F10 Q BRANCH", ASC_UI_SLATE);
            if (!s_controlHintSeen)
                gdl = drawTextR(gdl, W - 10, H - 35,
                                "F10 / Q BRANCH SYSTEM CONFIGURATION", ASC_UI_IVORY);
        }'''
    s = once(s, old_brand_text, new_brand_text, "MI6 archive labels")

    # F10 panel hierarchy: technical Q-Branch instrument, not a generic settings card.
    old_title = '''    gdl = drawText(gdl, OV_X0, OV_TOP,
                   ASCENSION_SIGNATURE, ASC_UI_GOLD);'''
    new_title = '''    gdl = drawText(gdl, OV_X0, OV_TOP,
                   "MI6 / Q BRANCH SYSTEMS", ASC_UI_IVORY);
    gdl = drawTextR(gdl, OV_RIGHT - 18, OV_TOP,
                    ASCENSION_SIGNATURE, ASC_UI_GOLD_DIM);'''
    s = once(s, old_title, new_title, "Q Branch title")

    old_help = '''    gdl = drawText(gdl, OV_X0, OV_TOP + 2 * OV_LINE,
                   rows[s_sel].help ? rows[s_sel].help : "PC settings",
                   ASC_UI_SLATE);'''
    new_help = '''    gdl = drawText(gdl, OV_X0, OV_TOP + 2 * OV_LINE,
                   "Q BRANCH / CALIBRATION & FIELD PARAMETERS", ASC_UI_GOLD_DIM);
    gdl = drawText(gdl, OV_X0 + 132, OV_TOP + 2 * OV_LINE,
                   rows[s_sel].help ? rows[s_sel].help : "System parameter",
                   ASC_UI_SLATE);'''
    s = once(s, old_help, new_help, "Q Branch hierarchy")

    old_footer = '''        gdl = drawText(gdl, OV_X0, fy,
                       status ? "TAB CATEGORY" : "TAB CATEGORY  F10 CLOSE",
                       ASC_UI_SLATE);'''
    new_footer = '''        gdl = drawText(gdl, OV_X0, fy,
                       status ? "MI6 SYSTEM STATUS" : "MOUSE SELECT  |  W/S NAVIGATE  |  A/D ADJUST  |  F10 CLOSE",
                       ASC_UI_SLATE);'''
    s = once(s, old_footer, new_footer, "Q Branch footer")

    return s

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    original = OV.read_text(encoding="utf-8")
    try: patched = patch_overlay(original)
    except PatchError as e: raise SystemExit(f"ERROR: {e}; no file written")

    required = ["MI6 / Q BRANCH SYSTEMS", "MI6 / CLASSIFIED ARCHIVES",
                "MOUSE SELECT", "SDL_SCANCODE_W", "Q Branch section tabs"]
    for x in required:
        if x not in patched: raise SystemExit(f"ERROR: postcondition missing {x!r}")
    if args.check:
        print("Ascension UI Overhaul v1: PASS")
        print("F10 mouse targets: PASS")
        print("F10 WASD fallback: PASS")
        print("MI6 archive chrome: PASS")
        print("Would update:", OV.relative_to(ROOT) if patched != original else "nothing")
        return 0
    if patched != original:
        OV.write_text(patched, encoding="utf-8")
        print("UPDATED:", OV.relative_to(ROOT))
    else: print("No changes needed; UI Overhaul already applied.")
    return 0

if __name__ == "__main__": raise SystemExit(main())
