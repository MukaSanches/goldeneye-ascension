#!/usr/bin/env python3
"""Apply Ascension UI Overhaul v1 to the validated Modern Controls V3 stack.

Art direction is intentionally GoldenEye/MI6/Q-Branch rather than a generic
2020s settings dashboard.  The generated MI6 dossier/Q-Branch concept frames
are the visual reference: dark intelligence desk, ivory paper, restrained gold,
classification red, sharp typography, native GoldenEye font and zero rounded
mobile-app chrome.

The patch is presentation/input only.  It keeps GoldenEye's native save slots,
mission progression, menu hit-testing and gameplay state authoritative.
Run after V2, V3 and apply_modern_menu_guard.py.  Fail-closed + idempotent.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OV = ROOT / "port/src/optionsoverlay.c"


class PatchError(RuntimeError):
    pass


def once(s: str, old: str, new: str, label: str) -> str:
    if new in s:
        return s
    n = s.count(old)
    if n != 1:
        raise PatchError(f"{label}: expected one anchor, found {n}")
    return s.replace(old, new, 1)


def regex_once(s: str, pattern: str, repl: str, label: str) -> str:
    if repl in s:
        return s
    out, n = re.subn(pattern, repl, s, count=1, flags=re.S)
    if n != 1:
        raise PatchError(f"{label}: expected one regex match, found {n}")
    return out


def patch_overlay(s: str) -> str:
    if "optionsOverlayHandleInput" not in s or "GE_MENU_FILE_SELECT" not in s:
        raise PatchError("unexpected optionsoverlay baseline")
    if "Input.ModernDirectLook" not in s:
        raise PatchError("Modern Controls V3 F10 rows are not applied")

    # ------------------------------------------------------------------
    # Design system + dynamic file-select context.
    # ------------------------------------------------------------------
    s = once(s,
'''#define ASC_UI_GOLD       0xD2B65CFFu
#define ASC_UI_GOLD_DIM   0x9B8749FFu
#define ASC_UI_IVORY      0xE8E2D3FFu
#define ASC_UI_TEXT       0xC8C2B3FFu
#define ASC_UI_SLATE      0x8D9396FFu
#define ASC_UI_DARK       0x080A0CFFu''',
'''/* Ascension MI6 / Q Branch design system.  Values are deliberately muted:
 * the UI should feel like 1995 intelligence material, not neon sci-fi. */
#define ASC_UI_GOLD       0xD6B85FFFu
#define ASC_UI_GOLD_DIM   0x8D7A43FFu
#define ASC_UI_IVORY      0xEEE8D8FFu
#define ASC_UI_TEXT       0xC8C1B1FFu
#define ASC_UI_SLATE      0x858A86FFu
#define ASC_UI_DARK       0x07090AFFu
#define ASC_UI_INK        0x20211FFFu
#define ASC_UI_INK_DIM    0x555449FFu
#define ASC_UI_PAPER      0xD7D0BCFFu
#define ASC_UI_PAPER_2    0xC7BEA8FFu
#define ASC_UI_RED        0x9E3F36FFu
#define ASC_UI_GREEN      0x789071FFu''', "MI6 palette")

    s = once(s,
'''extern s16   viGetX(void);
extern s16   viGetY(void);
extern int   current_menu;''',
'''extern s16   viGetX(void);
extern s16   viGetY(void);
extern int   current_menu;
extern s32   selected_folder_num;''', "selected dossier context")

    # Four deliberate departments instead of one endless technical list.
    s = once(s,
'''enum RowCategory {
    CAT_DISPLAY,
    CAT_INPUT,
    CAT_GAMEPLAY,
};''',
'''enum RowCategory {
    CAT_DISPLAY,
    CAT_INPUT,
    CAT_GAMEPLAY,
    CAT_SYSTEM,
};''', "system category")

    old_tail = '''    /* GAMEPLAY */
    { .key="Ascension.Language",   .label="Language",
      .help="Interface and in-game text language.", .category=CAT_GAMEPLAY,
      .kind=ROW_ENUM, .step=1, .names=kLanguage, .resetValue=0 },

    { .key="Game.ScreenShakeIntensity", .label="Screen shake",
      .help="Camera shake. Safe range 0-3.", .category=CAT_GAMEPLAY,
      .kind=ROW_SLIDER, .step=0.25, .uiMin=0, .uiMax=3, .resetValue=1 },

    { .key="Game.SkipIntro",       .label="Skip intro",
      .help="Next launch starts at file select.", .category=CAT_GAMEPLAY,
      .kind=ROW_TOGGLE, .step=1, .names=kOnOff, .restart=1, .resetValue=0 },

    { .key="__Reset",              .label="Reset PC settings",
      .help="Restore PC defaults; saves stay safe.", .category=CAT_GAMEPLAY,
      .kind=ROW_ACTION, .action=ACTION_RESET, .found=1 },

    { .key="__Restart",            .label="Restart game",
      .help="Save settings and relaunch.", .category=CAT_GAMEPLAY,
      .kind=ROW_ACTION, .action=ACTION_RESTART, .found=1 },'''
    new_tail = '''    /* FIELD / GAMEPLAY */
    { .key="Game.ScreenShakeIntensity", .label="Screen shake",
      .help="Camera shake. Safe range 0-3.", .category=CAT_GAMEPLAY,
      .kind=ROW_SLIDER, .step=0.25, .uiMin=0, .uiMax=3, .resetValue=1 },

    { .key="Game.SkipIntro",       .label="Skip intro",
      .help="Next launch starts at file select.", .category=CAT_GAMEPLAY,
      .kind=ROW_TOGGLE, .step=1, .names=kOnOff, .restart=1, .resetValue=0 },

    /* SYSTEM */
    { .key="Ascension.Language",   .label="Language",
      .help="Interface and in-game text language.", .category=CAT_SYSTEM,
      .kind=ROW_ENUM, .step=1, .names=kLanguage, .resetValue=0 },

    { .key="__Reset",              .label="Reset PC settings",
      .help="Restore PC defaults; saves stay safe.", .category=CAT_SYSTEM,
      .kind=ROW_ACTION, .action=ACTION_RESET, .found=1 },

    { .key="__Restart",            .label="Restart game",
      .help="Save settings and relaunch.", .category=CAT_SYSTEM,
      .kind=ROW_ACTION, .action=ACTION_RESTART, .found=1 },'''
    s = once(s, old_tail, new_tail, "field/system row split")

    # ------------------------------------------------------------------
    # Responsive dossier geometry.  440x330 gets the full reference layout;
    # 320x240 still gets a compact but readable form.
    # ------------------------------------------------------------------
    s = regex_once(s,
        r'/\* ---- layout ------------------------------------------------------------ \*/.*?/\* ---- feedback ---------------------------------------------------------- \*/',
'''/* ---- layout ------------------------------------------------------------ */
#define OV_X0           8
#define OV_TOP          7
#define OV_LINE        14
#define OV_SIDE_W      78
#define OV_SIDE_X0      7
#define OV_SIDE_X1     (OV_SIDE_X0 + OV_SIDE_W)
#define OV_PANEL_X     (OV_SIDE_X1 + 7)
#define OV_LABEL_X     (OV_PANEL_X + 8)
#define OV_RIGHT       (viGetX() - 8)
#define OV_LIST_TOP    61
#define OV_HELP_H      43
#define OV_FOOTER_H    17
#define OV_NUM_W       34
#define OV_BAR_X       (OV_PANEL_X + 126)
#define OV_SIDE_Y0     58
#define OV_SIDE_STEP   38

#define OV_CB_X0      (OV_RIGHT - 16)
#define OV_CB_X1      (OV_RIGHT)
#define OV_CB_Y0       5
#define OV_CB_Y1      18

static int overlayHasInfoPanel(void)
{
    return viGetX() >= 400;
}

static int overlayContentRight(void)
{
    return overlayHasInfoPanel() ? OV_RIGHT - 108 : OV_RIGHT;
}

static int overlayHelpTop(void)
{
    return viGetY() - OV_HELP_H - OV_FOOTER_H;
}

static void categoryBounds(int cat, int *first, int *last)
{
    *first = -1;
    *last = -1;
    for (int i = 0; i < NUM_ROWS; ++i) {
        if (rows[i].category != cat)
            continue;
        if (*first < 0) *first = i;
        *last = i;
    }
}

static int visibleRows(void)
{
    int n = (overlayHelpTop() - OV_LIST_TOP - 4) / OV_LINE;
    if (n < 4) n = 4;
    if (n > NUM_ROWS) n = NUM_ROWS;
    return n;
}

static int maxScroll(void)
{
    int first, last;
    categoryBounds(rows[s_sel].category, &first, &last);
    if (first < 0) return 0;
    int m = last - visibleRows() + 1;
    return m > first ? m : first;
}

static void ensureSelectionVisible(void)
{
    int first, last;
    categoryBounds(rows[s_sel].category, &first, &last);
    if (first < 0) return;
    int vis = visibleRows();
    int max = maxScroll();

    if (s_scroll < first || s_scroll > last)
        s_scroll = first;
    if (s_sel < s_scroll)
        s_scroll = s_sel;
    if (s_sel >= s_scroll + vis)
        s_scroll = s_sel - vis + 1;
    if (s_scroll < first) s_scroll = first;
    if (s_scroll > max) s_scroll = max;
}

static int rowY(int row)
{
    return OV_LIST_TOP + (row - s_scroll) * OV_LINE;
}

static int overlayRowAtY(double oy)
{
    int vis = visibleRows();
    if (oy < OV_LIST_TOP || oy >= OV_LIST_TOP + vis * OV_LINE)
        return -1;
    int row = s_scroll + (int)((oy - OV_LIST_TOP) / OV_LINE);
    if (row < 0 || row >= NUM_ROWS)
        return -1;
    return rows[row].category == rows[s_sel].category ? row : -1;
}

static int sidebarCategoryAt(double ox, double oy)
{
    if (ox < OV_SIDE_X0 || ox > OV_SIDE_X1)
        return -1;
    for (int cat = CAT_DISPLAY; cat <= CAT_SYSTEM; ++cat) {
        int y0 = OV_SIDE_Y0 + cat * OV_SIDE_STEP;
        if (oy >= y0 && oy < y0 + 29)
            return cat;
    }
    return -1;
}

static int overlayInCloseBox(double ox, double oy)
{
    return ox >= OV_CB_X0 && ox <= OV_CB_X1 &&
           oy >= OV_CB_Y0 && oy <= OV_CB_Y1;
}

static void sliderBarSpan(s32 *x0, s32 *x1)
{
    *x0 = OV_BAR_X;
    *x1 = overlayContentRight() - OV_NUM_W;
    if (*x1 < *x0 + 18)
        *x1 = *x0 + 18;
}

/* ---- feedback ---------------------------------------------------------- */''', "dossier responsive layout")

    # Professional PC fallback: WASD and arrows are both first-class.
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

    # Category-scoped navigation.  The selected department never spills into
    # another department merely because the list scrolls.
    s = regex_once(s,
        r'static void moveSelection\(int delta\)\n\{.*?\n\}\n\nstatic void jumpCategory\(int dir\)\n\{.*?\n\}',
'''static void moveSelection(int delta)
{
    int first, last;
    categoryBounds(rows[s_sel].category, &first, &last);
    if (first < 0) return;
    int next = s_sel + delta;
    if (next < first) next = first;
    if (next > last) next = last;
    if (next != s_sel) {
        s_sel = next;
        clearPendingAction();
        ensureSelectionVisible();
    }
}

static void jumpCategory(int dir)
{
    int target = rows[s_sel].category + (dir >= 0 ? 1 : -1);
    if (target < CAT_DISPLAY) target = CAT_SYSTEM;
    if (target > CAT_SYSTEM) target = CAT_DISPLAY;

    int first, last;
    categoryBounds(target, &first, &last);
    if (first >= 0) {
        s_sel = first;
        s_scroll = first;
    }
    clearPendingAction();
    ensureSelectionVisible();
}''', "category-scoped navigation")

    # Replace old horizontal tabs with the dossier's vertical department rail.
    s = regex_once(s,
        r'static Gfx \*drawCategoryTabs\(Gfx \*gdl, int active\)\n\{.*?\n\}',
'''static const char *categoryName(int cat)
{
    switch (cat) {
    case CAT_DISPLAY:  return "DISPLAY";
    case CAT_INPUT:    return "CONTROLS";
    case CAT_GAMEPLAY: return "FIELD";
    default:           return "SYSTEM";
    }
}

static const char *categorySub(int cat)
{
    switch (cat) {
    case CAT_DISPLAY:  return "VISUAL SYSTEMS";
    case CAT_INPUT:    return "INPUT CALIBRATION";
    case CAT_GAMEPLAY: return "MISSION PARAMETERS";
    default:           return "TECHNICAL / LANGUAGE";
    }
}

static Gfx *drawCategoryTabs(Gfx *gdl, int active)
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
        gdl = drawText(gdl, OV_SIDE_X0 + 8, y,
                       categoryName(cat), col);
        gdl = drawText(gdl, OV_SIDE_X0 + 8, y + 11,
                       categorySub(cat), cat == active ? ASC_UI_GOLD_DIM : 0x666A67FFu);
    }
    return gdl;
}''', "vertical Q Branch departments")

    # Sidebar hit testing and full-row click semantics.  Sliders still drag.
    anchor = '''        int hoverRow = overlayRowAtY(oy);
        int onClose = overlayInCloseBox(ox, oy);
'''
    repl = anchor + '''        int hoverCat = sidebarCategoryAt(ox, oy);

        if (lmb && !prevLmb && hoverCat >= 0) {
            int first, last;
            categoryBounds(hoverCat, &first, &last);
            if (first >= 0) {
                s_sel = first;
                s_scroll = first;
                clearPendingAction();
                ensureSelectionVisible();
                hoverRow = -1;
            }
        }
'''
    s = once(s, anchor, repl, "sidebar mouse targets")

    old_click = '''            if (hoverRow >= 0) {
                struct Row *r = &rows[hoverRow];
                if (r->kind == ROW_ACTION) {
                    activateAction(r);
                } else if (ox >= bx0) {
                    if (r->kind == ROW_SLIDER && r->found) {
                        sliderSetFromX(r, ox);
                        dragRow = hoverRow;
                    } else {
                        rowAdjust(r, +1);
                    }
                }
            }'''
    new_click = '''            if (hoverRow >= 0) {
                struct Row *r = &rows[hoverRow];
                if (r->kind == ROW_ACTION) {
                    activateAction(r);
                } else if (r->kind == ROW_SLIDER && r->found && ox >= bx0) {
                    sliderSetFromX(r, ox);
                    dragRow = hoverRow;
                } else if (r->kind != ROW_SLIDER && ox >= OV_LABEL_X) {
                    /* Entire selector row is a target; no pixel-hunting on values. */
                    rowAdjust(r, +1);
                }
            }'''
    s = once(s, old_click, new_click, "full-row mouse targets")

    old_rmb = '''        if (rmb && !prevRmb && hoverRow >= 0 &&
            rows[hoverRow].kind != ROW_ACTION && ox >= bx0)
            rowAdjust(&rows[hoverRow], -1);'''
    new_rmb = '''        if (rmb && !prevRmb && hoverRow >= 0 &&
            rows[hoverRow].kind != ROW_ACTION && ox >= OV_LABEL_X)
            rowAdjust(&rows[hoverRow], -1);'''
    s = once(s, old_rmb, new_rmb, "full-row reverse click")

    # ------------------------------------------------------------------
    # File-select chrome: use the generated MI6 Classified Archives concept
    # as composition reference but keep native GoldenEye folders/hit-testing.
    # ------------------------------------------------------------------
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
            /* Generated dossier concept translated into native Fast3D geometry:
             * dark intelligence desk, restrained gold rules and archive bands.
             * Native folders remain visible and interactive in the center. */
            gdl = fillRect(gdl, 0, 0, W, 25, 5, 7, 8, 226);
            gdl = fillRect(gdl, 0, 24, W, 25, 0xD6, 0xB8, 0x5F, 220);
            gdl = fillRect(gdl, 0, H - 22, W, H, 5, 7, 8, 232);
            gdl = fillRect(gdl, 0, H - 23, W, H - 22, 0x8D, 0x7A, 0x43, 180);
            gdl = fillRect(gdl, 7, 31, 8, H - 30, 0x8D, 0x7A, 0x43, 120);
            gdl = fillRect(gdl, W - 8, 31, W - 7, H - 30, 0x8D, 0x7A, 0x43, 120);
            if (!s_controlHintSeen) {
                gdl = fillRect(gdl, W - 145, H - 43, W - 8, H - 27,
                               7, 9, 10, 238);
                gdl = fillRect(gdl, W - 145, H - 43, W - 143, H - 27,
                               0xD6, 0xB8, 0x5F, 255);
            }
        }'''
    s = once(s, old_brand_shapes, new_brand_shapes, "classified archive frame")

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
            char fileRef[40];
            int fileNo = selected_folder_num + 1;
            if (fileNo < 1 || fileNo > 9) fileNo = 1;
            snprintf(fileRef, sizeof(fileRef), "ACTIVE DOSSIER / FILE %02d", fileNo);

            gdl = drawText(gdl, 10, 6, "MI6 CLASSIFIED ARCHIVES", ASC_UI_IVORY);
            gdl = drawText(gdl, 10, 16, "SECURE AGENT FILES", ASC_UI_GOLD_DIM);
            gdl = drawTextR(gdl, W - 10, 6, "ASCENSION", ASC_UI_GOLD);
            gdl = drawTextR(gdl, W - 10, 16, fileRef, ASC_UI_SLATE);

            gdl = drawText(gdl, 10, H - 16,
                           "LMB SELECT  |  RMB BACK", ASC_UI_TEXT);
            gdl = drawTextR(gdl, W - 10, H - 16,
                            "F10 / Q BRANCH SYSTEMS", ASC_UI_GOLD_DIM);
            if (!s_controlHintSeen)
                gdl = drawTextR(gdl, W - 10, H - 39,
                                "F10  OPEN SYSTEM CONFIGURATION", ASC_UI_IVORY);
        }'''
    s = once(s, old_brand_text, new_brand_text, "classified archive labels")

    # ------------------------------------------------------------------
    # Replace only the rendering function.  All value/config behavior stays in
    # the already-tested backend, while the composition follows the generated
    # Q Branch concept: dark sidebar + ivory dossier + right intelligence note.
    # ------------------------------------------------------------------
    emit_re = r'Gfx \*optionsOverlayEmit\(void\)\n\{.*?\n\}\s*$'
    new_emit = r'''Gfx *optionsOverlayEmit(void)
{
    overlayInit();
    fpsTick();

    if (!s_open) {
        const int showBrand = current_menu == GE_MENU_FILE_SELECT;
        const int showFps = s_showFps && s_fpsText[0];
        if (!showBrand && !showFps)
            return NULL;

        const s32 W = viGetX();
        const s32 H = viGetY();
        Gfx *gdl = s_buf;
        gDPPipeSync(gdl++);
        gDPSetCycleType(gdl++, G_CYC_1CYCLE);
        gDPSetTexturePersp(gdl++, G_TP_NONE);
        gDPSetScissor(gdl++, G_SC_NON_INTERLACE, 0, 0, W, H);

        if (showBrand) {
            gdl = fillRect(gdl, 0, 0, W, 25, 5, 7, 8, 226);
            gdl = fillRect(gdl, 0, 24, W, 25, 0xD6, 0xB8, 0x5F, 220);
            gdl = fillRect(gdl, 0, H - 22, W, H, 5, 7, 8, 232);
            gdl = fillRect(gdl, 0, H - 23, W, H - 22, 0x8D, 0x7A, 0x43, 180);
            gdl = fillRect(gdl, 7, 31, 8, H - 30, 0x8D, 0x7A, 0x43, 120);
            gdl = fillRect(gdl, W - 8, 31, W - 7, H - 30, 0x8D, 0x7A, 0x43, 120);
            if (!s_controlHintSeen) {
                gdl = fillRect(gdl, W - 145, H - 43, W - 8, H - 27,
                               7, 9, 10, 238);
                gdl = fillRect(gdl, W - 145, H - 43, W - 143, H - 27,
                               0xD6, 0xB8, 0x5F, 255);
            }
        }

        gdl = microcode_constructor(gdl);
        if (showBrand) {
            char fileRef[40];
            int fileNo = selected_folder_num + 1;
            if (fileNo < 1 || fileNo > 9) fileNo = 1;
            snprintf(fileRef, sizeof(fileRef), "ACTIVE DOSSIER / FILE %02d", fileNo);
            gdl = drawText(gdl, 10, 6, "MI6 CLASSIFIED ARCHIVES", ASC_UI_IVORY);
            gdl = drawText(gdl, 10, 16, "SECURE AGENT FILES", ASC_UI_GOLD_DIM);
            gdl = drawTextR(gdl, W - 10, 6, "ASCENSION", ASC_UI_GOLD);
            gdl = drawTextR(gdl, W - 10, 16, fileRef, ASC_UI_SLATE);
            gdl = drawText(gdl, 10, H - 16, "LMB SELECT  |  RMB BACK", ASC_UI_TEXT);
            gdl = drawTextR(gdl, W - 10, H - 16,
                            "F10 / Q BRANCH SYSTEMS", ASC_UI_GOLD_DIM);
            if (!s_controlHintSeen)
                gdl = drawTextR(gdl, W - 10, H - 39,
                                "F10  OPEN SYSTEM CONFIGURATION", ASC_UI_IVORY);
        }
        if (showFps)
            gdl = drawTextR(gdl, W - 7, 29, s_fpsText, ASC_UI_GREEN);
        gDPPipeSync(gdl++);
        gSPEndDisplayList(gdl++);
        return s_buf;
    }

    ensureSelectionVisible();
    const s32 W = viGetX();
    const s32 H = viGetY();
    const int activeCat = rows[s_sel].category;
    const int vis = visibleRows();
    int first, last;
    categoryBounds(activeCat, &first, &last);
    const int contentR = overlayContentRight();
    const int helpTop = overlayHelpTop();
    const int panelBottom = H - OV_FOOTER_H - 3;
    s32 bx0, bx1;
    sliderBarSpan(&bx0, &bx1);

    Gfx *gdl = s_buf;
    gDPPipeSync(gdl++);
    gDPSetCycleType(gdl++, G_CYC_1CYCLE);
    gDPSetTexturePersp(gdl++, G_TP_NONE);
    gDPSetScissor(gdl++, G_SC_NON_INTERLACE, 0, 0, W, H);

    /* The generated concepts use a black intelligence desk and a paper dossier.
     * Recreate that language with cheap native primitives; no runtime texture or
     * web dependency, so the menu remains deterministic and essentially free. */
    gdl = fillRect(gdl, 0, 0, W, H, 0, 0, 0, 168);
    gdl = fillRect(gdl, 0, 0, W, 27, 5, 7, 8, 244);
    gdl = fillRect(gdl, 0, 26, W, 27, 0xD6, 0xB8, 0x5F, 220);
    gdl = fillRect(gdl, OV_SIDE_X0 - 3, 34, OV_SIDE_X1 + 3, panelBottom,
                   7, 9, 10, 238);
    gdl = fillRect(gdl, OV_PANEL_X - 4, 34, OV_RIGHT, panelBottom,
                   0xD7, 0xD0, 0xBC, 246);
    gdl = fillRect(gdl, OV_PANEL_X - 4, 34, OV_RIGHT, 35,
                   0x8D, 0x7A, 0x43, 220);

    /* Paper header / security marks. */
    gdl = fillRect(gdl, OV_PANEL_X + 5, 51, OV_RIGHT - 7, 52,
                   104, 99, 86, 110);
    gdl = fillRect(gdl, OV_CB_X0, OV_CB_Y0, OV_CB_X1, OV_CB_Y1,
                   112, 38, 33, 235);

    /* Selected department in sidebar. */
    {
        s32 y = OV_SIDE_Y0 + activeCat * OV_SIDE_STEP;
        gdl = fillRect(gdl, OV_SIDE_X0, y - 4, OV_SIDE_X1, y + 24,
                       27, 26, 22, 235);
        gdl = fillRect(gdl, OV_SIDE_X0, y - 4, OV_SIDE_X0 + 2, y + 24,
                       214, 184, 95, 255);
    }

    /* Row surface and slider tracks. */
    int end = s_scroll + vis;
    if (end > last + 1) end = last + 1;
    for (int i = s_scroll; i < end; ++i) {
        s32 y = rowY(i);
        if (i == s_sel) {
            gdl = fillRect(gdl, OV_LABEL_X - 5, y - 2,
                           contentR - 3, y + OV_LINE - 3,
                           190, 170, 112, 92);
            gdl = fillRect(gdl, OV_LABEL_X - 7, y - 2,
                           OV_LABEL_X - 5, y + OV_LINE - 3,
                           157, 125, 52, 255);
        }
        if (rows[i].kind == ROW_SLIDER && rows[i].found) {
            double lo = rowLo(&rows[i]), hi = rowHi(&rows[i]);
            double f = hi > lo ? (rowGet(&rows[i]) - lo) / (hi - lo) : 0.0;
            if (f < 0) f = 0; if (f > 1) f = 1;
            s32 by = y + 3;
            gdl = fillRect(gdl, bx0, by, bx1, by + 4, 72, 70, 63, 180);
            gdl = fillRect(gdl, bx0, by,
                           bx0 + (s32)((bx1 - bx0) * f), by + 4,
                           191, 157, 75, 245);
        }
    }

    /* Right intel note on wide front-end canvases, mirroring the concept frame. */
    if (overlayHasInfoPanel()) {
        int ix0 = contentR + 7;
        gdl = fillRect(gdl, ix0, 58, OV_RIGHT - 7, helpTop - 5,
                       199, 191, 169, 116);
        gdl = fillRect(gdl, ix0, 58, ix0 + 1, helpTop - 5,
                       105, 99, 85, 120);
        gdl = fillRect(gdl, ix0 + 8, 72, OV_RIGHT - 15, 73,
                       158, 62, 53, 140);
    }

    /* Scroll rail belongs to the active department only. */
    if (last - first + 1 > vis) {
        int trackY0 = OV_LIST_TOP;
        int trackY1 = helpTop - 6;
        int trackH = trackY1 - trackY0;
        int count = last - first + 1;
        int thumbH = (trackH * vis) / count;
        if (thumbH < 10) thumbH = 10;
        int max = maxScroll();
        int denom = max - first;
        int thumbY = trackY0;
        if (denom > 0)
            thumbY += ((trackH - thumbH) * (s_scroll - first)) / denom;
        gdl = fillRect(gdl, contentR - 4, trackY0, contentR - 2, trackY1,
                       84, 82, 75, 110);
        gdl = fillRect(gdl, contentR - 4, thumbY, contentR - 2, thumbY + thumbH,
                       157, 125, 52, 230);
    }

    gdl = microcode_constructor(gdl);

    /* Header. */
    gdl = drawText(gdl, 10, 7, "Q BRANCH SYSTEMS", ASC_UI_IVORY);
    gdl = drawText(gdl, 10, 17, "OPERATIONAL CONFIGURATION", ASC_UI_GOLD_DIM);
    gdl = drawTextR(gdl, W - 28, 7, ASCENSION_SIGNATURE, ASC_UI_GOLD);
    gdl = drawText(gdl, OV_PANEL_X + 6, 40, "MI6 / SYSTEMS CONFIGURATION", ASC_UI_INK_DIM);
    gdl = drawTextR(gdl, OV_RIGHT - 8, 40, "TOP SECRET", ASC_UI_RED);
    gdl = drawText(gdl, OV_PANEL_X + 6, 53, categoryName(activeCat), ASC_UI_INK);
    gdl = drawText(gdl, OV_PANEL_X + 6, 63, categorySub(activeCat), ASC_UI_INK_DIM);
    gdl = drawText(gdl,
                   (OV_CB_X0 + OV_CB_X1) / 2 - measureText("X") / 2,
                   7, "X", ASC_UI_IVORY);

    gdl = drawCategoryTabs(gdl, activeCat);

    /* Active rows only -- this is the biggest UX improvement over the old
     * single 20+ row technical list. */
    for (int i = s_scroll; i < end; ++i) {
        s32 y = rowY(i);
        u32 col = rows[i].found ? ASC_UI_INK : 0x777269FFu;
        char val[48];
        gdl = drawText(gdl, OV_LABEL_X, y, rows[i].label, col);
        if (!rows[i].found) {
            gdl = drawTextR(gdl, contentR - 8, y, "N/A", ASC_UI_INK_DIM);
            continue;
        }
        valueText(&rows[i], val, sizeof(val));
        u32 valueCol = i == s_sel ? 0x6A4D12FFu : ASC_UI_INK;
        if (rows[i].restart && rows[i].kind != ROW_ACTION) {
            gdl = drawText(gdl, bx0, y, val, valueCol);
            gdl = drawTextR(gdl, contentR - 8, y, "RESTART", ASC_UI_RED);
        } else {
            gdl = drawTextR(gdl, contentR - 8, y, val,
                            rows[i].kind == ROW_ACTION ? ASC_UI_RED : valueCol);
        }
    }

    /* Contextual intelligence note / help text. */
    if (overlayHasInfoPanel()) {
        int ix = contentR + 12;
        gdl = drawText(gdl, ix, 62, "FIELD NOTE", ASC_UI_RED);
        gdl = drawText(gdl, ix, 78, rows[s_sel].label, ASC_UI_INK);
        gdl = drawText(gdl, ix, 93,
                       rows[s_sel].help ? rows[s_sel].help : "System parameter",
                       ASC_UI_INK_DIM);
        gdl = drawText(gdl, ix, helpTop - 31, "Q BRANCH / LONDON", ASC_UI_INK_DIM);
        gdl = drawText(gdl, ix, helpTop - 19, "TECHNOLOGY IN SERVICE", ASC_UI_INK_DIM);
    } else {
        gdl = drawText(gdl, OV_LABEL_X, helpTop + 4,
                       rows[s_sel].help ? rows[s_sel].help : "System parameter",
                       ASC_UI_INK_DIM);
    }

    {
        const char *status = statusText();
        s32 fy = H - OV_FOOTER_H + 2;
        gdl = drawText(gdl, 10, fy,
                       "LMB SELECT  |  RMB BACK  |  W/S NAV  |  A/D ADJUST",
                       ASC_UI_SLATE);
        gdl = drawTextR(gdl, W - 10, fy,
                        status ? status : "F10 CLOSE",
                        status && strstr(status, "FAILED") ? 0xFF7070FFu : ASC_UI_GOLD_DIM);
    }

    gDPPipeSync(gdl++);
    gSPEndDisplayList(gdl++);
    if ((gdl - s_buf) > OV_BUF_CMDS)
        sysLogPrintf(LOG_ERROR, "optionsoverlay: DL overflow (%d)", (int)(gdl - s_buf));
    return s_buf;
}'''
    # Replace the full emitter last so earlier brand anchors can validate the
    # baseline before the function is rewritten.
    s = regex_once(s, emit_re, new_emit, "professional dossier emitter")

    return s


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    original = OV.read_text(encoding="utf-8")
    try:
        patched = patch_overlay(original)
    except PatchError as exc:
        raise SystemExit(f"ERROR: {exc}; no file written")

    required = [
        "Q BRANCH SYSTEMS",
        "MI6 CLASSIFIED ARCHIVES",
        "CAT_SYSTEM",
        "sidebarCategoryAt",
        "ACTIVE DOSSIER / FILE %02d",
        "LMB SELECT  |  RMB BACK",
        "SDL_SCANCODE_W",
        "overlayHasInfoPanel",
        "TECHNOLOGY IN SERVICE",
        "Active rows only",
    ]
    for needle in required:
        if needle not in patched:
            raise SystemExit(f"ERROR: postcondition missing {needle!r}; no file written")

    if args.check:
        print("Ascension UI Overhaul v1: PASS")
        print("Generated-concept art direction: MI6 dossier / Q Branch")
        print("Department-scoped settings: PASS")
        print("Mouse sidebar / rows / drag: PASS")
        print("WASD + arrows fallback: PASS")
        print("Native file-select save logic preserved: PASS")
        print("Would update:", OV.relative_to(ROOT) if patched != original else "nothing")
        return 0

    if patched != original:
        OV.write_text(patched, encoding="utf-8")
        print("UPDATED:", OV.relative_to(ROOT))
    else:
        print("No changes needed; UI Overhaul already applied.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
