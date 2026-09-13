/*
 * GoldenEye Ascension — reversible Human AI overlay.
 *
 * The original game AI remains untouched in src/game/. This port-layer module
 * observes ChrRecord and adds optional continuous perception, uncertain memory,
 * room-aware hearing, psychology and conservative squad tactics. Human AI is
 * OFF by default and restores script-owned character parameters when disabled.
 *
 * Design references are documented in docs/dev/HUMAN-AI.md. No code or assets
 * from other games are used here.
 */

#include <math.h>
#include <stdint.h>
#include <stdatomic.h>
#include <stdlib.h>
#include <string.h>

#include <ultra64.h>
#include <bondconstants.h>
#include <bondtypes.h>

#include "platform.h"
#include "config.h"
#include "system.h"
#include "human_ai.h"

#include "bg.h"
#include "bondview.h"
#include "chraction.h"
#include "chr.h"
#include "gun.h"
#include "loadobjectmodel.h"
#include "lv.h"
#include "player.h"
#include "stan.h"

/* Stable, non-static game primitives that are intentionally not in the public
 * chraction header. Reusing them preserves GE navigation/targeting semantics. */
extern s32  plot_course_for_actor(ChrRecord *self, coord3d *target, StandTile *stan, SPEED speed);
extern void chrlvSetTargetToPlayer(ChrRecord *self);

#define HAI_PI              3.14159265358979323846f
#define HAI_TAU             (2.0f * HAI_PI)
#define HAI_MAX_ROOMS       256
#define HAI_MAX_DEATHS      24
#define HAI_CLOSE_VISION_M  8.0f
#define HAI_MIN_HEARING     0.12f

static int   cfgHumanMode      = 0;
static int   cfgHumanDebug     = 0;
static float cfgHumanIntensity = 1.0f;
static int   cfgMaxTactical    = 6;

PD_CONSTRUCTOR static void humanAiConfigInit(void)
{
    configRegisterInt("AI.HumanMode", &cfgHumanMode, 0, 1);
    configRegisterInt("AI.Debug", &cfgHumanDebug, 0, 1);
    configRegisterFloat("AI.Intensity", &cfgHumanIntensity, 0.50f, 2.00f);
    configRegisterInt("AI.MaxTactical", &cfgMaxTactical, 1, 10);
}

typedef enum HumanMentalState {
    HAI_CALM = 0,
    HAI_CURIOUS,
    HAI_SUSPICIOUS,
    HAI_ALERT,
    HAI_COMBAT,
    HAI_SEARCHING,
    HAI_SURRENDERING
} HumanMentalState;

typedef enum HumanRole {
    HAI_ROLE_HOLD = 0,
    HAI_ROLE_ADVANCE,
    HAI_ROLE_FLANK_LEFT,
    HAI_ROLE_FLANK_RIGHT,
    HAI_ROLE_COVER
} HumanRole;

typedef enum HumanAttention {
    HAI_ATTN_ROUTINE = 0,
    HAI_ATTN_SOUND,
    HAI_ATTN_VISUAL,
    HAI_ATTN_DANGER,
    HAI_ATTN_TARGET
} HumanAttention;

typedef struct HumanParams {
    f32 vision;
    f32 hearing;
    s8 accuracy;
    s8 speed;
    s8 argh;
    u8 grenade;
    u8 morale;
    u8 alertness;
} HumanParams;

typedef struct HumanGuardState {
    Model *identityModel;
    s16 identityChrnum;
    u8 initialized;
    u8 appliedValid;

    HumanParams base;
    HumanParams applied;

    f32 awareness;
    f32 fear;
    f32 suppression;
    f32 pain;
    f32 confidence;
    f32 attention;
    f32 eyeAdaptation;
    f32 uncertainty;
    f32 dangerMemory;

    f32 courage;
    f32 aggression;
    f32 discipline;
    f32 perception;
    f32 teamwork;
    f32 nervousness;
    f32 experience;

    coord3d estimate;
    StandTile *estimateStan;

    s32 observedLastSee;
    s32 observedLastHear;
    s32 lastDirectVisual;
    s32 lastContact;
    s32 reactionUntil;
    s32 searchUntil;
    s32 nextVisionTick;
    s32 nextHearTick;
    s32 nextSearchTick;
    s32 nextTacticTick;
    s32 nextCommTick;

    f32 lastDamage;
    s8 lastCloseArghs;
    u8 wasAlive;
    u8 confirmed;
    u8 directVisible;
    u8 surrendered;
    u8 role;
    u8 attentionTarget;
    u8 mentalState;

    uint32_t rng;
} HumanGuardState;

typedef struct HumanDeathEvent {
    coord3d pos;
    s32 room;
    s16 chrnum;
} HumanDeathEvent;

static HumanGuardState *s_states = NULL;
static ChrRecord *s_slotsBase = NULL;
static s32 s_stateCount = 0;
static s32 s_lastTick = -1;
static int s_started = 0;
static _Atomic int s_effectiveMode = ATOMIC_VAR_INIT(0);
static _Atomic int s_toggleRequest = ATOMIC_VAR_INIT(0);
static _Atomic int s_setRequest = ATOMIC_VAR_INIT(-1);

static f32 clampf32(f32 v, f32 lo, f32 hi)
{
    return v < lo ? lo : v > hi ? hi : v;
}

static s32 clampi(s32 v, s32 lo, s32 hi)
{
    return v < lo ? lo : v > hi ? hi : v;
}

static f32 approachf(f32 cur, f32 target, f32 amount)
{
    if (cur < target) {
        cur += amount;
        return cur > target ? target : cur;
    }
    cur -= amount;
    return cur < target ? target : cur;
}

static f32 distXZ(const coord3d *a, const coord3d *b)
{
    f32 dx = a->x - b->x;
    f32 dz = a->z - b->z;
    return sqrtf(dx * dx + dz * dz);
}

