#ifndef ASCENSION_STEAM_AUDIO_H
#define ASCENSION_STEAM_AUDIO_H

#include <stddef.h>

#if defined(_WIN32)
#define ASC_IPLCALL __stdcall
#else
#define ASC_IPLCALL
#endif

typedef unsigned int ASC_IPLuint32;
typedef int ASC_IPLint32;
typedef unsigned char ASC_IPLuint8;
typedef float ASC_IPLfloat32;
typedef size_t ASC_IPLsize;

typedef enum {
    ASC_IPL_FALSE,
    ASC_IPL_TRUE
} ASC_IPLbool;

typedef enum {
    ASC_IPL_STATUS_SUCCESS,
    ASC_IPL_STATUS_FAILURE,
    ASC_IPL_STATUS_OUTOFMEMORY,
    ASC_IPL_STATUS_INITIALIZATION
} ASC_IPLerror;

typedef enum {
    ASC_IPL_LOGLEVEL_INFO,
    ASC_IPL_LOGLEVEL_WARNING,
    ASC_IPL_LOGLEVEL_ERROR,
    ASC_IPL_LOGLEVEL_DEBUG
} ASC_IPLLogLevel;

typedef enum {
    ASC_IPL_SIMDLEVEL_SSE2,
    ASC_IPL_SIMDLEVEL_SSE4,
    ASC_IPL_SIMDLEVEL_AVX,
    ASC_IPL_SIMDLEVEL_AVX2,
    ASC_IPL_SIMDLEVEL_AVX512
} ASC_IPLSIMDLevel;

typedef enum {
    ASC_IPL_CONTEXTFLAGS_VALIDATION = 1 << 0,
    ASC_IPL_CONTEXTFLAGS_FORCE_32BIT = 0x7fffffff
} ASC_IPLContextFlags;

typedef void (ASC_IPLCALL *ASC_IPLLogFunction)(ASC_IPLLogLevel level, const char *message);
typedef void *(ASC_IPLCALL *ASC_IPLAllocateFunction)(ASC_IPLsize size, ASC_IPLsize alignment);
typedef void (ASC_IPLCALL *ASC_IPLFreeFunction)(void *memoryBlock);

typedef struct _IPLContext_t *ASC_IPLContext;
typedef struct _IPLHRTF_t *ASC_IPLHRTF;
typedef struct _IPLVirtualSurroundEffect_t *ASC_IPLVirtualSurroundEffect;
typedef struct _IPLBinauralEffect_t *ASC_IPLBinauralEffect;

typedef struct {
    ASC_IPLuint32 version;
    ASC_IPLLogFunction logCallback;
    ASC_IPLAllocateFunction allocateCallback;
    ASC_IPLFreeFunction freeCallback;
    ASC_IPLSIMDLevel simdLevel;
    ASC_IPLContextFlags flags;
} ASC_IPLContextSettings;

typedef struct {
    ASC_IPLfloat32 x;
    ASC_IPLfloat32 y;
    ASC_IPLfloat32 z;
} ASC_IPLVector3;

typedef enum {
    ASC_IPL_SPEAKERLAYOUTTYPE_MONO,
    ASC_IPL_SPEAKERLAYOUTTYPE_STEREO,
    ASC_IPL_SPEAKERLAYOUTTYPE_QUADRAPHONIC,
    ASC_IPL_SPEAKERLAYOUTTYPE_SURROUND_5_1,
    ASC_IPL_SPEAKERLAYOUTTYPE_SURROUND_7_1,
    ASC_IPL_SPEAKERLAYOUTTYPE_CUSTOM
} ASC_IPLSpeakerLayoutType;

typedef enum {
    ASC_IPL_AUDIOEFFECTSTATE_TAILREMAINING,
    ASC_IPL_AUDIOEFFECTSTATE_TAILCOMPLETE
} ASC_IPLAudioEffectState;

typedef struct {
    ASC_IPLSpeakerLayoutType type;
    ASC_IPLint32 numSpeakers;
    ASC_IPLVector3 *speakers;
} ASC_IPLSpeakerLayout;

typedef struct {
    ASC_IPLint32 samplingRate;
    ASC_IPLint32 frameSize;
} ASC_IPLAudioSettings;

typedef struct {
    ASC_IPLint32 numChannels;
    ASC_IPLint32 numSamples;
    ASC_IPLfloat32 **data;
} ASC_IPLAudioBuffer;

typedef enum {
    ASC_IPL_HRTFTYPE_DEFAULT,
    ASC_IPL_HRTFTYPE_SOFA
} ASC_IPLHRTFType;

