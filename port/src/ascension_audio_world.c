#include "ascension_audio_world.h"

#include <math.h>
#include <pthread.h>
#include <stdatomic.h>
#include <stddef.h>
#include <string.h>
#include <time.h>

#define ASC_WORLD_UNIT_TO_M 0.01f
#define ASC_SPEED_OF_SOUND_MPS 343.0f
#define ASC_MIN_CUTOFF_HZ 850.0f
#define ASC_MAX_CUTOFF_HZ 20000.0f
#define ASC_DELAY_SAMPLES 8192
#define ASC_REVERB_SAMPLES 1536
#define ASC_WORKER_HZ 120
#define ASC_PI 3.14159265358979323846f

typedef struct AscWorldInput {
    uint32_t voice_key;
    int valid;
    float sx, sy, sz;
    float lx, ly, lz;
    float yaw_deg;
    float near_units;
    float far_units;
    float obstruction;
    float transmission;
    int room_count;
    int closed_portals;
    double submit_time_s;
} AscWorldInput;

typedef struct AscWorldSlot {
    atomic_uint voice_key;
    atomic_int published;
    AscensionAudioWorldSnapshot snapshot[2];
    AscWorldInput pending;
    int pending_valid;
    float previous_source[3];
    float previous_listener[3];
    double previous_time_s;
    int have_previous;
    float lowpass_state;
    float delay_line[ASC_DELAY_SAMPLES];
    unsigned int delay_write;
    float delay_samples_smoothed;
    float reverb_l[ASC_REVERB_SAMPLES];
    float reverb_r[ASC_REVERB_SAMPLES];
    unsigned int reverb_write;
} AscWorldSlot;

static AscWorldSlot g_slots[ASCENSION_AUDIO_WORLD_MAX_SOURCES];
static pthread_mutex_t g_input_mutex = PTHREAD_MUTEX_INITIALIZER;
static pthread_t g_worker;
static atomic_int g_running = 0;
static int g_worker_started = 0;
static int g_sample_rate = 48000;

static float ascClamp(float v, float lo, float hi) { return v < lo ? lo : (v > hi ? hi : v); }
static int ascFinite(float v) { return isfinite(v) != 0; }

static double ascNowSeconds(void)
{
#if defined(CLOCK_MONOTONIC)
    struct timespec ts;
    if (clock_gettime(CLOCK_MONOTONIC, &ts) == 0)
        return (double)ts.tv_sec + (double)ts.tv_nsec * 1.0e-9;
#endif
    return (double)clock() / (double)CLOCKS_PER_SEC;
}

static int ascFindSlotRead(uint32_t key)
{
    int i;
    if (key == 0) return -1;
    for (i = 0; i < ASCENSION_AUDIO_WORLD_MAX_SOURCES; ++i)
        if (atomic_load_explicit(&g_slots[i].voice_key, memory_order_acquire) == key) return i;
    return -1;
}

static int ascFindOrClaimSlotLocked(uint32_t key)
{
    int i, free_index = -1;
    if (key == 0) return -1;
    for (i = 0; i < ASCENSION_AUDIO_WORLD_MAX_SOURCES; ++i) {
        unsigned int current = atomic_load_explicit(&g_slots[i].voice_key, memory_order_relaxed);
        if (current == key) return i;
        if (current == 0 && free_index < 0) free_index = i;
    }
    if (free_index < 0) free_index = (int)(key % ASCENSION_AUDIO_WORLD_MAX_SOURCES);
    memset(&g_slots[free_index], 0, sizeof(g_slots[free_index]));
    atomic_store_explicit(&g_slots[free_index].voice_key, key, memory_order_release);
    atomic_store_explicit(&g_slots[free_index].published, 0, memory_order_release);
    return free_index;
}

