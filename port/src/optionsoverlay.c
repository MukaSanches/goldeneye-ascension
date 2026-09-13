/*
 * GoldenEye Ascension F10 options overlay.
 *
 * Port-layer only. No original front-end/game menu code is replaced. The
 * overlay appends its own small 2D display list after the game DL and edits
 * registered port config values in-place. Categories keep the UI usable as
 * Ascension grows instead of turning F10 into one long developer list.
 */

#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <SDL.h>

#include <PR/ultratypes.h>
#ifndef _SHIFTL
#define _SHIFTL(v, s, w) ((u32)(((u32)(v) & ((0x01 << (w)) - 1)) << (s)))
#define _SHIFTR(v, s, w) ((u32)(((u32)(v) >> (s)) & ((0x01 << (w)) - 1)))
#endif
#include <PR/gbi.h>

#include "platform.h"
#include "system.h"
#include "config.h"
#include "video.h"
#include "input.h"
#include "human_ai.h"
#include "optionsoverlay.h"

struct font;
struct fontchar;
extern struct font     *ptrFontBankGothic;
extern struct fontchar *ptrFontBankGothicChars;
extern Gfx  *microcode_constructor(Gfx *gdl);
extern Gfx  *textRender(Gfx *gdl, s32 *x, s32 *y, char *text, struct fontchar *chars,
                        struct font *font, u32 colour, s32 width, s32 height,
                        u32 yOffset, s32 lineheight);
extern void  textMeasure(s32 *textheight, s32 *textwidth, char *text,
                         struct fontchar *chars, struct font *font, s32 lineheight);
extern s16   viGetX(void);
extern s16   viGetY(void);

/* ------------------------------------------------------------------------- */

enum RowKind {
    ROW_TOGGLE,
    ROW_SLIDER,
    ROW_ENUM,
    ROW_MSAA,
    ROW_RES
};

enum Category {
    CAT_GAMEPLAY = 0,
    CAT_AI,
    CAT_VIDEO,
    CAT_CONTROLS,
    CAT_INTERFACE,
    CAT_ADVANCED,
    CAT_COUNT
};

static const char *const kCategoryNames[CAT_COUNT] = {
    "GAME", "AI", "VIDEO", "INPUT", "UI", "ADV"
};

static const char *const kOnOff[]       = { "OFF", "ON", NULL };
static const char *const kClassicHuman[]= { "CLASSIC", "HUMAN", NULL };
static const char *const kTexFilter[]   = { "NEAREST", "BILINEAR", "3-POINT", NULL };
static const char *const kCapture[]     = { "ALWAYS", "CLICK LOCK", NULL };
static const char *const kPointer[]     = { "LEGACY", "1:1", NULL };
static const char *const kInputPath[]   = { "OS", "RAW", NULL };
static const int         kMsaaSeq[]     = { 1, 2, 4, 8 };

static const int kResList[][2] = {
    {  640,  480 }, {  800,  600 }, {  960,  720 }, { 1024,  768 },
    { 1152,  864 }, { 1280,  720 }, { 1280,  800 }, { 1280,  960 },
    { 1366,  768 }, { 1440,  900 }, { 1600,  900 }, { 1600, 1200 },
    { 1680, 1050 }, { 1920, 1080 }, { 1920, 1200 }, { 2560, 1440 },
    { 3200, 1800 }, { 3840, 2160 },
};
#define NUM_RES ((int)(sizeof(kResList) / sizeof(kResList[0])))
static int s_resFit[NUM_RES];
static int s_resFitN = 0;
static int s_resSel = 0;

struct Row {
    int                category;
    const char        *key;
    const char        *label;
    int                kind;
    double             step;
    const char *const *names;
    int                restart;
    double             uiMin, uiMax;

    int                found;
    int                type;
    void              *ptr;
    double             cfgMin, cfgMax;
};

#define R(cat,key,label,kind,step,names,restart,lo,hi) \
    { cat, key, label, kind, step, names, restart, lo, hi, 0,0,NULL,0,0 }

static struct Row rows[] = {
    /* Gameplay: player-facing behaviour/QoL only. */
    R(CAT_GAMEPLAY, "Game.ScreenShakeIntensity", "Screen shake",      ROW_SLIDER, 0.25, NULL, 0, 0, 3),
    R(CAT_GAMEPLAY, "Game.SkipIntro",            "Skip intro",        ROW_TOGGLE, 1,    kOnOff, 0, 0, 0),
    R(CAT_GAMEPLAY, "Game.NoHitFlash",           "Disable hit flash", ROW_TOGGLE, 1,    kOnOff, 0, 0, 0),

