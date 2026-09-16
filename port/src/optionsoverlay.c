/*
 * Ascension F10 control overlay.
 *
 * Port-layer only: this file never edits GoldenEye's original menu/gameplay
 * code. It draws a small fast3d display list after the game DL and edits only
 * options already registered by the PC port.
 *
 * 0.0.2 goals:
 *   - discoverable F10 entry point on file select;
 *   - compact DISPLAY / INPUT / GAMEPLAY grouping;
 *   - real scrolling that works at 240p and larger virtual viewports;
 *   - contextual help, safe ranges and visible apply/restart feedback;
 *   - explicit Reset PC settings and Restart game actions.
 */

#include <math.h>
#include <stdarg.h>
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
#include "optionsoverlay.h"

/* ---- game symbols used only for rendering/UI context ------------------- */
struct font;
struct fontchar;
extern struct font     *ptrFontBankGothic;
extern struct fontchar *ptrFontBankGothicChars;
extern Gfx  *microcode_constructor(Gfx *gdl);
extern Gfx  *textRender(Gfx *gdl, s32 *x, s32 *y, char *text,
                        struct fontchar *chars, struct font *font,
                        u32 colour, s32 width, s32 height,
                        u32 yOffset, s32 lineheight);
extern void  textMeasure(s32 *textheight, s32 *textwidth, char *text,
                         struct fontchar *chars, struct font *font,
                         s32 lineheight);

#include "ascension_version.h"
#include "ascension_locale.h"
extern s16   viGetX(void);
extern s16   viGetY(void);
extern int   current_menu;

#define GE_MENU_FILE_SELECT 5

/* ---- Ascension palette: port-owned UI only ----------------------------- */
#define ASC_UI_GOLD       0xD2B65CFFu
#define ASC_UI_GOLD_DIM   0x9B8749FFu
#define ASC_UI_IVORY      0xE8E2D3FFu
#define ASC_UI_TEXT       0xC8C2B3FFu
#define ASC_UI_SLATE      0x8D9396FFu
#define ASC_UI_DARK       0x080A0CFFu

enum RowKind {
    ROW_TOGGLE,
    ROW_SLIDER,
    ROW_ENUM,
    ROW_MSAA,
    ROW_RES,
    ROW_ACTION,
};

enum RowCategory {
    CAT_DISPLAY,
    CAT_INPUT,
    CAT_GAMEPLAY,
};

enum RowAction {
    ACTION_NONE,
    ACTION_RESET,
    ACTION_RESTART,
};

static const char *const kOnOff[]     = { "OFF", "ON", NULL };
static const char *const kTexFilter[] = { "NEAREST", "BILINEAR", "3-POINT", NULL };
static const char *const kCapture[]   = { "ALWAYS GRAB", "CLICK-TO-LOCK", NULL };
static const char *const kControlPreset[] = { "CLASSIC", "HYBRID", "MODERN", NULL };
static const char *const kLanguage[]  = { "ENGLISH", "PORTUGUESE (BRAZIL)", NULL };
static const int kMsaaSeq[] = { 1, 2, 4, 8 };

static const int kResList[][2] = {
    {  640,  480 }, {  800,  600 }, {  960,  720 }, { 1024,  768 },
    { 1152,  864 }, { 1280,  720 }, { 1280,  800 }, { 1280,  960 },
    { 1366,  768 }, { 1440,  900 }, { 1600,  900 }, { 1600, 1200 },
    { 1680, 1050 }, { 1920, 1080 }, { 1920, 1200 }, { 2560, 1440 },
    { 3200, 1800 }, { 3840, 2160 },
};
#define NUM_RES ((int)(sizeof(kResList) / sizeof(kResList[0])))

static int s_resFit[NUM_RES];
static int s_resFitN;
static int s_resSel;

struct Row {
    const char        *key;
    const char        *label;
    const char        *help;
    int                category;
    int                kind;
    double             step;
    const char *const *names;
    int                restart;
    double             uiMin, uiMax;
    double             resetValue;
    int                action;

    int                found;
    int                type;
    void              *ptr;
    double             cfgMin, cfgMax;
};

static struct Row rows[] = {
    /* DISPLAY */
    { .key="Video.Fullscreen",     .label="Fullscreen",
      .help="Windowed or fullscreen display.", .category=CAT_DISPLAY,
      .kind=ROW_TOGGLE, .step=1, .names=kOnOff, .resetValue=0 },

