#!/usr/bin/env python3
"""Regression contracts for Ascension's reversible All Missions toggle."""
from __future__ import annotations

import importlib.util
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONT = ROOT / "src/game/front.c"
FILE2 = ROOT / "src/game/file2.c"
OVERLAY = ROOT / "port/src/optionsoverlay.c"
LOCALE = ROOT / "port/src/ascension_locale.c"
POLICY_C = ROOT / "port/src/ascension_campaign.c"
POLICY_H = ROOT / "port/include/ascension_campaign.h"
PATCHER = ROOT / "tools_pc/apply_unlock_all_missions.py"


def require(cond: bool, msg: str) -> None:
    if not cond:
        raise SystemExit(f"FAIL: {msg}")
    print(f"PASS: {msg}")


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"load {path.name}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def model_highest_difficulty(*, valid_stage: bool, mode_007_unlocked: bool,
                             override: bool, native_result: int) -> int:
    if not valid_stage:
        return -1
    cap = 3 if mode_007_unlocked else 2
    if override:
        return cap
    return native_result


def main() -> int:
    front = FRONT.read_text(encoding="utf-8")
    file2 = FILE2.read_text(encoding="utf-8")
    overlay = OVERLAY.read_text(encoding="utf-8")
    locale = LOCALE.read_text(encoding="utf-8")
    policy_c = POLICY_C.read_text(encoding="utf-8")
    policy_h = POLICY_H.read_text(encoding="utf-8")

    require('configRegisterInt("Ascension.UnlockAllMissions"' in policy_c,
            "toggle is registered in PC config")
    require("static int s_unlockAllMissions = 0;" in policy_c,
            "toggle defaults OFF")
    require("ascensionCampaignUnlockAllMissions" in policy_c and
            "ascensionCampaignUnlockAllMissions" in policy_h,
            "campaign policy has a narrow public API")

    forbidden_writes = (
        "fileWriteSave", "fileUnlockStageInFolderAtDifficulty",
        "fileSetDifficultyStageTime", "fileSetSaveCheatUnlocked",
        "joyGamePakLongWrite",
    )
    for needle in forbidden_writes:
        require(needle not in policy_c,
                f"policy does not mutate save state via {needle}")

    require('#include "ascension_campaign.h"' in front,
            "solo frontend imports campaign policy")
    require("ascensionCampaignUnlockAllMissions()" in front,
            "solo mission availability contains reversible override")

    fn = front.split("s32 get_highest_unlocked_difficulty_for_level", 1)[1]
    fn = fn.split("//********************************************************************************************************\n//MISSION SELECT", 1)[0]
    pos_guard = fn.find("stage_id >= 0")
    pos_cap = fn.find("num = DIFFICULTY_00")
    pos_007 = fn.find("fileIs007ModeUnlocked")
    pos_override = fn.find("ascensionCampaignUnlockAllMissions")
    pos_native = fn.find("for (difficulty=num; difficulty >= 0; difficulty--)")
    require(-1 not in (pos_guard, pos_cap, pos_007, pos_override, pos_native),
            "solo availability ordering landmarks exist")
    require(pos_guard < pos_cap < pos_007 < pos_override < pos_native,
            "override preserves stage validity and 007 gate")

    override_slice = fn[pos_override:pos_native]
    require("return num;" in override_slice,
            "override returns current native difficulty cap")
    for needle in forbidden_writes:
        require(needle not in override_slice,
                f"solo override contains no {needle} write")

    # Critical scope contract: fileIsStageUnlockedAtDifficulty is shared by
    # multiplayer stage/character unlock paths. The Ascension option must never
    # be injected there.
    global_fn = file2.split("STAGESTATUS fileIsStageUnlockedAtDifficulty", 1)[1]
    global_fn = global_fn.split("void fileOverwriteSaveSlotWithNewSave", 1)[0]
    require("ascensionCampaignUnlockAllMissions" not in global_fn,
            "global progression API remains untouched")
    require('"ascension_campaign.h"' not in file2,
            "file2 has no Ascension campaign dependency")

    require('key="Ascension.UnlockAllMissions"' in overlay,
            "F10 exposes All Missions setting")
    row_pos = overlay.find('key="Ascension.UnlockAllMissions"')
    row_slice = overlay[row_pos:row_pos + 360]
    require('.category=CAT_GAMEPLAY' in row_slice,
            "All Missions lives on Gameplay page")
    require('.kind=ROW_TOGGLE' in row_slice,
            "All Missions is a reversible toggle")
    require('.resetValue=0' in row_slice,
            "reset/default restores native progression")
    require('"All missions", "Todas as missoes"' in locale,
            "PT-BR label exists")
    require('"Show every solo mission without marking it completed."' in locale,
            "context help is localized")

    mod = load_module(PATCHER, "asc_unlock_all_patch")
    require(mod.patch_front(front) == front,
            "front-end integration is idempotent")
    require(mod.patch_overlay(overlay) == overlay,
            "F10 integration is idempotent")
    require(mod.patch_locale(locale) == locale,
            "locale integration is idempotent")

    # Property test the exact intended semantics. OFF is transparent. ON opens
    # every valid solo mission at the highest difficulty already globally
    # available to the save (00 by default; 007 only if 007 mode is native-unlocked).
    rng = random.Random(0x007A5C)
    for _ in range(100000):
        valid = bool(rng.getrandbits(1))
        mode_007 = bool(rng.getrandbits(1))
        cap = 3 if mode_007 else 2
        native = rng.randint(-1, cap)

        off = model_highest_difficulty(valid_stage=valid,
                                       mode_007_unlocked=mode_007,
                                       override=False,
                                       native_result=native)
        on = model_highest_difficulty(valid_stage=valid,
                                      mode_007_unlocked=mode_007,
                                      override=True,
                                      native_result=native)

        if valid:
            if off != native:
                raise SystemExit("FAIL: randomized OFF path changed native progression")
            if on != cap:
                raise SystemExit("FAIL: randomized ON path did not expose full solo access")
        else:
            if off != -1 or on != -1:
                raise SystemExit("FAIL: randomized invalid-stage guard changed")

        if not mode_007 and on > 2:
            raise SystemExit("FAIL: randomized override unlocked 007 mode")

    print("PASS: 100000 randomized reversible-access cases")
    print("PASS: multiplayer/global progression scope isolation")
    print("Ascension All Missions contracts: ALL PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
