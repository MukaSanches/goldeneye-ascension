/* Scheduler-thread integration for the optional Human AI overlay.
 *
 * videoInit() installs its screenshot/frame-dump callback in fast3d's
 * gfx_pre_swap_hook. We chain that callback instead of editing video.c or any
 * original game source: Human AI runs once per rendered simulation frame on
 * the scheduler thread, then the original capture hook continues unchanged.
 */

#include <SDL.h>

#include "system.h"
#include "human_ai.h"

/* Defined with C linkage by port/fast3d/gfx_sdl2.cpp. */
extern void (*gfx_pre_swap_hook)(void);

static void (*s_previousPreSwapHook)(void) = NULL;
static int s_attached = 0;
static int s_f9WasDown = 0;

static void humanAiPreSwapHook(void)
{
    /* Runtime reversible toggle. SDL events are pumped by the host thread,
     * while this only reads the stable keyboard-state snapshot. Edge detect
     * here so key repeat cannot bounce between modes. */
    const Uint8 *keys = SDL_GetKeyboardState(NULL);
    int f9Down = keys && keys[SDL_SCANCODE_F9];
    if (f9Down && !s_f9WasDown) {
        humanAiToggle();
    }
    s_f9WasDown = f9Down;

    humanAiTick();

    if (s_previousPreSwapHook) {
        s_previousPreSwapHook();
    }
}

void humanAiAttachRenderHook(void)
{
    if (s_attached) return;
    s_previousPreSwapHook = gfx_pre_swap_hook;
    gfx_pre_swap_hook = humanAiPreSwapHook;
    s_attached = 1;
    sysLogPrintf(LOG_INFO, "human-ai: scheduler hook attached (F9 toggles Classic/Human)");
}

void humanAiDetachRenderHook(void)
{
    if (!s_attached) return;
    if (gfx_pre_swap_hook == humanAiPreSwapHook) {
        gfx_pre_swap_hook = s_previousPreSwapHook;
    }
    s_previousPreSwapHook = NULL;
    s_attached = 0;
    s_f9WasDown = 0;
}