    /* AI: Human is a real game mode, not a hidden debug switch. */
    R(CAT_AI, "AI.HumanMode",    "Enemy AI",         ROW_ENUM,   1,   kClassicHuman, 0, 0, 0),
    R(CAT_AI, "AI.Intensity",    "Human intensity",  ROW_SLIDER, 0.1, NULL,          0, 0.5, 2.0),
    R(CAT_AI, "AI.MaxTactical",  "Tactical actors",  ROW_SLIDER, 1,   NULL,          0, 1, 10),

    /* Video. */
    R(CAT_VIDEO, "Video.Fullscreen",    "Fullscreen",     ROW_TOGGLE, 1,  kOnOff,     0, 0, 0),
    R(CAT_VIDEO, "__Resolution",        "Resolution",     ROW_RES,    0,  NULL,       0, 0, 0),
    R(CAT_VIDEO, "Video.VSync",         "VSync",          ROW_TOGGLE, 1,  kOnOff,     0, 0, 0),
    R(CAT_VIDEO, "Video.FpsCap",        "Frame cap",      ROW_SLIDER, 10, NULL,       0, 0, 360),
    R(CAT_VIDEO, "Video.MSAA",          "MSAA",           ROW_MSAA,   0,  NULL,       1, 0, 0),
    R(CAT_VIDEO, "Video.TextureFilter", "Texture filter", ROW_ENUM,   1,  kTexFilter, 0, 0, 0),
    R(CAT_VIDEO, "Video.Anisotropy",    "Anisotropic",    ROW_SLIDER, 1,  NULL,       0, 1, 16),
    R(CAT_VIDEO, "Video.FovScale",      "FOV",            ROW_SLIDER, 5,  NULL,       0, 50, 150),

    /* Controls: only settings that a normal player can understand/use. */
    R(CAT_CONTROLS, "Input.MouseEnabled",       "Mouse",             ROW_TOGGLE, 1,   kOnOff,     0, 0, 0),
    R(CAT_CONTROLS, "Input.MouseAimSpeed",      "Aim sensitivity",   ROW_SLIDER, 2,   NULL,       0, 1, 200),
    R(CAT_CONTROLS, "Input.MouseTurnSpeed",     "Turn sensitivity",  ROW_SLIDER, 5,   NULL,       0, 1, 200),
    R(CAT_CONTROLS, "Input.MouseYScale",        "Vertical scale",    ROW_SLIDER, 5,   NULL,       0, 1, 200),
    R(CAT_CONTROLS, "Input.MouseSmoothing",     "Mouse smoothing",   ROW_SLIDER, 5,   NULL,       0, 0, 90),
    R(CAT_CONTROLS, "Input.MouseRawInput",      "Mouse input",       ROW_ENUM,   1,   kInputPath, 0, 0, 0),
    R(CAT_CONTROLS, "Input.MouseInvertY",       "Invert mouse Y",    ROW_TOGGLE, 1,   kOnOff,     0, 0, 0),
    R(CAT_CONTROLS, "Input.MouseCaptureMode",   "Mouse capture",     ROW_ENUM,   1,   kCapture,   0, 0, 0),
    R(CAT_CONTROLS, "Input.PadDeadzone",        "Gamepad deadzone",  ROW_SLIDER, 500, NULL,       0, 0, 30000),
    R(CAT_CONTROLS, "Input.PadTriggerPct",      "Trigger threshold", ROW_SLIDER, 2,   NULL,       0, 1, 99),
    R(CAT_CONTROLS, "Input.PadLookInvertY",     "Invert pad Y",      ROW_TOGGLE, 1,   kOnOff,     0, 0, 0),

    /* Interface / front-end feel. */
    R(CAT_INTERFACE, "Video.DisplayFPS",       "Show FPS",           ROW_TOGGLE, 1, kOnOff,   0, 0, 0),
    R(CAT_INTERFACE, "Input.MenuPointerMode",  "Menu pointer",       ROW_ENUM,   1, kPointer, 0, 0, 0),
    R(CAT_INTERFACE, "Input.MenuPointerSpeed", "Pointer speed",      ROW_SLIDER, 10,NULL,     0, 10, 300),