    { .key="__Resolution",         .label="Resolution",
      .help="Window size when not fullscreen.", .category=CAT_DISPLAY,
      .kind=ROW_RES },

    { .key="Video.VSync",          .label="VSync",
      .help="Reduces tearing. Applies now.", .category=CAT_DISPLAY,
      .kind=ROW_TOGGLE, .step=1, .names=kOnOff, .resetValue=1 },

    { .key="Video.FpsCap",         .label="Frame cap",
      .help="OFF or 30/60/90/120 FPS.", .category=CAT_DISPLAY,
      .kind=ROW_SLIDER, .step=30, .uiMin=0, .uiMax=120, .resetValue=0 },

    { .key="Video.DisplayFPS",     .label="Display FPS",
      .help="Show a small FPS counter.", .category=CAT_DISPLAY,
      .kind=ROW_TOGGLE, .step=1, .names=kOnOff, .resetValue=0 },

    { .key="Video.MSAA",           .label="MSAA",
      .help="Smooth edges. Restart required.", .category=CAT_DISPLAY,
      .kind=ROW_MSAA, .restart=1, .resetValue=1 },

    { .key="Video.TextureFilter",  .label="Texture filter",
      .help="Texture sharpness and smoothing.", .category=CAT_DISPLAY,
      .kind=ROW_ENUM, .step=1, .names=kTexFilter, .resetValue=1 },

    { .key="Video.Anisotropy",     .label="Anisotropic",
      .help="Sharper distant textures. 1-16.", .category=CAT_DISPLAY,
      .kind=ROW_SLIDER, .step=1, .uiMin=1, .uiMax=16, .resetValue=4 },

    { .key="Video.FovScale",       .label="FOV scale %",
      .help="View width. Safe range 70-120.", .category=CAT_DISPLAY,
      .kind=ROW_SLIDER, .step=5, .uiMin=70, .uiMax=120, .resetValue=100 },

    /* INPUT */
    { .key="Input.ControlPreset", .label="Control preset",
      .help="Choose Classic, Hybrid or Modern Ascension controls.",
      .category=CAT_INPUT,
      .kind=ROW_ENUM, .step=1, .names=kControlPreset,
      .uiMin=0, .uiMax=2, .resetValue=2 },

    { .key="Input.MouseAimSpeed",  .label="Mouse aim speed",
      .help="Aim sensitivity. Range 1-100.", .category=CAT_INPUT,
      .kind=ROW_SLIDER, .step=1, .uiMin=1, .uiMax=100, .resetValue=16 },

    { .key="Input.MouseTurnSpeed", .label="Mouse turn speed",
      .help="Turn sensitivity. Range 1-100.", .category=CAT_INPUT,
      .kind=ROW_SLIDER, .step=1, .uiMin=1, .uiMax=100, .resetValue=100 },

    { .key="Input.MouseInvertY",   .label="Mouse invert Y",
      .help="Reverse vertical mouse look.", .category=CAT_INPUT,
      .kind=ROW_TOGGLE, .step=1, .names=kOnOff, .resetValue=0 },

    { .key="Input.MouseCaptureMode", .label="Mouse capture",
      .help="Choose how mouse lock activates.", .category=CAT_INPUT,
      .kind=ROW_TOGGLE, .step=1, .names=kCapture, .resetValue=1 },

    /* GAMEPLAY */
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
      .kind=ROW_ACTION, .action=ACTION_RESTART, .found=1 },
};
#define NUM_ROWS ((int)(sizeof(rows) / sizeof(rows[0])))

static int s_inited;
static volatile int s_open;
static int s_sel;
static int s_scroll;

static int  s_showFps;
static int  s_controlHintSeen;
static char s_fpsText[16] = "";

static char     s_status[48] = "";
static uint64_t s_statusUntilUs;
static int      s_pendingAction;
static uint64_t s_pendingUntilUs;

PD_CONSTRUCTOR static void overlayConfigInit(void)
{
    configRegisterInt("Video.DisplayFPS", &s_showFps, 0, 1);
    configRegisterInt("Ascension.ControlHintSeen", &s_controlHintSeen, 0, 1);
}

/* ---- layout ------------------------------------------------------------ */
#define OV_X0          16
#define OV_LABEL_X     24
#define OV_TOP          8
#define OV_LINE        14
#define OV_HDR_LINES    3
#define OV_LIST_TOP    (OV_TOP + OV_HDR_LINES * OV_LINE)
#define OV_RIGHT       (viGetX() - OV_X0)
#define OV_NUM_W       36
#define OV_BAR_X      150
#define OV_FOOTER_H    20