static uint32_t mix32(uint32_t x)
{
    x ^= x >> 16;
    x *= 0x7feb352dU;
    x ^= x >> 15;
    x *= 0x846ca68bU;
    x ^= x >> 16;
    return x ? x : 0x9e3779b9U;
}

static uint32_t rngNext(HumanGuardState *s)
{
    uint32_t x = s->rng;
    x ^= x << 13;
    x ^= x >> 17;
    x ^= x << 5;
    s->rng = x ? x : 0x6d2b79f5U;
    return s->rng;
}

static f32 rng01(HumanGuardState *s)
{
    return (f32)(rngNext(s) & 0x00ffffffU) / 16777215.0f;
}

static f32 rngSigned(HumanGuardState *s)
{
    return rng01(s) * 2.0f - 1.0f;
}

static const char *mentalName(HumanMentalState state)
{
    switch (state) {
    case HAI_CALM: return "CALM";
    case HAI_CURIOUS: return "CURIOUS";
    case HAI_SUSPICIOUS: return "SUSPICIOUS";
    case HAI_ALERT: return "ALERT";
    case HAI_COMBAT: return "COMBAT";
    case HAI_SEARCHING: return "SEARCHING";
    case HAI_SURRENDERING: return "SURRENDERING";
    default: return "?";
    }
}

static int charAlive(const ChrRecord *chr)
{
    return chr && chr->model && chr->prop &&
           chr->actiontype != ACT_DIE && chr->actiontype != ACT_DEAD;
}

static int charArmed(ChrRecord *chr)
{
    return chrGetEquippedWeaponProp(chr, GUNRIGHT) != NULL ||
           chrGetEquippedWeaponProp(chr, GUNLEFT) != NULL;
}

static int charCivilian(const ChrRecord *chr)
{
    return (chr->chrflags & CHRFLAG_COUNT_DEATH_AS_CIVILIAN) != 0;
}

static int charMissionProtected(const ChrRecord *chr)
{
    return (chr->chrflags & CHRFLAG_INVINCIBLE) != 0;
}

static s32 charRoom(const ChrRecord *chr)
{
    return chr && chr->prop && chr->prop->stan ? getTileRoom(chr->prop->stan) : -1;
}

static void captureParams(HumanParams *p, const ChrRecord *chr)
{
    p->vision = chr->visionrange;
    p->hearing = chr->hearingscale;
    p->accuracy = chr->accuracyrating;
    p->speed = chr->speedrating;
    p->argh = chr->arghrating;
    p->grenade = chr->grenadeprob;
    p->morale = chr->morale;
    p->alertness = chr->alertness;
}

/* If stage bytecode changed a field after our last write, preserve that new
 * value as baseline. This keeps the overlay subordinate to mission scripts. */
static void syncBaseline(HumanGuardState *s, ChrRecord *chr)
{
    if (!s->appliedValid) {
        captureParams(&s->base, chr);
        return;
    }

    if (chr->visionrange != s->applied.vision) s->base.vision = chr->visionrange;
    if (chr->hearingscale != s->applied.hearing) s->base.hearing = chr->hearingscale;
    if (chr->accuracyrating != s->applied.accuracy) s->base.accuracy = chr->accuracyrating;
    if (chr->speedrating != s->applied.speed) s->base.speed = chr->speedrating;
    if (chr->arghrating != s->applied.argh) s->base.argh = chr->arghrating;
    if (chr->grenadeprob != s->applied.grenade) s->base.grenade = chr->grenadeprob;
    if (chr->morale != s->applied.morale) s->base.morale = chr->morale;
    if (chr->alertness != s->applied.alertness) s->base.alertness = chr->alertness;
    s->appliedValid = 0;
}

static void restoreGuard(HumanGuardState *s, ChrRecord *chr)
{
    if (!s || !s->initialized || !s->appliedValid || !chr ||
        chr->model != s->identityModel || chr->chrnum != s->identityChrnum) return;

    chr->visionrange = s->base.vision;
    chr->hearingscale = s->base.hearing;
    chr->accuracyrating = s->base.accuracy;
    chr->speedrating = s->base.speed;
    chr->arghrating = s->base.argh;
    chr->grenadeprob = s->base.grenade;
    chr->morale = s->base.morale;
    chr->alertness = s->base.alertness;
    s->appliedValid = 0;
}

static void restoreAll(void)
{
    if (!s_states || !s_slotsBase || s_slotsBase != g_ChrSlots) return;
    s32 count = s_stateCount < g_NumChrSlots ? s_stateCount : g_NumChrSlots;
    for (s32 i = 0; i < count; ++i) restoreGuard(&s_states[i], &g_ChrSlots[i]);
}

static void initGuardState(HumanGuardState *s, ChrRecord *chr, s32 slot)
{
    memset(s, 0, sizeof(*s));
    s->identityModel = chr->model;
    s->identityChrnum = chr->chrnum;
    s->initialized = 1;
    captureParams(&s->base, chr);

    uint32_t seed = (uint32_t)(uint16_t)chr->chrnum * 0x9e3779b9U;
    seed ^= (uint32_t)(slot + 1) * 0x85ebca6bU;
    seed ^= (uint32_t)(uintptr_t)chr->model;
    s->rng = mix32(seed);

    f32 rating = clampf32(((f32)chr->accuracyrating + (f32)chr->speedrating + 80.0f) / 280.0f, 0.0f, 1.0f);
    s->experience = clampf32(0.25f + 0.45f * rating + 0.30f * rng01(s), 0.0f, 1.0f);
    s->discipline = clampf32(0.25f + 0.55f * s->experience + 0.20f * rng01(s), 0.0f, 1.0f);
    s->courage = clampf32(0.20f + 0.45f * s->experience + 0.35f * rng01(s), 0.0f, 1.0f);
    s->aggression = clampf32(0.15f + 0.55f * rng01(s) + 0.20f * s->courage, 0.0f, 1.0f);
    s->perception = clampf32(0.35f + 0.40f * s->experience + 0.25f * rng01(s), 0.0f, 1.0f);
    s->teamwork = clampf32(0.25f + 0.45f * s->discipline + 0.30f * rng01(s), 0.0f, 1.0f);
    s->nervousness = clampf32(0.65f - 0.35f * s->experience + 0.35f * rngSigned(s), 0.0f, 1.0f);

    s->attention = 0.50f + 0.30f * s->discipline;
    s->eyeAdaptation = 0.55f;
    s->confidence = 35.0f + 50.0f * s->courage;
    s->mentalState = HAI_CALM;
    s->attentionTarget = HAI_ATTN_ROUTINE;
    s->role = (u8)(rngNext(s) % 5U);
    s->lastDamage = chr->damage;
    s->lastCloseArghs = chr->numclosearghs;
    s->wasAlive = (u8)charAlive(chr);
    s->observedLastSee = chr->lastseetarget60;
    s->observedLastHear = chr->lastheartarget60;
    s->nextVisionTick = g_GlobalTimer + slot % 3;
    s->nextHearTick = g_GlobalTimer;
    s->nextSearchTick = g_GlobalTimer + slot % 13;
    s->nextTacticTick = g_GlobalTimer + slot % 17;
    s->nextCommTick = g_GlobalTimer + slot % 19;
}

