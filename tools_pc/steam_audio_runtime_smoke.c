#include <SDL.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "ascension_steam_audio.h"

#define FRAME 128

static int loadfn(void *lib, const char *name, void *dst, size_t size)
{
    void *p = SDL_LoadFunction(lib, name);
    if (!p || size != sizeof(p)) {
        fprintf(stderr, "missing Steam Audio symbol: %s (%s)\n", name, SDL_GetError());
        return 0;
    }
    memcpy(dst, &p, sizeof(p));
    return 1;
}

int main(int argc, char **argv)
{
    const char *path = argc > 1 ? argv[1] : "phonon.dll";
    void *lib = SDL_LoadObject(path);
    ASC_iplContextCreateFn contextCreate = NULL;
    ASC_iplContextReleaseFn contextRelease = NULL;
    ASC_iplHRTFCreateFn hrtfCreate = NULL;
    ASC_iplHRTFReleaseFn hrtfRelease = NULL;
    ASC_iplVirtualSurroundEffectCreateFn effectCreate = NULL;
    ASC_iplVirtualSurroundEffectReleaseFn effectRelease = NULL;
    ASC_iplVirtualSurroundEffectApplyFn effectApply = NULL;
    ASC_IPLContext context = NULL;
    ASC_IPLHRTF hrtf = NULL;
    ASC_IPLVirtualSurroundEffect effect = NULL;
    ASC_IPLContextSettings contextSettings;
    ASC_IPLAudioSettings audioSettings;
    ASC_IPLHRTFSettings hrtfSettings;
    ASC_IPLVirtualSurroundEffectSettings effectSettings;
    ASC_IPLVirtualSurroundEffectParams params;
    float inL[FRAME] = {0}, inR[FRAME] = {0}, outL[FRAME] = {0}, outR[FRAME] = {0};
    float *inPlanes[2] = {inL, inR};
    float *outPlanes[2] = {outL, outR};
    ASC_IPLAudioBuffer inBuffer = {2, FRAME, inPlanes};
    ASC_IPLAudioBuffer outBuffer = {2, FRAME, outPlanes};
    double energy = 0.0;
    int i;

    if (!lib) {
        fprintf(stderr, "could not load %s: %s\n", path, SDL_GetError());
        return 2;
    }

#define LOAD(var, symbol) do { if (!loadfn(lib, symbol, &var, sizeof(var))) return 3; } while (0)
    LOAD(contextCreate, "iplContextCreate");
    LOAD(contextRelease, "iplContextRelease");
    LOAD(hrtfCreate, "iplHRTFCreate");
    LOAD(hrtfRelease, "iplHRTFRelease");
    LOAD(effectCreate, "iplVirtualSurroundEffectCreate");
    LOAD(effectRelease, "iplVirtualSurroundEffectRelease");
    LOAD(effectApply, "iplVirtualSurroundEffectApply");
#undef LOAD

    memset(&contextSettings, 0, sizeof(contextSettings));
    contextSettings.version = ASC_STEAMAUDIO_VERSION;
    contextSettings.simdLevel = ASC_IPL_SIMDLEVEL_SSE2;
    if (contextCreate(&contextSettings, &context) != ASC_IPL_STATUS_SUCCESS || !context) {
        fprintf(stderr, "Steam Audio context creation failed\n");
        SDL_UnloadObject(lib);
        return 4;
    }

    audioSettings.samplingRate = 22050;
    audioSettings.frameSize = FRAME;
    memset(&hrtfSettings, 0, sizeof(hrtfSettings));
    hrtfSettings.type = ASC_IPL_HRTFTYPE_DEFAULT;
    /* Steam Audio's public contract requires a positive linear volume; 1.0 is
       its neutral value and is also used by Valve's virtual-surround benchmark. */
    hrtfSettings.volume = 1.0f;
    hrtfSettings.normType = ASC_IPL_HRTFNORMTYPE_RMS;
    if (hrtfCreate(context, &audioSettings, &hrtfSettings, &hrtf) != ASC_IPL_STATUS_SUCCESS || !hrtf) {
        fprintf(stderr, "Steam Audio HRTF creation failed\n");
        contextRelease(&context);
        SDL_UnloadObject(lib);
        return 5;
    }

    memset(&effectSettings, 0, sizeof(effectSettings));
    effectSettings.speakerLayout.type = ASC_IPL_SPEAKERLAYOUTTYPE_STEREO;
    effectSettings.hrtf = hrtf;
    if (effectCreate(context, &audioSettings, &effectSettings, &effect) != ASC_IPL_STATUS_SUCCESS || !effect) {
        fprintf(stderr, "Steam Audio virtual surround creation failed\n");
        hrtfRelease(&hrtf);
        contextRelease(&context);
        SDL_UnloadObject(lib);
        return 6;
    }

    /* A non-symmetric stereo impulse is enough to prove the DSP executed and
       produced finite binaural output rather than simply loading the DLL. */
    inL[0] = 0.75f;
    inR[0] = 0.20f;
    params.hrtf = hrtf;
    effectApply(effect, &params, &inBuffer, &outBuffer);

    for (i = 0; i < FRAME; ++i) {
        if (!isfinite(outL[i]) || !isfinite(outR[i])) {
            fprintf(stderr, "Steam Audio produced non-finite output at frame %d\n", i);
            effectRelease(&effect);
            hrtfRelease(&hrtf);
            contextRelease(&context);
            SDL_UnloadObject(lib);
            return 7;
        }
        energy += fabs((double)outL[i]) + fabs((double)outR[i]);
    }

    effectRelease(&effect);
    hrtfRelease(&hrtf);
    contextRelease(&context);
    SDL_UnloadObject(lib);

    if (energy < 1e-6) {
        fprintf(stderr, "Steam Audio DSP smoke produced silent output\n");
        return 8;
    }

    printf("Steam Audio 4.8.1 ABI/runtime/HRTF smoke: PASS (energy=%.6f)\n", energy);
    return 0;
}
