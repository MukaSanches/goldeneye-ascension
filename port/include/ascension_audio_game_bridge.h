#ifndef ASCENSION_AUDIO_GAME_BRIDGE_H
#define ASCENSION_AUDIO_GAME_BRIDGE_H

#include <ultra64.h>
#include <snd.h>

#ifdef __cplusplus
extern "C" {
#endif

void ascensionAudioWorldSubmitFromGame(ALSoundState *state, const coord3d *source,
                                       f32 near_range, f32 far_range);

#ifdef __cplusplus
}
#endif

#endif