static int ensureStateStorage(void)
{
    if (g_NumChrSlots <= 0 || !g_ChrSlots) return 0;
    if (s_states && s_slotsBase == g_ChrSlots && s_stateCount == g_NumChrSlots) return 1;

    free(s_states);
    s_states = (HumanGuardState *)calloc((size_t)g_NumChrSlots, sizeof(*s_states));
    s_slotsBase = g_ChrSlots;
    s_stateCount = g_NumChrSlots;
    s_lastTick = g_GlobalTimer;
    if (!s_states) {
        s_slotsBase = NULL;
        s_stateCount = 0;
        sysLogPrintf(LOG_ERROR, "human-ai: state allocation failed");
        return 0;
    }
    return 1;
}

static s32 currentPlayerRoom(void)
{
    PropRecord *player = getCurrentPlayerProp();
    return player && player->stan ? getTileRoom(player->stan) : -1;
}

/* Shortest portal-hop map from Bond's current room. It is a semantic acoustic
 * graph: each room transition attenuates a sound instead of treating walls as
 * transparent. */
static void buildRoomHops(s16 hops[HAI_MAX_ROOMS], s32 startRoom)
{
    for (s32 i = 0; i < HAI_MAX_ROOMS; ++i) hops[i] = -1;
    if (startRoom < 0 || startRoom >= HAI_MAX_ROOMS || !g_BgPortals) return;

    s16 queue[HAI_MAX_ROOMS];
    s32 head = 0, tail = 0;
    hops[startRoom] = 0;
    queue[tail++] = (s16)startRoom;

    while (head < tail) {
        s32 room = queue[head++];
        s32 depth = hops[room];
        if (depth >= 6) continue;
        for (s32 p = 0; p < PORTMAX && g_BgPortals[p].offset_portal != NULL; ++p) {
            s32 a = g_BgPortals[p].connectedRoom1;
            s32 b = g_BgPortals[p].connectedRoom2;
            s32 next = a == room ? b : b == room ? a : -1;
            if (next < 0 || next >= HAI_MAX_ROOMS || hops[next] >= 0) continue;
            hops[next] = (s16)(depth + 1);
            if (tail < HAI_MAX_ROOMS) queue[tail++] = (s16)next;
        }
    }
}

static f32 acousticAttenuation(s32 hops)
{
    switch (hops) {
    case 0: return 1.00f;
    case 1: return 0.62f;
    case 2: return 0.38f;
    case 3: return 0.23f;
    case 4: return 0.14f;
    case 5: return 0.08f;
    default: return 0.0f;
    }
}

static int roomsCommunicate(s32 a, s32 b)
{
    if (a < 0 || b < 0) return 0;
    if (a == b) return 2;
    return bgRoomsSharePortal(a, b) ? 1 : 0;
}

static void rememberPosition(HumanGuardState *s, PropRecord *player, f32 uncertainty, int exact)
{
    if (!player) return;
    coord3d pos = player->pos;
    StandTile *stan = player->stan;
    f32 radius = exact ? 0.0f : clampf32(uncertainty, 20.0f, 3000.0f);

    if (!exact && radius > 0.0f && player->stan) {
        f32 angle = rng01(s) * HAI_TAU;
        f32 r = sqrtf(rng01(s)) * radius;
        coord3d candidate = pos;
        candidate.x += cosf(angle) * r;
        candidate.z += sinf(angle) * r;

        coord3d snapped;
        StandTile *snappedStan = NULL;
        if (getposstan(&candidate, player->stan, 20.0f, &snapped, &snappedStan) && snappedStan) {
            pos = snapped;
            stan = snappedStan;
        }
    }

    s->estimate = pos;
    s->estimateStan = stan;
    s->uncertainty = radius;
}

static void injectApproximateHearing(ChrRecord *chr, HumanGuardState *s)
{
    if (!s->estimateStan) return;
    chr->lastheartarget60 = g_GlobalTimer;
    chr->lastknowntargetpos = s->estimate;
    chr->targetTile = s->estimateStan;
    chr->hidden |= CHRHIDDEN_ALERT_GUARD_RELATED;
    s->observedLastHear = chr->lastheartarget60;
}

static void confirmVisual(ChrRecord *chr, HumanGuardState *s, PropRecord *player)
{
    s->confirmed = 1;
    s->awareness = 100.0f;
    s->lastContact = g_GlobalTimer;
    s->lastDirectVisual = g_GlobalTimer;
    s->searchUntil = g_GlobalTimer + (s32)(CHRLV_FRAMERATE_F * (14.0f + 10.0f * s->discipline));
    s->attention = 1.0f;
    s->attentionTarget = HAI_ATTN_TARGET;
    rememberPosition(s, player, 0.0f, 1);

    chr->lastseetarget60 = g_GlobalTimer;
    chr->lastknowntargetpos = player->pos;
    chr->targetTile = player->stan;
    chrlvSetTargetToPlayer(chr);
    s->observedLastSee = chr->lastseetarget60;
}

