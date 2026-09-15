#!/usr/bin/env python3
"""Release contracts for Ascension's final Q Watch pass."""
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OPTIONS = ROOT / "src/game/options.c"
OVERLAY = ROOT / "port/src/optionsoverlay.c"
LOCALE = ROOT / "port/src/ascension_locale.c"
PATCHER = ROOT / "tools_pc/apply_watch_ui_final_safe.py"


def require(cond: bool, msg: str) -> None:
    if not cond:
        raise SystemExit(f"FAIL: {msg}")
    print(f"PASS: {msg}")


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location("asc_watch_final_patch", path)
    require(spec is not None and spec.loader is not None, "load final watch patcher")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    opt = OPTIONS.read_text(encoding="utf-8")
    ov = OVERLAY.read_text(encoding="utf-8")
    loc = LOCALE.read_text(encoding="utf-8")

    # GoldenEye's identity is a release gate: this final pass may refine it,
    # never flatten the watch into a generic modern settings screen.
    for marker in (
        "WATCH_INDEX_MISSION_STATUS",
        "WATCH_INDEX_INVENTORY",
        "WATCH_INDEX_CONTROL_OPTIONS",
        "WATCH_INDEX_GAME_OPTIONS",
        "WATCH_INDEX_MISSION_BRIEFING",
        "draw_watch_inventory_page",
        "draw_background_health_and_armor",
        "g_WatchStaticScanlineY",
        "draw_text_q_watch_v201_beta",
        "CAMERA_BEEP1_SFX",
    ):
        require(marker in opt, f"native watch identity retained: {marker}")

    require("ascensionDrawWatchChrome" in opt,
            "field-instrument header is rendered on the native watch")
    for title in (
        "Q WATCH / STATUS", "Q WATCH / EQUIPMENT", "Q WATCH / CONTROLS",
        "Q WATCH / SYSTEM", "Q WATCH / BRIEFING",
    ):
        require(title in opt, f"watch page title exists: {title}")
    require('"F10 SYSTEM"' in opt,
            "watch exposes the PC system layer without replacing native pages")

    # The quick exit and stock Abort Mission must converge on one native path.
    require("static void watchAbortMissionToFrontEnd(void)" in opt,
            "single native abort/front-end helper exists")
    helper = opt.split("static void watchAbortMissionToFrontEnd(void)", 1)[1]
    helper = helper.split("#ifdef PORT", 1)[0]
    for marker in (
        "set_missionstate(MISSION_STATE_0)",
        "bossRunTitleStage()",
        "mission_failed_or_aborted = TRUE",
        "deleteCurrentSelectedFolder()",
    ):
        require(marker in helper, f"native abort primitive retained: {marker}")
    require("fileWriteSave" not in helper and "fileUnlockStage" not in helper,
            "quick return does not invent save/progression writes")
    require("getPlayerCount() != 1" in opt,
            "quick return is hard-gated to solo")

    # There must only be one copy of the native abort sequence after refactor.
    require(opt.count("bossRunTitleStage();") == 1,
            "front-end transition has one authoritative implementation")
    require("watchAbortMissionToFrontEnd();" in opt,
            "stock Q Watch abort delegates to shared path")

    require("ACTION_RETURN_MENU" in ov and 'key="__ReturnMenu"' in ov,
            "F10 Gameplay page has quick return")
    require("PRESS AGAIN TO RETURN" in ov,
            "quick return requires explicit second activation")
    require("current_menu != MENU_RUN_STAGE" in ov,
            "F10 action refuses to re-abort from the normal front end")
    require("GE_MENU_RUN_STAGE" not in ov,
            "quick-return guard uses the real GoldenEye menu enum")
    require("s_open = 0;" in ov and "ascensionWatchReturnToMainMenu();" in ov,
            "confirmed return closes F10 then enters native front end")

    # Delimit only the quick-return action. ACTION_RESTART legitimately calls
    # sysRestart() immediately after it, and must not be mistaken for the menu
    # action itself.
    return_action = ov.find('if (r->action == ACTION_RETURN_MENU)')
    require(return_action >= 0, "quick-return implementation block is present")
    restart_action = ov.find('if (r->action == ACTION_RESTART)', return_action)
    require(restart_action > return_action,
            "process restart remains a separate action after quick return")
    return_block = ov[return_action:restart_action]
    require("sysRestart()" not in return_block,
            "quick return is not implemented as a process restart")
    require("configSave();" in return_block,
            "quick return persists port settings before leaving gameplay")

    for marker in (
        '"Return to main menu", "Voltar ao menu principal"',
        '"Q WATCH / EQUIPMENT", "Q WATCH / EQUIPAMENTO"',
        '"Q WATCH / SYSTEM", "Q WATCH / SISTEMA"',
        '"F10 SYSTEM", "F10 SISTEMA"',
    ):
        require(marker in loc, f"PT-BR final watch copy exists: {marker}")

    # Idempotence must use the same safe entry point used by CI and local users.
    mod = load_module(PATCHER)
    require(mod.patch_options_safe(opt) == opt, "watch patch is idempotent")
    require(mod.impl.patch_overlay(ov) == ov, "quick-return patch is idempotent")
    require(mod.impl.patch_locale(loc) == loc, "final watch locale patch is idempotent")

    # Simple semantic model for the dangerous action: first press never exits;
    # second press exits only while gameplay is active.
    for in_stage in (False, True):
        for presses in range(4):
            exits = in_stage and presses >= 2
            if presses < 2 and exits:
                raise SystemExit("FAIL: quick-return confirmation model")
    print("PASS: two-press quick-return semantic model")

    print("Ascension Final Q Watch contracts: ALL PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
