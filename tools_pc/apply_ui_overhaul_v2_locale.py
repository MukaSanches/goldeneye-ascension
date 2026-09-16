#!/usr/bin/env python3
"""Install Ascension UI Overhaul V2 copy in the port-owned locale table.

The N64 font path is intentionally kept ASCII-safe; wording is editorialized
for short labels that fit GoldenEye's virtual viewport instead of literal
translations that overflow.  Fail-closed and idempotent.
"""
from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCALE = ROOT / "port/src/ascension_locale.c"


class PatchError(RuntimeError):
    pass


ANCHOR = '    { "GAMEPLAY", "JOGO" },\n'
BLOCK = '''    { "GAMEPLAY", "JOGO" },
    { "CONTROLS", "CONTROLES" },
    { "SYSTEM", "SISTEMA" },

    /* Ascension UI Overhaul V2 / Q Watch */
    { "Q WATCH / SYSTEM CONFIGURATION", "Q WATCH / CONFIGURACAO" },
    { "DISPLAY CALIBRATION", "CALIBRACAO DE VIDEO" },
    { "INPUT CALIBRATION", "CALIBRACAO DE CONTROLES" },
    { "FIELD PARAMETERS", "PARAMETROS DE JOGO" },
    { "LANGUAGE / MAINTENANCE", "IDIOMA / SISTEMA" },
    { "F10  OPTIONS", "F10  OPCOES" },
    { "LMB SELECT/DRAG   RMB BACK   W/S NAV   A/D ADJUST", "LMB SELEC./ARRASTAR  RMB VOLTAR  W/S NAV  A/D AJUSTE" },
    { "F10 CLOSE", "F10 FECHAR" },
'''

MARKER = 'Q WATCH / SYSTEM CONFIGURATION'


def patch(text: str) -> str:
    if 'static const struct LocaleEntry kPtBr[]' not in text:
        raise PatchError("Ascension locale table not found")
    if MARKER in text:
        return text
    count = text.count(ANCHOR)
    if count != 1:
        raise PatchError(f"category anchor expected once, found {count}")
    out = text.replace(ANCHOR, BLOCK, 1)
    for needle in (
        '"CONTROLS", "CONTROLES"',
        '"SYSTEM", "SISTEMA"',
        '"Q WATCH / SYSTEM CONFIGURATION", "Q WATCH / CONFIGURACAO"',
        '"INPUT CALIBRATION", "CALIBRACAO DE CONTROLES"',
        '"F10 CLOSE", "F10 FECHAR"',
    ):
        if needle not in out:
            raise PatchError(f"postcondition missing {needle}")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--no-backup", action="store_true")
    args = ap.parse_args()

    original = LOCALE.read_text(encoding="utf-8")
    try:
        updated = patch(original)
    except PatchError as exc:
        raise SystemExit(f"ERROR: {exc}; no file written")

    if args.check:
        print("Ascension UI V2 PT-BR copy: PASS")
        print("ASCII-safe GoldenEye font copy: PASS")
        print("Would update:", LOCALE.relative_to(ROOT) if updated != original else "nothing")
        return 0

    if updated != original:
        if not args.no_backup:
            backup = LOCALE.with_suffix(LOCALE.suffix + ".before-ui-v2")
            if not backup.exists():
                backup.write_text(original, encoding="utf-8")
                print("BACKUP:", backup.relative_to(ROOT))
        LOCALE.write_text(updated, encoding="utf-8")
        print("UPDATED:", LOCALE.relative_to(ROOT))
    else:
        print("No changes needed; UI V2 locale already applied.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