static f32 humanAngleToBond(ChrRecord *chr)
{
    f32 angle = fabsf(chrGetAngleToBond(chr));
    while (angle >= HAI_TAU) angle -= HAI_TAU;
    return angle > HAI_PI ? HAI_TAU - angle : angle;
}

static f32 visualAngleFactor(f32 angle)
{
    f32 d30 = HAI_PI * (30.0f / 180.0f);
    f32 d60 = HAI_PI * (60.0f / 180.0f);
    f32 d90 = HAI_PI * (90.0f / 180.0f);
    f32 d110 = HAI_PI * (110.0f / 180.0f);
    if (angle <= d30) return 1.00f;
    if (angle <= d60) return 0.78f;
    if (angle <= d90) return 0.42f;
    if (angle <= d110) return 0.16f;
    return 0.0f;
}

static f32 darknessFromAlpha(u8 alpha)
{
    return clampf32((f32)alpha / 160.0f, 0.0f, 1.0f);
}

static HumanMentalState deriveMentalState(const HumanGuardState *s)
{
    if (s->surrendered) return HAI_SURRENDERING;
    if (s->confirmed && s->directVisible) return HAI_COMBAT;
    if (s->confirmed) return HAI_SEARCHING;
    if (s->awareness >= 75.0f) return HAI_ALERT;
    if (s->awareness >= 45.0f) return HAI_SUSPICIOUS;
    if (s->awareness >= 15.0f) return HAI_CURIOUS;
    return HAI_CALM;
}

static void logTransition(ChrRecord *chr, HumanGuardState *s,
                          HumanMentalState before, HumanMentalState after)
{
    if (!cfgHumanDebug || before == after) return;
    sysLogPrintf(LOG_INFO,
        "human-ai: chr=%d %s->%s aw=%.1f fear=%.1f sup=%.1f uncertainty=%.0f",
        (int)chr->chrnum, mentalName(before), mentalName(after),
        s->awareness, s->fear, s->suppression, s->uncertainty);
}

static void updatePhysiology(ChrRecord *chr, HumanGuardState *s, f32 dt,
                             HumanDeathEvent deaths[], s32 *deathCount)
{
    int alive = charAlive(chr);
    if (s->wasAlive && !alive && *deathCount < HAI_MAX_DEATHS && chr->prop) {
        HumanDeathEvent *event = &deaths[(*deathCount)++];
        event->pos = chr->prop->pos;
        event->room = charRoom(chr);
        event->chrnum = chr->chrnum;
    }
    s->wasAlive = (u8)alive;
    if (!alive) return;

    if (chr->damage > s->lastDamage + 0.001f) {
        f32 delta = chr->damage - s->lastDamage;
        s->pain = clampf32(s->pain + 30.0f + delta * 12.0f, 0.0f, 100.0f);
        s->suppression = clampf32(s->suppression + 25.0f + delta * 8.0f, 0.0f, 100.0f);
        s->fear = clampf32(s->fear + (18.0f + delta * 5.0f) * (1.25f - 0.65f * s->courage), 0.0f, 100.0f);
        s->dangerMemory = clampf32(s->dangerMemory + 25.0f, 0.0f, 100.0f);
        s->attention = 1.0f;
        s->attentionTarget = HAI_ATTN_DANGER;
    }
    s->lastDamage = chr->damage;

    s32 nearDelta = (s32)chr->numclosearghs - (s32)s->lastCloseArghs;
    if (nearDelta > 0 && nearDelta < 32) {
        s->suppression = clampf32(s->suppression + nearDelta * (16.0f + 8.0f * s->nervousness), 0.0f, 100.0f);
        s->fear = clampf32(s->fear + nearDelta * (5.0f + 8.0f * s->nervousness), 0.0f, 100.0f);
        s->awareness = clampf32(s->awareness + 20.0f + nearDelta * 5.0f, 0.0f, 100.0f);
        s->dangerMemory = clampf32(s->dangerMemory + 12.0f, 0.0f, 100.0f);
        s->attention = 1.0f;
        s->attentionTarget = HAI_ATTN_DANGER;
    }
    s->lastCloseArghs = chr->numclosearghs;

    s->pain = clampf32(s->pain - 22.0f * dt, 0.0f, 100.0f);
    s->suppression = clampf32(s->suppression - (8.0f + 6.0f * s->discipline) * dt, 0.0f, 100.0f);
    s->fear = clampf32(s->fear - (1.5f + 2.5f * s->courage) * dt, 0.0f, 100.0f);
    s->dangerMemory = clampf32(s->dangerMemory - 0.65f * dt, 0.0f, 100.0f);
    s->confidence = clampf32(45.0f + 45.0f * s->courage - 0.45f * s->fear - 0.25f * s->suppression, 0.0f, 100.0f);
}

static void applyDeathAwareness(ChrRecord *chr, HumanGuardState *s,
                                const HumanDeathEvent deaths[], s32 deathCount)
{
    if (!charAlive(chr) || !chr->prop) return;
    s32 room = charRoom(chr);

    for (s32 i = 0; i < deathCount; ++i) {
        if (deaths[i].chrnum == chr->chrnum) continue;
        f32 distance = distXZ(&chr->prop->pos, &deaths[i].pos);
        int link = roomsCommunicate(room, deaths[i].room);
        if (distance > 1800.0f || link == 0) continue;

        f32 strength = (link == 2 ? 1.0f : 0.60f) *
                       (1.0f - clampf32(distance / 2200.0f, 0.0f, 0.8f));
        s->fear = clampf32(s->fear + strength * (18.0f + 22.0f * s->nervousness), 0.0f, 100.0f);
        s->dangerMemory = clampf32(s->dangerMemory + strength * 35.0f, 0.0f, 100.0f);
        s->awareness = clampf32(s->awareness + strength * 22.0f, 0.0f, 100.0f);
        s->attention = clampf32(s->attention + strength * 0.30f, 0.0f, 1.0f);
        s->attentionTarget = HAI_ATTN_DANGER;
    }
}

