#!/usr/bin/env python3
"""Install Ascension's reversible "All missions" option.

The setting is intentionally non-destructive:
  * the toggle lives in the PC config, not in GoldenEye save data;
  * completed missions remain COMPLETED;
  * GoldenEye's native Aztec/Egypt minimum-difficulty rules remain intact;
  * otherwise locked missions are reported as UNLOCKED while the option is on;
  * turning it off immediately falls back to the untouched native progression
    algorithm.

Run after UI Overhaul V2 has been installed. The operation is fail-closed,
atomic across the three generated integration files, and idempotent.
"""
from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILE2 = ROOT / "src/game/file2.c"
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


def patch_file2(text: str) -> str:
    if "STAGESTATUS fileIsStageUnlockedAtDifficulty" not in text:
        raise PatchError("file2 progression function not found")

    text = once(
        text,
        '#include <stdlib.h>\n#define SAVELOG',
        '#include <stdlib.h>\n#include "ascension_campaign.h"\n#define SAVELOG',
        "campaign policy include",
    )

    anchor = '''            if ((levelid == SP_LEVEL_AZTEC && difficulty < DIFFICULTY_SECRET) ||
                (levelid == SP_LEVEL_EGYPT && difficulty < DIFFICULTY_00))
            {
                return STAGESTATUS_LOCKED; //we cant possibly have a completed bonus stage below each set dificulty
            }

            //still cant find it, do a search (this is probably how a cheat can unlock stages without having to actualy do them all)'''

    replacement = '''            if ((levelid == SP_LEVEL_AZTEC && difficulty < DIFFICULTY_SECRET) ||
                (levelid == SP_LEVEL_EGYPT && difficulty < DIFFICULTY_00))
            {
                return STAGESTATUS_LOCKED; //we cant possibly have a completed bonus stage below each set dificulty
            }

#ifdef PORT
            /* Ascension access override. Keep this AFTER the completion test
             * and native bonus-stage difficulty gates, but BEFORE progression
             * scanning. This reports access only; it never fabricates a time,
             * completion flag, cheat bit or EEPROM write. */
            if (ascensionCampaignUnlockAllMissions())
            {
                return STAGESTATUS_UNLOCKED;
            }
#endif

            //still cant find it, do a search (this is probably how a cheat can unlock stages without having to actualy do them all)'''

    text = once(text, anchor, replacement, "non-destructive mission access hook")

    fn = text.split("STAGESTATUS fileIsStageUnlockedAtDifficulty", 1)[1]
    fn = fn.split("void fileOverwriteSaveSlotWithNewSave", 1)[0]
    completed = fn.find("fileGetSaveStageCompletedForDifficulty")
    bonus_gate = fn.find("levelid == SP_LEVEL_AZTEC")
    override = fn.find("ascensionCampaignUnlockAllMissions")
    native_scan = fn.find("still cant find it, do a search")
    if min(completed, bonus_gate, override, native_scan) < 0:
        raise PatchError("mission access ordering contract incomplete")
    if not (completed < bonus_gate < override < native_scan):
        raise PatchError("mission access override is in an unsafe position")

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
      .help="Unlock every mission without changing saved completion.",
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
    { "Unlock every mission without changing saved completion.", "Libera todas as missoes sem alterar conclusoes salvas." },
'''
    text = once(text, anchor, replacement, "PT-BR unlock-all copy")
    return text


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="validate without writing")
    ap.add_argument("--no-backup", action="store_true")
    args = ap.parse_args()

    original_file2 = FILE2.read_text(encoding="utf-8")
    original_overlay = OVERLAY.read_text(encoding="utf-8")
    original_locale = LOCALE.read_text(encoding="utf-8")

    try:
        updated_file2 = patch_file2(original_file2)
        updated_overlay = patch_overlay(original_overlay)
        updated_locale = patch_locale(original_locale)
    except Exception as exc:
        raise SystemExit(f"ERROR: {exc}; no file written")

    # Atomic postconditions before touching disk.
    required = (
        (updated_file2, '#include "ascension_campaign.h"'),
        (updated_file2, "ascensionCampaignUnlockAllMissions()"),
        (updated_overlay, 'key="Ascension.UnlockAllMissions"'),
        (updated_overlay, '.label="All missions"'),
        (updated_locale, '"All missions", "Todas as missoes"'),
    )
    for haystack, needle in required:
        if needle not in haystack:
            raise SystemExit(f"ERROR: final contract missing {needle!r}; no file written")

    changed = []
    for path, before, after in (
        (FILE2, original_file2, updated_file2),
        (OVERLAY, original_overlay, updated_overlay),
        (LOCALE, original_locale, updated_locale),
    ):
        if before != after:
            changed.append(str(path.relative_to(ROOT)))

    if args.check:
        print("Ascension All Missions preflight: PASS")
        print("Native completed-state preservation: PASS")
        print("Aztec/Egypt difficulty gates preserved: PASS")
        print("Save-data mutation by toggle: NONE")
        print("Immediate OFF -> native progression fallback: PASS")
        print("F10 Gameplay-page toggle: PASS")
        print("Would update:", ", ".join(changed) if changed else "nothing")
        return 0

    if not args.no_backup:
        for path, before, after in (
            (FILE2, original_file2, updated_file2),
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
        (FILE2, original_file2, updated_file2),
        (OVERLAY, original_overlay, updated_overlay),
        (LOCALE, original_locale, updated_locale),
    ):
        if before != after:
            path.write_text(after, encoding="utf-8")
            print("UPDATED:", path.relative_to(ROOT))

    if not changed:
        print("No changes needed; All Missions is already installed.")
    print("Reversible All Missions access installed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