static void ascComputeSnapshot(AscWorldSlot *slot, const AscWorldInput *in)
{
    AscensionAudioWorldSnapshot s;
    float dx = in->sx - in->lx, dy = in->sy - in->ly, dz = in->sz - in->lz;
    float distance_units = sqrtf(dx * dx + dy * dy + dz * dz);
    float distance_m = distance_units * ASC_WORLD_UNIT_TO_M;
    float yaw = in->yaw_deg * (ASC_PI / 180.0f), cy = cosf(yaw), sy = sinf(yaw);
    float right, up, forward, len;
    float obstruction = ascClamp(in->obstruction, 0.0f, 1.0f);
    float transmission = ascClamp(in->transmission, 0.0f, 1.0f);
    float effective_volume, effective_surface, absorption, t60, cutoff, air_gain;
    float radial_src = 0.0f, radial_lis = 0.0f;
    double dt;
    int back;
    memset(&s, 0, sizeof(s));
    s.voice_key = in->voice_key; s.valid = 1;

    if (!ascFinite(distance_m) || distance_m < 0.001f) {
        distance_m = 0.001f; dx = 0.0f; dy = 0.0f; dz = -1.0f; distance_units = 1.0f;
    }

    /* Steam Audio listener space: +X right, +Y up, -Z forward. */
    right = -(dx * cy + dz * sy);
    up = dy;
    forward = dx * sy - dz * cy;
    len = sqrtf(right * right + up * up + forward * forward);
    if (len < 1.0e-5f || !ascFinite(len)) { right = 0.0f; up = 0.0f; forward = 1.0f; len = 1.0f; }
    s.direction_x = right / len;
    s.direction_y = up / len;
    s.direction_z = -forward / len;
    s.distance_m = distance_m;
    s.propagation_delay_s = ascClamp(distance_m / ASC_SPEED_OF_SOUND_MPS, 0.0f, 0.165f);

    /* Keep the game's canonical authored attenuation; this layer only adds
       physically motivated air/barrier losses, preventing double attenuation. */
    air_gain = expf(-0.0022f * distance_m);
    s.direct_gain = ascClamp(air_gain * (1.0f - 0.72f * obstruction) *
                             (0.35f + 0.65f * transmission), 0.03f, 1.0f);
    cutoff = ASC_MAX_CUTOFF_HZ * expf(-0.0065f * distance_m);
    cutoff *= (1.0f - 0.82f * obstruction);
    cutoff *= (0.55f + 0.45f * transmission);
    s.lowpass_hz = ascClamp(cutoff, ASC_MIN_CUTOFF_HZ, ASC_MAX_CUTOFF_HZ);
    s.occlusion = obstruction; s.transmission = transmission;

    /* Sabine-form bounded room decay from real traversed room topology. */
    effective_volume = 75.0f + 45.0f * (float)(in->room_count > 0 ? in->room_count : 1);
    effective_surface = 105.0f + 55.0f * (float)(in->room_count > 0 ? in->room_count : 1);
    absorption = ascClamp(0.22f + 0.26f * obstruction + 0.08f * (float)in->closed_portals, 0.12f, 0.78f);
    t60 = 0.161f * effective_volume / (effective_surface * absorption);
    s.reverb_t60_s = ascClamp(t60, 0.24f, 2.40f);
    s.reverb_send = ascClamp(0.045f + 0.055f * (float)(in->room_count > 1 ? in->room_count - 1 : 0)
                             + 0.12f * obstruction + 0.04f * (float)in->closed_portals, 0.025f, 0.42f);
    s.early_reflection_delay_s = ascClamp((2.4f + distance_m * 0.08f + 1.7f * (float)in->room_count) / 1000.0f,
                                           0.003f, 0.045f);
    s.early_reflection_gain = ascClamp(0.055f + 0.035f * (float)in->room_count + 0.06f * obstruction,
                                       0.04f, 0.28f);
    s.room_count = in->room_count; s.closed_portals = in->closed_portals;

    /* Doppler is derived from consecutive world positions and c=343 m/s. */
    dt = in->submit_time_s - slot->previous_time_s;
    if (slot->have_previous && dt > 0.002 && dt < 0.5) {
        float inv_dt_m = ASC_WORLD_UNIT_TO_M / (float)dt;
        float ux = dx / distance_units, uy = dy / distance_units, uz = dz / distance_units;
        float vsx = (in->sx - slot->previous_source[0]) * inv_dt_m;
        float vsy = (in->sy - slot->previous_source[1]) * inv_dt_m;
        float vsz = (in->sz - slot->previous_source[2]) * inv_dt_m;
        float vlx = (in->lx - slot->previous_listener[0]) * inv_dt_m;
        float vly = (in->ly - slot->previous_listener[1]) * inv_dt_m;
        float vlz = (in->lz - slot->previous_listener[2]) * inv_dt_m;
        radial_src = ascClamp(vsx * ux + vsy * uy + vsz * uz, -80.0f, 80.0f);
        radial_lis = ascClamp(vlx * ux + vly * uy + vlz * uz, -80.0f, 80.0f);
    }
    s.doppler_ratio = ascClamp((ASC_SPEED_OF_SOUND_MPS + radial_lis) /
                               (ASC_SPEED_OF_SOUND_MPS + radial_src), 0.82f, 1.22f);
    if (!ascFinite(s.doppler_ratio)) s.doppler_ratio = 1.0f;

    slot->previous_source[0] = in->sx; slot->previous_source[1] = in->sy; slot->previous_source[2] = in->sz;
    slot->previous_listener[0] = in->lx; slot->previous_listener[1] = in->ly; slot->previous_listener[2] = in->lz;
    slot->previous_time_s = in->submit_time_s; slot->have_previous = 1;

    back = 1 - atomic_load_explicit(&slot->published, memory_order_relaxed);
    slot->snapshot[back] = s;
    atomic_thread_fence(memory_order_release);
    atomic_store_explicit(&slot->published, back, memory_order_release);
}