static void updateVisual(ChrRecord *chr, HumanGuardState *s, PropRecord *player, f32 dt)
{
    s->directVisible = 0;
    if (g_GlobalTimer < s->nextVisionTick) return;
    s->nextVisionTick = g_GlobalTimer + 2 + (s32)(rngNext(s) & 1U);

    f32 distance = chrGetDistanceToBond(chr);
    f32 maxDistance = fmaxf(200.0f, fmaxf(1.0f, s->base.vision) * 100.0f);
    f32 angleFactor = visualAngleFactor(humanAngleToBond(chr));
    if (angleFactor <= 0.0f || distance > maxDistance * 1.15f || !chrCanSeeBond(chr)) return;

    s->directVisible = 1;
    f32 rangeFactor = clampf32(1.0f - distance / fmaxf(maxDistance, 1.0f), 0.05f, 1.0f);
    f32 targetDark = g_CurrentPlayer ? darknessFromAlpha(g_CurrentPlayer->tileColor.a) : 0.0f;
    f32 guardDark = darknessFromAlpha(chr->shadecol.a);

    if (targetDark > guardDark + 0.12f) {
        s->eyeAdaptation = clampf32(s->eyeAdaptation + dt * (0.18f + 0.28f * s->experience), 0.0f, 1.0f);
    } else {
        s->eyeAdaptation = approachf(s->eyeAdaptation, 0.65f, dt * 0.65f);
    }

    f32 lightFactor = clampf32(1.0f - targetDark * 0.55f, 0.35f, 1.0f);
    if (targetDark > guardDark + 0.12f) lightFactor *= 0.42f + 0.58f * s->eyeAdaptation;

    coord3d *prev = getCurrentPlayerPrevPos();
    f32 motion = prev ? distXZ(&player->pos, prev) : 0.0f;
    f32 motionFactor = 0.82f + clampf32(motion / 45.0f, 0.0f, 0.55f);
    f32 attentionFactor = 0.65f + 0.55f * s->attention;
    f32 gain = 105.0f * rangeFactor * angleFactor * lightFactor * motionFactor *
               attentionFactor * (0.65f + 0.55f * s->perception) * cfgHumanIntensity;
    if (s->awareness >= 45.0f) gain *= 1.25f;
    if (s->awareness >= 75.0f) gain *= 1.20f;

    s->awareness = clampf32(s->awareness + gain * dt, 0.0f, 100.0f);
    s->attention = clampf32(s->attention + dt * 0.8f, 0.0f, 1.0f);
    s->attentionTarget = HAI_ATTN_VISUAL;
    s->lastDirectVisual = g_GlobalTimer;
    s->lastContact = g_GlobalTimer;
    rememberPosition(s, player, fmaxf(20.0f, distance * 0.015f), 0);

    if (!s->confirmed && s->awareness >= 90.0f) {
        if (s->reactionUntil <= 0) {
            f32 reaction = 0.95f - 0.48f * s->experience - 0.20f * s->discipline;
            reaction += rngSigned(s) * (0.10f + 0.12f * s->nervousness);
            if (distance < 350.0f) reaction *= 0.60f;
            reaction = clampf32(reaction, 0.18f, 1.10f);
            s->reactionUntil = g_GlobalTimer + (s32)(reaction * CHRLV_FRAMERATE_F);
        }
        if (g_GlobalTimer >= s->reactionUntil) confirmVisual(chr, s, player);
    } else if (s->confirmed) {
        confirmVisual(chr, s, player);
    }
}

static f32 playerGunNoise(void)
{
    f32 noise = 0.0f;
    if (get_hands_firing_status(GUNRIGHT)) noise = fmaxf(noise, getCurrentPlayerNoise(GUNRIGHT));
    if (get_hands_firing_status(GUNLEFT)) noise = fmaxf(noise, getCurrentPlayerNoise(GUNLEFT));
    return noise;
}

static void updateHearing(ChrRecord *chr, HumanGuardState *s, PropRecord *player,
                          const s16 roomHops[HAI_MAX_ROOMS], f32 gunNoise, f32 movement)
{
    if (g_GlobalTimer < s->nextHearTick || !chr->prop || !chr->prop->stan) return;
    s->nextHearTick = g_GlobalTimer + 3;

    s32 room = charRoom(chr);
    s32 hops = room >= 0 && room < HAI_MAX_ROOMS ? roomHops[room] : -1;
    if (hops < 0 || hops > 5) return;

    f32 attenuation = acousticAttenuation(hops);
    f32 gunRadius = gunNoise > 0.0f ? gunNoise * 100.0f : 0.0f;
    f32 moveRadius = movement > 1.5f ? clampf32(120.0f + movement * 28.0f, 120.0f, 1100.0f) : 0.0f;
    f32 rawRadius = fmaxf(gunRadius, moveRadius);
    if (attenuation <= 0.0f || rawRadius <= 0.0f) return;

    f32 radius = rawRadius * fmaxf(0.05f, s->base.hearing) * attenuation;
    f32 distance = distXZ(&chr->prop->pos, &player->pos);
    if (distance > radius) return;

    int gunEvent = gunRadius >= moveRadius && gunRadius > 0.0f;
    f32 proximity = clampf32(1.0f - distance / fmaxf(radius, 1.0f), 0.0f, 1.0f);
    f32 strength = (gunEvent ? 38.0f + 45.0f * proximity : 8.0f + 22.0f * proximity) *
                   (0.72f + 0.48f * s->perception) * cfgHumanIntensity;

    s->awareness = clampf32(s->awareness + strength, 0.0f, 100.0f);
    s->attention = 1.0f;
    s->attentionTarget = HAI_ATTN_SOUND;
    s->lastContact = g_GlobalTimer;
    s->dangerMemory = clampf32(s->dangerMemory + (gunEvent ? 18.0f : 5.0f), 0.0f, 100.0f);

    f32 uncertainty = 55.0f + 85.0f * (f32)hops + distance * (gunEvent ? 0.025f : 0.060f);
    uncertainty *= 1.25f - 0.50f * s->experience;
    rememberPosition(s, player, uncertainty, 0);
    if (s->awareness >= 25.0f) injectApproximateHearing(chr, s);
}

