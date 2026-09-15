#!/usr/bin/env python3
"""Regression contract for Ascension Audio Remaster."""
from __future__ import annotations

import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIO = ROOT / "port" / "src" / "audio.c"
ENGINE = ROOT / "port" / "src" / "ascension_audio_remaster.c"
MIXER = ROOT / "port" / "src" / "mixer.c"
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
    mixer = MIXER.read_text(encoding="utf-8")
    abi = ABI.read_text(encoding="utf-8")
    patcher = PATCHER.read_text(encoding="utf-8")
    bootstrap = BOOTSTRAP.read_text(encoding="utf-8")
    bundler = BUNDLER.read_text(encoding="utf-8")

    require('#include "ascension_audio_remaster.h"' in audio, "audio.c must include remaster bridge")
    require("ascensionAudioRemasterInit(have.freq);" in audio, "remaster must initialize at real device rate")
    require("ascensionAudioRemasterShutdown();" in audio, "remaster must shut down")
    require("ascensionAudioRemasterProcess((const int16_t *)buf, len)" in audio, "final SDL queue must route through remaster")
    require("SDL_QueueAudio(dev, ascensionBuf" in audio, "remastered buffer must be queued")

    # Non-negotiable architectural invariants: do not patch Rare's gameplay or
    # depend on ROM/game audio assets for Ascension's DSP layer.
    require("src/audi.c" not in patcher, "audio remaster patcher must stay in port/src/audio.c")
    require("src/snd.c" not in patcher, "audio remaster must not patch Rare's sound player")
    require("assets/music" not in engine and "assets/" not in engine, "remaster must not depend on game assets")

    # Steam Audio 4.8.1 base/fallback path.
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

    require("0.68f * s_audio.wetL" in engine, "post-mix fallback HRTF must materially contribute")
    require("ASC_AUDIO_FRAME 128" in engine, "post-mix fallback frame must remain 128 samples")
    require("GE_ASCENSION_AUDIO_BYPASS" in engine, "developer A/B bypass must remain available")
    require("mastering fallback active" in engine, "missing DLL must never make the game silent")

    # Source-object path: this is the new preferred renderer. One binaural
    # effect is maintained per physical voice and all objects are pre-created,
    # so the real-time mixer never allocates Steam Audio state.
    for token in (
        "IPLBinauralEffect",
        "IPLBinauralEffectParams",
        "IPL_HRTFINTERPOLATION_BILINEAR",
        "iplBinauralEffectCreate",
        "iplBinauralEffectReset",
        "iplBinauralEffectApply",
    ):
        require(token in abi.replace("ASC_", "") or token.replace("IPL_", "ASC_IPL_") in abi or token in engine,
                f"missing per-source Steam Audio contract token: {token}")

    require("ASC_SOURCE_EFFECTS 64" in engine, "source renderer must keep an independent effect pool")
    require("ASCENSION_AUDIO_SOURCE_FRAME" in engine, "source renderer must use the low-latency frame contract")
    require("ASC_IPL_HRTFINTERPOLATION_BILINEAR" in engine, "moving sources must use high-quality HRTF interpolation")
    require("GE_ASCENSION_SOURCE_HRTF" in engine, "source HRTF must have an emergency A/B fallback switch")
    require("ascensionAudioSourceProcess" in engine, "source renderer entry point must exist")
    require("isfinite(outLeft[i])" in engine and "isfinite(outRight[i])" in engine,
            "source frame must be validated before replacing legacy audio")

    # Mixer safety/science contracts. GoldenEye's legacy contribution is mixed
    # first. The HRTF stage computes a delta only after successful processing.
    # Horizontal azimuth is recovered from the game's equal-power L/R gains:
    # alpha=atan2(R,L), azimuth=2*alpha-pi/2, +X right / -Z forward.
    require('#include "ascension_audio_remaster.h"' in mixer, "mixer must expose source HRTF bridge")
    require("ascensionAudioSourceHrtfActive()" in mixer, "mixer must gate optional source HRTF")
    require("atan2f(sumR, sumL)" in mixer, "mixer must invert equal-power pan mathematically")
    require("sqrtf(gl * gl + gr * gr)" in mixer, "mixer must recover pre-pan source magnitude")
    require("dirX = sinf(azimuth)" in mixer and "dirZ = -cosf(azimuth)" in mixer,
            "mixer must map azimuth into Steam Audio coordinates")
    require("ascensionAudioSourceProcess" in mixer, "mixer must render each source independently")
    require("mixL[idx] += ascFloatContribution(hrtfL[k]) - legacyL[k]" in mixer,
            "successful HRTF must replace only the original direct contribution")
    require("dry[0][i] = mixerClamp16" in mixer and "dry[1][i] = mixerClamp16" in mixer,
            "legacy dry mix must always be rendered before optional replacement")

    # Supply-chain pinning.
    require(
        'SDK_SHA256 = "4a0aa5ec1176f38f0b0993a37c2259d9e86f27e22d5e24f83ec4c3cb9a1d5449"' in bootstrap,
        "Steam Audio SDK checksum must remain pinned",
    )
    require('VALVE_TAG_COMMIT = "0da18255cca520771f363ee01f100572b39a308e"' in bootstrap,
            "Steam Audio license source commit must remain pinned")
    require('LICENSE_GIT_BLOB_SHA1 = "d645695673349e3947e8e5ae42332d0ac3164cd7"' in bootstrap,
            "Steam Audio license blob must remain verified")
    require("steamaudio_4.8.1.zip" in bootstrap, "Steam Audio SDK version must remain pinned")

    # Distribution remains zero-install.
    require('cp build-pc/phonon.dll "$OUT/phonon.dll"' in bundler,
            "Windows bundle must include Steam Audio runtime")
    require("LICENSE-Steam-Audio-Apache-2.0.md" in bundler,
            "Windows bundle must include Steam Audio license")
    require("unresolved runtime dependencies" in bundler,
            "Windows bundler must reject incomplete Steam Audio dependency closure")

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

    print("Ascension Audio Remaster + per-source HRTF regression contract: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
