/*
 * Audio mixing — software implementation of GE's RSP audio ucode opcodes.
 *
 * On PC the RSP is replaced by scalar software DSP against a small DMEM
 * scratch buffer. Ascension's source-object audio enhancement is deliberately
 * inserted here, after each physical voice has been decoded/resampled but
 * before the final stereo interleave. The original mix is always rendered
 * first and therefore remains the authoritative fail-safe path.
 */

#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <PR/abi.h>
#include <PR/os.h>
#include "system.h"

extern char *getenv(const char *);
static FILE *sMixerTraceFile = NULL;
static int sMixerTraceChecked = 0;
static int mixerTraceOn(void)
{
    if (!sMixerTraceChecked) {
        sMixerTraceChecked = 1;
        if (getenv("GE_MIXERTRACE")) {
            sMixerTraceFile = fopen("mixertrace.log", "a");
            if (sMixerTraceFile) setvbuf(sMixerTraceFile, NULL, _IONBF, 0);
        }
    }
    return sMixerTraceFile != NULL;
}
#define MTRACE(...) do { if (mixerTraceOn()) fprintf(sMixerTraceFile, __VA_ARGS__); } while (0)

#include "platform.h"
#include "system.h"
#include "mixer.h"
#include "audio.h"
#include "ascension_audio_remaster.h"

#define DMEM_SIZE 4096
#define ASC_SPATIAL_MAX_VOICES 64
#define ASC_SPATIAL_MAX_SAMPLES 160
#define ASC_PI 3.14159265358979323846f

static u8 sDmem[DMEM_SIZE];

#define DMEM_U8(a)  (sDmem + (a))
#define DMEM_S16(a) ((s16 *)(sDmem + (a)))

static inline s16 mixerClamp16(s32 v)
{
    if (v < -0x8000) return -0x8000;
    if (v > 0x7fff) return 0x7fff;
    return (s16)v;
}

/*
 * A tap contains only information that already exists in the original
 * envelope mixer. stateAddr is a stable physical-voice identity for the
 * lifetime of that voice. input is the post-resample mono PCM. gainL/R are
 * the exact Q15 dry gains which the original mixer applies.
 *
 * We intentionally do not invent distance, height, walls or room geometry.
 * At this layer GoldenEye provides a horizontal equal-power pan. That pan is
 * inverted mathematically into an azimuth, then Steam Audio renders the
 * point source with an HRTF. Full XYZ propagation can be added only when real
 * world-space source/listener metadata is exposed to port/.
 */
typedef struct {
    u32 stateAddr;
    int used;
    s16 input[ASC_SPATIAL_MAX_SAMPLES];
    s16 gainL[ASC_SPATIAL_MAX_SAMPLES];
    s16 gainR[ASC_SPATIAL_MAX_SAMPLES];
} AscSpatialTap;

static AscSpatialTap sSpatialTaps[ASC_SPATIAL_MAX_VOICES];
static u32 sSpatialSamples;

static void ascSpatialBegin(u32 sampleCount)
{
    memset(sSpatialTaps, 0, sizeof(sSpatialTaps));
    sSpatialSamples = sampleCount <= ASC_SPATIAL_MAX_SAMPLES ? sampleCount : 0;
}

static AscSpatialTap *ascSpatialTapFor(u32 stateAddr)
{
    AscSpatialTap *freeTap = NULL;
    unsigned i;

    if (!sSpatialSamples) {
        return NULL;
    }

    for (i = 0; i < ASC_SPATIAL_MAX_VOICES; ++i) {
        if (sSpatialTaps[i].used && sSpatialTaps[i].stateAddr == stateAddr) {
            return &sSpatialTaps[i];
        }
        if (!sSpatialTaps[i].used && !freeTap) {
            freeTap = &sSpatialTaps[i];
        }
    }

    if (freeTap) {
        freeTap->used = 1;
        freeTap->stateAddr = stateAddr;
    }
    return freeTap;
}