/* Mission bytecode remains authoritative. If it already observed a target,
 * absorb the fact rather than trying to undo the level designer's intent. */
static void absorbOriginalEvents(ChrRecord *chr, HumanGuardState *s, PropRecord *player)
{
    if (chr->lastseetarget60 > 0 && chr->lastseetarget60 != s->observedLastSee) {
        s->observedLastSee = chr->lastseetarget60;
        s->awareness = 100.0f;
        s->confirmed = 1;
        s->lastContact = g_GlobalTimer;
        s->searchUntil = g_GlobalTimer + (s32)(CHRLV_FRAMERATE_F * 18.0f);
        rememberPosition(s, player, 0.0f, 1);
    }

    if (chr->lastheartarget60 > 0 && chr->lastheartarget60 != s->observedLastHear) {
        s->observedLastHear = chr->lastheartarget60;
        if (!s->confirmed) {
            f32 distance = chrGetDistanceToBond(chr);
            s->awareness = clampf32(s->awareness + 32.0f, 0.0f, 100.0f);
            rememberPosition(s, player, 100.0f + distance * 0.05f, 0);
            chr->lastknowntargetpos = s->estimate;
            chr->targetTile = s->estimateStan;
            s->attention = 1.0f;
            s->attentionTarget = HAI_ATTN_SOUND;
        }
    }
}

static void updateMemory(HumanGuardState *s, f32 dt)
{
    f32 baselineAttention = 0.50f + 0.30f * s->discipline;
    s->attention = approachf(s->attention, baselineAttention,
                             dt * (0.14f + 0.22f * s->discipline));

    if (s->confirmed && !s->directVisible) {
        s->uncertainty = clampf32(s->uncertainty +
                                  dt * (28.0f + 45.0f * (1.0f - s->experience)),
                                  0.0f, 3000.0f);
        if (g_GlobalTimer > s->searchUntil) {
            s->confirmed = 0;
            s->awareness = fminf(s->awareness, 58.0f);
            s->uncertainty = fmaxf(s->uncertainty, 450.0f);
        } else {
            s->awareness = fmaxf(s->awareness, 72.0f);
        }
    } else if (!s->directVisible && !s->confirmed) {
        f32 decay = s->awareness >= 75.0f ? 3.0f : s->awareness >= 45.0f ? 4.5f : 7.0f;
        f32 floor = s->dangerMemory * 0.25f;
        s->awareness = fmaxf(floor, s->awareness - decay * dt);
        s->uncertainty = clampf32(s->uncertainty + 18.0f * dt, 0.0f, 3000.0f);
        if (s->awareness < 70.0f) s->reactionUntil = 0;
    }
}

static void searchRememberedArea(ChrRecord *chr, HumanGuardState *s)
{
    if (!s->estimateStan || g_GlobalTimer < s->nextSearchTick || !chrHasStoppedOrPatroling(chr)) return;
    s->nextSearchTick = g_GlobalTimer + (s32)(CHRLV_FRAMERATE_F * (0.8f + 0.9f * rng01(s)));

    coord3d candidate = s->estimate;
    f32 radius = clampf32(90.0f + s->uncertainty * 0.70f, 100.0f, 1300.0f);
    f32 angle = rng01(s) * HAI_TAU;
    f32 r = sqrtf(rng01(s)) * radius;
    candidate.x += cosf(angle) * r;
    candidate.z += sinf(angle) * r;

    coord3d snapped;
    StandTile *stan = NULL;
    if (getposstan(&candidate, s->estimateStan, 20.0f, &snapped, &stan) && stan) {
        plot_course_for_actor(chr, &snapped, stan,
                              s->awareness >= 75.0f || s->fear >= 60.0f ? SPEED_RUN : SPEED_WALK);
        if (cfgHumanDebug) {
            sysLogPrintf(LOG_INFO, "human-ai: chr=%d searches uncertainty=%.0f",
                         (int)chr->chrnum, s->uncertainty);
        }
    }
}

static int tryCoverOrFlank(ChrRecord *chr, HumanGuardState *s, int *tacticalCount)
{
    if (*tacticalCount >= cfgMaxTactical || g_GlobalTimer < s->nextTacticTick ||
        !chrHasStoppedOrPatroling(chr)) return 0;

    s->nextTacticTick = g_GlobalTimer + (s32)(CHRLV_FRAMERATE_F * (0.8f + 1.5f * rng01(s)));
    u8 quadrant = 0;

    if (s->suppression > 62.0f || s->fear > 78.0f || s->role == HAI_ROLE_COVER) {
        quadrant = QUADRANT_BACK;
    } else if (s->role == HAI_ROLE_FLANK_LEFT) {
        quadrant = QUADRANT_SIDE1;
    } else if (s->role == HAI_ROLE_FLANK_RIGHT) {
        quadrant = QUADRANT_SIDE2;
    } else if (s->role == HAI_ROLE_ADVANCE && s->confidence > 55.0f) {
        if (chrGoToBond(chr, SPEED_RUN)) {
            (*tacticalCount)++;
            return 1;
        }
        return 0;
    } else {
        return 0;
    }

    if (check_2328_preset_set_with_method(chr, quadrant) && chr->padpreset1 >= 0 &&
        chrGoToPad(chr, chr->padpreset1, SPEED_RUN)) {
        (*tacticalCount)++;
        return 1;
    }

    if (s->suppression < 75.0f && rng01(s) < 0.45f &&
        (actor_steps_sideways(chr) || actor_hops_sideways(chr))) {
        (*tacticalCount)++;
        return 1;
    }
    return 0;
}

