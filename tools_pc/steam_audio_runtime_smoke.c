#include <SDL.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "ascension_steam_audio.h"

#define FRAME 128
#define SOURCE_FRAME 16
#define SOURCE_TEST_FRAMES 32

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
    ASC_iplBinauralEffectCreateFn binauralCreate = NULL;
    ASC_iplBinauralEffectReleaseFn binauralRelease = NULL;
    ASC_iplBinauralEffectResetFn binauralReset = NULL;
    ASC_iplBinauralEffectApplyFn binauralApply = NULL;
    ASC_IPLContext context = NULL;
    ASC_IPLHRTF hrtf = NULL;
    ASC_IPLHRTF sourceHrtf = NULL;
    ASC_IPLVirtualSurroundEffect effect = NULL;
    ASC_IPLBinauralEffect binaural = NULL;
    ASC_IPLContextSettings contextSettings;
    ASC_IPLAudioSettings audioSettings;
    ASC_IPLAudioSettings sourceAudioSettings;
    ASC_IPLHRTFSettings hrtfSettings;
    ASC_IPLVirtualSurroundEffectSettings effectSettings;
    ASC_IPLVirtualSurroundEffectParams params;
    ASC_IPLBinauralEffectSettings binauralSettings;
    ASC_IPLBinauralEffectParams binauralParams;
    float inL[FRAME] = {0}, inR[FRAME] = {0}, outL[FRAME] = {0}, outR[FRAME] = {0};
    float *inPlanes[2] = {inL, inR};
    float *outPlanes[2] = {outL, outR};
    ASC_IPLAudioBuffer inBuffer = {2, FRAME, inPlanes};
    ASC_IPLAudioBuffer outBuffer = {2, FRAME, outPlanes};
    float sourceIn[SOURCE_FRAME] = {0};
    float sourceOutL[SOURCE_FRAME] = {0};
    float sourceOutR[SOURCE_FRAME] = {0};
    float *sourceInPlanes[1] = {sourceIn};
    float *sourceOutPlanes[2] = {sourceOutL, sourceOutR};
    ASC_IPLAudioBuffer sourceInBuffer = {1, SOURCE_FRAME, sourceInPlanes};
    ASC_IPLAudioBuffer sourceOutBuffer = {2, SOURCE_FRAME, sourceOutPlanes};
    double virtualEnergy = 0.0;
    double binauralEnergy = 0.0;
    int i;
    int frame;

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
    LOAD(binauralCreate, "iplBinauralEffectCreate");
    LOAD(binauralRelease, "iplBinauralEffectRelease");
    LOAD(binauralReset, "iplBinauralEffectReset");
    LOAD(binauralApply, "iplBinauralEffectApply");
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

    inL[0] = 0.75f;
    inR[0] = 0.20f;
    params.hrtf = hrtf;
    effectApply(effect, &params, &inBuffer, &outBuffer);

    for (i = 0; i < FRAME; ++i) {
        if (!isfinite(outL[i]) || !isfinite(outR[i])) {
            fprintf(stderr, "Steam Audio virtual surround produced non-finite output at frame %d\n", i);
            effectRelease(&effect);
            hrtfRelease(&hrtf);
            contextRelease(&context);
            SDL_UnloadObject(lib);
            return 7;
        }
        virtualEnergy += fabs((double)outL[i]) + fabs((double)outR[i]);
    }
    if (virtualEnergy < 1e-6) {
        fprintf(stderr, "Steam Audio virtual surround smoke produced silent output\n");
        effectRelease(&effect);
        hrtfRelease(&hrtf);
        contextRelease(&context);
        SDL_UnloadObject(lib);
        return 8;
    }

    /* Exercise the exact low-latency format used by the in-game physical
     * voices: mono, 22.05 kHz, 16 samples, bilinear HRTF, source to the right.
     *
     * HRTF is convolution and therefore has persistent state/tail. A valid
     * implementation is allowed to delay an impulse beyond the first tiny
     * 16-sample block. Keep the effect alive and inspect a sequence of blocks;
     * this tests the real streaming contract instead of assuming zero DSP
     * latency and falsely rejecting a correct runtime. */
    sourceAudioSettings.samplingRate = 22050;
    sourceAudioSettings.frameSize = SOURCE_FRAME;
    if (hrtfCreate(context, &sourceAudioSettings, &hrtfSettings, &sourceHrtf) != ASC_IPL_STATUS_SUCCESS || !sourceHrtf) {
        fprintf(stderr, "Steam Audio source HRTF creation failed\n");
        effectRelease(&effect);
        hrtfRelease(&hrtf);
        contextRelease(&context);
        SDL_UnloadObject(lib);
        return 9;
    }

    memset(&binauralSettings, 0, sizeof(binauralSettings));
    binauralSettings.hrtf = sourceHrtf;
    if (binauralCreate(context, &sourceAudioSettings, &binauralSettings, &binaural) != ASC_IPL_STATUS_SUCCESS || !binaural) {
        fprintf(stderr, "Steam Audio binaural effect creation failed\n");
        hrtfRelease(&sourceHrtf);
        effectRelease(&effect);
        hrtfRelease(&hrtf);
        contextRelease(&context);
        SDL_UnloadObject(lib);
        return 10;
    }

    memset(&binauralParams, 0, sizeof(binauralParams));
    binauralParams.direction.x = 1.0f;
    binauralParams.direction.y = 0.0f;
    binauralParams.direction.z = 0.0f;
    binauralParams.interpolation = ASC_IPL_HRTFINTERPOLATION_BILINEAR;
    binauralParams.spatialBlend = 1.0f;
    binauralParams.hrtf = sourceHrtf;
    binauralParams.peakDelays = NULL;
    binauralReset(binaural);

    for (frame = 0; frame < SOURCE_TEST_FRAMES; ++frame) {
        memset(sourceIn, 0, sizeof(sourceIn));
        memset(sourceOutL, 0, sizeof(sourceOutL));
        memset(sourceOutR, 0, sizeof(sourceOutR));
        if (frame == 0) {
            sourceIn[0] = 0.75f;
        }

        binauralApply(binaural, &binauralParams, &sourceInBuffer, &sourceOutBuffer);

        for (i = 0; i < SOURCE_FRAME; ++i) {
            if (!isfinite(sourceOutL[i]) || !isfinite(sourceOutR[i])) {
                fprintf(stderr, "Steam Audio binaural source produced non-finite output at block %d sample %d\n", frame, i);
                binauralRelease(&binaural);
                hrtfRelease(&sourceHrtf);
                effectRelease(&effect);
                hrtfRelease(&hrtf);
                contextRelease(&context);
                SDL_UnloadObject(lib);
                return 11;
            }
            binauralEnergy += fabs((double)sourceOutL[i]) + fabs((double)sourceOutR[i]);
        }
    }

    binauralRelease(&binaural);
    hrtfRelease(&sourceHrtf);
    effectRelease(&effect);
    hrtfRelease(&hrtf);
    contextRelease(&context);
    SDL_UnloadObject(lib);

    if (binauralEnergy < 1e-6) {
        fprintf(stderr, "Steam Audio binaural source streaming smoke produced silent output\n");
        return 12;
    }

    printf("Steam Audio 4.8.1 ABI/runtime smoke: PASS (virtual=%.6f, binaural=%.6f)\n",
           virtualEnergy, binauralEnergy);
    return 0;
}
