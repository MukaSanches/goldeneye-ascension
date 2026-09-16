#!/usr/bin/env python3
"""Install Ascension Audio Remaster hooks into port/src/audio.c.

Fail-closed and idempotent: this patcher only changes the PC SDL handoff and
never edits Rare/libaudio game sources.
"""
from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "port" / "src" / "audio.c"
MARKER = '#include "ascension_audio_remaster.h"'


def patched_text(src: str) -> str:
    if MARKER in src:
        return src

    include_anchor = '#include "audio.h"\n'
    init_anchor = '    SDL_PauseAudioDevice(dev, 0);\n    sysLogPrintf(LOG_INFO, "audioInit: opened SDL audio device at %d Hz", have.freq);'
    destroy_anchor = 'void audioDestroy(void)\n{\n    if (dev) { SDL_CloseAudioDevice(dev); dev = 0; }\n}'
    queue_anchor = '            SDL_QueueAudio(dev, buf, len);\n            lastBufferBytes = len;'

    missing = [
        name
        for name, anchor in (
            ("include", include_anchor),
            ("init", init_anchor),
            ("destroy", destroy_anchor),
            ("queue", queue_anchor),
        )
        if anchor not in src
    ]
    if missing:
        raise SystemExit(
            "audio remaster patch refused: unexpected audio.c shape; missing anchors: "
            + ", ".join(missing)
        )

    src = src.replace(include_anchor, include_anchor + MARKER + '\n', 1)
    src = src.replace(
        init_anchor,
        '    SDL_PauseAudioDevice(dev, 0);\n'
        '    ascensionAudioRemasterInit(have.freq);\n'
        '    sysLogPrintf(LOG_INFO, "audioInit: opened SDL audio device at %d Hz", have.freq);',
        1,
    )
    src = src.replace(
        destroy_anchor,
        'void audioDestroy(void)\n'
        '{\n'
        '    ascensionAudioRemasterShutdown();\n'
        '    if (dev) { SDL_CloseAudioDevice(dev); dev = 0; }\n'
        '}',
        1,
    )
    src = src.replace(
        queue_anchor,
        '            const int16_t *ascensionBuf = ascensionAudioRemasterProcess((const int16_t *)buf, len);\n'
        '            SDL_QueueAudio(dev, ascensionBuf ? ascensionBuf : (const int16_t *)buf, len);\n'
        '            lastBufferBytes = len;',
        1,
    )
    return src


def validate(src: str) -> None:
    required = (
        MARKER,
        'ascensionAudioRemasterInit(have.freq);',
        'ascensionAudioRemasterShutdown();',
        'ascensionAudioRemasterProcess((const int16_t *)buf, len)',
    )
    missing = [token for token in required if token not in src]
    if missing:
        raise SystemExit("audio remaster contract missing: " + ", ".join(missing))
    if src.count(MARKER) != 1:
        raise SystemExit("audio remaster include duplicated")
    if src.count('ascensionAudioRemasterProcess((const int16_t *)buf, len)') != 1:
        raise SystemExit("audio remaster queue hook duplicated")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    src = TARGET.read_text(encoding="utf-8")
    if args.check:
        validate(src)
        print("Ascension Audio Remaster hook contract: PASS")
        return 0

    out = patched_text(src)
    validate(out)
    if out != src:
        TARGET.write_text(out, encoding="utf-8")
        print("Installed Ascension Audio Remaster hooks")
    else:
        print("Ascension Audio Remaster hooks already installed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
