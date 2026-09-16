#include <stdlib.h>
#include <SDL.h>
#include <PR/ultratypes.h>
#include <PR/os.h>

#include "system.h"
#include "config.h"
#include "romdata.h"
#include "dram.h"
#include "video.h"
#include "audio.h"
#include "input.h"
#include "mixer.h"
#include "crash.h"
#include "thread_config.h"
#include "ascension_defaults.h"

extern void mainproc(void *args);
extern OSThread mainThread;

static void androidPersist(void)
{
    configSave();
}

/* SDLActivity looks for SDL_main in the application shared library. */
int SDL_main(int argc, char **argv)
{
    sysSetArgs(argc, argv);
    sysLogPrintf(LOG_INFO, "GoldenEye Ascension Android native core starting");
    crashInit();
    configLoad();
    ascensionRestoreOriginalVisualDefaultsOnce();
    atexit(androidPersist);

    if (romdataInit() != 0) {
        sysLogPrintf(LOG_ERROR, "ROM unavailable or invalid in Android app storage");
        return 2;
    }

    if (!dramReserve()) {
        sysLogPrintf(LOG_ERROR, "Unable to reserve compatible N64 DRAM views");
        return 3;
    }

    if (videoInit() != 0) {
        sysLogPrintf(LOG_ERROR, "videoInit failed");
        return 4;
    }

    if (audioInit() != 0)
        sysLogPrintf(LOG_WARNING, "audio output unavailable; continuing with fail-audible fallback disabled");
    mixerInit();
    inputInit();

    portKernelInit();
    osCreateThread(&mainThread, MAIN_THREAD_ID, &mainproc, NULL, NULL,
                   MAIN_THREAD_PRIORITY);
    osStartThread(&mainThread);

    /* SDL's Android backend translates lifecycle, controller and window
     * events into the same queue used by the desktop port. Keep event pumping
     * on the SDL/game host thread exactly as the PC build does. */
    while (!sysRestartRequested()) {
        videoPumpEvents();
        sysSleep(8000);
    }

    configSave();
    audioDestroy();
    return 0;
}
