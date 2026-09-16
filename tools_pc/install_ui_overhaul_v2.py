#!/usr/bin/env python3
"""Atomic installer for Ascension UI Overhaul V2.

This is the public migration entry point. It normalizes the one V1 mouse
binding that changed between iterations, preserves V1's already page-bounded
vertical navigation, applies the V2 renderer migration and PT-BR copy as a
single fail-closed operation, then writes only after every postcondition
succeeds.
"""
from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OV = ROOT / "port/src/optionsoverlay.c"
LOCALE = ROOT / "port/src/ascension_locale.c"
V2_PATCHER = ROOT / "tools_pc/apply_ui_overhaul_v2.py"
LOCALE_PATCHER = ROOT / "tools_pc/apply_ui_overhaul_v2_locale.py"


class InstallError(RuntimeError):
    pass


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise InstallError(f"cannot import {path.name}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


V1_RMB = '''        if (rmb && !prevRmb && hoverRow >= 0 &&
            rows[hoverRow].kind != ROW_ACTION && ox >= OV_LABEL_X)
            rowAdjust(&rows[hoverRow], -1);'''

V2_RMB = '''        if (rmb && !prevRmb) {
            optionsOverlayToggle();
            return;
        }'''

# V1 already scopes vertical focus to the active department. V2 retains that
# behavior and changes only presentation plus the PC-standard RMB Back action.
PAGE_BOUNDED_NAV = '''    int first, last;
    categoryBounds(rows[s_sel].category, &first, &last);
    if (first < 0) return;
    int next = s_sel + delta;
    if (next < first) next = first;
    if (next > last) next = last;'''


def normalize_v1_input(text: str) -> str:
    if "Ascension UI Overhaul V2 - Q Watch compact settings" in text:
        return text
    if PAGE_BOUNDED_NAV not in text:
        raise InstallError("V1 page-bounded navigation contract missing")
    if V2_RMB in text:
        return text
    count = text.count(V1_RMB)
    if count != 1:
        raise InstallError(f"V1 RMB migration anchor expected once, found {count}")
    return text.replace(V1_RMB, V2_RMB, 1)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="validate without writing")
    ap.add_argument("--no-backup", action="store_true")
    args = ap.parse_args()

    original_ov = OV.read_text(encoding="utf-8")
    original_locale = LOCALE.read_text(encoding="utf-8")

    try:
        v2 = load(V2_PATCHER, "asc_ui_v2_core")
        loc = load(LOCALE_PATCHER, "asc_ui_v2_locale")
        prepared = normalize_v1_input(original_ov)
        updated_ov = v2.patch(prepared)
        updated_locale = loc.patch(original_locale)
    except Exception as exc:
        # Patcher exceptions are intentionally surfaced without partial writes.
        raise SystemExit(f"ERROR: {exc}; no file written")

    required = [
        "Ascension UI Overhaul V2 - Q Watch compact settings",
        "ptrFontZurichBold",
        "Q WATCH / SYSTEM CONFIGURATION",
        "tabCategoryAt",
        V2_RMB,
        PAGE_BOUNDED_NAV,
    ]
    for needle in required:
        if needle not in updated_ov:
            raise SystemExit(f"ERROR: final UI contract missing {needle!r}; no file written")

    if "MI6 CLASSIFIED ARCHIVES" in updated_ov or "FIELD NOTE" in updated_ov:
        raise SystemExit("ERROR: V1 visual chrome survived migration; no file written")
    if '"Q WATCH / SYSTEM CONFIGURATION", "Q WATCH / CONFIGURACAO"' not in updated_locale:
        raise SystemExit("ERROR: PT-BR V2 copy missing; no file written")

    if args.check:
        print("Ascension UI Overhaul V2 atomic preflight: PASS")
        print("V1 input migration: PASS")
        print("Page-bounded vertical navigation: PASS")
        print("Q Watch renderer: PASS")
        print("PT-BR copy: PASS")
        changed = []
        if updated_ov != original_ov:
            changed.append(str(OV.relative_to(ROOT)))
        if updated_locale != original_locale:
            changed.append(str(LOCALE.relative_to(ROOT)))
        print("Would update:", ", ".join(changed) if changed else "nothing")
        return 0

    if not args.no_backup:
        for path, original in ((OV, original_ov), (LOCALE, original_locale)):
            backup = path.with_suffix(path.suffix + ".before-ui-v2")
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
        print("No changes needed; UI Overhaul V2 is already installed.")

    print("Ascension UI Overhaul V2 installed atomically.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