    /* Advanced: deliberately separated from normal player-facing controls. */
    R(CAT_ADVANCED, "Video.FixMipTextures",     "Mip texture fix",     ROW_TOGGLE, 1,  kOnOff, 0, 0, 0),
    R(CAT_ADVANCED, "Video.WrapFix",            "Texture wrap fix",    ROW_TOGGLE, 1,  kOnOff, 0, 0, 0),
    R(CAT_ADVANCED, "Input.AimBand",            "Aim analog band",     ROW_SLIDER, 1,  NULL,   0, 5, 40),
    R(CAT_ADVANCED, "Input.HipfirePitchSpeed",  "Hipfire pitch",       ROW_SLIDER, 10, NULL,   0, 10, 300),
    R(CAT_ADVANCED, "AI.Debug",                 "Human AI debug log",  ROW_TOGGLE, 1,  kOnOff, 0, 0, 0),
};
#undef R
#define NUM_ROWS ((int)(sizeof(rows) / sizeof(rows[0])))

static int s_inited = 0;
static volatile int s_open = 0;
static int s_category = CAT_GAMEPLAY;
static int s_sel = 0; /* index inside active category, not rows[] */

static int s_showFps = 0;
static char s_fpsText[16] = "";

PD_CONSTRUCTOR static void overlayConfigInit(void)
{
    configRegisterInt("Video.DisplayFPS", &s_showFps, 0, 1);
}

/* ------------------------------------------------------------------------- */

static void fpsTick(void)
{
    static uint64_t winStartUs = 0;
    static int frames = 0;
    uint64_t nowUs = sysGetMicroseconds();

    if (winStartUs == 0) {
        winStartUs = nowUs;
        return;
    }
    frames++;
    if (nowUs - winStartUs >= 500000) {
        int fps = (int)((double)frames * 1000000.0 / (double)(nowUs - winStartUs) + 0.5);
        snprintf(s_fpsText, sizeof(s_fpsText), "%d FPS", fps);
        winStartUs = nowUs;
        frames = 0;
    }
}

static int categoryRowCount(int category)
{
    int n = 0;
    for (int i = 0; i < NUM_ROWS; ++i) if (rows[i].category == category) ++n;
    return n;
}

static struct Row *categoryRow(int category, int index)
{
    int n = 0;
    for (int i = 0; i < NUM_ROWS; ++i) {
        if (rows[i].category != category) continue;
        if (n++ == index) return &rows[i];
    }
    return NULL;
}

static void normalizeSelection(void)
{
    int n = categoryRowCount(s_category);
    if (n <= 0) { s_sel = 0; return; }
    if (s_sel < 0) s_sel = n - 1;
    if (s_sel >= n) s_sel = 0;
}

static void changeCategory(int dir)
{
    s_category += dir >= 0 ? 1 : -1;
    if (s_category < 0) s_category = CAT_COUNT - 1;
    if (s_category >= CAT_COUNT) s_category = 0;
    s_sel = 0;
    normalizeSelection();
}

/* ------------------------------------------------------------------------- */
/* Layout: category tabs solve the old 13-row hard limit.                    */

#define OV_X0         14
#define OV_LABEL_X    22
#define OV_TOP         8
#define OV_LINE       15
#define OV_TAB_Y      (OV_TOP + 15)
#define OV_HINT_Y     (OV_TOP + 30)
#define OV_ROWS_Y     (OV_TOP + 47)
#define OV_ROW_Y(i)   (OV_ROWS_Y + (i) * OV_LINE)
#define OV_RIGHT      (viGetX() - OV_X0)
#define OV_NUM_W      38
#define OV_BAR_X      148
#define OV_CB_X0      (OV_RIGHT - 14)
#define OV_CB_X1      (OV_RIGHT + 6)
#define OV_CB_Y0      (OV_TOP - 3)
#define OV_CB_Y1      (OV_TOP + 11)

static void sliderBarSpan(s32 *x0, s32 *x1)
{
    *x0 = OV_BAR_X;
    *x1 = OV_RIGHT - OV_NUM_W;
    if (*x1 < *x0 + 16) *x1 = *x0 + 16;
}

