#include "ascension_audio_remaster.h"
#include "ascension_audio_world.h"
#include "ascension_audio_world_runtime.h"

#include <stdint.h>

/*
 * Mixer-facing adapter.
 *
 * IMPORTANT REAL-TIME RULE:
 * The audio callback never initializes the world engine, creates threads, or
 * takes the game-side publication mutex. The game thread activates/publishes
 * world state when a positional SFX is created. The mixer only consumes an
 * already-published atomic snapshot; otherwise it falls back to the proven
 * Steam Audio pan-HRTF path.
 */
int ascensionAudioWorldSourceProcess(uint32_t voiceKey,
                                     const float *mono,
                                     float fallbackDirectionX,
                                     float fallbackDirectionY,
                                     float fallbackDirectionZ,
                                     float *outLeft,
                                     float *outRight)
{
    AscensionAudioWorldSnapshot snapshot;
    float physicalMono[ASCENSION_AUDIO_SOURCE_FRAME];

    if (!mono || !outLeft || !outRight) return 0;

    if (ascensionAudioWorldRuntimeActive() &&
        ascensionAudioWorldGet(voiceKey, &snapshot)) {
        ascensionAudioWorldProcessMono(voiceKey, mono,
                                       (int)ASCENSION_AUDIO_SOURCE_FRAME,
                                       physicalMono);

        if (ascensionAudioSourceProcess(voiceKey,
                                        physicalMono,
                                        snapshot.direction_x,
                                        snapshot.direction_y,
                                        snapshot.direction_z,
                                        outLeft,
                                        outRight)) {
            ascensionAudioWorldProcessStereoField(voiceKey,
                                                  outLeft,
                                                  outRight,
                                                  (int)ASCENSION_AUDIO_SOURCE_FRAME,
                                                  outLeft,
                                                  outRight);
            return 1;
        }
    }

    /* Never lose a voice because the acoustic-world layer is unavailable. */
    return ascensionAudioSourceProcess(voiceKey,
                                       mono,
                                       fallbackDirectionX,
                                       fallbackDirectionY,
                                       fallbackDirectionZ,
                                       outLeft,
                                       outRight);
}

void ascensionAudioWorldSourceReset(uint32_t voiceKey)
{
    /* Do not call ascensionAudioWorldResetVoice here. This function runs from
     * the mixer/audio path and ResetVoice owns game-side publication state.
     * The next game-thread publication replaces the atomic snapshot. */
    ascensionAudioSourceReset(voiceKey);
}
