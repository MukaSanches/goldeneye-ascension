#include <SDL.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "system.h"
#include "ascension_audio_remaster.h"
#include "ascension_steam_audio.h"

#define ASC_AUDIO_FRAME 128
#define ASC_AUDIO_FIFO_FRAMES 8192
#define ASC_AUDIO_MAX_CALL_FRAMES 4096
#define ASC_SOURCE_EFFECTS 64

/*
 * Ascension Audio Remaster
 * ------------------------
 * There are now two Steam Audio paths, with an audible-safe fallback chain:
 *
 *  1. Preferred: per-source IPLBinauralEffect. The software RSP mixer keeps
 *     GoldenEye's original mix intact, captures each mono physical voice,
 *     derives the voice's authored horizontal direction from its equal-power
 *     L/R envelope, and asks this module to render a true HRTF for that one
 *     source. The original contribution is replaced only after a complete,
 *     finite binaural frame has been produced successfully.
 *
 *  2. Fallback: the earlier post-mix IPLVirtualSurroundEffect. If the
 *     per-source API is unavailable, disabled, or cannot initialize, the
 *     proven stereo HRTF path remains available exactly as before.
 *
 * If Steam Audio itself is unavailable, conservative mastering remains. If
 * GE_ASCENSION_AUDIO_BYPASS=1 is set, the untouched GoldenEye mix is returned.
 * GE_ASCENSION_SOURCE_HRTF=0 disables only the new source path for A/B tests.
 *
 * No allocation, file I/O, mutex, or Steam Audio object construction occurs
 * in the per-source processing callback. Every effect is pre-created here.
 */

typedef struct {
    float data[ASC_AUDIO_FIFO_FRAMES][2];
    unsigned readPos;
    unsigned writePos;
    unsigned count;
} StereoFifo;

typedef struct {
    ASC_IPLBinauralEffect effect;
    uint32_t voiceKey;
    uint64_t lastUse;
    int assigned;
} SourceEffectSlot;

typedef struct {
    void *library;
    ASC_IPLContext context;

    /* Legacy post-mix fallback, kept deliberately intact. */
    ASC_IPLHRTF hrtf;
    ASC_IPLVirtualSurroundEffect effect;

    /* High-quality per-source path. */
    ASC_IPLHRTF sourceHrtf;
    SourceEffectSlot sourceEffects[ASC_SOURCE_EFFECTS];
    uint64_t sourceSerial;

    ASC_iplContextCreateFn contextCreate;
    ASC_iplContextReleaseFn contextRelease;
    ASC_iplHRTFCreateFn hrtfCreate;
    ASC_iplHRTFReleaseFn hrtfRelease;
    ASC_iplVirtualSurroundEffectCreateFn effectCreate;
    ASC_iplVirtualSurroundEffectReleaseFn effectRelease;
    ASC_iplVirtualSurroundEffectResetFn effectReset;
    ASC_iplVirtualSurroundEffectApplyFn effectApply;
    ASC_iplBinauralEffectCreateFn binauralCreate;
    ASC_iplBinauralEffectReleaseFn binauralRelease;
    ASC_iplBinauralEffectResetFn binauralReset;
    ASC_iplBinauralEffectApplyFn binauralApply;
    ASC_iplBinauralEffectGetTailFn binauralGetTail;
    ASC_iplBinauralEffectGetTailSizeFn binauralGetTailSize;

    int sampleRate;
    int initialized;
    int steamActive;
    int sourceActive;
    int bypass;

    StereoFifo inputFifo;
    StereoFifo outputFifo;

    float inL[ASC_AUDIO_FRAME];
    float inR[ASC_AUDIO_FRAME];
    float wetL[ASC_AUDIO_FRAME];
    float wetR[ASC_AUDIO_FRAME];
    float *inPlanes[2];
    float *outPlanes[2];

    int16_t returnS16[ASC_AUDIO_MAX_CALL_FRAMES * 2];

    float dcPrevIn[2];
    float dcPrevOut[2];
    float lowState[2];
    float highLPState[2];
    float lowAlpha;
    float highAlpha;
} AscensionAudioState;

static AscensionAudioState s_audio;