static int overlayRowAtY(double oy)
{
    int n = categoryRowCount(s_category);
    for (int i = 0; i < n; ++i) {
        double top = OV_ROW_Y(i) - 3;
        if (oy >= top && oy < top + OV_LINE) return i;
    }
    return -1;
}

static int overlayInCloseBox(double ox, double oy)
{
    return ox >= OV_CB_X0 && ox <= OV_CB_X1 && oy >= OV_CB_Y0 && oy <= OV_CB_Y1;
}

static int overlayTabAtX(double ox)
{
    int left = OV_X0;
    int right = OV_RIGHT - 20;
    int width = right - left;
    if (width <= 0 || ox < left || ox > right) return -1;
    int tab = (int)((ox - left) * CAT_COUNT / width);
    return tab >= 0 && tab < CAT_COUNT ? tab : -1;
}

/* ------------------------------------------------------------------------- */

static void resolveCb(const char *key, int type, void *ptr, double min, double max,
                      double step, const char *label, const char *const *names,
                      void *ctx)
{
    (void)step; (void)label; (void)names; (void)ctx;
    for (int i = 0; i < NUM_ROWS; ++i) {
        if (strcmp(rows[i].key, key) == 0) {
            rows[i].found = 1;
            rows[i].type = type;
            rows[i].ptr = ptr;
            rows[i].cfgMin = min;
            rows[i].cfgMax = max;
        }
    }
}

static void overlayInit(void)
{
    if (s_inited) return;
    s_inited = 1;

    for (int i = 0; i < NUM_ROWS; ++i) {
        if (rows[i].kind != ROW_RES)
            configSetOptionMeta(rows[i].key, rows[i].label, rows[i].step, rows[i].names);
    }
    configForEachOption(resolveCb, NULL);

    for (int i = 0; i < NUM_ROWS; ++i) {
        if (rows[i].kind == ROW_RES) {
            rows[i].found = 1;
            continue;
        }
        if (!rows[i].found)
            sysLogPrintf(LOG_WARNING, "optionsoverlay: option '%s' not registered", rows[i].key);
    }

    {
        int dw = 1920, dh = 1080;
        videoGetDesktopSize(&dw, &dh);
        for (int i = 0; i < NUM_RES; ++i) {
            if (kResList[i][0] <= dw && kResList[i][1] <= dh)
                s_resFit[s_resFitN++] = i;
        }
        if (s_resFitN == 0) s_resFit[s_resFitN++] = 0;

        int cw = 0, ch = 0;
        videoGetWindowSize(&cw, &ch);
        long best = -1;
        for (int k = 0; k < s_resFitN; ++k) {
            int i = s_resFit[k];
            long d = labs((long)kResList[i][0] - cw) + labs((long)kResList[i][1] - ch);
            if (best < 0 || d < best) { best = d; s_resSel = k; }
        }
    }

    const char *e = getenv("GE_OPTIONSOVERLAY");
    if (e && atoi(e) != 0) {
        s_open = 1;
        sysLogPrintf(LOG_INFO, "optionsoverlay: auto-opened (GE_OPTIONSOVERLAY)");
    }
}

static double rowGet(const struct Row *r)
{
    if (!r->found || !r->ptr) return 0.0;
    switch (r->type) {
    case CONFIG_OPT_INT:   return (double)*(int *)r->ptr;
    case CONFIG_OPT_UINT:  return (double)*(unsigned int *)r->ptr;
    case CONFIG_OPT_FLOAT: return (double)*(float *)r->ptr;
    default:               return 0.0;
    }
}

static double rowLo(const struct Row *r)
{
    return r->uiMin != r->uiMax ? r->uiMin : r->cfgMin;
}

static double rowHi(const struct Row *r)
{
    return r->uiMin != r->uiMax ? r->uiMax : r->cfgMax;
}

static void rowSet(struct Row *r, double v)
{
    if (!r || !r->found || !r->ptr) return;
    double lo = rowLo(r), hi = rowHi(r);
    if (lo != hi) {
        if (v < lo) v = lo;
        if (v > hi) v = hi;
    }

    switch (r->type) {
    case CONFIG_OPT_INT:   *(int *)r->ptr = (int)lround(v); break;
    case CONFIG_OPT_UINT:  *(unsigned int *)r->ptr = (unsigned int)(v < 0 ? 0 : lround(v)); break;
    case CONFIG_OPT_FLOAT: *(float *)r->ptr = (float)v; break;
    default: return;
    }

    /* AI.HumanMode has lifecycle work (restore/apply) beyond changing config. */
    if (strcmp(r->key, "AI.HumanMode") == 0) {
        humanAiSetEnabled(v != 0.0);
    }

    if (strcmp(r->key, "Video.Fullscreen") == 0) {
        videoRequestFullscreen((int)lround(v));
    } else if (strncmp(r->key, "Video.", 6) == 0 && !r->restart) {
        videoRequestLiveConfig();
    }
}