#define OV_CB_X0      (OV_RIGHT - 14)
#define OV_CB_X1      (OV_RIGHT + 7)
#define OV_CB_Y0      (OV_TOP - 3)
#define OV_CB_Y1      (OV_TOP + 10)

static int visibleRows(void)
{
    int n = (viGetY() - OV_LIST_TOP - OV_FOOTER_H) / OV_LINE;
    if (n < 4) n = 4;
    if (n > NUM_ROWS) n = NUM_ROWS;
    return n;
}

static int maxScroll(void)
{
    int m = NUM_ROWS - visibleRows();
    return m > 0 ? m : 0;
}

static void ensureSelectionVisible(void)
{
    int vis = visibleRows();
    int max = maxScroll();

    if (s_sel < s_scroll)
        s_scroll = s_sel;
    if (s_sel >= s_scroll + vis)
        s_scroll = s_sel - vis + 1;

    if (s_scroll < 0) s_scroll = 0;
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

    int slot = (int)((oy - OV_LIST_TOP) / OV_LINE);
    int row = s_scroll + slot;
    return (row >= 0 && row < NUM_ROWS) ? row : -1;
}

static int overlayInCloseBox(double ox, double oy)
{
    return ox >= OV_CB_X0 && ox <= OV_CB_X1 &&
           oy >= OV_CB_Y0 && oy <= OV_CB_Y1;
}

static void sliderBarSpan(s32 *x0, s32 *x1)
{
    *x0 = OV_BAR_X;
    *x1 = OV_RIGHT - OV_NUM_W;
    if (*x1 < *x0 + 16)
        *x1 = *x0 + 16;
}

/* ---- feedback ---------------------------------------------------------- */
static void setStatus(const char *fmt, ...)
{
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(s_status, sizeof(s_status), fmt, ap);
    va_end(ap);
    s_statusUntilUs = sysGetMicroseconds() + 2200000ull;
}

static const char *statusText(void)
{
    if (!s_status[0])
        return NULL;
    if (sysGetMicroseconds() > s_statusUntilUs) {
        s_status[0] = 0;
        return NULL;
    }
    return s_status;
}

static void clearPendingAction(void)
{
    s_pendingAction = ACTION_NONE;
    s_pendingUntilUs = 0;
}

static int pendingActionIs(int action)
{
    if (s_pendingAction != action)
        return 0;
    if (sysGetMicroseconds() > s_pendingUntilUs) {
        clearPendingAction();
        return 0;
    }
    return 1;
}

/* ---- config resolution ------------------------------------------------- */
static void resolveCb(const char *key, int type, void *ptr,
                      double min, double max, double step,
                      const char *label, const char *const *names, void *ctx)
{
    (void)step; (void)label; (void)names; (void)ctx;

    for (int i = 0; i < NUM_ROWS; i++) {
        if (rows[i].kind == ROW_ACTION || rows[i].kind == ROW_RES)
            continue;
        if (strcmp(rows[i].key, key) == 0) {
            rows[i].found  = 1;
            rows[i].type   = type;
            rows[i].ptr    = ptr;
            rows[i].cfgMin = min;
            rows[i].cfgMax = max;
            return;
        }
    }
}

static double rowGet(const struct Row *r)
{
    if (!r->found || !r->ptr)
        return 0.0;

    switch (r->type) {
    case CONFIG_OPT_INT:   return (double)*(int *)r->ptr;
    case CONFIG_OPT_UINT:  return (double)*(unsigned int *)r->ptr;
    case CONFIG_OPT_FLOAT: return (double)*(float *)r->ptr;
    default:               return 0.0;
    }
}

static double rowLo(const struct Row *r)
{
    return (r->uiMin != r->uiMax) ? r->uiMin : r->cfgMin;
}

static double rowHi(const struct Row *r)
{
    return (r->uiMin != r->uiMax) ? r->uiMax : r->cfgMax;
}