static s32 ascFloatContribution(float x)
{
    float scaled;
    if (!isfinite(x)) return 0;
    if (x > 2.0f) x = 2.0f;
    if (x < -2.0f) x = -2.0f;
    scaled = x * 32768.0f;
    return (s32)(scaled + (scaled >= 0.0f ? 0.5f : -0.5f));
}

static void ascSpatialApply(s16 *left, s16 *right, u32 n)
{
    s32 mixL[ASC_SPATIAL_MAX_SAMPLES];
    s32 mixR[ASC_SPATIAL_MAX_SAMPLES];
    unsigned voice;
    u32 i;

    if (!ascensionAudioSourceHrtfActive() || !left || !right ||
        !sSpatialSamples || n != sSpatialSamples ||
        n > ASC_SPATIAL_MAX_SAMPLES ||
        (n % ASCENSION_AUDIO_SOURCE_FRAME) != 0) {
        return;
    }

    for (i = 0; i < n; ++i) {
        mixL[i] = left[i];
        mixR[i] = right[i];
    }

    for (voice = 0; voice < ASC_SPATIAL_MAX_VOICES; ++voice) {
        AscSpatialTap *tap = &sSpatialTaps[voice];
        u32 base;

        if (!tap->used) continue;

        for (base = 0; base < n; base += ASCENSION_AUDIO_SOURCE_FRAME) {
            float mono[ASCENSION_AUDIO_SOURCE_FRAME];
            float hrtfL[ASCENSION_AUDIO_SOURCE_FRAME];
            float hrtfR[ASCENSION_AUDIO_SOURCE_FRAME];
            s32 legacyL[ASCENSION_AUDIO_SOURCE_FRAME];
            s32 legacyR[ASCENSION_AUDIO_SOURCE_FRAME];
            float sumL = 0.0f;
            float sumR = 0.0f;
            float azimuth;
            float alpha;
            float dirX;
            float dirZ;
            unsigned k;

            for (k = 0; k < ASCENSION_AUDIO_SOURCE_FRAME; ++k) {
                u32 idx = base + k;
                float gl = (float)tap->gainL[idx] / 32768.0f;
                float gr = (float)tap->gainR[idx] / 32768.0f;
                float prePanGain = sqrtf(gl * gl + gr * gr);
                float sample = (float)tap->input[idx] / 32768.0f;
                float weight = fabsf(sample) + 0.000001f;

                mono[k] = sample * prePanGain;
                legacyL[k] = ((s32)tap->input[idx] * (s32)tap->gainL[idx]) >> 15;
                legacyR[k] = ((s32)tap->input[idx] * (s32)tap->gainR[idx]) >> 15;
                sumL += fabsf(gl) * weight;
                sumR += fabsf(gr) * weight;
            }

            if (sumL + sumR < 0.000001f) {
                continue;
            }

            /* GE's env mixer uses an equal-power pair. For gains L/R:
             *   alpha = atan2(R,L) in [0,pi/2]
             *   azimuth = 2*alpha - pi/2 in [-pi/2,+pi/2]
             * Steam Audio uses +X right and -Z forward. */
            alpha = atan2f(sumR, sumL);
            azimuth = 2.0f * alpha - 0.5f * ASC_PI;

            /* A perfectly centered source carries no horizontal location
             * information. Preserve it exactly instead of pretending that
             * "center" proves a front/back position. This also protects the
             * largely centered soundtrack and UI from unnecessary HRTF tone. */
            if (fabsf(azimuth) < 0.035f) {
                continue;
            }

            dirX = sinf(azimuth);
            dirZ = -cosf(azimuth);

            if (!ascensionAudioSourceProcess(tap->stateAddr, mono,
                                             dirX, 0.0f, dirZ,
                                             hrtfL, hrtfR)) {
                continue;
            }

            /* Critical safety invariant: the legacy signal already exists in
             * mixL/R. Only after the whole 16-sample HRTF frame succeeds do
             * we subtract that source's old direct contribution and add its
             * binaural replacement. Failure means a zero delta, never silence. */
            for (k = 0; k < ASCENSION_AUDIO_SOURCE_FRAME; ++k) {
                u32 idx = base + k;
                mixL[idx] += ascFloatContribution(hrtfL[k]) - legacyL[k];
                mixR[idx] += ascFloatContribution(hrtfR[k]) - legacyR[k];
            }
        }
    }

    for (i = 0; i < n; ++i) {
        left[i] = mixerClamp16(mixL[i]);
        right[i] = mixerClamp16(mixR[i]);
    }
}

