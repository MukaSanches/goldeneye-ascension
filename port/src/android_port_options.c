/*
 * Android definitions for host-port options whose desktop source is normally
 * completed by the Ascension prepare stack before a PC build.
 *
 * Keep the option contract identical to the upstream video layer: zero means
 * original GoldenEye damage flash, one suppresses the coloured hit flash.
 */
#if defined(__ANDROID__)

#include <PR/ultratypes.h>
#include "config.h"

s32 portNoHitFlash = 0;

PD_CONSTRUCTOR static void androidPortGameOptionsInit(void)
{
    configRegisterInt("Game.NoHitFlash", &portNoHitFlash, 0, 1);
}

#endif /* __ANDROID__ */
