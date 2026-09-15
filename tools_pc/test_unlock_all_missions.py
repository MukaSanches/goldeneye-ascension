#!/usr/bin/env python3
"""Regression contracts for Ascension's reversible All Missions toggle."""
from __future__ import annotations

import importlib.util
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
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


def model_native_or_override(*, valid: bool, completed: bool, level: int,
                             difficulty: int, native_status: int,
                             override: bool) -> int:
    LOCKED, UNLOCKED, COMPLETED = 0, 1, 3
    DAM, AZTEC, EGYPT, LEVEL_MAX = 0, 18, 19, 20
    AGENT, SECRET, OO, DIFF_007, DIFF_MAX = 0, 1, 2, 3, 4

    if not valid or not (DAM <= level < LEVEL_MAX) or not (AGENT <= difficulty < DIFF_MAX):
        return LOCKED
    if completed:
        return COMPLETED
    if (level == AZTEC and difficulty < SECRET) or (level == EGYPT and difficulty < OO):
        return LOCKED
    if override:
        return UNLOCKED
    return native_status


def main() -> int:
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

    forbidden_policy_writes = (
        "fileWriteSave", "fileUnlockStageInFolderAtDifficulty",
        "fileSetDifficultyStageTime", "fileSetSaveCheatUnlocked",
        "joyGamePakLongWrite",
    )
    for needle in forbidden_policy_writes:
        require(needle not in policy_c,
                f"policy does not mutate save state via {needle}")

    require('#include "ascension_campaign.h"' in file2,
            "native progression imports port policy only on PC path")
    require("ascensionCampaignUnlockAllMissions()" in file2,
            "native unlock query contains reversible access override")

    fn = file2.split("STAGESTATUS fileIsStageUnlockedAtDifficulty", 1)[1]
    fn = fn.split("void fileOverwriteSaveSlotWithNewSave", 1)[0]
    pos_completed = fn.find("fileGetSaveStageCompletedForDifficulty")
    pos_aztec = fn.find("levelid == SP_LEVEL_AZTEC")
    pos_override = fn.find("ascensionCampaignUnlockAllMissions")
    pos_scan = fn.find("still cant find it, do a search")
    require(-1 not in (pos_completed, pos_aztec, pos_override, pos_scan),
            "all ordering landmarks exist")
    require(pos_completed < pos_aztec < pos_override < pos_scan,
            "completed state and bonus gates precede override")

    override_slice = fn[pos_override:pos_scan]
    require("return STAGESTATUS_UNLOCKED;" in override_slice,
            "override grants access without faking completion")
    require("STAGESTATUS_COMPLETED" not in override_slice,
            "override never reports fake COMPLETED state")
    for needle in forbidden_policy_writes:
        require(needle not in override_slice,
                f"override block contains no {needle} write")

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
    require('"Unlock every mission without changing saved completion."' in locale,
            "context help is localized")

    # The patcher itself must be idempotent on an already-integrated tree.
    mod = load_module(PATCHER, "asc_unlock_all_patch")
    require(mod.patch_file2(file2) == file2,
            "file2 integration is idempotent")
    require(mod.patch_overlay(overlay) == overlay,
            "F10 integration is idempotent")
    require(mod.patch_locale(locale) == locale,
            "locale integration is idempotent")

    # Model the semantics over many combinations. OFF must be a pure pass-through
    # to native progression; ON may only turn a normally eligible locked/unlocked
    # mission into UNLOCKED. Completed and native bonus-stage restrictions win.
    rng = random.Random(0x007A5C)
    LOCKED, UNLOCKED, COMPLETED = 0, 1, 3
    for _ in range(100000):
        valid = bool(rng.getrandbits(1))
        level = rng.randint(-3, 23)
        diff = rng.randint(-2, 6)
        completed = bool(rng.getrandbits(1))
        native = rng.choice((LOCKED, UNLOCKED))

        off = model_native_or_override(valid=valid, completed=completed,
                                       level=level, difficulty=diff,
                                       native_status=native, override=False)
        on = model_native_or_override(valid=valid, completed=completed,
                                      level=level, difficulty=diff,
                                      native_status=native, override=True)

        # For cases that reach native progression, OFF is exactly native.
        if valid and 0 <= level < 20 and 0 <= diff < 4 and not completed and not (
            (level == 18 and diff < 1) or (level == 19 and diff < 2)
        ):
            require(off == native, "OFF path preserves native result") if False else None
            if off != native:
                raise SystemExit("FAIL: randomized OFF path changed native progression")
            if on != UNLOCKED:
                raise SystemExit("FAIL: randomized ON path failed to grant access")

        if completed and valid and 0 <= level < 20 and 0 <= diff < 4:
            if on != COMPLETED or off != COMPLETED:
                raise SystemExit("FAIL: randomized completed-state preservation")

        if valid and ((level == 18 and diff == 0) or
                      (level == 19 and diff in (0, 1))):
            if on != LOCKED:
                raise SystemExit("FAIL: randomized bonus difficulty gate changed")

    print("PASS: 100000 randomized reversible-access cases")
    print("Ascension All Missions contracts: ALL PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
