#!/usr/bin/env python3
"""Idempotently wire real GoldenEye world positions into Ascension Audio 3D.

Only the PC build is affected: every inserted game hook is inside #ifdef PORT.
The script fails closed if the expected decomp seams change, so a future
upstream edit cannot silently apply the hook at the wrong location.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
PROPOBJ = ROOT / "src/game/propobj.c"
WORLD = ROOT / "port/src/ascension_audio_world.c"


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

    # Door loops update their volume every tick without re-entering
    # chrobjSndCreatePostEvent. Refresh their real XYZ while they are playing.
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


def patch_world_warning() -> bool:
    text = WORLD.read_text(encoding="utf-8")
    original = text
    old = '        if (input != output) memcpy(output, input, (size_t)frame_count * sizeof(float)); return;\n'
    new = (
        '        if (input != output) {\n'
        '            memcpy(output, input, (size_t)frame_count * sizeof(float));\n'
        '        }\n'
        '        return;\n'
    )
    if old in text:
        text = text.replace(old, new, 1)
    if text != original:
        WORLD.write_text(text, encoding="utf-8", newline="\n")
        return True
    return False


def main() -> int:
    try:
        changed_prop = patch_propobj()
        changed_world = patch_world_warning()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    changed = []
    if changed_prop:
        changed.append("propobj.c")
    if changed_world:
        changed.append("ascension_audio_world.c")
    if changed:
        print("Ascension Audio 3D integration applied: " + ", ".join(changed))
    else:
        print("Ascension Audio 3D integration already applied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
