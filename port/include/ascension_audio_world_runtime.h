#ifndef ASCENSION_AUDIO_WORLD_RUNTIME_H
#define ASCENSION_AUDIO_WORLD_RUNTIME_H

#ifdef __cplusplus
extern "C" {
#endif

/* Initializes the acoustic-world worker exactly once for the PC audio rate.
 * Safe to call from either the game thread or the mixer path. */
int ascensionAudioWorldRuntimeEnsure(void);
int ascensionAudioWorldRuntimeActive(void);

#ifdef __cplusplus
}
#endif

#endif
