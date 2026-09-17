/*
 * Android runtime bridge for Ascension's Q Watch state gate.
 *
 * The desktop 0.0.4 prepare pipeline injects this function into options.c via
 * tools_pc/apply_watch_runtime_fix.py. Android intentionally builds the clean
 * source tree instead of running the desktop mutation stack, so provide the
 * same semantics as a normal Android translation unit.
 */
#if defined(__ANDROID__)

#include <ultra64.h>
#include <bondconstants.h>
#include "bondview.h"
#include "player.h"
#include "ascension_watch.h"

int ascensionWatchIsActive(void)
{
    return g_CurrentPlayer != NULL &&
           g_CurrentPlayer->watch_animation_state != WATCH_ANIMATION_0x0;
}

#endif /* __ANDROID__ */
