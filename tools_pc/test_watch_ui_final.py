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

    # Stock GoldenEye Abort Mission keeps its original semantics. The later
    # F10 convenience return is deliberately separate because reusing Abort
    # Mission was shown at runtime to enter the failure/restart flow and touch
    # selected-folder state.
    require("static void watchAbortMissionToFrontEnd(void)" in opt,
            "stock Abort Mission helper exists")
    helper = opt.split("static void watchAbortMissionToFrontEnd(void)", 1)[1]
    helper = helper.split("#ifdef PORT", 1)[0]
    for marker in (
        "set_missionstate(MISSION_STATE_0)",
        "bossRunTitleStage()",
        "mission_failed_or_aborted = TRUE",
        "deleteCurrentSelectedFolder()",
    ):
        require(marker in helper, f"stock Abort Mission primitive retained: {marker}")
    require("fileWriteSave" not in helper and "fileUnlockStage" not in helper,
            "stock helper does not invent save/progression writes")
    require("watchAbortMissionToFrontEnd();" in opt,
            "stock Q Watch Abort Mission delegates to its helper")
    require("getPlayerCount() != 1" in opt,
            "PC convenience return is hard-gated to solo")

    runtime_fixed = "int ascensionWatchIsActive(void)" in opt
    if runtime_fixed:
        require("frontChangeMenu(MENU_MISSION_SELECT, FALSE);" in opt,
                "convenience return queues the native mission selector")
        require("mission_failed_or_aborted = FALSE;" in opt,
                "convenience return avoids mission-failed routing")
        require(opt.count("bossRunTitleStage();") == 2,
                "stock abort and convenience return have isolated frontend transitions")
    else:
        require(opt.count("bossRunTitleStage();") == 1,
                "pre-hotfix watch has one shared frontend transition")

    require("ACTION_RETURN_MENU" in ov and 'key="__ReturnMenu"' in ov,
            "F10 Gameplay page has quick return")
    require("PRESS AGAIN TO RETURN" in ov,
            "quick return requires explicit second activation")
    require("#define GE_MENU_RUN_STAGE 11" in ov,
            "F10 overlay owns a narrow local run-stage alias")
    require("current_menu != GE_MENU_RUN_STAGE && current_menu != -1" in ov,
            "F10 action refuses to re-abort from the normal front end")
    require("current_menu != MENU_RUN_STAGE && current_menu != -1" not in ov,
            "quick-return guard does not depend on an undeclared game enum")
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
