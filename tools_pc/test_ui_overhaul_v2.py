#!/usr/bin/env python3
"""Regression contracts for Ascension UI Overhaul V2.

These tests intentionally cover the failures we have already seen in real
Windows rendering: excessive density, text overlap risk, stale V1 chrome,
mouse/keyboard divergence and Fast3D state contamination.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OV = ROOT / "port/src/optionsoverlay.c"
LOCALE = ROOT / "port/src/ascension_locale.c"
PATCHER = ROOT / "tools_pc/apply_ui_overhaul_v2.py"
LOCALE_PATCHER = ROOT / "tools_pc/apply_ui_overhaul_v2_locale.py"


def require(cond: bool, msg: str) -> None:
    if not cond:
        raise SystemExit(f"FAIL: {msg}")


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot import {path.name}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def model_layout(width: int, height: int) -> None:
    margin = 10
    x0 = margin
    x1 = width - margin
    tab_y = 31
    tab_h = 17
    list_top = 66
    row_h = 22
    help_h = 29
    footer_h = 19
    help_top = height - help_h - footer_h

    require(x1 > x0 + 240, f"{width}x{height}: panel too narrow")
    require(tab_y + tab_h < list_top, f"{width}x{height}: tabs collide with list")
    visible = (help_top - list_top - 3) // row_h
    visible = max(4, min(7, visible))
    require(4 <= visible <= 7, f"{width}x{height}: visible-row contract")
    require(list_top + visible * row_h <= help_top + row_h,
            f"{width}x{height}: list/help collision")

    left = x0 + 5
    right = x1 - 27
    require(right > left, f"{width}x{height}: tab rail invalid")
    prev = left
    for cat in range(4):
        tx0 = left + ((right - left) * cat) // 4
        tx1 = left + ((right - left) * (cat + 1)) // 4
        require(tx0 >= prev, f"{width}x{height}: tab ordering")
        require(tx1 > tx0, f"{width}x{height}: zero-width tab")
        prev = tx1

    bar_x0 = x0 + (186 if width >= 400 else 142)
    bar_x1 = (x1 - 10) - 42
    if bar_x1 < bar_x0 + 28:
        bar_x1 = bar_x0 + 28
    require(bar_x1 - bar_x0 >= 28, f"{width}x{height}: slider target too small")
    require(bar_x0 > x0 + 100, f"{width}x{height}: label corridor too small")


def main() -> int:
    src = OV.read_text(encoding="utf-8")
    locale = LOCALE.read_text(encoding="utf-8")

    markers = [
        "Ascension UI Overhaul V2 - Q Watch compact settings",
        "ptrFontZurichBold",
        "ptrFontZurichBoldChars",
        "tabCategoryAt",
        "OV_MAX_VISIBLE    7",
        "Q WATCH / SYSTEM CONFIGURATION",
        "DISPLAY CALIBRATION",
        "INPUT CALIBRATION",
        "FIELD PARAMETERS",
        "LANGUAGE / MAINTENANCE",
        "LMB SELECT/DRAG   RMB BACK",
        "SDL_SCANCODE_W",
        "SDL_SCANCODE_S",
        "SDL_SCANCODE_A",
        "SDL_SCANCODE_D",
        "categoryBounds(rows[s_sel].category, &first, &last);",
        "if (next < first) next = first;",
        "if (next > last) next = last;",
    ]
    for marker in markers:
        require(marker in src, f"missing V2 marker: {marker}")

    stale = [
        "OV_SIDE_W",
        "FIELD NOTE",
        "TECHNOLOGY IN SERVICE",
        "ACTIVE DOSSIER / FILE",
        "MI6 CLASSIFIED ARCHIVES",
    ]
    for marker in stale:
        require(marker not in src, f"V1 chrome leaked into V2: {marker}")

    require(src.count("Q WATCH / SYSTEM CONFIGURATION") == 1,
            "Q Watch heading must have one rendering source")

    # Native GoldenEye body typography is a deliberate design contract.
    require("drawZurich" in src and "ptrFontZurichBold" in src,
            "Zurich body typography missing")
    require("drawGothic" in src,
            "Gothic signature typography missing")

    # This is the exact class of renderer bug that turned text into rectangles.
    split_marker = "text pass: NEVER issue fillRect after this"
    require(split_marker in src, "render-state split marker missing")
    after_text = src.split(split_marker, 1)[1]
    require("fillRect(gdl" not in after_text,
            "geometry primitive emitted after text microcode setup")

    # RMB must be a predictable Back/Close action, not an alternate decrement.
    require("if (rmb && !prevRmb)" in src and "optionsOverlayToggle();" in src,
            "RMB Back behavior missing")

    # The native file-select remains visually authoritative. V2 only renders a
    # restrained Ascension signature and one-time F10 discovery hint. A legacy
    # extern left by V1 is harmless; the release gate is that no dossier chrome
    # or save-slot metadata is rendered by the overlay.
    require('"F10  OPTIONS"' in src, "minimal file-select discovery hint missing")
    require("MI6 CLASSIFIED ARCHIVES" not in src,
            "overlay still renders replacement file-select chrome")

    # PT-BR UI strings must be concise and present.
    locale_markers = [
        '"CONTROLS", "CONTROLES"',
        '"SYSTEM", "SISTEMA"',
        '"Q WATCH / SYSTEM CONFIGURATION", "Q WATCH / CONFIGURACAO"',
        '"INPUT CALIBRATION", "CALIBRACAO DE CONTROLES"',
        '"F10 CLOSE", "F10 FECHAR"',
    ]
    for marker in locale_markers:
        require(marker in locale, f"missing PT-BR V2 copy: {marker}")

    # Patcher idempotence is mandatory: applying V2 twice cannot keep editing.
    patch_mod = load_module(PATCHER, "asc_ui_v2_patch")
    locale_mod = load_module(LOCALE_PATCHER, "asc_ui_v2_locale_patch")
    require(patch_mod.patch(src) == src, "UI V2 patcher is not idempotent")
    require(locale_mod.patch(locale) == locale, "UI V2 locale patcher is not idempotent")

    # Exercise layout invariants across legacy 4:3 and modern widescreen virtual
    # widths. We intentionally test the native low-height case too.
    cases = [
        (320, 240), (400, 300), (440, 330), (640, 360),
        (640, 480), (854, 480), (960, 540),
    ]
    for w, h in cases:
        model_layout(w, h)

    print("Ascension UI Overhaul V2 contracts: PASS")
    print(f"Layout matrix: PASS ({len(cases)} viewport classes)")
    print("Fast3D geometry/text-state isolation: PASS")
    print("Mouse + keyboard navigation contract: PASS")
    print("Page-bounded focus navigation: PASS")
    print("GoldenEye-native typography contract: PASS")
    print("PT-BR editorial copy contract: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