typedef enum {
    ASC_IPL_HRTFNORMTYPE_NONE,
    ASC_IPL_HRTFNORMTYPE_RMS
} ASC_IPLHRTFNormType;

typedef enum {
    ASC_IPL_HRTFINTERPOLATION_NEAREST,
    ASC_IPL_HRTFINTERPOLATION_BILINEAR
} ASC_IPLHRTFInterpolation;

typedef struct {
    ASC_IPLHRTFType type;
    const char *sofaFileName;
    const ASC_IPLuint8 *sofaData;
    int sofaDataSize;
    float volume;
    ASC_IPLHRTFNormType normType;
} ASC_IPLHRTFSettings;

typedef struct {
    ASC_IPLSpeakerLayout speakerLayout;
    ASC_IPLHRTF hrtf;
} ASC_IPLVirtualSurroundEffectSettings;

typedef struct {
    ASC_IPLHRTF hrtf;
} ASC_IPLVirtualSurroundEffectParams;

typedef struct {
    ASC_IPLHRTF hrtf;
} ASC_IPLBinauralEffectSettings;

typedef struct {
    ASC_IPLVector3 direction;
    ASC_IPLHRTFInterpolation interpolation;
    ASC_IPLfloat32 spatialBlend;
    ASC_IPLHRTF hrtf;
    ASC_IPLfloat32 *peakDelays;
} ASC_IPLBinauralEffectParams;

#define ASC_STEAMAUDIO_VERSION_MAJOR 4u
#define ASC_STEAMAUDIO_VERSION_MINOR 8u
#define ASC_STEAMAUDIO_VERSION_PATCH 1u
#define ASC_STEAMAUDIO_VERSION \
    ((ASC_IPLuint32)((ASC_STEAMAUDIO_VERSION_MAJOR << 16) | \
                     (ASC_STEAMAUDIO_VERSION_MINOR << 8) | \
                     ASC_STEAMAUDIO_VERSION_PATCH))

typedef ASC_IPLerror (ASC_IPLCALL *ASC_iplContextCreateFn)(ASC_IPLContextSettings *, ASC_IPLContext *);
typedef void (ASC_IPLCALL *ASC_iplContextReleaseFn)(ASC_IPLContext *);
typedef ASC_IPLerror (ASC_IPLCALL *ASC_iplHRTFCreateFn)(ASC_IPLContext, ASC_IPLAudioSettings *, ASC_IPLHRTFSettings *, ASC_IPLHRTF *);
typedef void (ASC_IPLCALL *ASC_iplHRTFReleaseFn)(ASC_IPLHRTF *);
typedef ASC_IPLerror (ASC_IPLCALL *ASC_iplVirtualSurroundEffectCreateFn)(ASC_IPLContext, ASC_IPLAudioSettings *, ASC_IPLVirtualSurroundEffectSettings *, ASC_IPLVirtualSurroundEffect *);
typedef void (ASC_IPLCALL *ASC_iplVirtualSurroundEffectReleaseFn)(ASC_IPLVirtualSurroundEffect *);
typedef void (ASC_IPLCALL *ASC_iplVirtualSurroundEffectResetFn)(ASC_IPLVirtualSurroundEffect);
typedef ASC_IPLAudioEffectState (ASC_IPLCALL *ASC_iplVirtualSurroundEffectApplyFn)(ASC_IPLVirtualSurroundEffect, ASC_IPLVirtualSurroundEffectParams *, ASC_IPLAudioBuffer *, ASC_IPLAudioBuffer *);
typedef ASC_IPLerror (ASC_IPLCALL *ASC_iplBinauralEffectCreateFn)(ASC_IPLContext, ASC_IPLAudioSettings *, ASC_IPLBinauralEffectSettings *, ASC_IPLBinauralEffect *);
typedef void (ASC_IPLCALL *ASC_iplBinauralEffectReleaseFn)(ASC_IPLBinauralEffect *);
typedef void (ASC_IPLCALL *ASC_iplBinauralEffectResetFn)(ASC_IPLBinauralEffect);
typedef ASC_IPLAudioEffectState (ASC_IPLCALL *ASC_iplBinauralEffectApplyFn)(ASC_IPLBinauralEffect, ASC_IPLBinauralEffectParams *, ASC_IPLAudioBuffer *, ASC_IPLAudioBuffer *);
typedef ASC_IPLAudioEffectState (ASC_IPLCALL *ASC_iplBinauralEffectGetTailFn)(ASC_IPLBinauralEffect, ASC_IPLAudioBuffer *);
typedef ASC_IPLint32 (ASC_IPLCALL *ASC_iplBinauralEffectGetTailSizeFn)(ASC_IPLBinauralEffect);

#endif