static void rowAdjust(struct Row *r, int dir)
{
    if (!r || !r->found) return;
    double v = rowGet(r);

    switch (r->kind) {
    case ROW_TOGGLE:
        rowSet(r, v != 0.0 ? 0.0 : 1.0);
        break;
    case ROW_MSAA: {
        int idx = 0;
        for (int i = 0; i < 4; ++i) if (kMsaaSeq[i] == (int)lround(v)) idx = i;
        idx += dir >= 0 ? 1 : -1;
        if (idx < 0) idx = 0;
        if (idx > 3) idx = 3;
        rowSet(r, (double)kMsaaSeq[idx]);
        break;
    }
    case ROW_ENUM: {
        double lo = r->cfgMin, hi = r->cfgMax;
        v += dir >= 0 ? 1.0 : -1.0;
        if (v < lo) v = hi;
        if (v > hi) v = lo;
        rowSet(r, v);
        break;
    }
    case ROW_RES: {
        if (s_resFitN <= 0 || videoIsFullscreen()) break;
        s_resSel += dir >= 0 ? 1 : -1;
        if (s_resSel < 0) s_resSel = s_resFitN - 1;
        if (s_resSel >= s_resFitN) s_resSel = 0;
        int i = s_resFit[s_resSel];
        videoRequestWindowSize(kResList[i][0], kResList[i][1]);
        break;
    }
    default:
        rowSet(r, v + (dir >= 0 ? r->step : -r->step));
        break;
    }
}

/* ------------------------------------------------------------------------- */

void optionsOverlayToggle(void)
{
    overlayInit();
    s_open = !s_open;
    normalizeSelection();
    sysLogPrintf(LOG_INFO, "optionsoverlay: %s", s_open ? "opened" : "closed");
    if (!s_open) configSave();
}

int optionsOverlayIsOpen(void)
{
    if (!s_inited) overlayInit();
    return s_open;
}

void optionsOverlayScroll(int dir)
{
    if (!s_open || dir == 0) return;
    int n = categoryRowCount(s_category);
    if (n <= 0) return;
    s_sel += dir > 0 ? -1 : 1;
    normalizeSelection();
}

static void sliderSetFromX(struct Row *r, double ox)
{
    double lo = rowLo(r), hi = rowHi(r);
    if (!r || hi <= lo) return;
    s32 bx0, bx1;
    sliderBarSpan(&bx0, &bx1);
    double f = (ox - bx0) / (double)(bx1 - bx0);
    if (f < 0) f = 0;
    if (f > 1) f = 1;
    double v = lo + f * (hi - lo);
    double step = r->step > 0.0 ? r->step : 1.0;
    v = lround(v / step) * step;
    rowSet(r, v);
}