static void ascProcessPendingOnce(void)
{
    AscWorldInput copy[ASCENSION_AUDIO_WORLD_MAX_SOURCES];
    int valid[ASCENSION_AUDIO_WORLD_MAX_SOURCES], i;
    pthread_mutex_lock(&g_input_mutex);
    for (i = 0; i < ASCENSION_AUDIO_WORLD_MAX_SOURCES; ++i) {
        valid[i] = g_slots[i].pending_valid;
        if (valid[i]) { copy[i] = g_slots[i].pending; g_slots[i].pending_valid = 0; }
    }
    pthread_mutex_unlock(&g_input_mutex);
    for (i = 0; i < ASCENSION_AUDIO_WORLD_MAX_SOURCES; ++i)
        if (valid[i]) ascComputeSnapshot(&g_slots[i], &copy[i]);
}

#ifndef ASC_AUDIO_WORLD_TEST_SYNC
static void *ascWorkerMain(void *unused)
{
    struct timespec sleep_time;
    (void)unused;
    sleep_time.tv_sec = 0; sleep_time.tv_nsec = 1000000000L / ASC_WORKER_HZ;
    while (atomic_load_explicit(&g_running, memory_order_acquire)) {
        ascProcessPendingOnce(); nanosleep(&sleep_time, NULL);
    }
    ascProcessPendingOnce(); return NULL;
}
#endif

int ascensionAudioWorldInit(int sample_rate)
{
    ascensionAudioWorldReset();
    g_sample_rate = sample_rate > 8000 ? sample_rate : 48000;
#ifdef ASC_AUDIO_WORLD_TEST_SYNC
    atomic_store_explicit(&g_running, 0, memory_order_release); g_worker_started = 0; return 1;
#else
    atomic_store_explicit(&g_running, 1, memory_order_release);
    if (pthread_create(&g_worker, NULL, ascWorkerMain, NULL) != 0) {
        atomic_store_explicit(&g_running, 0, memory_order_release); g_worker_started = 0; return 0;
    }
    g_worker_started = 1; return 1;
#endif
}

