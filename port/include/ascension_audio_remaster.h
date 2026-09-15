#ifndef ASCENSION_AUDIO_REMASTER_H
#define ASCENSION_AUDIO_REMASTER_H

#include <stdint.h>

/* Transparent post-mix remaster for the PC port. No game/audio asset changes. */
int ascensionAudioRemasterInit(int sampleRate);
void ascensionAudioRemasterShutdown(void);
const int16_t *ascensionAudioRemasterProcess(const int16_t *stereoS16, uint32_t lenBytes);
int ascensionAudioRemasterActive(void);

/*
 * Per-source Steam Audio path used by the software RSP mixer.
 *
 * The mixer always renders GoldenEye's original stereo contribution first.
 * These functions are an optional replacement layer: a source is replaced by
 * binaural HRTF output only when Steam Audio successfully produces a complete
 * frame. Returning 0 means "keep the original mix" and is therefore always
 * audible-safe.
 */
#define ASCENSION_AUDIO_SOURCE_FRAME 16u

int ascensionAudioSourceHrtfActive(void);
void ascensionAudioSourceReset(uint32_t voiceKey);
int ascensionAudioSourceProcess(uint32_t voiceKey,
                                const float *mono,
                                float directionX,
                                float directionY,
                                float directionZ,
                                float *outLeft,
                                float *outRight);

#endif