void optionsOverlayHandleInput(void)
{
    static int prevUp, prevDn, prevLf, prevRt, prevTab, prevPgUp, prevPgDn;
    static int prevLmb, prevRmb;
    static int dragRow = -1;

    if (!s_open) {
        prevUp = prevDn = prevLf = prevRt = prevTab = prevPgUp = prevPgDn = 0;
        prevLmb = prevRmb = 0;
        dragRow = -1;
        return;
    }

    inputSuspendForOverlay();

    const Uint8 *ks = SDL_GetKeyboardState(NULL);
    int mx = 0, my = 0;
    Uint32 mb = SDL_GetMouseState(&mx, &my);
    int lmb = (mb & SDL_BUTTON(SDL_BUTTON_LEFT)) ? 1 : 0;
    int rmb = (mb & SDL_BUTTON(SDL_BUTTON_RIGHT)) ? 1 : 0;

    int up = ks[SDL_SCANCODE_UP] || ks[SDL_SCANCODE_KP_8];
    int dn = ks[SDL_SCANCODE_DOWN] || ks[SDL_SCANCODE_KP_2];
    int lf = ks[SDL_SCANCODE_LEFT] || ks[SDL_SCANCODE_KP_4];
    int rt = ks[SDL_SCANCODE_RIGHT] || ks[SDL_SCANCODE_KP_6] ||
             ks[SDL_SCANCODE_RETURN] || ks[SDL_SCANCODE_KP_ENTER];
    int tab = ks[SDL_SCANCODE_TAB];
    int pgup = ks[SDL_SCANCODE_PAGEUP];
    int pgdn = ks[SDL_SCANCODE_PAGEDOWN];

    int n = categoryRowCount(s_category);
    if (up && !prevUp && n > 0) { --s_sel; normalizeSelection(); }
    if (dn && !prevDn && n > 0) { ++s_sel; normalizeSelection(); }
    if (lf && !prevLf) rowAdjust(categoryRow(s_category, s_sel), -1);
    if (rt && !prevRt) rowAdjust(categoryRow(s_category, s_sel), +1);

    if (tab && !prevTab) changeCategory((SDL_GetModState() & KMOD_SHIFT) ? -1 : +1);
    if (pgup && !prevPgUp) changeCategory(-1);
    if (pgdn && !prevPgDn) changeCategory(+1);

    int ww = 0, wh = 0;
    videoGetWindowSize(&ww, &wh);
    if (ww > 0 && wh > 0) {
        double ox = (double)mx * (double)viGetX() / ww;
        double oy = (double)my * (double)viGetY() / wh;
        int hoverRow = overlayRowAtY(oy);
        int onClose = overlayInCloseBox(ox, oy);
        int tabHit = (oy >= OV_TAB_Y - 3 && oy < OV_TAB_Y + 12) ? overlayTabAtX(ox) : -1;

        if (hoverRow >= 0 && !onClose) s_sel = hoverRow;

        s32 bx0, bx1;
        sliderBarSpan(&bx0, &bx1);
        if (lmb && !prevLmb) {
            if (onClose) {
                optionsOverlayToggle();
                return;
            }
            if (tabHit >= 0) {
                s_category = tabHit;
                s_sel = 0;
                normalizeSelection();
                dragRow = -1;
            } else if (hoverRow >= 0 && ox >= bx0) {
                struct Row *r = categoryRow(s_category, hoverRow);
                if (r && r->kind == ROW_SLIDER && r->found) {
                    sliderSetFromX(r, ox);
                    dragRow = hoverRow;
                } else {
                    rowAdjust(r, +1);
                }
            }
        }

        if (lmb && dragRow >= 0) {
            struct Row *r = categoryRow(s_category, dragRow);
            if (r && r->kind == ROW_SLIDER) sliderSetFromX(r, ox);
        }
        if (!lmb) dragRow = -1;

        if (rmb && !prevRmb && hoverRow >= 0 && !onClose && ox >= bx0)
            rowAdjust(categoryRow(s_category, hoverRow), -1);
    }

    prevUp = up; prevDn = dn; prevLf = lf; prevRt = rt;
    prevTab = tab; prevPgUp = pgup; prevPgDn = pgdn;
    prevLmb = lmb; prevRmb = rmb;
}

/* ------------------------------------------------------------------------- */

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

static Gfx *drawText(Gfx *gdl, s32 x, s32 y, const char *str, u32 colour)
{
    s32 px = x, py = y;
    return textRender(gdl, &px, &py, (char *)str, ptrFontBankGothicChars,
                      ptrFontBankGothic, colour, viGetX(), viGetY(), 0, 0);
}

static s32 measureText(const char *str)
{
    s32 h = 0, w = 0;
    textMeasure(&h, &w, (char *)str, ptrFontBankGothicChars, ptrFontBankGothic, 0);
    return w;
}

static Gfx *drawTextR(Gfx *gdl, s32 xr, s32 y, const char *str, u32 colour)
{
    return drawText(gdl, xr - measureText(str), y, str, colour);
}

