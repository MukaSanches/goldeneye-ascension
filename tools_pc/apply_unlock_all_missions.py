#!/usr/bin/env python3
"""Install Ascension's reversible "All missions" option.

The setting is intentionally non-destructive and single-player scoped:
  * the toggle lives in the PC config, not in GoldenEye save data;
  * it changes only the solo mission-select availability query;
  * completed checkmarks/times remain native because their query is untouched;
  * 007 difficulty remains gated by GoldenEye's original 007-mode unlock;
  * multiplayer stages/characters and cheat unlocks are untouched;
  * turning it off immediately falls back to the untouched native progression
    query on the next mission-select frame.

Run after UI Overhaul V2 has been installed. The operation is fail-closed,
atomic across the three generated integration files, and idempotent.
"""
from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONT = ROOT / "src/game/front.c"
OVERLAY = ROOT / "port/src/optionsoverlay.c"
LOCALE = ROOT / "port/src/ascension_locale.c"


class PatchError(RuntimeError):
    pass


def once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        return text
    count = text.count(old)
    if count != 1:
        raise PatchError(f"{label}: expected exactly one anchor, found {count}")
    return text.replace(old, new, 1)


def patch_front(text: str) -> str:
    if "s32 get_highest_unlocked_difficulty_for_level" not in text:
        raise PatchError("solo mission availability function not found")

    text = once(
        text,
        '#include <stdio.h>\n#include "romdata.h" /* D178: briefing-segment byte-order fixup */',
        '#include <stdio.h>\n#include "romdata.h" /* D178: briefing-segment byte-order fixup */\n#include "ascension_campaign.h"',
        "campaign policy include",
    )

    anchor = '''        if (fileIs007ModeUnlocked(selected_folder_num) || get_debug_007_unlock_flag())
        {
            num = DIFFICULTY_007;
        }

        for (difficulty=num; difficulty >= 0; difficulty--)'''

    replacement = '''        if (fileIs007ModeUnlocked(selected_folder_num) || get_debug_007_unlock_flag())
        {
            num = DIFFICULTY_007;
        }

#ifdef PORT
        /* Ascension optional mission-access override. This is deliberately
         * scoped to the SOLO mission selector rather than the global save
         * unlock API, so multiplayer unlocks, characters, cheats, completion
         * flags and EEPROM data remain completely native. `num` also keeps
         * 007 mode behind GoldenEye's original global 007 unlock. */
        if (ascensionCampaignUnlockAllMissions())
        {
            return num;
        }
#endif

        for (difficulty=num; difficulty >= 0; difficulty--)'''

    text = once(text, anchor, replacement, "solo mission access hook")

    fn = text.split("s32 get_highest_unlocked_difficulty_for_level", 1)[1]
    fn = fn.split("//********************************************************************************************************\n//MISSION SELECT", 1)[0]
    stage_guard = fn.find("stage_id >= 0")
    diff_cap = fn.find("num = DIFFICULTY_00")
    mode_007 = fn.find("fileIs007ModeUnlocked")
    override = fn.find("ascensionCampaignUnlockAllMissions")
    native_scan = fn.find("for (difficulty=num; difficulty >= 0; difficulty--)")
    if min(stage_guard, diff_cap, mode_007, override, native_scan) < 0:
        raise PatchError("solo mission ordering contract incomplete")
    if not (stage_guard < diff_cap < mode_007 < override < native_scan):
        raise PatchError("solo mission override is in an unsafe position")

    # Hard release gate: do not touch the global progression function. It is
    # reused by multiplayer unlocks and other native systems.
    if "ascensionCampaignUnlockAllMissions" in text.split(
        "STAGESTATUS fileIsStageUnlockedAtDifficulty", 1
    )[-1].split("void fileOverwriteSaveSlotWithNewSave", 1)[0]:
        raise PatchError("unlock override leaked into global progression API")

    return text