static void applyRowValue(struct Row *r, double v, int feedback)
{
    if (!r->found || !r->ptr)
        return;

    double lo = rowLo(r), hi = rowHi(r);
    if (lo != hi) {
        if (v < lo) v = lo;
        if (v > hi) v = hi;
    }

    if (strcmp(r->key, "Video.FpsCap") == 0) {
        if (v > 0.0 && v < 30.0) v = 30.0;
        if (v > 120.0) v = 120.0;
        if (v > 0.0) v = lround(v / 30.0) * 30.0;
    }

    double old = rowGet(r);

    switch (r->type) {
    case CONFIG_OPT_INT:
        *(int *)r->ptr = (int)lround(v);
        break;
    case CONFIG_OPT_UINT:
        *(unsigned int *)r->ptr =
            (unsigned int)(v < 0.0 ? 0 : lround(v));
        break;
    case CONFIG_OPT_FLOAT:
        *(float *)r->ptr = (float)v;
        break;
    default:
        return;
    }

    if (fabs(old - rowGet(r)) < 0.0001)
        return;

    if (strcmp(r->key, "Video.Fullscreen") == 0) {
        videoRequestFullscreen((int)lround(v));
    } else if (strncmp(r->key, "Video.", 6) == 0 && !r->restart) {
        videoRequestLiveConfig();
    }

    if (feedback)
        setStatus(r->restart ? "RESTART REQUIRED" : "APPLIED");
}

static void normalizeSafeValues(void)
{
    for (int i = 0; i < NUM_ROWS; i++) {
        struct Row *r = &rows[i];
        if (!r->found || !r->ptr)
            continue;

        double v = rowGet(r);

        if (r->kind == ROW_MSAA) {
            int iv = (int)lround(v);
            int best = 1;
            if (iv >= 8) best = 8;
            else if (iv >= 4) best = 4;
            else if (iv >= 2) best = 2;
            applyRowValue(r, best, 0);
            continue;
        }

        double lo = rowLo(r), hi = rowHi(r);
        if (lo != hi && (v < lo || v > hi))
            applyRowValue(r, v < lo ? lo : hi, 0);

        if (strcmp(r->key, "Video.FpsCap") == 0) {
            v = rowGet(r);
            if ((v > 0.0 && v < 30.0) || v > 120.0 ||
                (v > 0.0 && ((int)lround(v) % 30) != 0))
                applyRowValue(r, v, 0);
        }
    }
}

static void buildResolutionList(void)
{
    int dw = 1920, dh = 1080;
    videoGetDesktopSize(&dw, &dh);

    s_resFitN = 0;
    for (int i = 0; i < NUM_RES; i++) {
        if (kResList[i][0] <= dw && kResList[i][1] <= dh)
            s_resFit[s_resFitN++] = i;
    }
    if (s_resFitN == 0)
        s_resFit[s_resFitN++] = 0;

    int cw = 0, ch = 0;
    videoGetWindowSize(&cw, &ch);

    long best = -1;
    s_resSel = 0;
    for (int k = 0; k < s_resFitN; k++) {
        int i = s_resFit[k];
        long d = labs((long)kResList[i][0] - cw) +
                 labs((long)kResList[i][1] - ch);
        if (best < 0 || d < best) {
            best = d;
            s_resSel = k;
        }
    }
}

static void overlayInit(void)
{
    if (s_inited)
        return;
    s_inited = 1;

    for (int i = 0; i < NUM_ROWS; i++) {
        if (rows[i].kind != ROW_ACTION && rows[i].kind != ROW_RES)
            configSetOptionMeta(rows[i].key, rows[i].label,
                                rows[i].step, rows[i].names);
    }

    configForEachOption(resolveCb, NULL);

    for (int i = 0; i < NUM_ROWS; i++) {
        if (rows[i].kind == ROW_RES || rows[i].kind == ROW_ACTION) {
            rows[i].found = 1;
            continue;
        }
        if (!rows[i].found)
            sysLogPrintf(LOG_WARNING,
                         "optionsoverlay: option '%s' not registered",
                         rows[i].key);
    }

    buildResolutionList();
    normalizeSafeValues();

    const char *e = getenv("GE_OPTIONSOVERLAY");
    if (e && atoi(e) != 0)
        s_open = 1;
}

/* ---- row behavior ------------------------------------------------------ */
static void restoreDefaults(void)
{
    for (int i = 0; i < NUM_ROWS; i++) {
        struct Row *r = &rows[i];
        if (r->kind == ROW_ACTION || r->kind == ROW_RES || !r->found)
            continue;
        applyRowValue(r, r->resetValue, 0);
    }

    /* Native NTSC-size window is the port's conservative baseline. */
    for (int k = 0; k < s_resFitN; k++) {
        int i = s_resFit[k];
        if (kResList[i][0] == 640 && kResList[i][1] == 480) {
            s_resSel = k;
            break;
        }
    }
    if (!videoIsFullscreen())
        videoRequestWindowSize(640, 480);

    configSave();
    setStatus("DEFAULTS RESTORED");
}