static void valueText(const struct Row *r, char *out, int n)
{
    double v = rowGet(r);

    if (r->kind == ROW_RES) {
        if (videoIsFullscreen()) snprintf(out, n, "FULLSCREEN");
        else if (s_resFitN <= 0) snprintf(out, n, "N/A");
        else {
            int i = s_resFit[s_resSel];
            snprintf(out, n, "%d x %d", kResList[i][0], kResList[i][1]);
        }
        return;
    }

    if ((r->kind == ROW_TOGGLE || r->kind == ROW_ENUM) && r->names) {
        int idx = (int)lround(v), count = 0;
        while (r->names[count]) ++count;
        if (idx >= 0 && idx < count) {
            snprintf(out, n, "%s", r->names[idx]);
            return;
        }
    }

    if (r->kind == ROW_MSAA) {
        if ((int)lround(v) <= 1) snprintf(out, n, "OFF");
        else snprintf(out, n, "%dx", (int)lround(v));
        return;
    }

    if (strcmp(r->key, "Game.ScreenShakeIntensity") == 0) {
        snprintf(out, n, "%d%%", (int)lround(v * 100.0));
    } else if (strcmp(r->key, "AI.Intensity") == 0) {
        snprintf(out, n, "%.1fx", v);
    } else if (strcmp(r->key, "Video.FpsCap") == 0 && (int)lround(v) == 0) {
        snprintf(out, n, "OFF");
    } else if (strcmp(r->key, "Video.FovScale") == 0 ||
               strcmp(r->key, "Input.MouseAimSpeed") == 0 ||
               strcmp(r->key, "Input.MouseTurnSpeed") == 0 ||
               strcmp(r->key, "Input.MouseYScale") == 0 ||
               strcmp(r->key, "Input.MouseSmoothing") == 0 ||
               strcmp(r->key, "Input.MenuPointerSpeed") == 0 ||
               strcmp(r->key, "Input.PadTriggerPct") == 0 ||
               strcmp(r->key, "Input.HipfirePitchSpeed") == 0) {
        snprintf(out, n, "%d%%", (int)lround(v));
    } else if (strcmp(r->key, "Input.PadDeadzone") == 0) {
        snprintf(out, n, "%d%%", (int)lround(v * 100.0 / 32767.0));
    } else if (strcmp(r->key, "Video.Anisotropy") == 0) {
        snprintf(out, n, "%dx", (int)lround(v));
    } else if (r->kind == ROW_SLIDER && r->type == CONFIG_OPT_FLOAT) {
        snprintf(out, n, "%.2f", v);
    } else {
        snprintf(out, n, "%d", (int)lround(v));
    }
}