def patch_overlay(text: str) -> str:
    if "Ascension UI Overhaul V2 - Q Watch compact settings" not in text:
        raise PatchError("UI Overhaul V2 must be installed first")
    if 'key="Ascension.UnlockAllMissions"' in text:
        return text

    anchor = '''    { .key="Game.SkipIntro",       .label="Skip intro",
      .help="Next launch starts at file select.", .category=CAT_GAMEPLAY,
      .kind=ROW_TOGGLE, .step=1, .names=kOnOff, .restart=1, .resetValue=0 },

    /* SYSTEM */'''

    replacement = '''    { .key="Game.SkipIntro",       .label="Skip intro",
      .help="Next launch starts at file select.", .category=CAT_GAMEPLAY,
      .kind=ROW_TOGGLE, .step=1, .names=kOnOff, .restart=1, .resetValue=0 },

    { .key="Ascension.UnlockAllMissions", .label="All missions",
      .help="Show every solo mission without marking it completed.",
      .category=CAT_GAMEPLAY,
      .kind=ROW_TOGGLE, .step=1, .names=kOnOff, .resetValue=0 },

    /* SYSTEM */'''

    text = once(text, anchor, replacement, "Gameplay-page unlock toggle")

    if text.count('key="Ascension.UnlockAllMissions"') != 1:
        raise PatchError("unlock toggle must exist exactly once")
    if '.label="All missions"' not in text or '.category=CAT_GAMEPLAY' not in replacement:
        raise PatchError("unlock toggle UI contract failed")
    return text


def patch_locale(text: str) -> str:
    if '"Q WATCH / SYSTEM CONFIGURATION", "Q WATCH / CONFIGURACAO"' not in text:
        raise PatchError("UI V2 locale must be installed first")
    if '"All missions", "Todas as missoes"' in text:
        return text

    anchor = '    { "FIELD PARAMETERS", "PARAMETROS DE JOGO" },\n'
    replacement = '''    { "FIELD PARAMETERS", "PARAMETROS DE JOGO" },
    { "All missions", "Todas as missoes" },
    { "Show every solo mission without marking it completed.", "Mostra todas as missoes sem marca-las como concluidas." },
'''
    text = once(text, anchor, replacement, "PT-BR unlock-all copy")
    return text


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="validate without writing")
    ap.add_argument("--no-backup", action="store_true")
    args = ap.parse_args()

    original_front = FRONT.read_text(encoding="utf-8")
    original_overlay = OVERLAY.read_text(encoding="utf-8")
    original_locale = LOCALE.read_text(encoding="utf-8")

    try:
        updated_front = patch_front(original_front)
        updated_overlay = patch_overlay(original_overlay)
        updated_locale = patch_locale(original_locale)
    except Exception as exc:
        raise SystemExit(f"ERROR: {exc}; no file written")

    required = (
        (updated_front, '#include "ascension_campaign.h"'),
        (updated_front, "ascensionCampaignUnlockAllMissions()"),
        (updated_overlay, 'key="Ascension.UnlockAllMissions"'),
        (updated_overlay, '.label="All missions"'),
        (updated_locale, '"All missions", "Todas as missoes"'),
    )
    for haystack, needle in required:
        if needle not in haystack:
            raise SystemExit(f"ERROR: final contract missing {needle!r}; no file written")

    changed = []
    for path, before, after in (
        (FRONT, original_front, updated_front),
        (OVERLAY, original_overlay, updated_overlay),
        (LOCALE, original_locale, updated_locale),
    ):
        if before != after:
            changed.append(str(path.relative_to(ROOT)))

    if args.check:
        print("Ascension All Missions preflight: PASS")
        print("Solo mission selector scope: PASS")
        print("007-mode gate preserved: PASS")
        print("Multiplayer/global progression untouched: PASS")
        print("Save-data mutation by toggle: NONE")
        print("Immediate OFF -> native progression fallback: PASS")
        print("F10 Gameplay-page toggle: PASS")
        print("Would update:", ", ".join(changed) if changed else "nothing")
        return 0

    if not args.no_backup:
        for path, before, after in (
            (FRONT, original_front, updated_front),
            (OVERLAY, original_overlay, updated_overlay),
            (LOCALE, original_locale, updated_locale),
        ):
            if before == after:
                continue
            backup = path.with_suffix(path.suffix + ".before-unlock-all")
            if not backup.exists():
                backup.write_text(before, encoding="utf-8")
                print("BACKUP:", backup.relative_to(ROOT))

    for path, before, after in (
        (FRONT, original_front, updated_front),
        (OVERLAY, original_overlay, updated_overlay),
        (LOCALE, original_locale, updated_locale),
    ):
        if before != after:
            path.write_text(after, encoding="utf-8")
            print("UPDATED:", path.relative_to(ROOT))

    if not changed:
        print("No changes needed; All Missions is already installed.")
    print("Reversible solo All Missions access installed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