static void activateAction(struct Row *r)
{
    uint64_t now = sysGetMicroseconds();

    if (!pendingActionIs(r->action)) {
        s_pendingAction = r->action;
        s_pendingUntilUs = now + 3500000ull;
        setStatus(r->action == ACTION_RESET ?
                  "PRESS AGAIN TO RESET" : "PRESS AGAIN TO RESTART");
        return;
    }

    clearPendingAction();

    if (r->action == ACTION_RESET) {
        restoreDefaults();
        return;
    }

    if (r->action == ACTION_RESTART) {
        configSave();
        setStatus("RESTARTING");
        if (sysRestart() != 0)
            setStatus("RESTART FAILED");
    }
}

static void rowAdjust(struct Row *r, int dir)
{
    if (!r->found)
        return;

    if (r->kind == ROW_ACTION) {
        activateAction(r);
        return;
    }

    if (r->kind == ROW_RES) {
        if (s_resFitN <= 0 || videoIsFullscreen()) {
            setStatus("WINDOWED MODE ONLY");
            return;
        }

        s_resSel += (dir >= 0) ? 1 : -1;
        if (s_resSel < 0) s_resSel = s_resFitN - 1;
        if (s_resSel >= s_resFitN) s_resSel = 0;

        int i = s_resFit[s_resSel];
        videoRequestWindowSize(kResList[i][0], kResList[i][1]);
        setStatus("APPLIED");
        return;
    }

    double v = rowGet(r);

    switch (r->kind) {
    case ROW_TOGGLE:
        applyRowValue(r, v != 0.0 ? 0.0 : 1.0, 1);
        break;

    case ROW_MSAA: {
        int idx = 0;
        for (int i = 0; i < 4; i++)
            if (kMsaaSeq[i] == (int)lround(v))
                idx = i;
        idx += dir >= 0 ? 1 : -1;
        if (idx < 0) idx = 0;
        if (idx > 3) idx = 3;
        applyRowValue(r, kMsaaSeq[idx], 1);
        break;
    }

    case ROW_ENUM: {
        double lo = r->cfgMin, hi = r->cfgMax;
        v += dir >= 0 ? 1.0 : -1.0;
        if (v < lo) v = hi;
        if (v > hi) v = lo;
        applyRowValue(r, v, 1);
        break;
    }

    case ROW_SLIDER:
        applyRowValue(r, v + (dir >= 0 ? r->step : -r->step), 1);
        break;

    default:
        break;
    }
}

static void moveSelection(int delta)
{
    int next = s_sel + delta;
    if (next < 0) next = 0;
    if (next >= NUM_ROWS) next = NUM_ROWS - 1;
    if (next != s_sel) {
        s_sel = next;
        clearPendingAction();
        ensureSelectionVisible();
    }
}

static void jumpCategory(int dir)
{
    int cat = rows[s_sel].category;
    int target = cat + (dir >= 0 ? 1 : -1);
    if (target < CAT_DISPLAY) target = CAT_GAMEPLAY;
    if (target > CAT_GAMEPLAY) target = CAT_DISPLAY;

    if (dir >= 0) {
        for (int i = 0; i < NUM_ROWS; i++) {
            if (rows[i].category == target) {
                s_sel = i;
                break;
            }
        }
    } else {
        for (int i = NUM_ROWS - 1; i >= 0; i--) {
            if (rows[i].category == target) {
                s_sel = i;
                break;
            }
        }
    }

    clearPendingAction();
    ensureSelectionVisible();
}

/* ---- public controls --------------------------------------------------- */
void optionsOverlayToggle(void)
{
    overlayInit();
    s_open = !s_open;

    if (s_open) {
        ensureSelectionVisible();
        if (!s_controlHintSeen) {
            s_controlHintSeen = 1;
            configSave();
        }
    } else {
        clearPendingAction();
        configSave();
    }

    sysLogPrintf(LOG_INFO, "optionsoverlay: %s",
                 s_open ? "opened" : "closed");
}

int optionsOverlayIsOpen(void)
{
    overlayInit();
    return s_open;
}

void optionsOverlayScroll(int dir)
{
    if (!s_open || dir == 0)
        return;
    moveSelection(dir > 0 ? -1 : 1);
}