Gfx *optionsOverlayEmit(void)
{
    if (!s_inited) overlayInit();
    fpsTick();

    if (!s_open) {
        if (!s_showFps || !s_fpsText[0]) return NULL;
        const s32 fw = viGetX(), fh = viGetY();
        Gfx *fgdl = s_buf;
        gDPPipeSync(fgdl++);
        gDPSetCycleType(fgdl++, G_CYC_1CYCLE);
        gDPSetTexturePersp(fgdl++, G_TP_NONE);
        gDPSetScissor(fgdl++, G_SC_NON_INTERLACE, 0, 0, fw, fh);
        fgdl = microcode_constructor(fgdl);
        fgdl = drawTextR(fgdl, fw - 6, 6, s_fpsText, 0x40ff60ff);
        gDPPipeSync(fgdl++);
        gSPEndDisplayList(fgdl++);
        return s_buf;
    }

    normalizeSelection();
    int activeRows = categoryRowCount(s_category);
    const s32 W = viGetX(), H = viGetY();
    const s32 right = OV_RIGHT;
    const s32 panelTop = OV_TOP - 6;
    s32 panelBottom = activeRows > 0 ? OV_ROW_Y(activeRows - 1) + OV_LINE - 3 : OV_ROWS_Y + 10;
    if (panelBottom > H - 4) panelBottom = H - 4;

    s32 bx0, bx1;
    sliderBarSpan(&bx0, &bx1);
    Gfx *gdl = s_buf;

    gDPPipeSync(gdl++);
    gDPSetCycleType(gdl++, G_CYC_1CYCLE);
    gDPSetTexturePersp(gdl++, G_TP_NONE);
    gDPSetScissor(gdl++, G_SC_NON_INTERLACE, 0, 0, W, H);

    /* Background / panel. */
    gdl = fillRect(gdl, 0, 0, W, H, 0, 0, 0, 150);
    gdl = fillRect(gdl, OV_X0 - 6, panelTop, W - (OV_X0 - 6), panelBottom, 7, 10, 21, 225);
    gdl = fillRect(gdl, OV_CB_X0, OV_CB_Y0, OV_CB_X1, OV_CB_Y1, 145, 35, 42, 240);

    /* Tabs. */
    int tabLeft = OV_X0, tabRight = OV_RIGHT - 20;
    int tabWidth = tabRight - tabLeft;
    for (int c = 0; c < CAT_COUNT; ++c) {
        int x0 = tabLeft + tabWidth * c / CAT_COUNT;
        int x1 = tabLeft + tabWidth * (c + 1) / CAT_COUNT - 1;
        if (c == s_category)
            gdl = fillRect(gdl, x0, OV_TAB_Y - 3, x1, OV_TAB_Y + 10, 48, 55, 106, 235);
        else
            gdl = fillRect(gdl, x0, OV_TAB_Y - 3, x1, OV_TAB_Y + 10, 22, 25, 42, 205);
    }

    for (int i = 0; i < activeRows; ++i) {
        struct Row *r = categoryRow(s_category, i);
        s32 rowY = OV_ROW_Y(i);
        if (i == s_sel)
            gdl = fillRect(gdl, OV_X0 - 2, rowY - 3, W - (OV_X0 - 2), rowY + OV_LINE - 4,
                           38, 45, 90, 220);
        if (r && r->kind == ROW_SLIDER && r->found) {
            double lo = rowLo(r), hi = rowHi(r);
            double f = hi > lo ? (rowGet(r) - lo) / (hi - lo) : 0.0;
            if (f < 0) f = 0; if (f > 1) f = 1;
            s32 by = rowY + 3;
            gdl = fillRect(gdl, bx0, by, bx1, by + 5, 55, 57, 67, 220);
            gdl = fillRect(gdl, bx0, by, bx0 + (s32)((bx1 - bx0) * f), by + 5,
                           211, 194, 76, 255);
        }
    }

    gdl = microcode_constructor(gdl);
    gdl = drawText(gdl, OV_X0, OV_TOP, "ASCENSION // OPTIONS", 0xffdf48ff);
    gdl = drawText(gdl, (OV_CB_X0 + OV_CB_X1) / 2 - measureText("X") / 2,
                   OV_TOP, "X", 0xffffffff);

    for (int c = 0; c < CAT_COUNT; ++c) {
        int x0 = tabLeft + tabWidth * c / CAT_COUNT;
        int x1 = tabLeft + tabWidth * (c + 1) / CAT_COUNT;
        int tw = measureText(kCategoryNames[c]);
        gdl = drawText(gdl, x0 + (x1 - x0 - tw) / 2, OV_TAB_Y,
                       kCategoryNames[c], c == s_category ? 0xffffffff : 0x9298a8ff);
    }

    gdl = drawText(gdl, OV_X0, OV_HINT_Y,
                   "TAB/PgUp/PgDn category  |  arrows/click value",
                   0x858c9cff);

    for (int i = 0; i < activeRows; ++i) {
        struct Row *r = categoryRow(s_category, i);
        if (!r) continue;
        s32 rowY = OV_ROW_Y(i);
        u32 col = i == s_sel ? 0xffffffff : 0xc5c8d0ff;
        char val[48];

        gdl = drawText(gdl, OV_LABEL_X, rowY, r->label, r->found ? col : 0x70747cff);
        if (!r->found) {
            gdl = drawTextR(gdl, right, rowY, "N/A", 0x70747cff);
            continue;
        }

        valueText(r, val, sizeof(val));
        if (r->restart) {
            gdl = drawText(gdl, bx0, rowY, val, col);
            gdl = drawTextR(gdl, right, rowY, "RESTART", 0x9498a0ff);
        } else {
            gdl = drawTextR(gdl, right, rowY, val, col);
        }
    }

    /* Human-AI status line: makes the reversible nature explicit. */
    if (s_category == CAT_AI) {
        const char *status = humanAiIsEnabled() ? "LIVE: HUMAN AI" : "LIVE: CLASSIC AI";
        gdl = drawTextR(gdl, right, OV_HINT_Y, status,
                        humanAiIsEnabled() ? 0x65ff86ff : 0x9ca2b0ff);
    }

    gDPPipeSync(gdl++);
    gSPEndDisplayList(gdl++);

    if ((gdl - s_buf) > OV_BUF_CMDS)
        sysLogPrintf(LOG_ERROR, "optionsoverlay: DL overflow (%d)", (int)(gdl - s_buf));
    return s_buf;
}