static int fifoPush(StereoFifo *fifo, float l, float r)
{
    if (fifo->count >= ASC_AUDIO_FIFO_FRAMES) {
        return 0;
    }
    fifo->data[fifo->writePos][0] = l;
    fifo->data[fifo->writePos][1] = r;
    fifo->writePos = (fifo->writePos + 1u) % ASC_AUDIO_FIFO_FRAMES;
    fifo->count++;
    return 1;
}

static int fifoPop(StereoFifo *fifo, float *l, float *r)
{
    if (!fifo->count) {
        return 0;
    }
    *l = fifo->data[fifo->readPos][0];
    *r = fifo->data[fifo->readPos][1];
    fifo->readPos = (fifo->readPos + 1u) % ASC_AUDIO_FIFO_FRAMES;
    fifo->count--;
    return 1;
}

static void steamLog(ASC_IPLLogLevel level, const char *message)
{
    if (!message) {
        return;
    }
    if (level == ASC_IPL_LOGLEVEL_ERROR) {
        sysLogPrintf(LOG_ERROR, "Steam Audio: %s", message);
    } else if (level == ASC_IPL_LOGLEVEL_WARNING) {
        sysLogPrintf(LOG_NOTE, "Steam Audio: %s", message);
    } else if (getenv("GE_ASCENSION_AUDIO_DIAG")) {
        sysLogPrintf(LOG_NOTE, "Steam Audio: %s", message);
    }
}

static int loadFunction(const char *name, void *destination, size_t destinationSize)
{
    void *symbol;
    if (!s_audio.library || destinationSize != sizeof(symbol)) {
        return 0;
    }
    symbol = SDL_LoadFunction(s_audio.library, name);
    if (!symbol) {
        return 0;
    }
    memcpy(destination, &symbol, sizeof(symbol));
    return 1;
}

static void *loadSteamAudioLibrary(void)
{
#if defined(_WIN32)
    const char *runtimeName = "phonon.dll";
    const char *repoPath = "third_party/steam-audio/4.8.1/windows-x64/phonon.dll";
#elif defined(__APPLE__)
    const char *runtimeName = "libphonon.dylib";
    const char *repoPath = "third_party/steam-audio/4.8.1/osx/libphonon.dylib";
#else
    const char *runtimeName = "libphonon.so";
    const char *repoPath = "third_party/steam-audio/4.8.1/linux-x64/libphonon.so";
#endif
    void *lib = NULL;
    char *base = SDL_GetBasePath();
    if (base) {
        size_t n = strlen(base) + strlen(runtimeName) + 2u;
        char *full = (char *)SDL_malloc(n);
        if (full) {
            snprintf(full, n, "%s%s", base, runtimeName);
            lib = SDL_LoadObject(full);
            SDL_free(full);
        }
        SDL_free(base);
    }
    if (!lib) {
        lib = SDL_LoadObject(runtimeName);
    }
    if (!lib) {
        lib = SDL_LoadObject(repoPath);
    }
    return lib;
}

static ASC_IPLSIMDLevel bestSimdLevel(void)
{
    if (SDL_HasAVX2()) {
        return ASC_IPL_SIMDLEVEL_AVX2;
    }
    if (SDL_HasAVX()) {
        return ASC_IPL_SIMDLEVEL_AVX;
    }
    if (SDL_HasSSE42()) {
        return ASC_IPL_SIMDLEVEL_SSE4;
    }
    return ASC_IPL_SIMDLEVEL_SSE2;
}

static void disableSourceHrtf(void)
{
    unsigned i;

    for (i = 0; i < ASC_SOURCE_EFFECTS; ++i) {
        if (s_audio.sourceEffects[i].effect && s_audio.binauralRelease) {
            s_audio.binauralRelease(&s_audio.sourceEffects[i].effect);
        }
        s_audio.sourceEffects[i].voiceKey = 0;
        s_audio.sourceEffects[i].lastUse = 0;
        s_audio.sourceEffects[i].assigned = 0;
    }
    if (s_audio.sourceHrtf && s_audio.hrtfRelease) {
        s_audio.hrtfRelease(&s_audio.sourceHrtf);
    }
    s_audio.sourceActive = 0;
    s_audio.sourceSerial = 0;
}

