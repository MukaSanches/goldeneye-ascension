/*
 * F10 in-game options overlay -- approach (C) from docs/dev/OPTIONS-MENU-PLAN.md.
 *
 * Port-layer only. No src/ menu code is touched: the overlay draws its own
 * fast3d 2D display list (appended after the game DL in gfx_run) and edits the
 * port-owned config.c variables directly. Live knobs apply immediately; knobs
 * that only make sense on the next launch are explicitly tagged "RESTART".
 *
 * Text + fill helpers are the game's own (textRender / microcode_constructor /
 * gDPFillRectangle) reached by extern -- same pattern input.c uses to read
 * current_menu / cursor_h_pos. This is a rendering/UI view, not a logic change.
 *
 * Ascension adds a deliberately small discovery layer on file select so a new
 * PC player can find this panel without reading a README. The stronger prompt
 * is shown until F10 is opened once; a compact F10 affordance remains.
 *
 * Diagnostic: set GE_OPTIONSOVERLAY=1 to auto-open at boot (headless layout
 * check). Env-gated, harmless when unset.
 */

#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <SDL.h>

#include <PR/ultratypes.h>
/* gbi.h's gDP* DL macros use _SHIFTL/_SHIFTR but do not define them -- game TUs
 * get them from <ultra64.h>/<PR/mbi.h>, which also drags in N64 OS headers that
 * shadow libc here. Define the two pure macros locally (verbatim from mbi.h) so
 * this stays a plain port TU. Without them GCC/ld fails "undefined reference to
 * _SHIFTL" (MinGW's chain happens to provide it). */
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
#include "ascension_version.h"

/* ---- game symbols (rendering/UI only; see input.c for the same pattern) ---- */
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
extern int   current_menu;

/* Keep this port TU independent of the large game headers. MENU_FILE_SELECT
 * is enum MENU value 5 in src/bondconstants.h (same ABI-int pattern as input.c). */
#define GE_MENU_FILE_SELECT 5

/* Ascension 0.0.2 UI palette. Original game assets/status colours are not
 * recoloured: these values are used only on port-owned surfaces. */
#define ASC_UI_GOLD      0xD2B65CFFu
#define ASC_UI_GOLD_DIM  0x9B8749FFu
#define ASC_UI_IVORY     0xE8E2D3FFu
#define ASC_UI_TEXT      0xC8C2B3FFu
#define ASC_UI_SLATE     0x8D9396FFu

/* ------------------------------------------------------------------------ */

enum { ROW_TOGGLE, ROW_SLIDER, ROW_ENUM, ROW_MSAA, ROW_RES };

static const char *const kOnOff[]     = { "OFF", "ON", NULL };
static const char *const kTexFilter[] = { "NEAREST", "BILINEAR", "3-POINT", NULL };
static const char *const kCapture[]   = { "ALWAYS GRAB", "CLICK-TO-LOCK", NULL };
static const int         kMsaaSeq[]   = { 1, 2, 4, 8 };

/* Windowed-mode resolution presets. Filtered at init to those that fit the
 * desktop; the Resolution row cycles the surviving list. */
static const int kResList[][2] = {
    {  640,  480 }, {  800,  600 }, {  960,  720 }, { 1024,  768 },
    { 1152,  864 }, { 1280,  720 }, { 1280,  800 }, { 1280,  960 },
    { 1366,  768 }, { 1440,  900 }, { 1600,  900 }, { 1600, 1200 },
    { 1680, 1050 }, { 1920, 1080 }, { 1920, 1200 }, { 2560, 1440 },
    { 3200, 1800 }, { 3840, 2160 },
};
#define NUM_RES ((int)(sizeof(kResList) / sizeof(kResList[0])))
static int s_resFit[NUM_RES];   /* indices into kResList that fit the desktop */
static int s_resFitN = 0;
static int s_resSel  = 0;       /* index into s_resFit */

struct Row {
    const char        *key;
    const char        *label;
    const char        *help;     /* short contextual explanation, not a manual */
    int                kind;
    double             step;
    const char *const *names;    /* ROW_TOGGLE / ROW_ENUM value names */
    int                restart;  /* value only takes effect on next launch */
    double             uiMin, uiMax; /* 0,0 -> use the registered clamp */

