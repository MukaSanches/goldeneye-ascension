#!/usr/bin/env python3
"""Regression contract for Ascension Audio Remaster."""
from __future__ import annotations

import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIO = ROOT / "port" / "src" / "audio.c"
ENGINE = ROOT / "port" / "src" / "ascension_audio_remaster.c"
ABI = ROOT / "port" / "include" / "ascension_steam_audio.h"
PATCHER = ROOT / "tools_pc" / "apply_audio_remaster.py"
BOOTSTRAP = ROOT / "tools_pc" / "ensure_steam_audio.py"
BUNDLER = ROOT / "tools_pc" / "bundle-win.sh"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    audio = AUDIO.read_text(encoding="utf-8")
    engine = ENGINE.read_text(encoding="utf-8")
    abi = ABI.read_text(encoding="utf-8")
    patcher = PATCHER.read_text(encoding="utf-8")
    bootstrap = BOOTSTRAP.read_text(encoding="utf-8")
    bundler = BUNDLER.read_text(encoding="utf-8")

    require('#include "ascension_audio_remaster.h"' in audio, "audio.c must include remaster bridge")
    require("ascensionAudioRemasterInit(have.freq);" in audio, "remaster must initialize at real device rate")
    require("ascensionAudioRemasterShutdown();" in audio, "remaster must shut down")
    require("ascensionAudioRemasterProcess((const int16_t *)buf, len)" in audio, "final SDL queue must route through remaster")
    require("SDL_QueueAudio(dev, ascensionBuf" in audio, "remastered buffer must be queued")

    # Non-negotiable architectural invariants: do not replace Rare's mixer and
    # do not touch ROM/game audio assets from this feature.
    require("src/audi.c" not in patcher, "audio remaster patcher must stay in port/src/audio.c")
    require("src/snd.c" not in patcher, "audio remaster must not patch Rare's sound player")
    require("assets/music" not in engine and "assets/" not in engine, "remaster must not depend on game assets")

    # Steam Audio is not just named: the engine must construct and apply the
    # actual HRTF virtual-surround effect from the pinned ABI.
    for token in (
        "iplContextCreate",
        "iplHRTFCreate",
        "iplVirtualSurroundEffectCreate",
        "iplVirtualSurroundEffectApply",
        "ASC_STEAMAUDIO_VERSION_MAJOR 4u",
        "ASC_STEAMAUDIO_VERSION_MINOR 8u",
        "ASC_STEAMAUDIO_VERSION_PATCH 1u",
    ):
        require(token in abi or token in engine, f"missing Steam Audio contract token: {token}")

    require("0.68f * s_audio.wetL" in engine, "HRTF path must materially contribute to output")
    require("ASC_AUDIO_FRAME 128" in engine, "fixed low-latency DSP frame must remain 128 samples")
    require("GE_ASCENSION_AUDIO_BYPASS" in engine, "developer A/B bypass must remain available")
    require("mastering fallback active" in engine, "missing DLL must never make the game silent")

    # Supply-chain pinning: SDK binary uses GitHub's release SHA-256 and the
    # license comes from the exact v4.8.1 tag commit with Git blob validation.
    require(
        'SDK_SHA256 = "4a0aa5ec1176f38f0b0993a37c2259d9e86f27e22d5e24f83ec4c3cb9a1d5449"' in bootstrap,
        "Steam Audio SDK checksum must remain pinned",
    )
    require('VALVE_TAG_COMMIT = "0da18255cca520771f363ee01f100572b39a308e"' in bootstrap,
            "Steam Audio license source commit must remain pinned")
    require('LICENSE_GIT_BLOB_SHA1 = "d645695673349e3947e8e5ae42332d0ac3164cd7"' in bootstrap,
            "Steam Audio license blob must remain verified")
    require("steamaudio_4.8.1.zip" in bootstrap, "Steam Audio SDK version must remain pinned")

    # Distribution must remain zero-install: dynamically loaded phonon.dll and
    # its license are copied into every Windows bundle automatically.
    require('cp build-pc/phonon.dll "$OUT/phonon.dll"' in bundler,
            "Windows bundle must include Steam Audio runtime")
    require("LICENSE-Steam-Audio-Apache-2.0.md" in bundler,
            "Windows bundle must include Steam Audio license")
    require("unresolved runtime dependencies" in bundler,
            "Windows bundler must reject incomplete Steam Audio dependency closure")

    # Mathematical sanity of the transparent peak curve used by the C engine:
    # monotonic, symmetric, sub-clipping, and not a destructive compressor.
    def soft_peak(x: float) -> float:
        y = 1.07 * x
        y = y / (1.0 + 0.085 * abs(y))
        return max(-0.985, min(0.985, y))

    xs = [i / 1000.0 for i in range(1001)]
    ys = [soft_peak(x) for x in xs]
    require(all(ys[i] <= ys[i + 1] for i in range(len(ys) - 1)), "soft peak curve must be monotonic")
    require(max(ys) <= 0.985 + 1e-9, "soft peak curve must remain below full scale")
    require(abs(soft_peak(0.25) + soft_peak(-0.25)) < 1e-9, "soft peak curve must remain symmetric")
    require(soft_peak(0.25) > 0.25, "quiet/mid-level signal should receive subtle make-up gain")
    require(math.isfinite(soft_peak(1.0)), "soft peak curve must stay finite")

    print("Ascension Audio Remaster regression contract: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