static void sliderSetFromX(struct Row *r, double ox)
{
    double lo = rowLo(r), hi = rowHi(r);
    if (hi <= lo)
        return;

    s32 bx0, bx1;
    sliderBarSpan(&bx0, &bx1);

    double f = (ox - bx0) / (double)(bx1 - bx0);
    if (f < 0) f = 0;
    if (f > 1) f = 1;

    double v = lo + f * (hi - lo);
    double step = r->step > 0.0 ? r->step : 1.0;
    v = lround(v / step) * step;
    applyRowValue(r, v, 1);
}

void optionsOverlayHandleInput(void)
{
    static int prevUp, prevDn, prevLf, prevRt, prevTab;
    static int prevLmb, prevRmb;
    static int dragRow = -1;

    if (!s_open) {
        prevUp = prevDn = prevLf = prevRt = prevTab = 0;
        prevLmb = prevRmb = 0;
        dragRow = -1;
        return;
    }

    inputSuspendForOverlay();

    const Uint8 *ks = SDL_GetKeyboardState(NULL);
    int mx = 0, my = 0;
    Uint32 mb = SDL_GetMouseState(&mx, &my);
    int lmb = (mb & SDL_BUTTON(SDL_BUTTON_LEFT)) != 0;
    int rmb = (mb & SDL_BUTTON(SDL_BUTTON_RIGHT)) != 0;

    int up = ks[SDL_SCANCODE_UP]   || ks[SDL_SCANCODE_KP_8];
    int dn = ks[SDL_SCANCODE_DOWN] || ks[SDL_SCANCODE_KP_2];
    int lf = ks[SDL_SCANCODE_LEFT] || ks[SDL_SCANCODE_KP_4];
    int rt = ks[SDL_SCANCODE_RIGHT] || ks[SDL_SCANCODE_KP_6] ||
             ks[SDL_SCANCODE_RETURN] || ks[SDL_SCANCODE_KP_ENTER];
    int tab = ks[SDL_SCANCODE_TAB];

    if (up && !prevUp) moveSelection(-1);
    if (dn && !prevDn) moveSelection(+1);
    if (lf && !prevLf) rowAdjust(&rows[s_sel], -1);
    if (rt && !prevRt) rowAdjust(&rows[s_sel], +1);
    if (tab && !prevTab) {
        int backwards = (SDL_GetModState() & KMOD_SHIFT) != 0;
        jumpCategory(backwards ? -1 : +1);
    }

    int ww = 0, wh = 0;
    videoGetWindowSize(&ww, &wh);

    if (ww > 0 && wh > 0) {
        double ox = (double)mx * (double)viGetX() / ww;
        double oy = (double)my * (double)viGetY() / wh;
        int hoverRow = overlayRowAtY(oy);
        int onClose = overlayInCloseBox(ox, oy);

        if (hoverRow >= 0 && !onClose && hoverRow != s_sel) {
            s_sel = hoverRow;
            clearPendingAction();
            ensureSelectionVisible();
        }

        s32 bx0, bx1;
        sliderBarSpan(&bx0, &bx1);

        if (lmb && !prevLmb) {
            if (onClose) {
                optionsOverlayToggle();
                return;
            }

            if (hoverRow >= 0) {
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
            }
        }

        if (lmb && dragRow >= 0 && rows[dragRow].kind == ROW_SLIDER)
            sliderSetFromX(&rows[dragRow], ox);
        if (!lmb)
            dragRow = -1;

        if (rmb && !prevRmb && hoverRow >= 0 &&
            rows[hoverRow].kind != ROW_ACTION && ox >= bx0)
            rowAdjust(&rows[hoverRow], -1);
    }

    prevUp = up; prevDn = dn; prevLf = lf; prevRt = rt; prevTab = tab;
    prevLmb = lmb; prevRmb = rmb;
}

/* ---- drawing ----------------------------------------------------------- */
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

static Gfx *drawText(Gfx *gdl, s32 x, s32 y,
                     const char *str, u32 colour)
{
    str = ascensionLocaleText(str);
    s32 px = x, py = y;
    return textRender(gdl, &px, &py, (char *)str,
                      ptrFontBankGothicChars, ptrFontBankGothic,
                      colour, viGetX(), viGetY(), 0, 0);
}

static s32 measureText(const char *str)
{
    str = ascensionLocaleText(str);
    s32 h = 0, w = 0;
    textMeasure(&h, &w, (char *)str,
                ptrFontBankGothicChars, ptrFontBankGothic, 0);
    return w;
}