    /* resolved from config.c at init */
    int                found;
    int                type;     /* CONFIG_OPT_*    */
    void              *ptr;
    double             cfgMin, cfgMax;
};

/* Keep explanations compact: BankGothic is intentionally wide at the native
 * 320x240 UI grid. The second header line changes with selection, so advanced
 * terms never need a separate manual just to be understood. */
static struct Row rows[] = {
    { .key="Video.Fullscreen",          .label="Fullscreen",       .help="Windowed / fullscreen display",  .kind=ROW_TOGGLE, .step=1,    .names=kOnOff },
    { .key="__Resolution",              .label="Resolution",       .help="Window size (windowed only)",     .kind=ROW_RES },
    { .key="Video.VSync",               .label="VSync",            .help="Reduces visible screen tearing",  .kind=ROW_TOGGLE, .step=1,    .names=kOnOff },
    { .key="Video.FpsCap",              .label="Frame cap",        .help="0 = native game timing",           .kind=ROW_SLIDER, .step=10,   .uiMin=0, .uiMax=360 },
    { .key="Video.DisplayFPS",          .label="Display FPS",      .help="Top-right performance counter",    .kind=ROW_TOGGLE, .step=1,    .names=kOnOff },
    { .key="Video.MSAA",                .label="MSAA",             .help="Edge smoothing; restart to apply", .kind=ROW_MSAA,               .restart=1 },
    { .key="Video.TextureFilter",       .label="Texture filter",   .help="Texture sharpness / smoothing",    .kind=ROW_ENUM,   .step=1,    .names=kTexFilter },
    { .key="Video.Anisotropy",          .label="Anisotropic",      .help="Sharper distant angled textures",  .kind=ROW_SLIDER, .step=1 },
    { .key="Video.FovScale",            .label="FOV scale %",      .help="Field of view without stretching", .kind=ROW_SLIDER, .step=5 },
    { .key="Input.MouseAimSpeed",       .label="Mouse aim speed",  .help="Vertical aiming sensitivity",      .kind=ROW_SLIDER, .step=1,    .uiMin=0, .uiMax=100 },
    { .key="Input.MouseTurnSpeed",      .label="Mouse turn speed", .help="Horizontal turning sensitivity",   .kind=ROW_SLIDER, .step=1,    .uiMin=0, .uiMax=100 },
    { .key="Input.MouseInvertY",        .label="Mouse invert Y",   .help="Reverse the mouse vertical axis",  .kind=ROW_TOGGLE, .step=1,    .names=kOnOff },
    { .key="Input.MouseCaptureMode",    .label="Mouse capture",    .help="Choose how mouse lock activates",  .kind=ROW_TOGGLE, .step=1,    .names=kCapture },
    { .key="Game.ScreenShakeIntensity", .label="Screen shake",     .help="Camera shake intensity",           .kind=ROW_SLIDER, .step=0.25 },
    { .key="Game.SkipIntro",            .label="Skip intro",       .help="Boot straight to file select",     .kind=ROW_TOGGLE, .step=1,    .names=kOnOff, .restart=1 },
};
#define NUM_ROWS ((int)(sizeof(rows) / sizeof(rows[0])))

static int  s_inited = 0;
static volatile int s_open = 0;
static int  s_sel = 0;

/* Port-owned presentation state. DisplayFPS is now surfaced in F10 instead of
 * being an ini-only secret. The discovery bit is persisted so the stronger
 * first-run prompt can retire itself after the player opens Ascension Control. */
static int      s_showFps = 0;
static int      s_controlHintSeen = 0;
static char     s_fpsText[16] = "";

PD_CONSTRUCTOR static void overlayConfigInit(void)
{
    configRegisterInt("Video.DisplayFPS", &s_showFps, 0, 1);
    configRegisterInt("Ascension.ControlHintSeen", &s_controlHintSeen, 0, 1);
}

/* Sampled once per emitted frame; recomputes the string every ~0.5 s. */
static void fpsTick(void)
{
    static uint64_t winStartUs = 0;
    static int      frames = 0;

    uint64_t nowUs = sysGetMicroseconds();
    if (winStartUs == 0) {
        winStartUs = nowUs;
        return;
    }
    frames++;
    uint64_t dtUs = nowUs - winStartUs;
    if (dtUs >= 500000) {
        int fps = (int)((double)frames * 1e6 / (double)dtUs + 0.5);
        snprintf(s_fpsText, sizeof(s_fpsText), "%d FPS", fps);
        winStartUs = nowUs;
        frames = 0;
    }
}

