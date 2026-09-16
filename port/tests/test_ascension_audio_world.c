#include "ascension_audio_world.h"
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <string.h>

static int finite_snapshot(const AscensionAudioWorldSnapshot *s)
{
    return isfinite(s->direction_x) && isfinite(s->direction_y) && isfinite(s->direction_z) &&
           isfinite(s->distance_m) && isfinite(s->direct_gain) && isfinite(s->lowpass_hz) &&
           isfinite(s->reverb_t60_s) && isfinite(s->doppler_ratio);
}

int main(void)
{
    AscensionAudioWorldSnapshot near_s, far_s, occ_s, above_s;
    float impulse[256] = {0}, mono[256], l[256] = {0}, r[256] = {0};
    int i;
    assert(ascensionAudioWorldInit(48000));
    assert(!ascensionAudioWorldGet(0x1111u, &near_s));
    ascensionAudioWorldSubmit(0x1111u, 0,0,-100, 0,0,0, 0, 0,6000, 0,1, 1,0);
    assert(ascensionAudioWorldGet(0x1111u, &near_s));
    assert(finite_snapshot(&near_s));
    assert(fabsf(near_s.direction_x) < 0.02f && fabsf(near_s.direction_y) < 0.02f);
    ascensionAudioWorldSubmit(0x2222u, 100,0,0, 0,0,0, 0, 0,6000, 0,1, 1,0);
    assert(ascensionAudioWorldGet(0x2222u, &far_s)); assert(fabsf(far_s.direction_x) > 0.95f);
    ascensionAudioWorldSubmit(0x3333u, 0,250,-100, 0,0,0, 0, 0,6000, 0,1, 1,0);
    assert(ascensionAudioWorldGet(0x3333u, &above_s)); assert(above_s.direction_y > 0.8f);
    ascensionAudioWorldSubmit(0x4444u, 0,0,-5000, 0,0,0, 0, 0,6000, 0,1, 2,0);
    assert(ascensionAudioWorldGet(0x4444u, &far_s));
    assert(far_s.distance_m > near_s.distance_m && far_s.lowpass_hz < near_s.lowpass_hz);
    assert(far_s.propagation_delay_s > near_s.propagation_delay_s);
    ascensionAudioWorldSubmit(0x5555u, 0,0,-1000, 0,0,0, 0, 0,6000, .9f,.15f, 3,2);
    assert(ascensionAudioWorldGet(0x5555u, &occ_s));
    assert(occ_s.direct_gain < near_s.direct_gain && occ_s.lowpass_hz < near_s.lowpass_hz);
    assert(occ_s.reverb_send > near_s.reverb_send);
    assert(occ_s.reverb_t60_s >= .24f && occ_s.reverb_t60_s <= 2.40f);
    assert(occ_s.doppler_ratio >= .82f && occ_s.doppler_ratio <= 1.22f);
    impulse[0] = 1.0f; memset(mono, 0, sizeof(mono));
    ascensionAudioWorldProcessMono(0x1111u, impulse, 256, mono);
    for (i=0;i<256;++i) assert(isfinite(mono[i]));
    for (i=0;i<256;++i) { l[i]=mono[i]; r[i]=mono[i]; }
    ascensionAudioWorldProcessStereoField(0x1111u, mono, mono, 256, l, r);
    for (i=0;i<256;++i) { assert(isfinite(l[i])); assert(isfinite(r[i])); }
    ascensionAudioWorldResetVoice(0x1111u); assert(!ascensionAudioWorldGet(0x1111u, &near_s));
    ascensionAudioWorldShutdown();
    puts("ascension_audio_world: all tests passed");
    return 0;
}