static void releaseSteam(void)
{
    disableSourceHrtf();
    if (s_audio.effect && s_audio.effectRelease) {
        s_audio.effectRelease(&s_audio.effect);
    }
    if (s_audio.hrtf && s_audio.hrtfRelease) {
        s_audio.hrtfRelease(&s_audio.hrtf);
    }
    if (s_audio.context && s_audio.contextRelease) {
        s_audio.contextRelease(&s_audio.context);
    }
    if (s_audio.library) {
        SDL_UnloadObject(s_audio.library);
        s_audio.library = NULL;
    }
    s_audio.steamActive = 0;
}

static int loadBinauralApi(void)
{
#define LOAD_SOURCE(member, symbol) \
    do { \
        if (!loadFunction(symbol, &s_audio.member, sizeof(s_audio.member))) { \
            sysLogPrintf(LOG_NOTE, \
                "Ascension Audio: optional Steam Audio source symbol missing: %s; post-mix fallback retained", \
                symbol); \
            s_audio.binauralCreate = NULL; \
            s_audio.binauralRelease = NULL; \
            s_audio.binauralReset = NULL; \
            s_audio.binauralApply = NULL; \
            s_audio.binauralGetTail = NULL; \
            s_audio.binauralGetTailSize = NULL; \
            return 0; \
        } \
    } while (0)

    LOAD_SOURCE(binauralCreate, "iplBinauralEffectCreate");
    LOAD_SOURCE(binauralRelease, "iplBinauralEffectRelease");
    LOAD_SOURCE(binauralReset, "iplBinauralEffectReset");
    LOAD_SOURCE(binauralApply, "iplBinauralEffectApply");
    LOAD_SOURCE(binauralGetTail, "iplBinauralEffectGetTail");
    LOAD_SOURCE(binauralGetTailSize, "iplBinauralEffectGetTailSize");
#undef LOAD_SOURCE
    return 1;
}

static int initSourceHrtf(void)
{
    ASC_IPLAudioSettings audioSettings;
    ASC_IPLHRTFSettings hrtfSettings;
    ASC_IPLBinauralEffectSettings effectSettings;
    const char *sourceMode;
    unsigned i;

    sourceMode = getenv("GE_ASCENSION_SOURCE_HRTF");
    if (sourceMode && sourceMode[0] == '0' && sourceMode[1] == '\0') {
        sysLogPrintf(LOG_NOTE,
            "Ascension Audio: per-source HRTF disabled by GE_ASCENSION_SOURCE_HRTF=0; post-mix fallback active");
        return 0;
    }

    if (!loadBinauralApi()) {
        return 0;
    }

    audioSettings.samplingRate = s_audio.sampleRate;
    audioSettings.frameSize = (ASC_IPLint32)ASCENSION_AUDIO_SOURCE_FRAME;

    memset(&hrtfSettings, 0, sizeof(hrtfSettings));
    hrtfSettings.type = ASC_IPL_HRTFTYPE_DEFAULT;
    hrtfSettings.volume = 1.0f;
    hrtfSettings.normType = ASC_IPL_HRTFNORMTYPE_RMS;

    if (s_audio.hrtfCreate(s_audio.context, &audioSettings, &hrtfSettings,
                           &s_audio.sourceHrtf) != ASC_IPL_STATUS_SUCCESS ||
        !s_audio.sourceHrtf) {
        sysLogPrintf(LOG_NOTE,
            "Ascension Audio: per-source HRTF creation failed; post-mix fallback retained");
        disableSourceHrtf();
        return 0;
    }

    memset(&effectSettings, 0, sizeof(effectSettings));
    effectSettings.hrtf = s_audio.sourceHrtf;

    for (i = 0; i < ASC_SOURCE_EFFECTS; ++i) {
        if (s_audio.binauralCreate(s_audio.context, &audioSettings, &effectSettings,
                                   &s_audio.sourceEffects[i].effect) != ASC_IPL_STATUS_SUCCESS ||
            !s_audio.sourceEffects[i].effect) {
            sysLogPrintf(LOG_NOTE,
                "Ascension Audio: per-source HRTF pool creation failed at slot %u; post-mix fallback retained",
                i);
            disableSourceHrtf();
            return 0;
        }
    }

    s_audio.sourceActive = 1;
    sysLogPrintf(LOG_NOTE,
        "Ascension Audio: per-source Steam Audio HRTF active (%u voices, %u-sample frames, bilinear)",
        (unsigned)ASC_SOURCE_EFFECTS, (unsigned)ASCENSION_AUDIO_SOURCE_FRAME);
    return 1;
}

