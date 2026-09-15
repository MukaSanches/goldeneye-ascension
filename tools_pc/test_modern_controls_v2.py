#!/usr/bin/env python3
"""Static/regression contracts for the generated Modern Controls V2 bridge.

The test intentionally accepts both the original numeric spelling of Classic
and the enum spelling used by later Ascension control layers. The invariant is
that Classic remains the default; formatting/refactoring must not create a
false regression.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def require(path: str, needles: list[str]) -> None:
    text = (ROOT / path).read_text(encoding="utf-8")
    missing = [n for n in needles if n not in text]
    if missing:
        raise SystemExit(f"FAIL {path}: missing {missing}")


require("port/include/ascension_controls.h", [
    "ASCENSION_CONTROLS_CLASSIC",
    "ASCENSION_CONTROLS_HYBRID",
    "ASCENSION_CONTROLS_MODERN",
    "ascensionControlsResolveAim",
    "ascensionControlsShapeMouseDelta",
])

require("port/src/ascension_controls.c", [
    'configRegisterInt("Input.ControlPreset", &s_controlPreset, 0, 2);',
    'configRegisterInt("Input.ModernAimToggle"',
    'configRegisterInt("Input.ModernRawMouse"',
    'configRegisterInt("Input.ModernMouseResponse"',
    'configRegisterInt("Input.ModernWheelQueue"',
    "if (!ascensionControlsIsModern() || s_modernMouseResponse == ASCENSION_MOUSE_LEGACY)",
])

controls = (ROOT / "port/src/ascension_controls.c").read_text(encoding="utf-8")
classic_defaults = (
    "static int s_controlPreset = 0;",
    "static int s_controlPreset = ASCENSION_CONTROLS_CLASSIC;",
)
if not any(default in controls for default in classic_defaults):
    raise SystemExit("FAIL port/src/ascension_controls.c: Classic is no longer the default preset")

require("port/src/input.c", [
    "ascensionControlsWantsRawMouse()",
    "ascensionControlsResolveAim(physicalAimHeld",
    "ascensionControlsShapeMouseDelta(edx, aimHeld)",
    "wheelQueue",
    "wheelGap",
    "ascensionControlsWheelQueueEnabled()",
])

require("port/src/optionsoverlay.c", [
    'Input.DedicatedCrouch',
    'Input.ModernAimToggle',
    'Input.ModernRawMouse',
    'Input.ModernMouseResponse',
    'Input.ModernWheelQueue',
    'kMouseResponse',
])

require("port/src/ascension_locale.c", [
    "Alternar mira moderna",
    "Mouse bruto moderno",
    "Resposta do mouse",
    "Troca de arma confiavel",
])

# Safety contract: V2 must remain a host-layer feature. The integration script
# has no reason to touch game/ROM/save/assets; flag accidental scope expansion.
patcher = (ROOT / "tools_pc/apply_modern_controls_v2.py").read_text(encoding="utf-8")
for forbidden in ["src/game/", "assets/", "ge007.eep", ".z64"]:
    if f'ROOT / "{forbidden}' in patcher:
        raise SystemExit(f"FAIL patcher scope: references forbidden write target {forbidden}")

print("Modern Controls V2 contracts: PASS")