static void maybeSurrender(ChrRecord *chr, HumanGuardState *s)
{
    if (s->surrendered || charMissionProtected(chr) || charCivilian(chr) ||
        !charArmed(chr) || !chrHasStoppedOrPatroling(chr)) return;

    f32 pressure = 0.55f * s->fear + 0.35f * s->suppression + 0.10f * s->pain;
    f32 threshold = 78.0f + 16.0f * s->courage + 8.0f * s->discipline;
    if (pressure < threshold || chr->morale > 55) return;

    f32 chance = clampf32((pressure - threshold) / 28.0f + (1.0f - s->courage) * 0.20f,
                          0.0f, 0.75f);
    if (rng01(s) < chance && chrTrySurrender(chr)) {
        s->surrendered = 1;
        s->confirmed = 0;
        s->mentalState = HAI_SURRENDERING;
        if (cfgHumanDebug) sysLogPrintf(LOG_INFO, "human-ai: chr=%d surrendered", (int)chr->chrnum);
    }
}

static void communicate(HumanGuardState *sender, ChrRecord *senderChr)
{
    if (g_GlobalTimer < sender->nextCommTick || sender->teamwork < 0.30f ||
        (!sender->confirmed && sender->awareness < 70.0f) || !senderChr->prop) return;

    sender->nextCommTick = g_GlobalTimer + (s32)(CHRLV_FRAMERATE_F * (0.9f + 1.2f * rng01(sender)));
    s32 senderRoom = charRoom(senderChr);

    for (s32 i = 0; i < s_stateCount; ++i) {
        HumanGuardState *receiver = &s_states[i];
        ChrRecord *receiverChr = &g_ChrSlots[i];
        if (receiver == sender || !receiver->initialized || !charAlive(receiverChr) ||
            !charArmed(receiverChr) || charCivilian(receiverChr) || !receiverChr->prop) continue;

        /* Do not invent hostility for a zero-context story actor. The mission
         * script still decides what a received alert actually means. */
        if (receiver->awareness < 5.0f && receiver->dangerMemory < 5.0f &&
            receiverChr->lastheartarget60 <= 0 && receiverChr->lastseetarget60 <= 0) continue;

        f32 distance = distXZ(&senderChr->prop->pos, &receiverChr->prop->pos);
        int link = roomsCommunicate(senderRoom, charRoom(receiverChr));
        f32 quality = link == 2 ? 1.0f : link == 1 ? 0.62f : 0.0f;
        if (quality == 0.0f && sender->teamwork > 0.78f && distance < 3500.0f) quality = 0.32f;
        if (quality <= 0.0f || distance > (link ? 2200.0f : 3500.0f)) continue;

        f32 received = sender->awareness * quality * (0.65f + 0.35f * receiver->teamwork);
        if (received <= receiver->awareness) continue;

        receiver->awareness = clampf32(received, 0.0f, 96.0f);
        receiver->attention = fmaxf(receiver->attention, 0.85f);
        receiver->attentionTarget = HAI_ATTN_SOUND;
        receiver->dangerMemory = fmaxf(receiver->dangerMemory, sender->dangerMemory * quality);
        receiver->estimate = sender->estimate;
        receiver->estimateStan = sender->estimateStan;
        receiver->uncertainty = clampf32(sender->uncertainty + 140.0f + distance * 0.03f +
                                          (1.0f - quality) * 250.0f, 80.0f, 3000.0f);
        if (receiver->estimateStan && receiver->awareness >= 25.0f) {
            injectApproximateHearing(receiverChr, receiver);
        }

        if (cfgHumanDebug) {
            sysLogPrintf(LOG_INFO, "human-ai: chr=%d shared contact with chr=%d q=%.2f",
                         (int)senderChr->chrnum, (int)receiverChr->chrnum, quality);
        }
    }
}

static void applyHumanParameters(ChrRecord *chr, HumanGuardState *s)
{
    HumanParams p = s->base;
    int armed = charArmed(chr);

    /* Prevent the binary original sight/hearing triggers from bypassing the
     * Human perception build-up. Close-range detection remains possible. */
    if (armed && !s->confirmed && s->awareness < 90.0f) {
        p.vision = fminf(p.vision, HAI_CLOSE_VISION_M);
        p.hearing = fminf(p.hearing, HAI_MIN_HEARING);
    }

    f32 accuracy = (f32)p.accuracy + (s->experience - 0.5f) * 8.0f -
                   s->suppression * 0.22f - s->pain * 0.18f - s->fear * 0.055f;
    p.accuracy = (s8)clampi((s32)lroundf(accuracy), -99, 100);

    f32 speed = (f32)p.speed + (s->aggression - 0.5f) * 5.0f -
                s->pain * 0.10f - s->suppression * 0.045f;
    p.speed = (s8)clampi((s32)lroundf(speed), -99, 100);

    if (p.grenade > 0) {
        f32 grenade = (f32)p.grenade * (0.78f + 0.42f * s->aggression) *
                      (1.0f - 0.0045f * s->fear);
        p.grenade = (u8)clampi((s32)lroundf(grenade), 0, 255);
    }

    f32 humanMorale = clampf32(45.0f + 150.0f * s->courage + 40.0f * s->discipline -
                                    1.05f * s->fear - 0.48f * s->suppression - 0.20f * s->pain,
                                0.0f, 255.0f);
    p.morale = (u8)clampi((s32)lroundf(0.35f * (f32)s->base.morale + 0.65f * humanMorale), 0, 255);

    s32 alert = (s32)lroundf(s->awareness * 2.55f);
    if (alert < s->base.alertness) alert = s->base.alertness;
    p.alertness = (u8)clampi(alert, 0, 255);

    chr->visionrange = p.vision;
    chr->hearingscale = p.hearing;
    chr->accuracyrating = p.accuracy;
    chr->speedrating = p.speed;
    chr->arghrating = p.argh;
    chr->grenadeprob = p.grenade;
    chr->morale = p.morale;
    chr->alertness = p.alertness;
    s->applied = p;
    s->appliedValid = 1;
}