static int initSteam(void)
{
    ASC_IPLContextSettings contextSettings;
    ASC_IPLAudioSettings audioSettings;
    ASC_IPLHRTFSettings hrtfSettings;
    ASC_IPLVirtualSurroundEffectSettings effectSettings;

    s_audio.library = loadSteamAudioLibrary();
    if (!s_audio.library) {
        sysLogPrintf(LOG_NOTE,
            "Ascension Audio: Steam Audio runtime not found; mastering fallback active (%s)",
            SDL_GetError());
        return 0;
    }

#define LOAD_REQUIRED(member, symbol) \
    do { \
        if (!loadFunction(symbol, &s_audio.member, sizeof(s_audio.member))) { \
            sysLogPrintf(LOG_ERROR, "Ascension Audio: Steam Audio symbol missing: %s", symbol); \
            releaseSteam(); \
            return 0; \
        } \
    } while (0)

    LOAD_REQUIRED(contextCreate, "iplContextCreate");
    LOAD_REQUIRED(contextRelease, "iplContextRelease");
    LOAD_REQUIRED(hrtfCreate, "iplHRTFCreate");
    LOAD_REQUIRED(hrtfRelease, "iplHRTFRelease");
    LOAD_REQUIRED(effectCreate, "iplVirtualSurroundEffectCreate");
    LOAD_REQUIRED(effectRelease, "iplVirtualSurroundEffectRelease");
    LOAD_REQUIRED(effectReset, "iplVirtualSurroundEffectReset");
    LOAD_REQUIRED(effectApply, "iplVirtualSurroundEffectApply");
#undef LOAD_REQUIRED

    memset(&contextSettings, 0, sizeof(contextSettings));
    contextSettings.version = ASC_STEAMAUDIO_VERSION;
    contextSettings.logCallback = steamLog;
    contextSettings.simdLevel = bestSimdLevel();
    contextSettings.flags = 0;
    if (s_audio.contextCreate(&contextSettings, &s_audio.context) != ASC_IPL_STATUS_SUCCESS || !s_audio.context) {
        sysLogPrintf(LOG_ERROR, "Ascension Audio: Steam Audio context creation failed");
        releaseSteam();
        return 0;
    }

    audioSettings.samplingRate = s_audio.sampleRate;
    audioSettings.frameSize = ASC_AUDIO_FRAME;

    memset(&hrtfSettings, 0, sizeof(hrtfSettings));
    hrtfSettings.type = ASC_IPL_HRTFTYPE_DEFAULT;
    hrtfSettings.volume = 1.0f;
    hrtfSettings.normType = ASC_IPL_HRTFNORMTYPE_RMS;
    if (s_audio.hrtfCreate(s_audio.context, &audioSettings, &hrtfSettings, &s_audio.hrtf) != ASC_IPL_STATUS_SUCCESS || !s_audio.hrtf) {
        sysLogPrintf(LOG_ERROR, "Ascension Audio: Steam Audio HRTF creation failed");
        releaseSteam();
        return 0;
    }

    memset(&effectSettings, 0, sizeof(effectSettings));
    effectSettings.speakerLayout.type = ASC_IPL_SPEAKERLAYOUTTYPE_STEREO;
    effectSettings.hrtf = s_audio.hrtf;
    if (s_audio.effectCreate(s_audio.context, &audioSettings, &effectSettings, &s_audio.effect) != ASC_IPL_STATUS_SUCCESS || !s_audio.effect) {
        sysLogPrintf(LOG_ERROR, "Ascension Audio: Steam Audio virtual-surround creation failed");
        releaseSteam();
        return 0;
    }

    s_audio.inPlanes[0] = s_audio.inL;
    s_audio.inPlanes[1] = s_audio.inR;
    s_audio.outPlanes[0] = s_audio.wetL;
    s_audio.outPlanes[1] = s_audio.wetR;
    s_audio.steamActive = 1;

    /* Source HRTF is an enhancement of the already-valid Steam path. Failure
     * here is intentionally non-fatal and leaves virtual surround available. */
    initSourceHrtf();
    return 1;
}

