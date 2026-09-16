#include "ascension_audio_remaster.h"
#include "ascension_audio_world.h"
#include "ascension_audio_world_runtime.h"

#include <stdint.h>

/*
 * Mixer-facing adapter.
 *
 * The legacy per-source HRTF remains the final fail-safe. When real world
 * metadata exists for the exact physical voice, the mono source first passes
 * through propagation/air/barrier DSP, then Steam Audio receives the real
 * listener-space XYZ direction. Early reflections and the bounded room field
 * are added only after a complete finite HRTF frame succeeds.
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

    if (ascensionAudioWorldRuntimeEnsure() &&
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
    if (ascensionAudioWorldRuntimeActive()) {
        ascensionAudioWorldResetVoice(voiceKey);
    }
    ascensionAudioSourceReset(voiceKey);
}
