#!/usr/bin/env python3
"""Keep the Ascension F10 menu entry point permanently discoverable.

Run after UI Overhaul V2 has been installed. The patch is deliberately tiny:
it only changes the closed-overlay file-select hint and its PT-BR copy. GoldenEye
menu/gameplay state is untouched. Fail-closed and idempotent.
"""
from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OV = ROOT / "port/src/optionsoverlay.c"
LOCALE = ROOT / "port/src/ascension_locale.c"


class PatchError(RuntimeError):
    pass


OLD_GEOMETRY = '''            if (!s_controlHintSeen)
                gdl = fillRect(gdl, 6, 5, 106, 20, 4, 5, 6, 176);'''

NEW_GEOMETRY = '''            /* F10 menu discovery is persistent: a new player must never need
             * prior knowledge to find Ascension's PC settings. Size the plate
             * from GoldenEye's own localized Zurich font metrics. */
            {
                const char *hint = "F10  OPEN OPTIONS";
                s32 hintW = measureTextFont(hint,
                                            ptrFontZurichBoldChars,
                                            ptrFontZurichBold);
                gdl = fillRect(gdl, 6, 5, 14 + hintW, 20, 4, 5, 6, 176);
            }'''

OLD_TEXT = '''            if (!s_controlHintSeen)
                gdl = drawZurich(gdl, 10, 9, "F10  OPTIONS", 0xE8E2D3FFu);'''

NEW_TEXT = '''            gdl = drawZurich(gdl, 10, 9, "F10  OPEN OPTIONS", 0xE8E2D3FFu);'''

OLD_LOCALE = '    { "F10  OPTIONS", "F10  OPCOES" },\n'
NEW_LOCALE = '    { "F10  OPEN OPTIONS", "F10  ABRIR OPCOES" },\n'


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        return text
    count = text.count(old)
    if count != 1:
        raise PatchError(f"{label}: expected exactly one anchor, found {count}")
    return text.replace(old, new, 1)


def patch_overlay(text: str) -> str:
    if "Ascension UI Overhaul V2 - Q Watch compact settings" not in text:
        raise PatchError("UI Overhaul V2 is not installed")
    text = replace_once(text, OLD_GEOMETRY, NEW_GEOMETRY, "F10 hint geometry")
    text = replace_once(text, OLD_TEXT, NEW_TEXT, "F10 hint text")
    if "F10 menu discovery is persistent" not in text:
        raise PatchError("persistent F10 postcondition missing")
    return text


def patch_locale(text: str) -> str:
    if "Q WATCH / SYSTEM CONFIGURATION" not in text:
        raise PatchError("UI Overhaul V2 locale copy is not installed")
    text = replace_once(text, OLD_LOCALE, NEW_LOCALE, "F10 PT-BR copy")
    if NEW_LOCALE not in text:
        raise PatchError("persistent F10 PT-BR postcondition missing")
    return text


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="validate without writing")
    ap.add_argument("--no-backup", action="store_true")
    args = ap.parse_args()

    original_ov = OV.read_text(encoding="utf-8")
    original_locale = LOCALE.read_text(encoding="utf-8")

    try:
        updated_ov = patch_overlay(original_ov)
        updated_locale = patch_locale(original_locale)
    except PatchError as exc:
        raise SystemExit(f"ERROR: {exc}; no file written")

    if args.check:
        print("Persistent F10 discovery hint: PASS")
        print("Localized dynamic-width hint plate: PASS")
        changed = []
        if updated_ov != original_ov:
            changed.append(str(OV.relative_to(ROOT)))
        if updated_locale != original_locale:
            changed.append(str(LOCALE.relative_to(ROOT)))
        print("Would update:", ", ".join(changed) if changed else "nothing")
        return 0

    if not args.no_backup:
        for path, original in ((OV, original_ov), (LOCALE, original_locale)):
            backup = path.with_suffix(path.suffix + ".before-persistent-f10")
            if not backup.exists():
                backup.write_text(original, encoding="utf-8")
                print("BACKUP:", backup.relative_to(ROOT))

    if updated_ov != original_ov:
        OV.write_text(updated_ov, encoding="utf-8")
        print("UPDATED:", OV.relative_to(ROOT))
    if updated_locale != original_locale:
        LOCALE.write_text(updated_locale, encoding="utf-8")
        print("UPDATED:", LOCALE.relative_to(ROOT))
    if updated_ov == original_ov and updated_locale == original_locale:
        print("No changes needed; persistent F10 hint is already installed.")

    print("F10 OPEN OPTIONS is now permanently visible on file select.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