void ascensionAudioWorldShutdown(void)
{
    if (g_worker_started) {
        atomic_store_explicit(&g_running, 0, memory_order_release); pthread_join(g_worker, NULL); g_worker_started = 0;
    }
    ascensionAudioWorldReset();
}

void ascensionAudioWorldReset(void)
{
    int i;
    pthread_mutex_lock(&g_input_mutex);
    memset(g_slots, 0, sizeof(g_slots));
    for (i = 0; i < ASCENSION_AUDIO_WORLD_MAX_SOURCES; ++i) {
        atomic_init(&g_slots[i].voice_key, 0); atomic_init(&g_slots[i].published, 0);
    }
    pthread_mutex_unlock(&g_input_mutex);
}

void ascensionAudioWorldResetVoice(uint32_t voice_key)
{
    int index = ascFindSlotRead(voice_key);
    if (index < 0) return;
    pthread_mutex_lock(&g_input_mutex);
    if (atomic_load_explicit(&g_slots[index].voice_key, memory_order_relaxed) == voice_key) {
        memset(&g_slots[index], 0, sizeof(g_slots[index]));
        atomic_store_explicit(&g_slots[index].voice_key, 0, memory_order_release);
        atomic_store_explicit(&g_slots[index].published, 0, memory_order_release);
    }
    pthread_mutex_unlock(&g_input_mutex);
}

void ascensionAudioWorldSubmit(uint32_t voice_key,
    float source_x, float source_y, float source_z,
    float listener_x, float listener_y, float listener_z,
    float listener_yaw_deg, float near_range_units, float far_range_units,
    float obstruction, float transmission, int room_count, int closed_portals)
{
    AscWorldInput input; int index;
    if (voice_key == 0) return;
    if (!ascFinite(source_x) || !ascFinite(source_y) || !ascFinite(source_z) ||
        !ascFinite(listener_x) || !ascFinite(listener_y) || !ascFinite(listener_z) || !ascFinite(listener_yaw_deg)) return;
    memset(&input, 0, sizeof(input));
    input.voice_key = voice_key; input.valid = 1;
    input.sx = source_x; input.sy = source_y; input.sz = source_z;
    input.lx = listener_x; input.ly = listener_y; input.lz = listener_z;
    input.yaw_deg = listener_yaw_deg; input.near_units = near_range_units; input.far_units = far_range_units;
    input.obstruction = obstruction; input.transmission = transmission;
    input.room_count = room_count < 1 ? 1 : (room_count > 32 ? 32 : room_count);
    input.closed_portals = closed_portals < 0 ? 0 : (closed_portals > 16 ? 16 : closed_portals);
    input.submit_time_s = ascNowSeconds();
    pthread_mutex_lock(&g_input_mutex);
    index = ascFindOrClaimSlotLocked(voice_key);
    if (index >= 0) { g_slots[index].pending = input; g_slots[index].pending_valid = 1; }
    pthread_mutex_unlock(&g_input_mutex);
#ifdef ASC_AUDIO_WORLD_TEST_SYNC
    ascProcessPendingOnce();
#endif
}

int ascensionAudioWorldGet(uint32_t voice_key, AscensionAudioWorldSnapshot *out_snapshot)
{
    int index, published; AscensionAudioWorldSnapshot copy;
    if (!out_snapshot) return 0;
    index = ascFindSlotRead(voice_key); if (index < 0) return 0;
    published = atomic_load_explicit(&g_slots[index].published, memory_order_acquire);
    copy = g_slots[index].snapshot[published]; atomic_thread_fence(memory_order_acquire);
    if (!copy.valid || copy.voice_key != voice_key) return 0;
    *out_snapshot = copy; return 1;
}

