#!/usr/bin/env python3
"""Atomic installer for Ascension UI Overhaul V2.

This is the public migration entry point. It normalizes the V1 input behavior
that changed between iterations, applies the V2 renderer migration and its
PT-BR copy as a single fail-closed operation, then writes only after every
postcondition succeeds.
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

V1_MOVE_SELECTION = '''static void moveSelection(int delta)
{
    int next = s_sel + delta;
    if (next < 0) next = 0;
    if (next >= NUM_ROWS) next = NUM_ROWS - 1;
    if (next != s_sel) {
        s_sel = next;
        clearPendingAction();
        ensureSelectionVisible();
    }
}'''

V2_MOVE_SELECTION = '''static void moveSelection(int delta)
{
    /* Q Watch pages are real pages: vertical navigation never falls through
     * into another category. At either edge focus wraps inside the page,
     * matching GoldenEye's predictable linear menu behavior. */
    int first, last;
    categoryBounds(rows[s_sel].category, &first, &last);
    if (first < 0 || last < first)
        return;

    int next = s_sel + delta;
    if (next < first) next = last;
    if (next > last) next = first;
    if (next != s_sel) {
        s_sel = next;
        clearPendingAction();
        ensureSelectionVisible();
    }
}'''


def replace_migration(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        return text
    count = text.count(old)
    if count != 1:
        raise InstallError(f"{label} migration anchor expected once, found {count}")
    return text.replace(old, new, 1)


def normalize_v1_input(text: str) -> str:
    if "Ascension UI Overhaul V2 - Q Watch compact settings" in text:
        return text
    text = replace_migration(text, V1_RMB, V2_RMB, "V1 RMB")
    text = replace_migration(text, V1_MOVE_SELECTION, V2_MOVE_SELECTION,
                             "V1 vertical navigation")
    return text


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
        V2_MOVE_SELECTION,
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
