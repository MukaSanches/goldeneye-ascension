#!/usr/bin/env python3
"""Ascension UI Overhaul V2: compact Q-Watch / MI6 settings interface.

This migrates the experimental V1 dossier overlay into a deliberately simpler
interface that follows GoldenEye's own visual grammar: black/translucent menu
surfaces, Zurich body copy, restrained gold focus, short pages and a single
context line.  It is presentation/input only; gameplay, missions and saves are
out of scope.

Run after Modern Controls V2/V3, apply_modern_menu_guard.py,
apply_ui_overhaul_v1.py and fix_ui_overhaul_text_state.py.

The patch is fail-closed and idempotent.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OV = ROOT / "port/src/optionsoverlay.c"


class PatchError(RuntimeError):
    pass


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        return text
    count = text.count(old)
    if count != 1:
        raise PatchError(f"{label}: expected exactly one anchor, found {count}")
    return text.replace(old, new, 1)


def regex_once(text: str, pattern: str, repl: str, label: str) -> str:
    out, count = re.subn(pattern, repl, text, count=1, flags=re.S)
    if count != 1:
        raise PatchError(f"{label}: expected exactly one match, found {count}")
    return out


LAYOUT = r'''/* ---- layout ------------------------------------------------------------ */
/*
 * V2 uses the same 320x240-ish virtual coordinate system as GoldenEye.  The
 * important constraint is information density: five to seven rows, not an
 * entire PC control panel squeezed into one frame.
 */
#define OV_MARGIN_X      10
#define OV_PANEL_X0      OV_MARGIN_X
#define OV_PANEL_X1      (viGetX() - OV_MARGIN_X)
#define OV_TOP            8
#define OV_HEADER_Y      11
#define OV_TAB_Y         31
#define OV_TAB_H         17
#define OV_SECTION_Y     51
#define OV_LIST_TOP      66
#define OV_ROW_H         22
#define OV_MAX_VISIBLE    7
#define OV_HELP_H        29
#define OV_FOOTER_H      19
#define OV_LABEL_X       (OV_PANEL_X0 + 10)
#define OV_RIGHT         (OV_PANEL_X1 - 10)
#define OV_NUM_W         42

#define OV_CB_X0         (OV_PANEL_X1 - 20)
#define OV_CB_X1         (OV_PANEL_X1 - 3)
#define OV_CB_Y0          7
#define OV_CB_Y1         20

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
    int n = (overlayHelpTop() - OV_LIST_TOP - 3) / OV_ROW_H;
    if (n < 4) n = 4;
    if (n > OV_MAX_VISIBLE) n = OV_MAX_VISIBLE;

    int first, last;
    categoryBounds(rows[s_sel].category, &first, &last);
    if (first >= 0) {
        int count = last - first + 1;
        if (n > count) n = count;
    }
    return n;
}

static int maxScroll(void)
{
    int first, last;
    categoryBounds(rows[s_sel].category, &first, &last);
    if (first < 0) return 0;
    int vis = visibleRows();
    int lastStart = last - vis + 1;
    return lastStart > first ? lastStart : first;
}

static void ensureSelectionVisible(void)
{
    int first, last;
    categoryBounds(rows[s_sel].category, &first, &last);
    if (first < 0) return;

    int vis = visibleRows();
    int max = maxScroll();
    if (s_scroll < first || s_scroll > max)
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
    return OV_LIST_TOP + (row - s_scroll) * OV_ROW_H;
}

static int overlayRowAtY(double oy)
{
    int vis = visibleRows();
    if (oy < OV_LIST_TOP || oy >= OV_LIST_TOP + vis * OV_ROW_H)
        return -1;
    int row = s_scroll + (int)((oy - OV_LIST_TOP) / OV_ROW_H);
    if (row < 0 || row >= NUM_ROWS)
        return -1;
    return rows[row].category == rows[s_sel].category ? row : -1;
}

/* Top tabs deliberately replace V1's oversized sidebar. */
static int tabCategoryAt(double ox, double oy)
{
    if (oy < OV_TAB_Y - 2 || oy > OV_TAB_Y + OV_TAB_H)
        return -1;
    if (ox < OV_PANEL_X0 + 5 || ox > OV_PANEL_X1 - 27)
        return -1;

    double x0 = OV_PANEL_X0 + 5;
    double x1 = OV_PANEL_X1 - 27;
    int cat = (int)(((ox - x0) * 4.0) / (x1 - x0));
    if (cat < CAT_DISPLAY) cat = CAT_DISPLAY;
    if (cat > CAT_SYSTEM) cat = CAT_SYSTEM;
    return cat;
}

static int overlayInCloseBox(double ox, double oy)
{
    return ox >= OV_CB_X0 && ox <= OV_CB_X1 &&
           oy >= OV_CB_Y0 && oy <= OV_CB_Y1;
}

static void sliderBarSpan(s32 *x0, s32 *x1)
{
    /* Leave a guaranteed label/value corridor even at the native viewport. */
    *x0 = viGetX() >= 400 ? OV_PANEL_X0 + 186 : OV_PANEL_X0 + 142;
    *x1 = OV_RIGHT - OV_NUM_W;
    if (*x1 < *x0 + 28)
        *x1 = *x0 + 28;
}

/* ---- feedback ---------------------------------------------------------- */'''


DRAWING = r'''/* ---- drawing ----------------------------------------------------------- */
/* Ascension UI Overhaul V2 - Q Watch compact settings. */
#define OV_BUF_CMDS 8192
static Gfx s_buf[OV_BUF_CMDS];

static Gfx *fillRect(Gfx *gdl, s32 x0, s32 y0, s32 x1, s32 y1,
                     u8 r, u8 g, u8 b, u8 a)
{
    gDPSetRenderMode(gdl++, G_RM_XLU_SURF, G_RM_XLU_SURF2);
    gDPSetCombineMode(gdl++, G_CC_PRIMITIVE, G_CC_PRIMITIVE);
    gDPSetPrimColor(gdl++, 0, 0, r, g, b, a);
    gDPFillRectangle(gdl++, x0, y0, x1, y1);
    return gdl;
}

static const char *categoryName(int cat)
{
    switch (cat) {
    case CAT_DISPLAY:  return "DISPLAY";
    case CAT_INPUT:    return "CONTROLS";
    case CAT_GAMEPLAY: return "GAMEPLAY";
    default:           return "SYSTEM";
    }
}

static const char *categorySub(int cat)
{
    switch (cat) {
    case CAT_DISPLAY:  return "DISPLAY CALIBRATION";
    case CAT_INPUT:    return "INPUT CALIBRATION";
    case CAT_GAMEPLAY: return "FIELD PARAMETERS";
    default:           return "LANGUAGE / MAINTENANCE";
    }
}

static Gfx *drawTextFont(Gfx *gdl, s32 x, s32 y, const char *str, u32 colour,
                         struct fontchar *chars, struct font *font)
{
    const char *localized = ascensionLocaleText(str ? str : "");
    s32 px = x, py = y;
    return textRender(gdl, &px, &py, (char *)localized,
                      chars, font, colour,
                      viGetX(), viGetY(), 0, 0);
}

static s32 measureTextRaw(const char *str,
                          struct fontchar *chars, struct font *font)
{
    s32 h = 0, w = 0;
    textMeasure(&h, &w, (char *)(str ? str : ""), chars, font, 0);
    return w;
}

static s32 measureTextFont(const char *str,
                           struct fontchar *chars, struct font *font)
{
    return measureTextRaw(ascensionLocaleText(str ? str : ""), chars, font);
}

static Gfx *drawZurich(Gfx *gdl, s32 x, s32 y, const char *str, u32 colour)
{
    return drawTextFont(gdl, x, y, str, colour,
                        ptrFontZurichBoldChars, ptrFontZurichBold);
}

static Gfx *drawGothic(Gfx *gdl, s32 x, s32 y, const char *str, u32 colour)
{
    return drawTextFont(gdl, x, y, str, colour,
                        ptrFontBankGothicChars, ptrFontBankGothic);
}

static Gfx *drawZurichR(Gfx *gdl, s32 xr, s32 y,
                        const char *str, u32 colour)
{
    return drawZurich(gdl,
                      xr - measureTextFont(str, ptrFontZurichBoldChars, ptrFontZurichBold),
                      y, str, colour);
}

static void fitZurich(const char *src, s32 maxWidth, char *out, int outN)
{
    const char *localized = ascensionLocaleText(src ? src : "");
    if (outN <= 0) return;
    snprintf(out, outN, "%s", localized);
    if (measureTextRaw(out, ptrFontZurichBoldChars, ptrFontZurichBold) <= maxWidth)
        return;

    int len = (int)strlen(out);
    while (len > 4) {
        len--;
        out[len] = '\0';
        if (len + 4 < outN) {
            out[len] = '.';
            out[len + 1] = '.';
            out[len + 2] = '.';
            out[len + 3] = '\0';
        }
        if (measureTextRaw(out, ptrFontZurichBoldChars, ptrFontZurichBold) <= maxWidth)
            return;
        out[len] = '\0';
    }
}

static void valueText(const struct Row *r, char *out, int n)
{
    if (r->kind == ROW_ACTION) {
        if (pendingActionIs(r->action))
            snprintf(out, n, "CONFIRM");
        else if (r->action == ACTION_RESET)
            snprintf(out, n, "RESET");
        else
            snprintf(out, n, "RESTART");
        return;
    }

    if (r->kind == ROW_RES) {
        if (videoIsFullscreen()) {
            snprintf(out, n, "FULLSCREEN");
        } else if (s_resFitN <= 0) {
            snprintf(out, n, "N/A");
        } else {
            int i = s_resFit[s_resSel];
            snprintf(out, n, "%d x %d", kResList[i][0], kResList[i][1]);
        }
        return;
    }

    double v = rowGet(r);

    if ((r->kind == ROW_TOGGLE || r->kind == ROW_ENUM) && r->names) {
        int idx = (int)lround(v);
        int cnt = 0;
        while (r->names[cnt]) cnt++;
        if (idx >= 0 && idx < cnt) {
            snprintf(out, n, "%s", r->names[idx]);
            return;
        }
    }

    if (r->kind == ROW_MSAA) {
        if ((int)lround(v) <= 1) snprintf(out, n, "OFF");
        else snprintf(out, n, "%dx", (int)lround(v));
        return;
    }

    if (strcmp(r->key, "Video.FpsCap") == 0 && (int)lround(v) == 0) {
        snprintf(out, n, "OFF");
        return;
    }

    if (r->kind == ROW_SLIDER && r->type == CONFIG_OPT_FLOAT) {
        snprintf(out, n, "%.2f", v);
        return;
    }

    snprintf(out, n, "%d", (int)lround(v));
}

static void fpsTick(void)
{
    static uint64_t winStartUs;
    static int frames;
    uint64_t nowUs = sysGetMicroseconds();
    if (!winStartUs) {
        winStartUs = nowUs;
        return;
    }
    frames++;
    uint64_t dtUs = nowUs - winStartUs;
    if (dtUs >= 500000) {
        int fps = (int)((double)frames * 1000000.0 / (double)dtUs + 0.5);
        snprintf(s_fpsText, sizeof(s_fpsText), "%d FPS", fps);
        frames = 0;
        winStartUs = nowUs;
    }
}

static void tabBounds(int cat, s32 *x0, s32 *x1)
{
    s32 left = OV_PANEL_X0 + 5;
    s32 right = OV_PANEL_X1 - 27;
    s32 width = right - left;
    *x0 = left + (width * cat) / 4;
    *x1 = left + (width * (cat + 1)) / 4;
}

Gfx *optionsOverlayEmit(void)
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

        /* Do not redesign the excellent native folder screen.  Only sign it. */
        if (showBrand) {
            s32 sigW = measureTextFont(ASCENSION_SIGNATURE,
                                       ptrFontBankGothicChars, ptrFontBankGothic);
            gdl = fillRect(gdl, W - sigW - 13, 4, W - 6, 19,
                           4, 5, 6, 176);
            gdl = fillRect(gdl, W - sigW - 13, 19, W - 6, 20,
                           235, 216, 121, 210);
            if (!s_controlHintSeen)
                gdl = fillRect(gdl, 6, 5, 106, 20, 4, 5, 6, 176);
        }

        /* Geometry is complete before text state. */
        gdl = microcode_constructor(gdl);

        if (showBrand) {
            gdl = drawGothic(gdl,
                             W - measureTextFont(ASCENSION_SIGNATURE,
                                                 ptrFontBankGothicChars,
                                                 ptrFontBankGothic) - 10,
                             8, ASCENSION_SIGNATURE, 0xEBD879FFu);
            if (!s_controlHintSeen)
                gdl = drawZurich(gdl, 10, 9, "F10  OPTIONS", 0xE8E2D3FFu);
        }
        if (showFps)
            gdl = drawZurichR(gdl, W - 8, 24, s_fpsText, 0x93C997FFu);

        gDPPipeSync(gdl++);
        gSPEndDisplayList(gdl++);
        return s_buf;
    }

    ensureSelectionVisible();

    const s32 W = viGetX();
    const s32 H = viGetY();
    const int activeCat = rows[s_sel].category;
    const int vis = visibleRows();
    const int listBottom = OV_LIST_TOP + vis * OV_ROW_H;
    const int helpTop = overlayHelpTop();

    s32 bx0, bx1;
    sliderBarSpan(&bx0, &bx1);

    Gfx *gdl = s_buf;
    gDPPipeSync(gdl++);
    gDPSetCycleType(gdl++, G_CYC_1CYCLE);
    gDPSetTexturePersp(gdl++, G_TP_NONE);
    gDPSetScissor(gdl++, G_SC_NON_INTERLACE, 0, 0, W, H);

    /* ---------------- geometry pass: no text is emitted here ------------- */
    gdl = fillRect(gdl, 0, 0, W, H, 0, 0, 0, 142);
    gdl = fillRect(gdl, OV_PANEL_X0, OV_TOP,
                   OV_PANEL_X1, H - 8, 7, 8, 9, 230);

    /* restrained GoldenEye gold: structure + focus, never wallpaper */
    gdl = fillRect(gdl, OV_PANEL_X0, OV_TOP,
                   OV_PANEL_X1, OV_TOP + 1, 235, 216, 121, 236);
    gdl = fillRect(gdl, OV_PANEL_X0, OV_TAB_Y + OV_TAB_H,
                   OV_PANEL_X1, OV_TAB_Y + OV_TAB_H + 1, 70, 65, 48, 210);

    s32 tx0, tx1;
    tabBounds(activeCat, &tx0, &tx1);
    gdl = fillRect(gdl, tx0 + 3, OV_TAB_Y + OV_TAB_H - 1,
                   tx1 - 3, OV_TAB_Y + OV_TAB_H + 1,
                   235, 216, 121, 255);

    /* Close is deliberately quiet; F10/RMB are the primary escape routes. */
    gdl = fillRect(gdl, OV_CB_X0, OV_CB_Y0, OV_CB_X1, OV_CB_Y1,
                   25, 25, 24, 220);

    for (int i = s_scroll; i < s_scroll + vis && i < NUM_ROWS; ++i) {
        if (rows[i].category != activeCat)
            break;
        s32 y = rowY(i);

        if (i == s_sel) {
            gdl = fillRect(gdl, OV_PANEL_X0 + 6, y - 3,
                           OV_PANEL_X1 - 6, y + 17,
                           30, 29, 24, 238);
            gdl = fillRect(gdl, OV_PANEL_X0 + 6, y - 3,
                           OV_PANEL_X0 + 8, y + 17,
                           235, 216, 121, 255);
        }

        if (rows[i].kind == ROW_SLIDER && rows[i].found) {
            double lo = rowLo(&rows[i]);
            double hi = rowHi(&rows[i]);
            double f = hi > lo ? (rowGet(&rows[i]) - lo) / (hi - lo) : 0.0;
            if (f < 0) f = 0;
            if (f > 1) f = 1;
            s32 by = y + 12;
            gdl = fillRect(gdl, bx0, by, bx1, by + 2, 73, 72, 66, 220);
            gdl = fillRect(gdl, bx0, by,
                           bx0 + (s32)((bx1 - bx0) * f), by + 2,
                           235, 216, 121, 255);
        }
    }

    /* Context and footer separators. */
    gdl = fillRect(gdl, OV_PANEL_X0 + 7, helpTop - 4,
                   OV_PANEL_X1 - 7, helpTop - 3, 65, 62, 52, 205);
    gdl = fillRect(gdl, OV_PANEL_X0, H - OV_FOOTER_H - 8,
                   OV_PANEL_X1, H - OV_FOOTER_H - 7, 65, 62, 52, 205);

    /* small scroll thumb -- page state, not decoration */
    {
        int first, last;
        categoryBounds(activeCat, &first, &last);
        int count = last >= first ? last - first + 1 : 0;
        if (count > vis) {
            int trackY0 = OV_LIST_TOP;
            int trackY1 = listBottom - 5;
            int trackH = trackY1 - trackY0;
            int thumbH = (trackH * vis) / count;
            if (thumbH < 8) thumbH = 8;
            int max = maxScroll();
            int span = max - first;
            int thumbY = trackY0;
            if (span > 0)
                thumbY += ((trackH - thumbH) * (s_scroll - first)) / span;
            gdl = fillRect(gdl, OV_PANEL_X1 - 5, trackY0,
                           OV_PANEL_X1 - 4, trackY1, 55, 54, 50, 170);
            gdl = fillRect(gdl, OV_PANEL_X1 - 5, thumbY,
                           OV_PANEL_X1 - 4, thumbY + thumbH,
                           235, 216, 121, 230);
        }
    }

    /* ---------------- text pass: NEVER issue fillRect after this ---------- */
    gdl = microcode_constructor(gdl);

    gdl = drawZurich(gdl, OV_PANEL_X0 + 8, OV_HEADER_Y,
                     "Q WATCH / SYSTEM CONFIGURATION", 0xEBD879FFu);
    gdl = drawGothic(gdl,
                     OV_CB_X0 - measureTextFont(ASCENSION_SIGNATURE,
                                                ptrFontBankGothicChars,
                                                ptrFontBankGothic) - 7,
                     OV_HEADER_Y, ASCENSION_SIGNATURE, 0x9B8749FFu);
    gdl = drawZurich(gdl, OV_CB_X0 + 5, OV_HEADER_Y, "X", 0xE8E2D3FFu);

    for (int cat = CAT_DISPLAY; cat <= CAT_SYSTEM; ++cat) {
        s32 x0, x1;
        tabBounds(cat, &x0, &x1);
        const char *name = categoryName(cat);
        s32 tw = measureTextFont(name, ptrFontZurichBoldChars, ptrFontZurichBold);
        s32 x = x0 + ((x1 - x0) - tw) / 2;
        gdl = drawZurich(gdl, x, OV_TAB_Y + 3, name,
                         cat == activeCat ? 0xEEE8D8FFu : 0x858A86FFu);
    }

    gdl = drawZurich(gdl, OV_LABEL_X, OV_SECTION_Y,
                     categorySub(activeCat), 0x9B8749FFu);

    for (int i = s_scroll; i < s_scroll + vis && i < NUM_ROWS; ++i) {
        if (rows[i].category != activeCat)
            break;
        s32 y = rowY(i);
        char val[48];
        char label[96];
        valueText(&rows[i], val, sizeof(val));

        int maxLabel = OV_RIGHT - OV_NUM_W - OV_LABEL_X - 12;
        if (rows[i].kind == ROW_SLIDER)
            maxLabel = bx0 - OV_LABEL_X - 8;
        fitZurich(rows[i].label, maxLabel, label, sizeof(label));

        u32 labelCol = rows[i].found
                     ? (i == s_sel ? 0xEEE8D8FFu : 0xC8C2B3FFu)
                     : 0x71736FFFu;
        u32 valueCol = i == s_sel ? 0xEBD879FFu : 0xC8C2B3FFu;

        gdl = drawZurich(gdl, OV_LABEL_X, y, label, labelCol);
        if (!rows[i].found) {
            gdl = drawZurichR(gdl, OV_RIGHT, y, "N/A", 0x71736FFFu);
            continue;
        }

        if (rows[i].kind == ROW_ACTION && rows[i].action == ACTION_RESET)
            valueCol = i == s_sel ? 0xD68A7DFFu : 0xA96E65FFu;
        gdl = drawZurichR(gdl, OV_RIGHT, y, val, valueCol);

        if (rows[i].restart && rows[i].kind != ROW_ACTION)
            gdl = drawZurichR(gdl, OV_RIGHT, y + 11, "RESTART", 0x9B8749FFu);
    }

    {
        char help[160];
        const char *status = statusText();
        fitZurich(status ? status : (rows[s_sel].help ? rows[s_sel].help : "PC settings"),
                  OV_PANEL_X1 - OV_PANEL_X0 - 24,
                  help, sizeof(help));
        gdl = drawZurich(gdl, OV_LABEL_X, helpTop + 3, help,
                         status ? 0xEBD879FFu : 0x858A86FFu);
    }

    gdl = drawZurich(gdl, OV_LABEL_X, H - OV_FOOTER_H - 2,
                     "LMB SELECT/DRAG   RMB BACK   W/S NAV   A/D ADJUST",
                     0x858A86FFu);
    gdl = drawZurichR(gdl, OV_RIGHT, H - OV_FOOTER_H - 2,
                      "F10 CLOSE", 0x9B8749FFu);

    gDPPipeSync(gdl++);
    gSPEndDisplayList(gdl++);

    if ((gdl - s_buf) > OV_BUF_CMDS)
        sysLogPrintf(LOG_ERROR, "optionsoverlay: DL overflow (%d)",
                     (int)(gdl - s_buf));
    return s_buf;
}
'''


def patch(text: str) -> str:
    # V2 is intentionally a migration from the already-reviewed V1 stack.
    required_v1 = [
        "Input.ModernDirectLook",
        "CAT_SYSTEM",
        "MI6 CLASSIFIED ARCHIVES",
        "Q BRANCH SYSTEMS",
    ]
    if "Ascension UI Overhaul V2 - Q Watch compact settings" in text:
        return text
    missing = [x for x in required_v1 if x not in text]
    if missing:
        raise PatchError("V1 UI stack missing: " + ", ".join(missing))

    # Use the same Zurich face the native file-select screen already uses for
    # folder text.  Gothic remains available only for the Ascension signature.
    old_fonts = '''extern struct font     *ptrFontBankGothic;
extern struct fontchar *ptrFontBankGothicChars;'''
    new_fonts = '''extern struct font     *ptrFontBankGothic;
extern struct fontchar *ptrFontBankGothicChars;
extern struct font     *ptrFontZurichBold;
extern struct fontchar *ptrFontZurichBoldChars;'''
    text = replace_once(text, old_fonts, new_fonts, "Zurich font externs")

    # Compact responsive geometry replaces V1's sidebar + paper sheet.
    text = regex_once(
        text,
        r'/\* ---- layout ------------------------------------------------------------ \*/.*?/\* ---- feedback ---------------------------------------------------------- \*/',
        LAYOUT,
        "compact layout",
    )

    # V1 input already has category click logic; point it at the top tabs.
    text = text.replace("sidebarCategoryAt", "tabCategoryAt")

    # Right mouse has one consistent meaning across GoldenEye menus: back.
    rmb_pattern = (
        r'\n\s*if \(rmb && !prevRmb && hoverRow >= 0 &&\s*'
        r'rows\[hoverRow\]\.kind != ROW_ACTION && ox >= bx0\)\s*'
        r'rowAdjust\(&rows\[hoverRow\], -1\);'
    )
    if re.search(rmb_pattern, text, flags=re.S):
        text = re.sub(
            rmb_pattern,
            '\n\n        if (rmb && !prevRmb) {\n'
            '            optionsOverlayToggle();\n'
            '            return;\n'
            '        }',
            text,
            count=1,
            flags=re.S,
        )
    elif "if (rmb && !prevRmb) {\n            optionsOverlayToggle();" not in text:
        raise PatchError("unexpected RMB handling")

    # Everything below the drawing boundary is presentation. Replacing it as
    # one unit avoids incremental render-state bugs and leaves config behavior
    # above this boundary untouched.
    marker = "/* ---- drawing ----------------------------------------------------------- */"
    pos = text.find(marker)
    if pos < 0:
        raise PatchError("drawing boundary not found")
    text = text[:pos] + DRAWING

    # Hard postconditions based on the failure modes seen in V1.
    must = [
        "Ascension UI Overhaul V2 - Q Watch compact settings",
        "ptrFontZurichBold",
        "tabCategoryAt",
        "OV_MAX_VISIBLE    7",
        "Q WATCH / SYSTEM CONFIGURATION",
        "Geometry is complete before text state",
        "text pass: NEVER issue fillRect after this",
        "RMB BACK",
    ]
    for needle in must:
        if needle not in text:
            raise PatchError(f"postcondition missing {needle!r}")

    forbidden = [
        "OV_SIDE_W",
        "FIELD NOTE",
        "TECHNOLOGY IN SERVICE",
        "ACTIVE DOSSIER / FILE",
    ]
    for needle in forbidden:
        if needle in text:
            raise PatchError(f"V1 visual residue remains: {needle!r}")

    # Render-state invariant: after the text-pass marker, rectangles are banned.
    tail = text.split("text pass: NEVER issue fillRect after this", 1)[1]
    if "fillRect(gdl" in tail:
        raise PatchError("rectangle primitive found after text-state setup")

    return text


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="validate without writing")
    ap.add_argument("--no-backup", action="store_true", help="do not write .before-ui-v2 backup")
    args = ap.parse_args()

    original = OV.read_text(encoding="utf-8")
    try:
        updated = patch(original)
    except PatchError as exc:
        raise SystemExit(f"ERROR: {exc}; no file written")

    if args.check:
        print("Ascension UI Overhaul V2 preflight: PASS")
        print("GoldenEye-native compact layout: PASS")
        print("Zurich body typography: PASS")
        print("Geometry/text render-state isolation: PASS")
        print("Would update:", OV.relative_to(ROOT) if updated != original else "nothing")
        return 0

    if updated != original:
        if not args.no_backup:
            backup = OV.with_suffix(OV.suffix + ".before-ui-v2")
            if not backup.exists():
                backup.write_text(original, encoding="utf-8")
                print("BACKUP:", backup.relative_to(ROOT))
        OV.write_text(updated, encoding="utf-8")
        print("UPDATED:", OV.relative_to(ROOT))
    else:
        print("No changes needed; UI Overhaul V2 already applied.")

    print("Compact Q-Watch settings interface installed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