static struct {
    u16 in;
    u16 out;
    u32 count;
    u16 dryR;
    u16 wetL;
    u16 wetR;
} sCtx;

void aSetBufferImpl(u32 flags, u16 i, u16 o, u16 c)
{
    if (flags & A_AUX) {
        sCtx.dryR = i;
        sCtx.wetL = o;
        sCtx.wetR = c;
    } else {
        sCtx.in = i;
        sCtx.out = o;
        sCtx.count = c;
    }
    MTRACE("[SETBUF] flags=%u i=%u o=%u c=%u\n", flags, i, o, c);
}

void aClearBufferImpl(u16 addr, u32 count)
{
    if (addr == 1088 /* AL_MAIN_L_OUT */) {
        if (ascensionAudioSourceHrtfActive()) {
            ascSpatialBegin(count >> 1);
        } else {
            sSpatialSamples = 0;
        }
        if (getenv("GE_DMEMWIPE")) {
            memset(sDmem, 0, sizeof(sDmem));
        }
    }
    memset(DMEM_U8(addr), 0, count);
}

void aLoadBufferImpl(u32 dramAddr)
{
    if (mixerTraceOn()) {
        const u8 *src = (const u8 *)osPhysicalToVirtual(dramAddr);
        u32 n = (sCtx.count > 72 ? 72 : sCtx.count);
        u32 k;
        fprintf(sMixerTraceFile, "[LOADBUF] dram=0x%08x -> in=%u count=%u bytes=", dramAddr, sCtx.in, sCtx.count);
        for (k = 0; k < n; k++) fprintf(sMixerTraceFile, "%02x", src[k]);
        fprintf(sMixerTraceFile, "\n");
    }
    memcpy(DMEM_U8(sCtx.in), osPhysicalToVirtual(dramAddr), sCtx.count);
}

void aSaveBufferImpl(u32 dramAddr)
{
    memcpy(osPhysicalToVirtual(dramAddr), DMEM_U8(sCtx.out), sCtx.count);
    (void)0;
}

void aDMEMMoveImpl(u16 in, u16 out, u32 count)
{
    memmove(DMEM_U8(out), DMEM_U8(in), count);
}

void aSegmentImpl(u32 seg, u32 base)
{
    (void)seg;
    (void)base;
}

static s16 sAdpcmTable[8][2][8];
static ADPCM_STATE *sAdpcmLoopState;

void aLoadADPCMImpl(u32 count, u32 dramAddr)
{
    u32 n = count;
    void *src = osPhysicalToVirtual(dramAddr);
    if (n > sizeof(sAdpcmTable)) n = sizeof(sAdpcmTable);
    memcpy(sAdpcmTable, src, n);
    if (mixerTraceOn()) {
        int p, q, r;
        fprintf(sMixerTraceFile, "[LOADADPCM] count=%u dram=%p book=", count, src);
        for (p = 0; p < 8; p++) for (q = 0; q < 2; q++) for (r = 0; r < 8; r++)
            fprintf(sMixerTraceFile, "%d,", sAdpcmTable[p][q][r]);
        fprintf(sMixerTraceFile, "\n");
    }
}

void aSetLoopImpl(u32 stateAddr)
{
    sAdpcmLoopState = (ADPCM_STATE *)osPhysicalToVirtual(stateAddr);
}

