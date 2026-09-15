#!/usr/bin/env python3
"""Regression contracts for the final Q Watch runtime hotfix."""
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OPTIONS = ROOT / "src/game/options.c"
VIDEO = ROOT / "port/src/video.c"
HEADER = ROOT / "port/include/ascension_watch.h"
PATCHER = ROOT / "tools_pc/apply_watch_runtime_fix.py"


def require(cond: bool, msg: str) -> None:
    if not cond:
        raise SystemExit(f"FAIL: {msg}")
    print(f"PASS: {msg}")


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location("asc_watch_runtime_fix", path)
    require(spec is not None and spec.loader is not None, "load watch runtime patcher")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def function_block(text: str, signature: str, end_marker: str) -> str:
    start = text.find(signature)
    require(start >= 0, f"function exists: {signature}")
    end = text.find(end_marker, start)
    require(end > start, f"function boundary exists: {signature}")
    return text[start:end]


def main() -> int:
    opt = OPTIONS.read_text(encoding="utf-8")
    vid = VIDEO.read_text(encoding="utf-8")
    hdr = HEADER.read_text(encoding="utf-8")

    require("int ascensionWatchIsActive(void)" in opt,
            "game layer exposes native Q Watch activity")
    active = function_block(opt, "int ascensionWatchIsActive(void)",
                            "void ascensionWatchReturnToMainMenu(void)")
    require("WATCH_ANIMATION_0x0" in active,
            "watch activity is keyed to GoldenEye's real closed state")
    require("g_CurrentPlayer != NULL" in active,
            "watch state bridge is null-safe")
    require("int ascensionWatchIsActive(void);" in hdr,
            "PORT bridge declares watch-state query")

    require('#include "ascension_watch.h"' in vid,
            "SDL video shell can query native watch state")
    esc = function_block(vid,
                         "ev.key.keysym.sym == SDLK_ESCAPE && !ev.key.repeat",
                         "case SDL_TEXTINPUT")
    require("ascensionWatchIsActive()" in esc,
            "Escape checks Q Watch before releasing capture")
    require("inputReleaseCapture();" in esc,
            "Escape still releases capture outside overlays/watch")
    require(esc.find("ascensionWatchIsActive()") < esc.find("inputReleaseCapture();"),
            "watch capture guard executes before release")

    ret = function_block(opt, "void ascensionWatchReturnToMainMenu(void)",
                         "#endif\n\n// initial pause screen")
    require("getPlayerCount() != 1" in ret,
            "quick return remains solo-only")
    require("set_missionstate(MISSION_STATE_0)" in ret,
            "quick return cleanly stops the active mission")
    require("frontChangeMenu(MENU_MISSION_SELECT, FALSE);" in ret,
            "quick return queues GoldenEye's native mission selector")
    require("bossRunTitleStage();" in ret,
            "quick return requests native frontend stage")
    require("mission_failed_or_aborted = FALSE;" in ret,
            "quick return is not classified as mission failure/abort")
    require("watchAbortMissionToFrontEnd();" not in ret,
            "quick return no longer reuses stock Abort Mission")
    require("deleteCurrentSelectedFolder" not in ret,
            "quick return cannot clear the selected save folder")
    require("sysRestart" not in ret,
            "quick return cannot restart the process/game")

    # Preserve the original Q Watch Abort Mission behavior separately. The
    # convenience button must not silently rewrite a stock GoldenEye action.
    require("static void watchAbortMissionToFrontEnd(void)" in opt,
            "stock Abort Mission helper remains isolated")

    mod = load_module(PATCHER)
    require(mod.patch_options(opt) == opt, "runtime options patch is idempotent")
    require(mod.patch_video(vid) == vid, "runtime video patch is idempotent")
    require(mod.patch_header(hdr) == hdr, "runtime header patch is idempotent")

    print("Ascension Watch Runtime Fix contracts: ALL PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