static SourceEffectSlot *sourceSlot(uint32_t voiceKey)
{
    SourceEffectSlot *oldest = NULL;
    unsigned i;

    for (i = 0; i < ASC_SOURCE_EFFECTS; ++i) {
        SourceEffectSlot *slot = &s_audio.sourceEffects[i];
        if (slot->assigned && slot->voiceKey == voiceKey) {
            slot->lastUse = ++s_audio.sourceSerial;
            return slot;
        }
        if (!slot->assigned) {
            oldest = slot;
            break;
        }
        if (!oldest || slot->lastUse < oldest->lastUse) {
            oldest = slot;
        }
    }

    if (!oldest || !oldest->effect) {
        return NULL;
    }

    /* A pool eviction is safe: the legacy voice is still in the mix. Reset
     * convolution history before assigning the effect to a different source. */
    s_audio.binauralReset(oldest->effect);
    oldest->voiceKey = voiceKey;
    oldest->assigned = 1;
    oldest->lastUse = ++s_audio.sourceSerial;
    return oldest;
}

int ascensionAudioSourceHrtfActive(void)
{
    return s_audio.initialized && !s_audio.bypass && s_audio.steamActive && s_audio.sourceActive;
}

void ascensionAudioSourceReset(uint32_t voiceKey)
{
    unsigned i;

    if (!ascensionAudioSourceHrtfActive() || !s_audio.binauralReset) {
        return;
    }

    for (i = 0; i < ASC_SOURCE_EFFECTS; ++i) {
        SourceEffectSlot *slot = &s_audio.sourceEffects[i];
        if (slot->assigned && slot->voiceKey == voiceKey) {
            s_audio.binauralReset(slot->effect);
            slot->lastUse = ++s_audio.sourceSerial;
            return;
        }
    }
}

int ascensionAudioSourceProcess(uint32_t voiceKey,
                                const float *mono,
                                float directionX,
                                float directionY,
                                float directionZ,
                                float *outLeft,
                                float *outRight)
{
    SourceEffectSlot *slot;
    ASC_IPLBinauralEffectParams params;
    ASC_IPLAudioBuffer inBuffer;
    ASC_IPLAudioBuffer outBuffer;
    float *inPlanes[1];
    float *outPlanes[2];
    float lengthSquared;
    float invLength;
    unsigned i;

    if (!ascensionAudioSourceHrtfActive() || !mono || !outLeft || !outRight ||
        !s_audio.binauralApply || !s_audio.binauralReset) {
        return 0;
    }

    lengthSquared = directionX * directionX + directionY * directionY + directionZ * directionZ;
    if (!isfinite(lengthSquared) || lengthSquared < 1.0e-12f) {
        return 0;
    }
    invLength = 1.0f / sqrtf(lengthSquared);
    directionX *= invLength;
    directionY *= invLength;
    directionZ *= invLength;

    slot = sourceSlot(voiceKey);
    if (!slot) {
        return 0;
    }

    inPlanes[0] = (float *)mono;
    outPlanes[0] = outLeft;
    outPlanes[1] = outRight;

    inBuffer.numChannels = 1;
    inBuffer.numSamples = (ASC_IPLint32)ASCENSION_AUDIO_SOURCE_FRAME;
    inBuffer.data = inPlanes;
    outBuffer.numChannels = 2;
    outBuffer.numSamples = (ASC_IPLint32)ASCENSION_AUDIO_SOURCE_FRAME;
    outBuffer.data = outPlanes;

    memset(&params, 0, sizeof(params));
    params.direction.x = directionX;
    params.direction.y = directionY;
    params.direction.z = directionZ;
    params.interpolation = ASC_IPL_HRTFINTERPOLATION_BILINEAR;
    params.spatialBlend = 1.0f;
    params.hrtf = s_audio.sourceHrtf;
    params.peakDelays = NULL;

    s_audio.binauralApply(slot->effect, &params, &inBuffer, &outBuffer);

    /* Steam Audio's apply call has no error return. Validate the entire frame
     * before the mixer is allowed to replace even one legacy sample. */
    for (i = 0; i < ASCENSION_AUDIO_SOURCE_FRAME; ++i) {
        if (!isfinite(outLeft[i]) || !isfinite(outRight[i]) ||
            fabsf(outLeft[i]) > 8.0f || fabsf(outRight[i]) > 8.0f) {
            s_audio.binauralReset(slot->effect);
            return 0;
        }
    }

    return 1;
}

