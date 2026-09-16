#include "ascension_audio_game_bridge.h"
#include "ascension_audio_world.h"
#include "ascension_audio_world_runtime.h"

#include <stdint.h>
#include <stdlib.h>

#include "synthInternals.h"
#include "player.h"
#include "stan.h"
#include "bg.h"

#define ASC_ROOM_PATH_MAX 24

void ascensionAudioWorldSubmitFromGame(ALSoundState *state, const coord3d *source,
                                       f32 near_range, f32 far_range)
{
    struct PropRecord *listener_prop;
    StandTile *walk_tile;
    s32 rooms[ASC_ROOM_PATH_MAX];
    s32 room_count = 0;
    s32 closed_portals = 0;
    s32 path_ok = 0;
    s32 i;
    float obstruction = 0.0f;
    float transmission = 1.0f;
    uint32_t voice_key;

    if (!state || !source || !g_CurrentPlayer || !g_CurrentPlayer->prop ||
        !state->voice.pvoice || !state->voice.pvoice->envmixer.state) return;
    if (!ascensionAudioWorldRuntimeEnsure()) return;

    listener_prop = g_CurrentPlayer->prop;
    voice_key = (uint32_t)(uintptr_t)osVirtualToPhysical(state->voice.pvoice->envmixer.state);
    if (!voice_key) return;

    walk_tile = listener_prop->stan;
    if (walk_tile) {
        path_ok = sub_GAME_7F0B0C24(&walk_tile,
                                    listener_prop->pos.x, listener_prop->pos.z,
                                    source->x, source->z,
                                    rooms, &room_count, ASC_ROOM_PATH_MAX);
    }

    if (room_count < 1) {
        room_count = 1;
    } else if (room_count > ASC_ROOM_PATH_MAX) {
        room_count = ASC_ROOM_PATH_MAX;
    }

    if (!path_ok) {
        /* Static STAN obstruction: concrete-like conservative transmission.
           We keep energy rather than muting so sound behind a wall remains
           localisable and believable. */
        obstruction = 0.86f;
        transmission = 0.18f;
    } else {
        for (i = 0; i + 1 < room_count; ++i) {
            coord3d p0, p1;
            s32 portal = bgGetPortalBetweenRooms(rooms[i], rooms[i + 1], &p0, &p1);
            if (portal >= 0 && bgGetDataPortalsControlBytes1Bit1(portal)) {
                ++closed_portals;
            }
        }
        if (closed_portals > 0) {
            obstruction = 0.58f + 0.08f * (float)(closed_portals > 3 ? 3 : closed_portals);
            transmission = 1.0f;
            for (i = 0; i < closed_portals && i < 4; ++i) transmission *= 0.55f;
        } else if (room_count > 1) {
            /* Open portals still create diffraction/room-transition loss. */
            obstruction = 0.08f * (float)(room_count - 1);
            if (obstruction > 0.28f) obstruction = 0.28f;
            transmission = 1.0f - 0.045f * (float)(room_count - 1);
            if (transmission < 0.72f) transmission = 0.72f;
        }
    }

    ascensionAudioWorldSubmit(voice_key,
        source->x, source->y, source->z,
        listener_prop->pos.x, listener_prop->pos.y, listener_prop->pos.z,
        g_CurrentPlayer->vv_theta,
        near_range, far_range,
        obstruction, transmission,
        room_count, closed_portals);
}
