#!/usr/bin/env python3
"""Static/regression contracts for the generated Modern Controls V2 bridge."""
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
    "static int s_controlPreset = 0;",
    "if (!ascensionControlsIsModern() || s_modernMouseResponse == ASCENSION_MOUSE_LEGACY)",
])

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