void aADPCMdecImpl(u32 flags, u32 stateAddr)
{
    ADPCM_STATE *state = (ADPCM_STATE *)osPhysicalToVirtual(stateAddr);
    u8 *in = DMEM_U8(sCtx.in);
    s16 *out = DMEM_S16(sCtx.out);
    s32 nbytes = (s32)((sCtx.count + 31) & ~31u);

    MTRACE("[ADPCMDEC] flags=%u state=%p in=%u out=%u count=%u book0=%d\n",
           flags, (void *)state, sCtx.in, sCtx.out, sCtx.count, sAdpcmTable[0][0][0]);

    if (flags & A_INIT) {
        memset(out, 0, 16 * sizeof(s16));
    } else if (flags & A_LOOP) {
        memcpy(out, sAdpcmLoopState, 16 * sizeof(s16));
    } else {
        memcpy(out, state, 16 * sizeof(s16));
    }
    out += 16;

    while (nbytes > 0) {
        int shift = *in >> 4;
        int tableIndex = *in++ & 0xf;
        s16 (*tbl)[8] = sAdpcmTable[tableIndex];
        int i, j, k;

        for (i = 0; i < 2; i++) {
            s16 ins[8];
            s16 prev1 = out[-1];
            s16 prev2 = out[-2];

            for (j = 0; j < 4; j++) {
                ins[j * 2]     = (s16)((((*in >> 4) << 28) >> 28) << shift);
                ins[j * 2 + 1] = (s16)((((*in++ & 0xf) << 28) >> 28) << shift);
            }
            for (j = 0; j < 8; j++) {
                s32 acc = tbl[0][j] * prev2 + tbl[1][j] * prev1 + ((s32)ins[j] << 11);
                for (k = 0; k < j; k++) {
                    acc += tbl[1][(j - k) - 1] * ins[k];
                }
                acc >>= 11;
                *out++ = mixerClamp16(acc);
            }
        }
        nbytes -= 16 * (s32)sizeof(s16);
    }

    memcpy(state, out - 16, 16 * sizeof(s16));

    if (mixerTraceOn()) {
        s16 *dumpOut = DMEM_S16(sCtx.out) + 16;
        u32 n = (sCtx.count > 64 ? 64 : sCtx.count);
        u32 k;
        fprintf(sMixerTraceFile, "[PCMOUT] book0=%d first-decoded-frame[0..%u]=", sAdpcmTable[0][0][0], n / 2 - 1);
        for (k = 0; k < n / 2; k++) fprintf(sMixerTraceFile, "%d,", dumpOut[k]);
        fprintf(sMixerTraceFile, "\n");
    }
}