/* Layout (game 2D pixel space = viGetX() x viGetY(), ~320x240). Fifteen rows
 * fit without scrolling by tightening only the vertical rhythm; BankGothic's
 * caps remain separated and the mouse hit target still spans a full row. */
#define OV_X0        20
#define OV_LABEL_X   28
#define OV_TOP       10
#define OV_LINE      13
#define OV_HDR       2                        /* title + contextual help */
#define OV_ROW_Y(i)  (OV_TOP + ((i) + OV_HDR) * OV_LINE)
#define OV_RIGHT     (viGetX() - OV_X0)       /* right edge for right-aligned text */
#define OV_NUM_W     36                       /* reserved width for a slider's number */
#define OV_BAR_X     150

/* Slider fill bar span in overlay space (shared by emit + hit-testing). */
static void sliderBarSpan(s32 *x0, s32 *x1)
{
    *x0 = OV_BAR_X;
    *x1 = OV_RIGHT - OV_NUM_W;
    if (*x1 < *x0 + 16) {
        *x1 = *x0 + 16;
    }
}

/* Row index the given overlay-space y falls in, or -1. */
static int overlayRowAtY(double oy)
{
    for (int i = 0; i < NUM_ROWS; i++) {
        double top = OV_ROW_Y(i) - 2;
        if (oy >= top && oy < top + OV_LINE) {
            return i;
        }
    }
    return -1;
}

/* The close box brackets the title row at the panel's right edge. */
#define OV_CB_X0   (OV_RIGHT - 14)
#define OV_CB_X1   (OV_RIGHT + 7)
#define OV_CB_Y0   (OV_TOP - 3)
#define OV_CB_Y1   (OV_TOP + 10)
static int overlayInCloseBox(double ox, double oy)
{
    return ox >= OV_CB_X0 && ox <= OV_CB_X1 &&
           oy >= OV_CB_Y0 && oy <= OV_CB_Y1;
}

/* ------------------------------------------------------------------------ */