static void setModeNow(int enabled)
{
    enabled = enabled ? 1 : 0;
    if (enabled == cfgHumanMode && enabled == atomic_load(&s_effectiveMode)) return;

    if (!enabled) {
        restoreAll();
        cfgHumanMode = 0;
        atomic_store(&s_effectiveMode, 0);
        sysLogPrintf(LOG_INFO, "human-ai: CLASSIC restored");
    } else {
        cfgHumanMode = 1;
        atomic_store(&s_effectiveMode, 1);
        s_lastTick = -1;
        sysLogPrintf(LOG_INFO, "human-ai: HUMAN enabled (experimental, reversible)");
    }
}

void humanAiInit(void)
{
    if (s_started) return;
    s_started = 1;
    const char *env = getenv("GE_HUMAN_AI");
    if (env && *env) cfgHumanMode = atoi(env) != 0;
    atomic_store(&s_effectiveMode, cfgHumanMode ? 1 : 0);
    sysLogPrintf(LOG_INFO, "human-ai: startup mode=%s intensity=%.2f max-tactical=%d",
                 cfgHumanMode ? "HUMAN" : "CLASSIC", cfgHumanIntensity, cfgMaxTactical);
}

void humanAiShutdown(void)
{
    restoreAll();
    free(s_states);
    s_states = NULL;
    s_slotsBase = NULL;
    s_stateCount = 0;
    s_started = 0;
}

void humanAiToggle(void)
{
    atomic_store(&s_toggleRequest, 1);
}

void humanAiSetEnabled(int enabled)
{
    atomic_store(&s_setRequest, enabled ? 1 : 0);
}

int humanAiIsEnabled(void)
{
    return atomic_load(&s_effectiveMode);
}

const char *humanAiModeName(void)
{
    return humanAiIsEnabled() ? "HUMAN" : "CLASSIC";
}

void humanAiTick(void)
{
    if (!s_started) return;

    int requested = atomic_exchange(&s_setRequest, -1);
    if (requested >= 0) setModeNow(requested);
    if (atomic_exchange(&s_toggleRequest, 0)) setModeNow(!humanAiIsEnabled());
    if (!humanAiIsEnabled()) return;

    if (!g_CurrentPlayer || !getCurrentPlayerProp() || !ensureStateStorage()) return;
    PropRecord *player = getCurrentPlayerProp();
    if (!player || !player->stan) return;

    if (s_lastTick == g_GlobalTimer) return;
    s32 deltaTicks = s_lastTick < 0 ? 1 : g_GlobalTimer - s_lastTick;
    s_lastTick = g_GlobalTimer;
    if (deltaTicks <= 0) deltaTicks = 1;
    if (deltaTicks > 8) deltaTicks = 8;
    f32 dt = (f32)deltaTicks / CHRLV_FRAMERATE_F;

    s16 roomHops[HAI_MAX_ROOMS];
    buildRoomHops(roomHops, currentPlayerRoom());

    coord3d *prev = getCurrentPlayerPrevPos();
    f32 movement = prev ? distXZ(&player->pos, prev) : 0.0f;
    f32 gunNoise = playerGunNoise();

    HumanDeathEvent deaths[HAI_MAX_DEATHS];
    s32 deathCount = 0;

    /* Pass 1: identity, script baseline and physiology. */
    for (s32 i = 0; i < s_stateCount; ++i) {
        ChrRecord *chr = &g_ChrSlots[i];
        HumanGuardState *state = &s_states[i];
        if (!chr->model || !chr->prop) continue;

        if (!state->initialized || state->identityModel != chr->model ||
            state->identityChrnum != chr->chrnum) {
            initGuardState(state, chr, i);
        } else {
            syncBaseline(state, chr);
        }
        updatePhysiology(chr, state, dt, deaths, &deathCount);
    }

    /* Pass 2: individual sensing/cognition and casualty awareness. */
    for (s32 i = 0; i < s_stateCount; ++i) {
        ChrRecord *chr = &g_ChrSlots[i];
        HumanGuardState *state = &s_states[i];
        if (!state->initialized || !charAlive(chr)) continue;

        HumanMentalState before = (HumanMentalState)state->mentalState;
        applyDeathAwareness(chr, state, deaths, deathCount);
        absorbOriginalEvents(chr, state, player);

        if (charArmed(chr)) {
            updateVisual(chr, state, player, dt);
            updateHearing(chr, state, player, roomHops, gunNoise, movement);
        }
        updateMemory(state, dt);

        HumanMentalState after = deriveMentalState(state);
        state->mentalState = (u8)after;
        logTransition(chr, state, before, after);
    }

    /* Pass 3: information spreads locally; no iteration-order clairvoyance. */
    for (s32 i = 0; i < s_stateCount; ++i) {
        ChrRecord *chr = &g_ChrSlots[i];
        HumanGuardState *state = &s_states[i];
        if (state->initialized && charAlive(chr) && charArmed(chr) && !charCivilian(chr)) {
            communicate(state, chr);
        }
    }

    /* Pass 4: conservative tactics only while the original AI is idle/patrol. */
    int tacticalCount = 0;
    for (s32 i = 0; i < s_stateCount; ++i) {
        ChrRecord *chr = &g_ChrSlots[i];
        HumanGuardState *state = &s_states[i];
        if (!state->initialized || !charAlive(chr)) continue;

        if (charArmed(chr)) {
            if (state->confirmed && !state->directVisible) {
                searchRememberedArea(chr, state);
            } else if (state->confirmed && state->directVisible) {
                tryCoverOrFlank(chr, state, &tacticalCount);
            }
            maybeSurrender(chr, state);
        }
        applyHumanParameters(chr, state);
    }
}