static Gfx *drawTextR(Gfx *gdl, s32 xr, s32 y,
                      const char *str, u32 colour)
{
    return drawText(gdl, xr - measureText(str), y, str, colour);
}

static const char *categoryName(int cat)
{
    switch (cat) {
    case CAT_DISPLAY:  return "DISPLAY";
    case CAT_INPUT:    return "INPUT";
    default:           return "GAMEPLAY";
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
            snprintf(out, n, "%d x %d",
                     kResList[i][0], kResList[i][1]);
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
        if ((int)lround(v) <= 1)
            snprintf(out, n, "OFF");
        else
            snprintf(out, n, "%dx", (int)lround(v));
        return;
    }

    if (strcmp(r->key, "Video.FpsCap") == 0 &&
        (int)lround(v) == 0) {
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

static Gfx *drawCategoryTabs(Gfx *gdl, int active)
{
    const char *names[] = { "DISPLAY", "INPUT", "GAMEPLAY" };
    const s32 xs[] = { OV_X0, OV_X0 + 78, OV_X0 + 132 };
    const int n = 3;

    for (int i = 0; i < n; i++) {
        u32 col = i == active ? ASC_UI_GOLD : ASC_UI_SLATE;
        gdl = drawText(gdl, xs[i], OV_TOP + OV_LINE, names[i], col);
    }
    return gdl;
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

        if (showBrand) {
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
        }

        gdl = microcode_constructor(gdl);

        if (showBrand) {
            gdl = drawText(gdl, 8, H - 14,
                           ASCENSION_SIGNATURE, ASC_UI_GOLD);
            gdl = drawTextR(gdl, W - 8, H - 14,
                            "F10 CONTROL", ASC_UI_SLATE);

            if (!s_controlHintSeen)
                gdl = drawTextR(gdl, W - 9, H - 32,
                                "PRESS F10 TO CONFIGURE",
                                ASC_UI_IVORY);
        }

        if (showFps)
            gdl = drawTextR(gdl, W - 6, 6,
                            s_fpsText, 0x40FF60FFu);

        gDPPipeSync(gdl++);
        gSPEndDisplayList(gdl++);
        return s_buf;
    }

    ensureSelectionVisible();

    const s32 W = viGetX();
    const s32 H = viGetY();
    const int vis = visibleRows();
    const int listBottom = OV_LIST_TOP + vis * OV_LINE;
    const int panelBottom = listBottom + OV_FOOTER_H - 4;
    const int activeCat = rows[s_sel].category;

    s32 bx0, bx1;
    sliderBarSpan(&bx0, &bx1);

    Gfx *gdl = s_buf;
    gDPPipeSync(gdl++);
    gDPSetCycleType(gdl++, G_CYC_1CYCLE);
    gDPSetTexturePersp(gdl++, G_TP_NONE);
    gDPSetScissor(gdl++, G_SC_NON_INTERLACE, 0, 0, W, H);

    /* background / panel */
    gdl = fillRect(gdl, 0, 0, W, H, 0, 0, 0, 150);
    gdl = fillRect(gdl, OV_X0 - 8, OV_TOP - 5,
                   W - (OV_X0 - 8), panelBottom,
                   8, 10, 12, 226);
    gdl = fillRect(gdl, OV_X0 - 8, OV_TOP - 5,
                   W - (OV_X0 - 8), OV_TOP - 4,
                   0xD2, 0xB6, 0x5C, 235);
    gdl = fillRect(gdl, OV_CB_X0, OV_CB_Y0, OV_CB_X1, OV_CB_Y1,
                   104, 31, 31, 235);

    /* category underline */
    {
        s32 ux0 = OV_X0;
        s32 ux1 = OV_X0 + 50;
        if (activeCat == CAT_INPUT) {
            ux0 = OV_X0 + 78;
            ux1 = ux0 + 32;
        } else if (activeCat == CAT_GAMEPLAY) {
            ux0 = OV_X0 + 132;
            ux1 = ux0 + 58;
        }
        gdl = fillRect(gdl, ux0, OV_TOP + OV_LINE + 10,
                       ux1, OV_TOP + OV_LINE + 11,
                       0xD2, 0xB6, 0x5C, 230);
    }

    for (int i = s_scroll; i < s_scroll + vis && i < NUM_ROWS; i++) {
        s32 y = rowY(i);

        if (i == s_sel) {
            gdl = fillRect(gdl, OV_X0 - 4, y - 2,
                           W - (OV_X0 - 4), y + OV_LINE - 3,
                           38, 34, 22, 220);
            gdl = fillRect(gdl, OV_X0 - 6, y - 2,
                           OV_X0 - 4, y + OV_LINE - 3,
                           0xD2, 0xB6, 0x5C, 255);
        }

        if (rows[i].kind == ROW_SLIDER && rows[i].found) {
            double lo = rowLo(&rows[i]);
            double hi = rowHi(&rows[i]);
            double f = hi > lo ? (rowGet(&rows[i]) - lo) / (hi - lo) : 0.0;
            if (f < 0) f = 0;
            if (f > 1) f = 1;

            s32 by = y + 3;
            gdl = fillRect(gdl, bx0, by, bx1, by + 4,
                           52, 52, 48, 220);
            gdl = fillRect(gdl, bx0, by,
                           bx0 + (s32)((bx1 - bx0) * f), by + 4,
                           210, 182, 92, 255);
        }
    }

    /* discreet scroll indicator */
    if (NUM_ROWS > vis) {
        int trackY0 = OV_LIST_TOP;
        int trackY1 = listBottom - 3;
        int trackH = trackY1 - trackY0;
        int thumbH = (trackH * vis) / NUM_ROWS;
        if (thumbH < 10) thumbH = 10;
        int max = maxScroll();
        int thumbY = trackY0;
        if (max > 0)
            thumbY += ((trackH - thumbH) * s_scroll) / max;

        gdl = fillRect(gdl, W - 8, trackY0, W - 6, trackY1,
                       44, 44, 42, 180);
        gdl = fillRect(gdl, W - 8, thumbY, W - 6, thumbY + thumbH,
                       210, 182, 92, 235);
    }

    gdl = microcode_constructor(gdl);

    gdl = drawText(gdl, OV_X0, OV_TOP,
                   ASCENSION_SIGNATURE, ASC_UI_GOLD);
    gdl = drawText(gdl,
                   (OV_CB_X0 + OV_CB_X1) / 2 - measureText("X") / 2,
                   OV_TOP, "X", ASC_UI_IVORY);

    gdl = drawCategoryTabs(gdl, activeCat);

    gdl = drawText(gdl, OV_X0, OV_TOP + 2 * OV_LINE,
                   rows[s_sel].help ? rows[s_sel].help : "PC settings",
                   ASC_UI_SLATE);

    for (int i = s_scroll; i < s_scroll + vis && i < NUM_ROWS; i++) {
        s32 y = rowY(i);
        u32 col = i == s_sel ? ASC_UI_IVORY : ASC_UI_TEXT;
        char val[48];

        gdl = drawText(gdl, OV_LABEL_X, y,
                       rows[i].label,
                       rows[i].found ? col : ASC_UI_SLATE);

        if (!rows[i].found) {
            gdl = drawTextR(gdl, OV_RIGHT, y, "N/A", ASC_UI_SLATE);
            continue;
        }

        valueText(&rows[i], val, sizeof(val));

        if (rows[i].restart && rows[i].kind != ROW_ACTION) {
            gdl = drawText(gdl, bx0, y, val, col);
            gdl = drawTextR(gdl, OV_RIGHT, y,
                            "RESTART", ASC_UI_GOLD_DIM);
        } else {
            u32 valueCol = (rows[i].kind == ROW_ACTION && i == s_sel)
                         ? ASC_UI_GOLD : col;
            gdl = drawTextR(gdl, OV_RIGHT, y, val, valueCol);
        }
    }

    {
        const char *status = statusText();
        s32 fy = listBottom + 3;
        gdl = drawText(gdl, OV_X0, fy,
                       status ? "TAB CATEGORY" : "TAB CATEGORY  F10 CLOSE",
                       ASC_UI_SLATE);
        if (status)
            gdl = drawTextR(gdl, OV_RIGHT, fy,
                            status,
                            strstr(status, "FAILED") ? 0xFF7070FFu : ASC_UI_GOLD);
    }

    gDPPipeSync(gdl++);
    gSPEndDisplayList(gdl++);

    if ((gdl - s_buf) > OV_BUF_CMDS)
        sysLogPrintf(LOG_ERROR, "optionsoverlay: DL overflow (%d)",
                     (int)(gdl - s_buf));

    return s_buf;
}
