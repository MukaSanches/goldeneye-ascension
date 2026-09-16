#!/usr/bin/env python3
"""Regression contract for the permanent F10 menu discovery hint."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OV = ROOT / "port/src/optionsoverlay.c"
LOCALE = ROOT / "port/src/ascension_locale.c"


def require(cond: bool, msg: str) -> None:
    if not cond:
        raise SystemExit(f"FAIL: {msg}")


def main() -> int:
    src = OV.read_text(encoding="utf-8")
    locale = LOCALE.read_text(encoding="utf-8")

    require("Ascension UI Overhaul V2 - Q Watch compact settings" in src,
            "UI V2 must be installed")
    require("F10 menu discovery is persistent" in src,
            "persistent F10 marker missing")
    require('"F10  OPEN OPTIONS"' in src,
            "visible F10 call-to-action missing")
    require("measureTextFont(hint" in src,
            "hint plate must use localized font metrics")
    require('"F10  OPEN OPTIONS", "F10  ABRIR OPCOES"' in locale,
            "PT-BR F10 call-to-action missing")
    require('if (!s_controlHintSeen)\n                gdl = drawZurich' not in src,
            "F10 hint is still one-time only")

    print("Persistent F10 menu discovery: PASS")
    print("PT-BR F10 ABRIR OPCOES: PASS")
    print("Dynamic localized hint width: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