void ascensionAudioWorldProcessMono(uint32_t voice_key, const float *input, int frame_count, float *output)
{
    AscensionAudioWorldSnapshot s; int index, i; float cutoff, a; AscWorldSlot *slot;
    if (!input || !output || frame_count <= 0) return;
    index = ascFindSlotRead(voice_key);
    if (index < 0 || !ascensionAudioWorldGet(voice_key, &s)) {
        if (input != output) memcpy(output, input, (size_t)frame_count * sizeof(float)); return;
    }
    slot = &g_slots[index];
    cutoff = ascClamp(s.lowpass_hz, ASC_MIN_CUTOFF_HZ, (float)g_sample_rate * 0.45f);
    a = expf(-2.0f * ASC_PI * cutoff / (float)g_sample_rate);
    for (i = 0; i < frame_count; ++i) {
        float x = ascFinite(input[i]) ? input[i] : 0.0f;
        float desired_delay = ascClamp(s.propagation_delay_s * (float)g_sample_rate, 0.0f, (float)(ASC_DELAY_SAMPLES - 2));
        unsigned int read_index; float delayed;
        slot->delay_samples_smoothed += 0.02f * (desired_delay - slot->delay_samples_smoothed);
        slot->delay_line[slot->delay_write] = x;
        read_index = (slot->delay_write + ASC_DELAY_SAMPLES - (unsigned int)slot->delay_samples_smoothed) % ASC_DELAY_SAMPLES;
        delayed = slot->delay_line[read_index]; slot->delay_write = (slot->delay_write + 1u) % ASC_DELAY_SAMPLES;
        slot->lowpass_state = (1.0f - a) * delayed + a * slot->lowpass_state;
        output[i] = ascClamp(slot->lowpass_state * s.direct_gain, -2.0f, 2.0f);
    }
}

void ascensionAudioWorldProcessStereoField(uint32_t voice_key, const float *dry_left, const float *dry_right,
    int frame_count, float *io_left, float *io_right)
{
    AscensionAudioWorldSnapshot s; int index, i; AscWorldSlot *slot; unsigned int delay_a, delay_b; float feedback;
    if (!dry_left || !dry_right || !io_left || !io_right || frame_count <= 0) return;
    index = ascFindSlotRead(voice_key); if (index < 0 || !ascensionAudioWorldGet(voice_key, &s)) return;
    slot = &g_slots[index];
    delay_a = (unsigned int)ascClamp(s.early_reflection_delay_s * (float)g_sample_rate, 1.0f, (float)(ASC_REVERB_SAMPLES - 32));
    delay_b = delay_a + 23u; if (delay_b >= ASC_REVERB_SAMPLES) delay_b = ASC_REVERB_SAMPLES - 1;
    feedback = ascClamp(powf(0.001f, ((float)delay_a / (float)g_sample_rate) / s.reverb_t60_s), 0.18f, 0.88f);
    for (i = 0; i < frame_count; ++i) {
        unsigned int ra = (slot->reverb_write + ASC_REVERB_SAMPLES - delay_a) % ASC_REVERB_SAMPLES;
        unsigned int rb = (slot->reverb_write + ASC_REVERB_SAMPLES - delay_b) % ASC_REVERB_SAMPLES;
        float early_l = slot->reverb_l[ra], early_r = slot->reverb_r[rb];
        float in_l = ascFinite(dry_left[i]) ? dry_left[i] : 0.0f, in_r = ascFinite(dry_right[i]) ? dry_right[i] : 0.0f;
        float mono = 0.5f * (in_l + in_r);
        float wet_l = early_l * s.early_reflection_gain + early_r * s.reverb_send;
        float wet_r = early_r * s.early_reflection_gain + early_l * s.reverb_send;
        slot->reverb_l[slot->reverb_write] = mono + early_r * feedback * 0.73f;
        slot->reverb_r[slot->reverb_write] = mono - early_l * feedback * 0.69f;
        slot->reverb_write = (slot->reverb_write + 1u) % ASC_REVERB_SAMPLES;
        io_left[i] = ascClamp(io_left[i] + wet_l, -2.0f, 2.0f);
        io_right[i] = ascClamp(io_right[i] + wet_r, -2.0f, 2.0f);
    }
}