static const s16 sResampleTable[64][4] = {
    {0x0c39, 0x66ad, 0x0d46, 0xffdf}, {0x0b39, 0x6696, 0x0e5f, 0xffd8},
    {0x0a44, 0x6669, 0x0f83, 0xffd0}, {0x095a, 0x6626, 0x10b4, 0xffc8},
    {0x087d, 0x65cd, 0x11f0, 0xffbf}, {0x07ab, 0x655e, 0x1338, 0xffb6},
    {0x06e4, 0x64d9, 0x148c, 0xffac}, {0x0628, 0x643f, 0x15eb, 0xffa1},
    {0x0577, 0x638f, 0x1756, 0xff96}, {0x04d1, 0x62cb, 0x18cb, 0xff8a},
    {0x0435, 0x61f3, 0x1a4c, 0xff7e}, {0x03a4, 0x6106, 0x1bd7, 0xff71},
    {0x031c, 0x6007, 0x1d6c, 0xff64}, {0x029f, 0x5ef5, 0x1f0b, 0xff56},
    {0x022a, 0x5dd0, 0x20b3, 0xff48}, {0x01be, 0x5c9a, 0x2264, 0xff3a},
    {0x015b, 0x5b53, 0x241e, 0xff2c}, {0x0101, 0x59fc, 0x25e0, 0xff1e},
    {0x00ae, 0x5896, 0x27a9, 0xff10}, {0x0063, 0x5720, 0x297a, 0xff02},
    {0x001f, 0x559d, 0x2b50, 0xfef4}, {0xffe2, 0x540d, 0x2d2c, 0xfee8},
    {0xffac, 0x5270, 0x2f0d, 0xfedb}, {0xff7c, 0x50c7, 0x30f3, 0xfed0},
    {0xff53, 0x4f14, 0x32dc, 0xfec6}, {0xff2e, 0x4d57, 0x34c8, 0xfebd},
    {0xff0f, 0x4b91, 0x36b6, 0xfeb6}, {0xfef5, 0x49c2, 0x38a5, 0xfeb0},
    {0xfedf, 0x47ed, 0x3a95, 0xfeac}, {0xfece, 0x4611, 0x3c85, 0xfeab},
    {0xfec0, 0x4430, 0x3e74, 0xfeac}, {0xfeb6, 0x424a, 0x4060, 0xfeaf},
    {0xfeaf, 0x4060, 0x424a, 0xfeb6}, {0xfeac, 0x3e74, 0x4430, 0xfec0},
    {0xfeab, 0x3c85, 0x4611, 0xfece}, {0xfeac, 0x3a95, 0x47ed, 0xfedf},
    {0xfeb0, 0x38a5, 0x49c2, 0xfef5}, {0xfeb6, 0x36b6, 0x4b91, 0xff0f},
    {0xfebd, 0x34c8, 0x4d57, 0xff2e}, {0xfec6, 0x32dc, 0x4f14, 0xff53},
    {0xfed0, 0x30f3, 0x50c7, 0xff7c}, {0xfedb, 0x2f0d, 0x5270, 0xffac},
    {0xfee8, 0x2d2c, 0x540d, 0xffe2}, {0xfef4, 0x2b50, 0x559d, 0x001f},
    {0xff02, 0x297a, 0x5720, 0x0063}, {0xff10, 0x27a9, 0x5896, 0x00ae},
    {0xff1e, 0x25e0, 0x59fc, 0x0101}, {0xff2c, 0x241e, 0x5b53, 0x015b},
    {0xff3a, 0x2264, 0x5c9a, 0x01be}, {0xff48, 0x20b3, 0x5dd0, 0x022a},
    {0xff56, 0x1f0b, 0x5ef5, 0x029f}, {0xff64, 0x1d6c, 0x6007, 0x031c},
    {0xff71, 0x1bd7, 0x6106, 0x03a4}, {0xff7e, 0x1a4c, 0x61f3, 0x0435},
    {0xff8a, 0x18cb, 0x62cb, 0x04d1}, {0xff96, 0x1756, 0x638f, 0x0577},
    {0xffa1, 0x15eb, 0x643f, 0x0628}, {0xffac, 0x148c, 0x64d9, 0x06e4},
    {0xffb6, 0x1338, 0x655e, 0x07ab}, {0xffbf, 0x11f0, 0x65cd, 0x087d},
    {0xffc8, 0x10b4, 0x6626, 0x095a}, {0xffd0, 0x0f83, 0x6669, 0x0a44},
    {0xffd8, 0x0e5f, 0x6696, 0x0b39}, {0xffdf, 0x0d46, 0x66ad, 0x0c39}
};

void aResampleImpl(u32 flags, u16 pitch, u32 stateAddr)
{
    RESAMPLE_STATE *stateBuf = (RESAMPLE_STATE *)osPhysicalToVirtual(stateAddr);
    s16 *state = (s16 *)stateBuf;
    s16 tmp[16];
    s16 *inInitial = DMEM_S16(sCtx.in);
    s16 *in = inInitial;
    s16 *out = DMEM_S16(sCtx.out);
    s32 nbytes = (s32)((sCtx.count + 15) & ~15u);
    u32 pitchAccumulator;
    s32 i;

    MTRACE("[RESAMPLE] flags=%u pitch=%u state=%p in=%u out=%u count=%u\n",
           flags, pitch, (void *)stateBuf, sCtx.in, sCtx.out, sCtx.count);

    if (flags & A_INIT) {
        memset(tmp, 0, 5 * sizeof(s16));
    } else {
        memcpy(tmp, state, 16 * sizeof(s16));
    }
    in -= 4;
    pitchAccumulator = (u16)tmp[4];
    memcpy(in, tmp, 4 * sizeof(s16));

    do {
        for (i = 0; i < 8; i++) {
            const s16 *tbl = sResampleTable[(pitchAccumulator * 64) >> 16];
            s32 sample = ((in[0] * tbl[0] + 0x4000) >> 15) +
                         ((in[1] * tbl[1] + 0x4000) >> 15) +
                         ((in[2] * tbl[2] + 0x4000) >> 15) +
                         ((in[3] * tbl[3] + 0x4000) >> 15);
            *out++ = mixerClamp16(sample);
            pitchAccumulator += (u32)pitch << 1;
            in += pitchAccumulator >> 16;
            pitchAccumulator %= 0x10000;
        }
        nbytes -= 8 * (s32)sizeof(s16);
    } while (nbytes > 0);

    state[4] = (s16)pitchAccumulator;
    memcpy(state, in, 4 * sizeof(s16));
    i = (s32)((in - inInitial + 4) & 7);
    in -= i;
    if (i != 0) i = -8 - i;
    state[5] = (s16)i;
    memcpy(state + 8, in, 8 * sizeof(s16));
}