static float spectralChannel(float x, int channel)
{
    float dc = x - s_audio.dcPrevIn[channel] + 0.995f * s_audio.dcPrevOut[channel];
    s_audio.dcPrevIn[channel] = x;
    s_audio.dcPrevOut[channel] = dc;

    s_audio.lowState[channel] += s_audio.lowAlpha * (dc - s_audio.lowState[channel]);
    s_audio.highLPState[channel] += s_audio.highAlpha * (dc - s_audio.highLPState[channel]);
    return dc + 0.045f * s_audio.lowState[channel]
              + 0.050f * (dc - s_audio.highLPState[channel]);
}

static float softPeak(float x)
{
    float y = 1.07f * x;
    y = y / (1.0f + 0.085f * fabsf(y));
    if (y > 0.985f) y = 0.985f;
    if (y < -0.985f) y = -0.985f;
    return y;
}

static void masterPair(float *left, float *right)
{
    float l = spectralChannel(*left, 0);
    float r = spectralChannel(*right, 1);
    float mid = 0.5f * (l + r);
    float side = 0.5f * (l - r) * 1.035f;
    *left = softPeak(mid + side);
    *right = softPeak(mid - side);
}

static int16_t floatToS16(float x)
{
    int v;
    if (x > 1.0f) x = 1.0f;
    if (x < -1.0f) x = -1.0f;
    v = (int)(x * 32767.0f + (x >= 0.0f ? 0.5f : -0.5f));
    if (v > 32767) v = 32767;
    if (v < -32768) v = -32768;
    return (int16_t)v;
}

static void processSteamFrames(void)
{
    while (s_audio.inputFifo.count >= ASC_AUDIO_FRAME) {
        ASC_IPLAudioBuffer inBuffer;
        ASC_IPLAudioBuffer outBuffer;
        ASC_IPLVirtualSurroundEffectParams params;
        unsigned i;

        for (i = 0; i < ASC_AUDIO_FRAME; ++i) {
            float l = 0.0f, r = 0.0f;
            fifoPop(&s_audio.inputFifo, &l, &r);
            s_audio.inL[i] = l;
            s_audio.inR[i] = r;
        }

        inBuffer.numChannels = 2;
        inBuffer.numSamples = ASC_AUDIO_FRAME;
        inBuffer.data = s_audio.inPlanes;
        outBuffer.numChannels = 2;
        outBuffer.numSamples = ASC_AUDIO_FRAME;
        outBuffer.data = s_audio.outPlanes;
        params.hrtf = s_audio.hrtf;

        s_audio.effectApply(s_audio.effect, &params, &inBuffer, &outBuffer);

        for (i = 0; i < ASC_AUDIO_FRAME; ++i) {
            float l = 0.32f * s_audio.inL[i] + 0.68f * s_audio.wetL[i];
            float r = 0.32f * s_audio.inR[i] + 0.68f * s_audio.wetR[i];
            masterPair(&l, &r);
            if (!fifoPush(&s_audio.outputFifo, l, r)) {
                memset(&s_audio.outputFifo, 0, sizeof(s_audio.outputFifo));
                for (unsigned j = 0; j < ASC_AUDIO_FRAME; ++j) {
                    fifoPush(&s_audio.outputFifo, 0.0f, 0.0f);
                }
                return;
            }
        }
    }
}

