#!/usr/bin/env python3
"""Idempotently wire real GoldenEye world positions into Ascension Audio 3D.

Only the PC build is affected: every inserted game hook is inside #ifdef PORT.
The script fails closed if the expected decomp seams change, so a future
upstream edit cannot silently apply the hook at the wrong location.

Runtime safety: world-state publication is synchronous with the game thread.
The mixer consumes already-published snapshots and never creates an acoustic
worker pthread from the audio path.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
PROPOBJ = ROOT / "src/game/propobj.c"
WORLD = ROOT / "port/src/ascension_audio_world.c"
MIXER = ROOT / "port/src/mixer.c"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count == 0:
        if new in text:
            return text
        raise RuntimeError(f"audio3d integration seam not found: {label}")
    if count != 1:
        raise RuntimeError(f"audio3d integration seam is ambiguous ({count} matches): {label}")
    return text.replace(old, new, 1)


def patch_propobj() -> bool:
    text = PROPOBJ.read_text(encoding="utf-8")
    original = text

    include_old = '#include "propobj.h"\n'
    include_new = '#include "propobj.h"\n#ifdef PORT\n#include "ascension_audio_game_bridge.h"\n#endif\n'
    if 'ascension_audio_game_bridge.h' not in text:
        text = replace_once(text, include_old, include_new, "propobj bridge include")

    event_old = (
        'void chrobjSndCreatePostEvent(ALSoundState *state, coord3d *pos, f32 low, f32 high)\n'
        '{\n'
        '    sndCreatePostEvent(state, 8, sub_GAME_7F053894(pos, low, high));\n'
        '}\n'
    )
    event_new = (
        'void chrobjSndCreatePostEvent(ALSoundState *state, coord3d *pos, f32 low, f32 high)\n'
        '{\n'
        '    sndCreatePostEvent(state, 8, sub_GAME_7F053894(pos, low, high));\n'
        '#ifdef PORT\n'
        '    ascensionAudioWorldSubmitFromGame(state, pos, low, high);\n'
        '#endif\n'
        '}\n'
    )
    if 'ascensionAudioWorldSubmitFromGame(state, pos, low, high);' not in text:
        text = replace_once(text, event_old, event_new, "positional SFX publication")

    open_old = '            sndCreatePostEvent(arg0->openSoundState, 8, sp1C);\n'
    open_new = (
        '            sndCreatePostEvent(arg0->openSoundState, 8, sp1C);\n'
        '#ifdef PORT\n'
        '            ascensionAudioWorldSubmitFromGame(arg0->openSoundState, &arg0->prop->pos, 5000.0f, 6000.0f);\n'
        '#endif\n'
    )
    if 'ascensionAudioWorldSubmitFromGame(arg0->openSoundState' not in text:
        text = replace_once(text, open_old, open_new, "door open-loop XYZ refresh")

    close_old = '            sndCreatePostEvent(arg0->closeSoundState, 8, sp1C);\n'
    close_new = (
        '            sndCreatePostEvent(arg0->closeSoundState, 8, sp1C);\n'
        '#ifdef PORT\n'
        '            ascensionAudioWorldSubmitFromGame(arg0->closeSoundState, &arg0->prop->pos, 5000.0f, 6000.0f);\n'
        '#endif\n'
    )
    if 'ascensionAudioWorldSubmitFromGame(arg0->closeSoundState' not in text:
        text = replace_once(text, close_old, close_new, "door close-loop XYZ refresh")

    if text != original:
        PROPOBJ.write_text(text, encoding="utf-8", newline="\n")
        return True
    return False


def patch_world() -> bool:
    text = WORLD.read_text(encoding="utf-8")
    original = text

    # Do not spawn an independent 120 Hz pthread inside the GoldenEye PC port.
    # Submit() now computes/publishes the acoustic snapshot synchronously on
    # the game thread; the audio mixer remains a consumer only.
    sync_anchor = '#include "ascension_audio_world.h"\n\n'
    sync_block = (
        '#include "ascension_audio_world.h"\n\n'
        '#ifndef ASC_AUDIO_WORLD_TEST_SYNC\n'
        '#define ASC_AUDIO_WORLD_TEST_SYNC 1\n'
        '#endif\n\n'
    )
    if '#define ASC_AUDIO_WORLD_TEST_SYNC 1' not in text:
        text = replace_once(text, sync_anchor, sync_block, "synchronous acoustic runtime")

    warning_old = '        if (input != output) memcpy(output, input, (size_t)frame_count * sizeof(float)); return;\n'
    warning_new = (
        '        if (input != output) {\n'
        '            memcpy(output, input, (size_t)frame_count * sizeof(float));\n'
        '        }\n'
        '        return;\n'
    )
    if warning_old in text:
        text = text.replace(warning_old, warning_new, 1)

    finite_old = 'static int ascFinite(float v) { return isfinite(v) != 0; }\n'
    finite_new = 'static int ascFinite(float v) { return __builtin_isfinite(v) != 0; }\n'
    if finite_old in text:
        text = text.replace(finite_old, finite_new, 1)

    if text != original:
        WORLD.write_text(text, encoding="utf-8", newline="\n")
        return True
    return False


def patch_mixer() -> bool:
    text = MIXER.read_text(encoding="utf-8")
    original = text

    raw_process = '            if (!ascensionAudioSourceProcess(tap->stateAddr, mono,\n'
    world_process = '            if (!ascensionAudioWorldSourceProcess(tap->stateAddr, mono,\n'
    if world_process not in text:
        text = replace_once(text, raw_process, world_process, "mixer world-aware source process")

    raw_reset = '                ascensionAudioSourceReset(stateAddr);\n'
    world_reset = '                ascensionAudioWorldSourceReset(stateAddr);\n'
    if world_reset not in text:
        text = replace_once(text, raw_reset, world_reset, "mixer world-aware source reset")

    if text != original:
        MIXER.write_text(text, encoding="utf-8", newline="\n")
        return True
    return False


def main() -> int:
    try:
        changed_prop = patch_propobj()
        changed_world = patch_world()
        changed_mixer = patch_mixer()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    changed = []
    if changed_prop:
        changed.append("propobj.c")
    if changed_world:
        changed.append("ascension_audio_world.c")
    if changed_mixer:
        changed.append("mixer.c")
    if changed:
        print("Ascension Audio 3D integration applied: " + ", ".join(changed))
    else:
        print("Ascension Audio 3D integration already applied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