static void resolveCb(const char *key, int type, void *ptr, double min, double max,
                      double step, const char *label, const char *const *names,
                      void *ctx)
{
    (void)step; (void)label; (void)names; (void)ctx;
    for (int i = 0; i < NUM_ROWS; i++) {
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

static void overlayInit(void)
{
    if (s_inited) {
        return;
    }
    s_inited = 1;

    /* Publish display metadata so config.c / future consumers can see it,
     * without config.c knowing any specific key. */
    for (int i = 0; i < NUM_ROWS; i++) {
        configSetOptionMeta(rows[i].key, rows[i].label, rows[i].step, rows[i].names);
    }
    configForEachOption(resolveCb, NULL);

    for (int i = 0; i < NUM_ROWS; i++) {
        if (rows[i].kind == ROW_RES) {
            rows[i].found = 1;   /* not config-backed; driven via video.c */
            continue;
        }
        if (!rows[i].found) {
            sysLogPrintf(LOG_WARNING, "optionsoverlay: option '%s' not registered",
                         rows[i].key);
        }
    }

    /* Build the windowed-resolution preset list: presets that fit the desktop,
     * plus the current window size snapped to the nearest surviving entry. */
    {
        int dw = 1920, dh = 1080;
        videoGetDesktopSize(&dw, &dh);
        s_resFitN = 0;
        for (int i = 0; i < NUM_RES; i++) {
            if (kResList[i][0] <= dw && kResList[i][1] <= dh) {
                s_resFit[s_resFitN++] = i;
            }
        }
        if (s_resFitN == 0) {
            s_resFit[s_resFitN++] = 0;
        }
        int cw = 0, ch = 0;
        videoGetWindowSize(&cw, &ch);
        long best = -1;
        for (int k = 0; k < s_resFitN; k++) {
            int i = s_resFit[k];
            long d = labs((long)kResList[i][0] - cw) +
                     labs((long)kResList[i][1] - ch);
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
    if (!r->found || !r->ptr) {
        return 0.0;
    }
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

static void rowSet(struct Row *r, double v)
{
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

    /* Live-apply the video knobs that need a fast3d/SDL call. Everything else
     * is read straight off the pointer by its owner every frame/poll. */
    if (strcmp(r->key, "Video.Fullscreen") == 0) {
        videoRequestFullscreen((int)lround(v));
    } else if (strncmp(r->key, "Video.", 6) == 0 && !r->restart) {
        videoRequestLiveConfig();
    }
}

static void rowAdjust(struct Row *r, int dir)
{
    if (!r->found) {
        return;
    }
    double v = rowGet(r);
    switch (r->kind) {
    case ROW_TOGGLE:
        rowSet(r, (v != 0.0) ? 0.0 : 1.0);
        break;
    case ROW_MSAA: {
        int idx = 0;
        for (int i = 0; i < 4; i++) {
            if (kMsaaSeq[i] == (int)lround(v)) idx = i;
        }
        idx += dir;
        if (idx < 0) idx = 0;
        if (idx > 3) idx = 3;
        rowSet(r, (double)kMsaaSeq[idx]);
        break;
    }
    case ROW_ENUM: {
        double lo = r->cfgMin, hi = r->cfgMax;
        v += dir;
        if (v < lo) v = hi;
        if (v > hi) v = lo;
        rowSet(r, v);
        break;
    }
    case ROW_RES: {
        if (s_resFitN <= 0 || videoIsFullscreen()) {
            break;   /* resolution is windowed-only */
        }
        s_resSel += (dir >= 0) ? 1 : -1;
        if (s_resSel < 0) s_resSel = s_resFitN - 1;
        if (s_resSel >= s_resFitN) s_resSel = 0;
        int i = s_resFit[s_resSel];
        videoRequestWindowSize(kResList[i][0], kResList[i][1]);
        break;
    }
    default: /* ROW_SLIDER */
        rowSet(r, v + dir * r->step);
        break;
    }
}

/* ------------------------------------------------------------------------ */

void optionsOverlayToggle(void)
{
    overlayInit();
    s_open = !s_open;

    /* Opening Ascension Control is the acknowledgement. Save immediately so
     * the onboarding prompt cannot return just because the process was closed
     * before the panel itself was closed. */
    if (s_open && !s_controlHintSeen) {
        s_controlHintSeen = 1;
        configSave();
    }

    sysLogPrintf(LOG_INFO, "optionsoverlay: %s", s_open ? "opened" : "closed");
    if (!s_open) {
        configSave();
    }
}

int optionsOverlayIsOpen(void)
{
    if (!s_inited) {
        overlayInit();
    }
    return s_open;
}

void optionsOverlayScroll(int dir)
{
    if (!s_open || dir == 0) {
        return;
    }
    s_sel += (dir > 0) ? -1 : 1;   /* wheel-up -> move up the list */
    if (s_sel < 0) s_sel = NUM_ROWS - 1;
    if (s_sel >= NUM_ROWS) s_sel = 0;
}

/* Set a slider row from an overlay-space x inside its value bar, snapped to
 * the row's step. */
static void sliderSetFromX(struct Row *r, double ox)
{
    double lo = rowLo(r), hi = rowHi(r);
    if (hi <= lo) {
        return;
    }
    s32 bx0, bx1;
    sliderBarSpan(&bx0, &bx1);
    double f = (ox - bx0) / (double)(bx1 - bx0);
    if (f < 0) f = 0;
    if (f > 1) f = 1;
    double v = lo + f * (hi - lo);
    double step = (r->step > 0.0) ? r->step : 1.0;
    v = lround(v / step) * step;
    rowSet(r, v);
}

void optionsOverlayHandleInput(void)
{
    static int prevUp, prevDn, prevLf, prevRt, prevLmb, prevRmb;
    static int dragRow = -1;

    if (!s_open) {
        prevUp = prevDn = prevLf = prevRt = prevLmb = prevRmb = 0;
        dragRow = -1;
        return;
    }

    /* The overlay owns the mouse while it is open: force the OS cursor free +
     * visible (a stage poll would otherwise leave it locked/hidden). */
    inputSuspendForOverlay();

    const Uint8 *ks = SDL_GetKeyboardState(NULL);
    int mx = 0, my = 0;
    Uint32 mb = SDL_GetMouseState(&mx, &my);
    int lmb = (mb & SDL_BUTTON(SDL_BUTTON_LEFT))  ? 1 : 0;
    int rmb = (mb & SDL_BUTTON(SDL_BUTTON_RIGHT)) ? 1 : 0;

    int up = ks[SDL_SCANCODE_UP]    || ks[SDL_SCANCODE_KP_8];
    int dn = ks[SDL_SCANCODE_DOWN]  || ks[SDL_SCANCODE_KP_2];
    int lf = ks[SDL_SCANCODE_LEFT]  || ks[SDL_SCANCODE_KP_4];
    int rt = ks[SDL_SCANCODE_RIGHT] || ks[SDL_SCANCODE_KP_6]
          || ks[SDL_SCANCODE_RETURN] || ks[SDL_SCANCODE_KP_ENTER];

    /* ---- keyboard / D-pad nav ---- */
    if (up && !prevUp) s_sel = (s_sel + NUM_ROWS - 1) % NUM_ROWS;
    if (dn && !prevDn) s_sel = (s_sel + 1) % NUM_ROWS;
    if (lf && !prevLf) rowAdjust(&rows[s_sel], -1);
    if (rt && !prevRt) rowAdjust(&rows[s_sel], +1);

    /* ---- mouse ---- */
    int ww = 0, wh = 0;
    videoGetWindowSize(&ww, &wh);
    if (ww > 0 && wh > 0) {
        double ox = (double)mx * (double)viGetX() / ww;
        double oy = (double)my * (double)viGetY() / wh;
        int hoverRow = overlayRowAtY(oy);
        int onClose  = overlayInCloseBox(ox, oy);

        if (hoverRow >= 0 && !onClose) {
            s_sel = hoverRow;   /* hover-to-highlight */
        }

        /* left press. A click in the label column only focuses the row; a
         * click in the value/control column (>= the bar-span start) changes
         * it -- so clicking to select a toggle doesn't also flip it. */
        s32 bx0, bx1;
        sliderBarSpan(&bx0, &bx1);
        if (lmb && !prevLmb) {
            if (onClose) {
                optionsOverlayToggle();   /* close + configSave */
                return;
            }
            if (hoverRow >= 0 && ox >= bx0) {
                struct Row *r = &rows[hoverRow];
                if (r->kind == ROW_SLIDER && r->found) {
                    sliderSetFromX(r, ox);
                    dragRow = hoverRow;
                } else {
                    rowAdjust(r, +1);   /* toggle / cycle forward */
                }
            }
        }
        /* drag a slider */
        if (lmb && dragRow >= 0 && rows[dragRow].kind == ROW_SLIDER) {
            sliderSetFromX(&rows[dragRow], ox);
        }
        if (!lmb) {
            dragRow = -1;
        }
        /* right press in the value column: cycle back / decrement */
        if (rmb && !prevRmb && hoverRow >= 0 && !onClose && ox >= bx0) {
            rowAdjust(&rows[hoverRow], -1);
        }
    }

    prevUp = up; prevDn = dn; prevLf = lf; prevRt = rt;
    prevLmb = lmb; prevRmb = rmb;
}

/* ------------------------------------------------------------------------ */

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

static void valueText(const struct Row *r, char *out, int n)
{
    double v = rowGet(r);
    if (r->kind == ROW_RES) {
        if (videoIsFullscreen()) {
            snprintf(out, n, "(fullscreen)");
        } else if (s_resFitN <= 0) {
            snprintf(out, n, "n/a");
        } else {
            int i = s_resFit[s_resSel];
            snprintf(out, n, "%d x %d", kResList[i][0], kResList[i][1]);
        }
        return;
    }
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
        else                     snprintf(out, n, "%dx", (int)lround(v));
        return;
    }
    if (r->kind == ROW_SLIDER && r->type == CONFIG_OPT_FLOAT) {
        snprintf(out, n, "%.2f", v);
        return;
    }
    if (r->kind == ROW_SLIDER && (int)lround(v) == 0 &&
        strcmp(r->key, "Video.FpsCap") == 0) {
        snprintf(out, n, "OFF");
        return;
    }
    snprintf(out, n, "%d", (int)lround(v));
}

static Gfx *drawText(Gfx *gdl, s32 x, s32 y, const char *str, u32 colour)
{
    s32 px = x, py = y;
    /* width/height are the on-screen CLIP rect textRenderGlyph tests against
     * (clipX=start x, clipY=start y, +clipWidth/+clipHeight), NOT the text's
     * own measured size -- passing the measured w/h clipped every glyph out
     * (baseline+height > measured h => nothing drawn).  Match the game: pass
     * the full 2D viewport, like bondview2.c's debug-text path. */
    return textRender(gdl, &px, &py, (char *)str, ptrFontBankGothicChars,
                      ptrFontBankGothic, colour, viGetX(), viGetY(), 0, 0);
}

static s32 measureText(const char *str)
{
    s32 h = 0, w = 0;
    textMeasure(&h, &w, (char *)str, ptrFontBankGothicChars, ptrFontBankGothic, 0);
    return w;
}

/* Right-aligned: the string ends at xr. */
static Gfx *drawTextR(Gfx *gdl, s32 xr, s32 y, const char *str, u32 colour)
{
    return drawText(gdl, xr - measureText(str), y, str, colour);
}

Gfx *optionsOverlayEmit(void)
{
    if (!s_inited) {
        overlayInit();
    }

    fpsTick();

    if (!s_open) {
        const int showBrand = (current_menu == GE_MENU_FILE_SELECT);
        const int showFps = s_showFps && s_fpsText[0];
        if (!showBrand && !showFps) {
            return NULL;   /* no port-layer UI to append */
        }

        /* Lightweight mini DL: Ascension identity + settings discovery on file
         * select, and optional FPS anywhere. Nothing touches game menu logic. */
        const s32 fw = viGetX();
        const s32 fh = viGetY();
        Gfx *fgdl = s_buf;
        gDPPipeSync(fgdl++);
        gDPSetCycleType(fgdl++, G_CYC_1CYCLE);
        gDPSetTexturePersp(fgdl++, G_TP_NONE);
        gDPSetScissor(fgdl++, G_SC_NON_INTERLACE, 0, 0, fw, fh);
        if (showBrand) {
            const s32 brandWidth = measureText(ASCENSION_SIGNATURE);
            fgdl = fillRect(fgdl, 8, fh - 19, 8 + brandWidth, fh - 18,
                            0xD2, 0xB6, 0x5C, 220);

            if (!s_controlHintSeen) {
                const char *firstHint = "PRESS F10 // CONFIGURE";
                const s32 hintWidth = measureText(firstHint);
                const s32 hx0 = fw - hintWidth - 14;
                fgdl = fillRect(fgdl, hx0, fh - 36, fw - 6, fh - 22,
                                8, 10, 12, 225);
                fgdl = fillRect(fgdl, hx0, fh - 36, hx0 + 2, fh - 22,
                                0xD2, 0xB6, 0x5C, 255);
            }
        }
        fgdl = microcode_constructor(fgdl);
        if (showBrand) {
            fgdl = drawText(fgdl, 8, fh - 14, ASCENSION_SIGNATURE, ASC_UI_GOLD);
            fgdl = drawTextR(fgdl, fw - 8, fh - 14, "F10 // CONTROL", ASC_UI_SLATE);
            if (!s_controlHintSeen) {
                fgdl = drawTextR(fgdl, fw - 9, fh - 32, "PRESS F10 // CONFIGURE",
                                 ASC_UI_IVORY);
            }
        }
        if (showFps) {
            fgdl = drawTextR(fgdl, fw - 6, 6, s_fpsText, 0x40ff60ff);
        }
        gDPPipeSync(fgdl++);
        gSPEndDisplayList(fgdl++);
        return s_buf;
    }

    const s32 W = viGetX();
    const s32 H = viGetY();
    const s32 right = OV_RIGHT;
    const s32 panelTop = OV_TOP - 7;
    const s32 panelBottom = OV_ROW_Y(NUM_ROWS - 1) + OV_LINE / 2 + 3;
    s32 bx0, bx1;
    sliderBarSpan(&bx0, &bx1);
    Gfx *gdl = s_buf;

    gDPPipeSync(gdl++);
    gDPSetCycleType(gdl++, G_CYC_1CYCLE);
    gDPSetTexturePersp(gdl++, G_TP_NONE);
    gDPSetScissor(gdl++, G_SC_NON_INTERLACE, 0, 0, W, H);

    /* ---- pass 1: all fills (G_CC_PRIMITIVE) ---- */
    gdl = fillRect(gdl, 0, 0, W, H, 0, 0, 0, 150);                       /* dim */
    gdl = fillRect(gdl, OV_X0 - 8, panelTop, W - (OV_X0 - 8), panelBottom,
                   8, 10, 12, 222);                                     /* carbon panel */
    gdl = fillRect(gdl, OV_X0 - 8, panelTop, W - (OV_X0 - 8), panelTop + 1,
                   0xD2, 0xB6, 0x5C, 235);                              /* identity rule */
    gdl = fillRect(gdl, OV_CB_X0, OV_CB_Y0, OV_CB_X1, OV_CB_Y1,
                   104, 31, 31, 235);                                   /* close */

    for (int i = 0; i < NUM_ROWS; i++) {
        s32 rowY = OV_ROW_Y(i);
        if (i == s_sel) {
            gdl = fillRect(gdl, OV_X0 - 4, rowY - 2, W - (OV_X0 - 4),
                           rowY + OV_LINE - 3, 38, 34, 22, 220);
            gdl = fillRect(gdl, OV_X0 - 6, rowY - 2, OV_X0 - 4,
                           rowY + OV_LINE - 3, 0xD2, 0xB6, 0x5C, 255);
        }
        if (rows[i].kind == ROW_SLIDER && rows[i].found) {
            double lo = rowLo(&rows[i]), hi = rowHi(&rows[i]);
            double f = (hi > lo) ? (rowGet(&rows[i]) - lo) / (hi - lo) : 0.0;
            if (f < 0) f = 0; if (f > 1) f = 1;
            s32 by = rowY + 3;
            gdl = fillRect(gdl, bx0, by, bx1, by + 4, 52, 52, 48, 220);
            gdl = fillRect(gdl, bx0, by, bx0 + (s32)((bx1 - bx0) * f), by + 4,
                           210, 182, 92, 255);
        }
    }

    /* ---- pass 2: text ---- */
    gdl = microcode_constructor(gdl);

    gdl = drawText(gdl, OV_X0, OV_TOP, ASCENSION_SIGNATURE, ASC_UI_GOLD);
    gdl = drawText(gdl, OV_X0, OV_TOP + OV_LINE,
                   rows[s_sel].help ? rows[s_sel].help : "PC options",
                   ASC_UI_SLATE);
    gdl = drawText(gdl, (OV_CB_X0 + OV_CB_X1) / 2 - measureText("X") / 2,
                   OV_TOP, "X", ASC_UI_IVORY);                          /* close glyph */

    for (int i = 0; i < NUM_ROWS; i++) {
        s32 rowY = OV_ROW_Y(i);
        u32 col = (i == s_sel) ? ASC_UI_IVORY : ASC_UI_TEXT;
        char val[48];

        gdl = drawText(gdl, OV_LABEL_X, rowY, (char *)rows[i].label,
                       rows[i].found ? col : ASC_UI_SLATE);
        if (!rows[i].found) {
            gdl = drawTextR(gdl, right, rowY, "(n/a)", ASC_UI_SLATE);
            continue;
        }

        valueText(&rows[i], val, sizeof(val));
        if (rows[i].restart) {
            /* Value remains readable; the lifecycle cue is deliberately gold
             * so it cannot be mistaken for a disabled state. */
            gdl = drawText(gdl, bx0, rowY, val, col);
            gdl = drawTextR(gdl, right, rowY, "RESTART", ASC_UI_GOLD_DIM);
        } else {
            gdl = drawTextR(gdl, right, rowY, val, col);
        }
    }

    gDPPipeSync(gdl++);
    gSPEndDisplayList(gdl++);

    if ((gdl - s_buf) > OV_BUF_CMDS) {
        sysLogPrintf(LOG_ERROR, "optionsoverlay: DL overflow (%d)", (int)(gdl - s_buf));
    }
    return s_buf;
}