int ascensionAudioRemasterInit(int sampleRate)
{
    unsigned i;
    const float pi = 3.14159265358979323846f;

    memset(&s_audio, 0, sizeof(s_audio));
    s_audio.sampleRate = sampleRate > 0 ? sampleRate : 22050;
    s_audio.bypass = getenv("GE_ASCENSION_AUDIO_BYPASS") ? 1 : 0;
    s_audio.lowAlpha = 1.0f - expf(-2.0f * pi * 180.0f / (float)s_audio.sampleRate);
    s_audio.highAlpha = 1.0f - expf(-2.0f * pi * 4200.0f / (float)s_audio.sampleRate);
    s_audio.initialized = 1;

    if (s_audio.bypass) {
        sysLogPrintf(LOG_NOTE, "Ascension Audio: developer bypass active");
        return 0;
    }

    initSteam();

    if (s_audio.steamActive && !s_audio.sourceActive) {
        /* Only the fallback post-mix HRTF needs a FIFO. The preferred source
         * path runs at the mixer's native block boundary with no added delay. */
        for (i = 0; i < ASC_AUDIO_FRAME; ++i) {
            fifoPush(&s_audio.outputFifo, 0.0f, 0.0f);
        }
        sysLogPrintf(LOG_NOTE,
            "Ascension Audio Remaster: Steam Audio 4.8.1 post-mix HRTF fallback active (%d Hz, %d-frame DSP)",
            s_audio.sampleRate, ASC_AUDIO_FRAME);
    } else if (s_audio.sourceActive) {
        sysLogPrintf(LOG_NOTE,
            "Ascension Audio Remaster: source-object HRTF + mastering active (%d Hz, zero extra post-mix FIFO latency)",
            s_audio.sampleRate);
    } else {
        sysLogPrintf(LOG_NOTE, "Ascension Audio Remaster: mastering fallback active");
    }
    return s_audio.steamActive;
}

void ascensionAudioRemasterShutdown(void)
{
    if (!s_audio.initialized) {
        return;
    }
    releaseSteam();
    memset(&s_audio, 0, sizeof(s_audio));
}

int ascensionAudioRemasterActive(void)
{
    return s_audio.initialized && !s_audio.bypass;
}

const int16_t *ascensionAudioRemasterProcess(const int16_t *stereoS16, uint32_t lenBytes)
{
    unsigned frames;
    unsigned i;

    if (!stereoS16 || !lenBytes || s_audio.bypass || !s_audio.initialized) {
        return stereoS16;
    }

    frames = lenBytes / (sizeof(int16_t) * 2u);
    if (!frames || frames > ASC_AUDIO_MAX_CALL_FRAMES) {
        return stereoS16;
    }

    /* Per-source HRTF has already happened before the final stereo sum. Never
     * run virtual surround again here: double HRTF destroys localization. */
    if (s_audio.sourceActive || !s_audio.steamActive) {
        for (i = 0; i < frames; ++i) {
            float l = (float)stereoS16[i * 2u + 0u] / 32768.0f;
            float r = (float)stereoS16[i * 2u + 1u] / 32768.0f;
            masterPair(&l, &r);
            s_audio.returnS16[i * 2u + 0u] = floatToS16(l);
            s_audio.returnS16[i * 2u + 1u] = floatToS16(r);
        }
        return s_audio.returnS16;
    }

    for (i = 0; i < frames; ++i) {
        float l = (float)stereoS16[i * 2u + 0u] / 32768.0f;
        float r = (float)stereoS16[i * 2u + 1u] / 32768.0f;
        if (!fifoPush(&s_audio.inputFifo, l, r)) {
            return stereoS16;
        }
    }

    processSteamFrames();

    for (i = 0; i < frames; ++i) {
        float l = 0.0f, r = 0.0f;
        if (!fifoPop(&s_audio.outputFifo, &l, &r)) {
            return stereoS16;
        }
        s_audio.returnS16[i * 2u + 0u] = floatToS16(l);
        s_audio.returnS16[i * 2u + 1u] = floatToS16(r);
    }

    return s_audio.returnS16;
}