void aInterleaveImpl(u16 l, u16 r)
{
    s16 *lp = DMEM_S16(l);
    s16 *rp = DMEM_S16(r);
    s16 *d = DMEM_S16(sCtx.out);
    u32 n = sCtx.count >> 1;
    u32 i;

    ascSpatialApply(lp, rp, n);

    for (i = 0; i < n; i++) {
        *d++ = *lp++;
        *d++ = *rp++;
    }
}

void aMixImpl(u32 flags, u16 gain, u16 in, u16 out)
{
    const s16 *inp = DMEM_S16(in);
    s16 *outp = DMEM_S16(out);
    u32 n = sCtx.count >> 1;
    u32 i;
    (void)flags;

    for (i = 0; i < n; i++) {
        s32 sample = ((s32)*outp * 0x7fff + (s32)*inp++ * (s16)gain + 0x4000) >> 15;
        *outp++ = mixerClamp16(sample);
    }
}

static struct {
    s16 volCur[2];
    s16 volTgt[2];
    s32 volRate[2];
    s16 dryamt, wetamt;
} sVol;

void aSetVolumeImpl(u32 flags, u16 v, u16 t, u16 r)
{
    if (flags & A_AUX) {
        sVol.dryamt = (s16)v;
        sVol.wetamt = (s16)r;
        if (getenv("GE_NOWET")) {
            sVol.wetamt = 0;
        }
    } else if (flags & A_VOL) {
        int ch = (flags & A_LEFT) ? 0 : 1;
        sVol.volCur[ch] = (s16)v;
    } else {
        int ch = (flags & A_LEFT) ? 0 : 1;
        sVol.volTgt[ch] = (s16)v;
        sVol.volRate[ch] = ((u32)t << 16) | (u16)r;
    }
}

static FILE *s_voiceDumpFile = NULL;

