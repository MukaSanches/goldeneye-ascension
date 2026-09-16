#include "ascension_audio_world_runtime.h"
#include "ascension_audio_world.h"

#include <pthread.h>
#include <stdatomic.h>
#include <stdlib.h>

#define ASCENSION_GE_AUDIO_RATE 22050

static pthread_once_t s_world_once = PTHREAD_ONCE_INIT;
static atomic_int s_world_active = 0;

static void ascensionAudioWorldRuntimeShutdown(void)
{
    if (atomic_exchange_explicit(&s_world_active, 0, memory_order_acq_rel)) {
        ascensionAudioWorldShutdown();
    }
}

static void ascensionAudioWorldRuntimeInitOnce(void)
{
    const char *mode = getenv("GE_ASCENSION_WORLD3D");

    /* Developer/safety A-B switch. It disables only the new real-world layer;
     * the proven Steam Audio per-source HRTF and original GoldenEye fallback
     * remain available. */
    if (mode && mode[0] == '0' && mode[1] == '\0') {
        return;
    }

    if (ascensionAudioWorldInit(ASCENSION_GE_AUDIO_RATE)) {
        atomic_store_explicit(&s_world_active, 1, memory_order_release);
        atexit(ascensionAudioWorldRuntimeShutdown);
    }
}

int ascensionAudioWorldRuntimeEnsure(void)
{
    pthread_once(&s_world_once, ascensionAudioWorldRuntimeInitOnce);
    return atomic_load_explicit(&s_world_active, memory_order_acquire) != 0;
}

int ascensionAudioWorldRuntimeActive(void)
{
    return atomic_load_explicit(&s_world_active, memory_order_acquire) != 0;
}
