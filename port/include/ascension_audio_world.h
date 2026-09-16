#ifndef ASCENSION_AUDIO_WORLD_H
#define ASCENSION_AUDIO_WORLD_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define ASCENSION_AUDIO_WORLD_MAX_SOURCES 64

typedef struct AscensionAudioWorldSnapshot {
    uint32_t voice_key;
    int valid;
    float direction_x;
    float direction_y;
    float direction_z;
    float distance_m;
    float propagation_delay_s;
    float direct_gain;
    float lowpass_hz;
    float occlusion;
    float transmission;
    float early_reflection_gain;
    float early_reflection_delay_s;
    float reverb_send;
    float reverb_t60_s;
    float doppler_ratio;
    int room_count;
    int closed_portals;
} AscensionAudioWorldSnapshot;

int ascensionAudioWorldInit(int sample_rate);
void ascensionAudioWorldShutdown(void);
void ascensionAudioWorldReset(void);
void ascensionAudioWorldResetVoice(uint32_t voice_key);

void ascensionAudioWorldSubmit(
    uint32_t voice_key,
    float source_x, float source_y, float source_z,
    float listener_x, float listener_y, float listener_z,
    float listener_yaw_deg,
    float near_range_units, float far_range_units,
    float obstruction, float transmission,
    int room_count, int closed_portals);

int ascensionAudioWorldGet(uint32_t voice_key, AscensionAudioWorldSnapshot *out_snapshot);

void ascensionAudioWorldProcessMono(
    uint32_t voice_key,
    const float *input,
    int frame_count,
    float *output);

void ascensionAudioWorldProcessStereoField(
    uint32_t voice_key,
    const float *dry_left,
    const float *dry_right,
    int frame_count,
    float *io_left,
    float *io_right);

#ifdef __cplusplus
}
#endif

#endif
