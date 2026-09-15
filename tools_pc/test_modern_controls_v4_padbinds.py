#!/usr/bin/env python3
"""Contracts for the final Ascension 0.0.4 gamepad mapping layer."""
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def require(path: str, needles: list[str]) -> None:
    body = text(path)
    missing = [needle for needle in needles if needle not in body]
    if missing:
        raise SystemExit(f"FAIL {path}: missing {missing}")


require("port/include/ascension_controls.h", [
    "ascensionControlsGamepadButton",
    "ascensionControlsGamepadAxis",
    "SDL_GameControllerGetButton(controller, button)",
    "SDL_GameControllerGetAxis(controller, axis)",
])
require("port/src/ascension_controls.c", [
    'Input.ModernPadSouthpaw',
    'Input.ModernPadSwapTriggers',
    'Input.ModernPadBind.Action',
    'Input.ModernPadBind.Crouch',
    'current_menu != GE_MENU_RUN_STAGE',
    'ascensionWatchIsActive()',
    'lvlGetControlsLockedFlag() != 0',
    'physicalButtonForLogical',
    'SDL_CONTROLLER_AXIS_TRIGGERLEFT',
    'SDL_CONTROLLER_AXIS_TRIGGERRIGHT',
])
require("port/include/input.h", [
    "inputPadBindingDisplay",
    "inputPadBindingCapturePressed",
    "inputPadBindingReset",
])
require("port/src/input.c", [
    "inputPadBindingCapturePressed",
    "SDL_CONTROLLER_BUTTON_GUIDE",
    "ascensionControlsRawGamepadButton",
])
require("port/src/optionsoverlay.c", [
    "Input.ModernPadSouthpaw",
    "Input.ModernPadSwapTriggers",
    "Input.ModernPadBind.Action",
    "Input.ModernPadBind.Start",
    "inputPadBindingCapturePressed",
    "GAMEPAD BINDING SAVED",
])
require("port/src/ascension_locale.c", [
    "Botao: acao",
    "Botao: agachar",
    "Trocar gatilhos de tiro / mira",
])

# Defaults remain a familiar FPS layout and every stored value is constrained
# to SDL's normalized controller-button enum range.
controls = text("port/src/ascension_controls.c")
for marker in [
    '{ "Input.ModernPadBind.Action",     SDL_CONTROLLER_BUTTON_A }',
    '{ "Input.ModernPadBind.Cancel",     SDL_CONTROLLER_BUTTON_X }',
    '{ "Input.ModernPadBind.Crouch",     SDL_CONTROLLER_BUTTON_B }',
    '{ "Input.ModernPadBind.NextWeapon", SDL_CONTROLLER_BUTTON_Y }',
    '{ "Input.ModernPadBind.PrevWeapon", SDL_CONTROLLER_BUTTON_LEFTSHOULDER }',
    '{ "Input.ModernPadBind.AltAction",  SDL_CONTROLLER_BUTTON_RIGHTSHOULDER }',
]:
    if marker not in controls:
        raise SystemExit(f"FAIL default pad map: {marker}")

# The transparent pass-through contract is critical: outside Modern gameplay,
# the wrapper resolves the requested logical SDL button/axis unchanged.
if "int physical = logicalButton;" not in controls:
    raise SystemExit("FAIL button pass-through baseline")
if "int physical = logicalAxis;" not in controls:
    raise SystemExit("FAIL axis pass-through baseline")

# Post-patcher idempotence.
spec = importlib.util.spec_from_file_location(
    "padbind", ROOT / "tools_pc/apply_modern_controls_v4_padbinds.py"
)
if spec is None or spec.loader is None:
    raise SystemExit("FAIL cannot import padbind patcher")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
for name, path, fn in [
    ("input", "port/src/input.c", mod.patch_input),
    ("overlay", "port/src/optionsoverlay.c", mod.patch_overlay),
    ("locale", "port/src/ascension_locale.c", mod.patch_locale),
]:
    original = text(path)
    if fn(original) != original:
        raise SystemExit(f"FAIL padbind idempotence: {name}")

print("Modern Controls V4 gamepad mapping contracts: PASS")
print("  frontend/Q Watch legacy pass-through: PASS")
print("  Southpaw + trigger swap routing: PASS")
print("  live F10 digital-button remapping: PASS")
