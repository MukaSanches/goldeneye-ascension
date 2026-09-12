#!/usr/bin/env python3
"""Ascension PT-BR localization coverage audit.

The game addresses text as (bank << 10) | slot. This tool inventories every
US-English text slot used by the PC port and compares it with explicit PT-BR
catalog entries. It deliberately does not treat an English fallback as
translated: every visible string must be reviewed, even when the final PT-BR
text is intentionally identical (names, brands, acronyms, etc.).

Catalog syntax accepted by the audit:
    PT(LTITLE, 29, "SELECIONAR MISSÃO\\n")
    KEEP(LTITLE, 22)  # intentional original text, e.g. "007"

Exit status is non-zero while required slots are missing, so this can be wired
into CI before declaring the localization complete.
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEXT_DIR = ROOT / "assets" / "obseg" / "text"

# Exact order from src/game/language.c::LnameX_lookuptable (LANG_US).
BANKS = [
    (1, "LAME", "LameE.c", "Library (multi)"),
    (2, "LARCH", "LarchE.c", "Archives"),
    (3, "LARK", "LarkE.c", "Facility"),
    (4, "LASH", "LashE.c", "Stack (multi)"),
    (5, "LAZT", "LaztE.c", "Aztec"),
    (6, "LCAT", "LcatE.c", "Citadel (multi)"),
    (7, "LCAVE", "LcaveE.c", "Caverns"),
    (8, "LAREC", "LarecE.c", "Control"),
    (9, "LCRAD", "LcradE.c", "Cradle"),
    (10, "LCRYP", "LcrypE.c", "Egypt"),
    (11, "LDAM", "LdamE.c", "Dam"),
    (12, "LDEPO", "LdepoE.c", "Depot"),
    (13, "LDEST", "LdestE.c", "Frigate"),
    (14, "LDISH", "LdishE.c", "Temple (multi)"),
    (15, "LEAR", "LearE.c", "Ear (unused)"),
    (16, "LELD", "LeldE.c", "Eld (unused)"),
    (17, "LIMP", "LimpE.c", "Basement (multi)"),
    (18, "LJUN", "LjunE.c", "Jungle"),
    (19, "LLEE", "LleeE.c", "Lee (unused)"),
    (20, "LLEN", "LlenE.c", "Cuba"),
    (21, "LLIP", "LlipE.c", "Lip (unused)"),
    (22, "LLUE", "LlueE.c", "Lue (unused)"),
    (23, "LOAT", "LoatE.c", "Caves (multi)"),
    (24, "LPAM", "LpamE.c", "Pam (unused)"),
    (25, "LPETE", "LpeteE.c", "Streets"),
    (26, "LREF", "LrefE.c", "Complex (multi)"),
    (27, "LRIT", "LritE.c", "Rit (unused)"),
    (28, "LRUN", "LrunE.c", "Runway"),
    (29, "LSEVB", "LsevbE.c", "Bunker 2"),
    (30, "LSEV", "LsevE.c", "Bunker 1"),
    (31, "LSEVX", "LsevxE.c", "Surface 1"),
    (32, "LSEVXB", "LsevxbE.c", "Surface 2"),
    (33, "LSHO", "LshoE.c", "Shooting Range (unused)"),
    (34, "LSILO", "LsiloE.c", "Silo"),
    (35, "LSTAT", "LstatE.c", "Statue"),
    (36, "LTRA", "LtraE.c", "Train"),
    (37, "LWAX", "LwaxE.c", "Wax (unused)"),
    (38, "LGUN", "LgunE.c", "Guns"),
    (39, "LTITLE", "LtitleE.c", "Menus/titles"),
    (40, "LMPMENU", "LmpmenuE.c", "Multiplayer menus"),
    (41, "LPROPOBJ", "LpropobjE.c", "Pickups/objects"),
    (42, "LMPWEAPONS", "LmpweaponsE.c", "Multiplayer weapons"),
    (43, "LOPTIONS", "LoptionsE.c", "Watch/options"),
    (44, "LMISC", "LmiscE.c", "Cheats/misc"),
]

UNUSED_BANKS = {"LEAR", "LELD", "LLEE", "LLIP", "LLUE", "LPAM", "LRIT", "LSHO", "LWAX"}

@dataclass(frozen=True)
class Slot:
    bank_num: int
    bank: str
    slot: int
    text: str
    area: str

    @property
    def ident(self) -> int:
        return (self.bank_num << 10) | self.slot


def _decode_c_string(token: str) -> str:
    # Python string escaping is compatible with the escapes used in these
    # generated C text arrays (\\n, quotes, backslashes).
    return ast.literal_eval(token)


def read_us_slots(bank_num: int, bank: str, filename: str, area: str) -> list[Slot]:
    path = TEXT_DIR / filename
    if not path.exists():
        raise FileNotFoundError(path)

    slots: list[Slot] = []
    slot_index = 0
    enabled = True
    stack: list[bool] = []

    for raw in path.read_text(encoding="utf-8", errors="strict").splitlines():
        line = raw.strip()
        if line.startswith("#ifdef"):
            symbol = line.split(maxsplit=1)[1].strip()
            stack.append(enabled)
            enabled = enabled and (symbol == "LANG_US")
            continue
        if line.startswith("#ifndef"):
            symbol = line.split(maxsplit=1)[1].strip()
            stack.append(enabled)
            enabled = enabled and (symbol != "LANG_US")
            continue
        if line.startswith("#else"):
            parent = stack[-1] if stack else True
            enabled = parent and not enabled
            continue
        if line.startswith("#endif"):
            enabled = stack.pop() if stack else True
            continue
        if not enabled:
            continue

        # Array entries are one C string literal or zero per slot in the source.
        m = re.match(r'^((?:"(?:\\.|[^"\\])*")|0)\s*,?\s*(?://.*)?$', line)
        if not m:
            continue
        token = m.group(1)
        if token != "0":
            text = _decode_c_string(token)
            slots.append(Slot(bank_num, bank, slot_index, text, area))
        slot_index += 1

    return slots


def load_reviewed_ids() -> set[tuple[str, int]]:
    roots = [ROOT / "port" / "src" / "localization", ROOT / "port" / "localization"]
    reviewed: set[tuple[str, int]] = set()
    pattern = re.compile(r'\b(?:PT|KEEP)\s*\(\s*([A-Z0-9_]+)\s*,\s*(\d+)\b')
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix not in {".c", ".h", ".inc"}:
                continue
            data = path.read_text(encoding="utf-8", errors="replace")
            for bank, slot in pattern.findall(data):
                reviewed.add((bank, int(slot)))
    return reviewed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--include-unused", action="store_true", help="require unused/debug banks too")
    parser.add_argument("--missing", type=int, default=120, help="maximum missing lines to print")
    args = parser.parse_args()

    all_slots: list[Slot] = []
    for bank_num, bank, filename, area in BANKS:
        if not args.include_unused and bank in UNUSED_BANKS:
            continue
        all_slots.extend(read_us_slots(bank_num, bank, filename, area))

    reviewed = load_reviewed_ids()
    missing = [s for s in all_slots if (s.bank, s.slot) not in reviewed]

    total = len(all_slots)
    done = total - len(missing)
    pct = 100.0 if total == 0 else done * 100.0 / total

    print(f"Ascension PT-BR: {done}/{total} slots explicitamente revisados ({pct:.2f}%)")
    print(f"Lacunas: {len(missing)}")

    if missing:
        print("\nPrimeiras lacunas:")
        for s in missing[: max(0, args.missing)]:
            preview = s.text.replace("\n", "\\n")
            if len(preview) > 110:
                preview = preview[:107] + "..."
            print(f"  {s.bank}:{s.slot:03d}  {s.area:<22}  {preview}")
        if len(missing) > args.missing:
            print(f"  ... +{len(missing) - args.missing} lacunas")
        return 1

    print("\nCOBERTURA DE TEXTO = 100% para todos os bancos ativos.")
    print("Ainda execute a auditoria visual de texturas/modelos antes de marcar a localização como 100% final.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
