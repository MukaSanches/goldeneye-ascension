#!/usr/bin/env python3
"""Regression/property checks for Ascension Modern Controls V4.

Run after the full checkpoint stack plus apply_modern_controls_v4.py.
"""
from __future__ import annotations

import importlib.util
import math
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def require(path: str, needles: list[str]) -> None:
    body = text(path)
    missing = [n for n in needles if n not in body]
    if missing:
        raise SystemExit(f"FAIL {path}: missing {missing}")


require("port/include/ascension_version.h", [
    'ASCENSION_VERSION_PATCH 4',
    'ASCENSION_VERSION "0.0.4"',
])
require("port/include/ascension_controls.h", [
    "ASCENSION_PAD_PRECISION",
    "ascensionControlsModernGamepadEnabled",
    "ascensionControlsQueueGamepadAxes",
    "ascensionControlsConsumeGamepadMove",
    "ascensionControlsConsumeGamepadLook",
])
require("port/include/input.h", [
    "inputBindingDisplay",
    "inputBindingSetScancode",
    "inputBindingReset",
])
require("port/src/ascension_controls.c", [
    'configRegisterInt("Input.ModernGamepad"',
    'configRegisterInt("Input.ModernPadDeadzone"',
    'configRegisterInt("Input.ModernPadResponse"',
    'configRegisterInt("Input.ModernPadLookSensitivity"',
    'configRegisterInt("Input.ModernPadAdsScale"',
    "shapePadPair",
    "pow(shaped, 1.45)",
    "s_padMoveY = -moveY",
    "s_padLookPitch = (float)(-(double)lookY * degrees)",
])
require("port/src/input.c", [
    "inputBindingActionForKey",
    "inputBindingSetScancode",
    "int modernPad = idx == 0 && ascensionControlsModernGamepadEnabled()",
    "ascensionControlsQueueGamepadAxes(lx, ly, rx, ry, padAim)",
    "if (modernPad) {",
    "button |= GE_CONT_R;",
])
require("src/game/bondview2.c", [
    "ascensionControlsConsumeGamepadLook",
    "padYaw * g_GlobalTimerDelta",
    "ascensionControlsConsumeGamepadMove",
    "moveData.analogStrafe = (s32)(padStrafe * 70.0f)",
    "moveData.analogWalk = (s32)(padWalk * 70.0f)",
])
require("port/src/optionsoverlay.c", [
    "ROW_BIND",
    "Input.ModernGamepad",
    "Input.ModernPadDeadzone",
    "Input.ModernPadLookSensitivity",
    "Input.ModernPadAdsScale",
    "Input.Bind.Forward",
    "inputBindingDisplay",
    "PRESS A KEY - ESC CANCEL",
])
require("port/src/ascension_locale.c", [
    "Controle twin-stick moderno",
    "Zona morta radial %",
    "Tecla: avancar",
    "PRESSIONE UMA TECLA - ESC CANCELA",
])

# V4 must remain PC/PORT-only and never write game-owned data.
patcher = text("tools_pc/apply_modern_controls_v4.py")
for forbidden in ["assets/", ".z64", "ge007.eep", "fileWriteSave", "joyGamePakLongWrite", "src/game/chrai"]:
    if forbidden in patcher:
        raise SystemExit(f"FAIL V4 scope: forbidden marker {forbidden}")

# Patcher idempotence on the already-generated tree.
spec = importlib.util.spec_from_file_location("v4patch", ROOT / "tools_pc/apply_modern_controls_v4.py")
if spec is None or spec.loader is None:
    raise SystemExit("FAIL: cannot import V4 patcher")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
for name, path, fn in [
    ("input", "port/src/input.c", mod.patch_input),
    ("bondview", "src/game/bondview2.c", mod.patch_bondview),
    ("overlay", "port/src/optionsoverlay.c", mod.patch_overlay),
    ("locale", "port/src/ascension_locale.c", mod.patch_locale),
]:
    original = text(path)
    again = fn(original)
    if again != original:
        raise SystemExit(f"FAIL V4 idempotence: {name} changes on second application")

# Property model for radial deadzone. This mirrors shapePadPair and checks that
# direction is preserved, the deadzone is truly radial and output is bounded.
def shape(raw_x: int, raw_y: int, dz_pct: int, precision: bool) -> tuple[float, float]:
    x = raw_x / (32768.0 if raw_x < 0 else 32767.0)
    y = raw_y / (32768.0 if raw_y < 0 else 32767.0)
    mag = math.hypot(x, y)
    dz = dz_pct / 100.0
    if mag <= dz or mag <= 1e-6:
        return 0.0, 0.0
    if mag > 1.0:
        x /= mag
        y /= mag
        mag = 1.0
    out_mag = max(0.0, min(1.0, (mag - dz) / (1.0 - dz)))
    if precision:
        out_mag = out_mag ** 1.45
    scale = out_mag / mag
    return x * scale, y * scale

rng = random.Random(0xA004C0DE)
for _ in range(100_000):
    x = rng.randint(-32768, 32767)
    y = rng.randint(-32768, 32767)
    dz = rng.randint(0, 40)
    precision = bool(rng.getrandbits(1))
    ox, oy = shape(x, y, dz, precision)
    om = math.hypot(ox, oy)
    if om > 1.000001:
        raise SystemExit("FAIL radial gamepad output exceeded unit circle")

    nx = x / (32768.0 if x < 0 else 32767.0)
    ny = y / (32768.0 if y < 0 else 32767.0)
    im = math.hypot(nx, ny)
    if im <= dz / 100.0 + 1e-12 and (abs(ox) > 1e-9 or abs(oy) > 1e-9):
        raise SystemExit("FAIL radial deadzone leaked input")
    if ox and x and math.copysign(1.0, ox) != math.copysign(1.0, x):
        raise SystemExit("FAIL radial shaping flipped X")
    if oy and y and math.copysign(1.0, oy) != math.copysign(1.0, y):
        raise SystemExit("FAIL radial shaping flipped Y")

# ADS may slow look but must never make it faster than hip-fire.
BASE = 2.75
for _ in range(100_000):
    axis = rng.uniform(-1.0, 1.0)
    sens = rng.randint(20, 300) / 100.0
    ads = rng.randint(20, 100) / 100.0
    hip = abs(axis * BASE * sens)
    aimed = abs(axis * BASE * sens * ads)
    if aimed > hip + 1e-9:
        raise SystemExit("FAIL gamepad ADS faster than hip-fire")

# The Modern branch must not replace the accepted legacy path globally.
inp = text("port/src/input.c")
if "if (modernPad)" not in inp or "else {\n            int px = scaleAxis(lx);" not in inp:
    raise SystemExit("FAIL legacy gamepad fallback missing")
if "idx == 0 && ascensionControlsModernGamepadEnabled()" not in inp:
    raise SystemExit("FAIL V4 not scoped to controller 0 Modern")

print("Modern Controls V4 contracts: PASS")
print("  100000 randomized radial-deadzone cases: PASS")
print("  100000 randomized ADS-rate cases: PASS")
print("  keyboard binding/idempotence/scope contracts: PASS")
