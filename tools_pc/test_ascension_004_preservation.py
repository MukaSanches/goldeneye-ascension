#!/usr/bin/env python3
"""Final-state preservation contracts for Ascension 0.0.4.

Unlike the historical patcher tests, this intentionally does not reapply an
older generator over a newer layer. It verifies that the composed release still
contains the manually accepted checkpoint invariants after V4 is installed.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def body(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def require(path: str, *needles: str) -> None:
    data = body(path)
    missing = [n for n in needles if n not in data]
    if missing:
        raise SystemExit(f"FAIL preservation {path}: missing {missing}")


require("port/src/input.c",
        "Ascension V3 menu guard: clear gameplay look residue only",
        "ascensionControlsQueueDirectLook",
        "ascensionControlsQueueGamepadAxes",
        "inputPadBindingCapturePressed")
require("port/src/video.c",
        "Ascension watch capture guard:",
        "ascensionWatchIsActive()",
        "inputReleaseCapture()")
require("src/game/options.c",
        "int ascensionWatchIsActive(void)",
        "frontChangeMenu(MENU_MISSION_SELECT, FALSE);",
        "mission_failed_or_aborted = FALSE;",
        "deleteCurrentSelectedFolder();")
require("port/include/ascension_watch.h",
        "int ascensionWatchIsActive(void);",
        "void ascensionWatchReturnToMainMenu(void);")
require("port/src/optionsoverlay.c",
        "Return to main menu",
        "Input.ModernPadBind.Action",
        "Input.ModernPadSouthpaw")
require("port/src/ascension_controls.c",
        "current_menu != GE_MENU_RUN_STAGE",
        "ascensionWatchIsActive()",
        "lvlGetControlsLockedFlag() != 0")

# The convenience return must remain separate from the stock abort semantics.
options = body("src/game/options.c")
start = options.find("void ascensionWatchReturnToMainMenu(void)")
if start < 0:
    raise SystemExit("FAIL preservation: quick-return bridge missing")
end = options.find("#endif", start)
quick = options[start:end if end >= 0 else len(options)]
for forbidden in ["deleteCurrentSelectedFolder", "sysRestart", "mission_failed_or_aborted = TRUE"]:
    if forbidden in quick:
        raise SystemExit(f"FAIL preservation: quick return contains {forbidden}")

# 0.0.4 additions must stay out of ROM/save/AI ownership.
for patch in ["tools_pc/apply_modern_controls_v4.py",
              "tools_pc/apply_modern_controls_v4_padbinds.py"]:
    data = body(patch)
    for forbidden in ["fileWriteSave", "joyGamePakLongWrite", "chrai", ".z64"]:
        if forbidden in data:
            raise SystemExit(f"FAIL preservation {patch}: forbidden {forbidden}")

print("Ascension 0.0.4 preservation contracts: PASS")
print("  accepted mouse/menu/Q Watch transitions retained: PASS")
print("  quick-return vs stock abort isolation retained: PASS")
print("  V4 save/ROM/AI ownership isolation retained: PASS")