void aEnvMixerImpl(u32 flags, u32 stateAddr)
{
    struct {
        s32 t[2];
        s32 rate[2];
        s16 tgt[2];
        s16 voldry;
        s16 volwet;
    } *saved = (void *)osPhysicalToVirtual(stateAddr);

    const s16 *in = DMEM_S16(sCtx.in);
    s16 *dry[2] = { DMEM_S16(sCtx.out), DMEM_S16(sCtx.dryR) };
    s16 *wet[2] = { DMEM_S16(sCtx.wetL), DMEM_S16(sCtx.wetR) };
    u32 nsamples = sCtx.count >> 1;
    AscSpatialTap *spatialTap = NULL;
    u32 spatialOffset = 0;
    s32 t[2], tgt[2], rate[2];
    s16 voldry, volwet;
    u32 i;
    int j;

    MTRACE("[ENVMIX] flags=%u state=%p in=%u out=%u dryR=%u wetL=%u wetR=%u count=%u\n",
           flags, (void *)saved, sCtx.in, sCtx.out, sCtx.dryR, sCtx.wetL, sCtx.wetR, sCtx.count);

    if (getenv("GE_VOICEDUMP")) {
        if (!s_voiceDumpFile) s_voiceDumpFile = fopen("voicedump.raw", "wb");
        if (s_voiceDumpFile) {
            u32 hdr[2] = { stateAddr, (u32)(sCtx.count >> 1) };
            u64 us = sysGetMicroseconds();
            fwrite(hdr, 4, 2, s_voiceDumpFile);
            fwrite(&us, 8, 1, s_voiceDumpFile);
            fwrite(in, sizeof(s16), sCtx.count >> 1, s_voiceDumpFile);
        }
    }

    if (ascensionAudioSourceHrtfActive() && sSpatialSamples &&
        sCtx.out >= AL_MAIN_L_OUT) {
        spatialOffset = ((u32)sCtx.out - (u32)AL_MAIN_L_OUT) >> 1;
        if (spatialOffset + nsamples <= sSpatialSamples) {
            spatialTap = ascSpatialTapFor(stateAddr);
            if ((flags & A_INIT) && spatialTap) {
                ascensionAudioSourceReset(stateAddr);
            }
        }
    }

    if (flags & A_INIT) {
        for (j = 0; j < 2; j++) {
            t[j] = sVol.volCur[j] << 16;
            rate[j] = sVol.volRate[j] >> 3;
            tgt[j] = sVol.volTgt[j] << 16;
        }
        voldry = sVol.dryamt;
        volwet = sVol.wetamt;
    } else {
        for (j = 0; j < 2; j++) {
            t[j] = saved->t[j];
            rate[j] = saved->rate[j];
            tgt[j] = saved->tgt[j] << 16;
        }
        voldry = saved->voldry;
        volwet = saved->volwet;
    }

    for (i = 0; i < nsamples; i++) {
        s16 gain[4];
        s16 vol[2];
        s16 insamp = in[i];

        for (j = 0; j < 2; j++) {
            t[j] += rate[j];
            if ((rate[j] <= 0 && t[j] <= tgt[j]) || (rate[j] > 0 && t[j] >= tgt[j])) {
                t[j] = tgt[j];
                rate[j] = 0;
            }
            vol[j] = (s16)(t[j] >> 16);
        }

        gain[0] = mixerClamp16(((s32)vol[0] * voldry + 0x4000) >> 15);
        gain[1] = mixerClamp16(((s32)vol[1] * voldry + 0x4000) >> 15);
        gain[2] = mixerClamp16(((s32)vol[0] * volwet + 0x4000) >> 15);
        gain[3] = mixerClamp16(((s32)vol[1] * volwet + 0x4000) >> 15);

        if (spatialTap) {
            u32 idx = spatialOffset + i;
            spatialTap->input[idx] = insamp;
            spatialTap->gainL[idx] = gain[0];
            spatialTap->gainR[idx] = gain[1];
        }

        dry[0][i] = mixerClamp16(dry[0][i] + (((s32)insamp * gain[0]) >> 15));
        dry[1][i] = mixerClamp16(dry[1][i] + (((s32)insamp * gain[1]) >> 15));
        wet[0][i] = mixerClamp16(wet[0][i] + (((s32)insamp * gain[2]) >> 15));
        wet[1][i] = mixerClamp16(wet[1][i] + (((s32)insamp * gain[3]) >> 15));
    }

    for (j = 0; j < 2; j++) {
        saved->t[j] = t[j];
        saved->rate[j] = rate[j];
        saved->tgt[j] = (s16)(tgt[j] >> 16);
    }
    saved->voldry = voldry;
    saved->volwet = volwet;
}

void aPoleFilterImpl(u32 flags, u16 gain, u32 stateAddr)
{
    (void)flags;
    (void)gain;
    (void)stateAddr;
}

void mixerInit(void)
{
    memset(sDmem, 0, sizeof(sDmem));
    memset(sAdpcmTable, 0, sizeof(sAdpcmTable));
    memset(&sCtx, 0, sizeof(sCtx));
    memset(&sVol, 0, sizeof(sVol));
    memset(sSpatialTaps, 0, sizeof(sSpatialTaps));
    sSpatialSamples = 0;
    sAdpcmLoopState = NULL;
}

void mixerDestroy(void)
{
}
