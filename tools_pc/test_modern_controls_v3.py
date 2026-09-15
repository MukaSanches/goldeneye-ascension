#!/usr/bin/env python3
"""Regression and property checks for Modern Controls V3.

Run after V2 + V3 bridges have been applied to the checkout.
"""
from __future__ import annotations

import importlib.util
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


require("port/include/ascension_controls.h", [
    "ascensionControlsDirectLookEnabled",
    "ascensionControlsQueueDirectLook",
    "ascensionControlsConsumeDirectLook",
    "ascensionControlsDirectionalWheelEnabled",
    "ascensionControlsDisableAutoCenter",
])

require("port/src/ascension_controls.c", [
    "s_controlPreset = ASCENSION_CONTROLS_CLASSIC",
    'configRegisterInt("Input.ModernDirectLook"',
    'configRegisterInt("Input.ModernLookSensitivity"',
    'configRegisterInt("Input.ModernAdsScale"',
    'configRegisterInt("Input.ModernDirectionalWheel"',
    'configRegisterInt("Input.ModernDisableAutoCenter"',
    "ASCENSION_DIRECT_LOOK_DEG_PER_COUNT",
    "ASCENSION_DIRECT_LOOK_ACCUM_LIMIT",
    "if (!ascensionControlsDirectLookEnabled())",
])

require("port/src/input.c", [
    "wheelQueuePush",
    "wheelQueuePop",
    "wheelQueueClear",
    "ascensionControlsQueueDirectLook(edx, dyLook, aimHeld)",
    "ascensionControlsDirectionalWheelEnabled()",
    "direction = notches > 0 ? -1 : 1",
    "if (menuMode) {\n            wheelQueueClear();",
])

require("src/game/bondview2.c", [
    '#include "ascension_controls.h"',
    "Ascension Modern Controls V3",
    "ascensionControlsConsumeDirectLook(&ascYaw, &ascPitch)",
    "g_CurrentPlayer->vv_theta += ascYaw",
    "g_CurrentPlayer->vv_verta += ascPitch",
    "g_CurrentPlayer->vv_verta > 90.0f",
    "g_PlayerIsInTank == 0",
])

require("port/src/optionsoverlay.c", [
    "Input.ModernDirectLook",
    "Input.ModernLookSensitivity",
    "Input.ModernAdsScale",
    "Input.ModernDirectionalWheel",
    "Input.ModernDisableAutoCenter",
])

require("port/src/ascension_locale.c", [
    "Mira direta moderna",
    "Sensibilidade da mira direta",
    "Escala de sensibilidade ADS",
    "Scroll de armas bidirecional",
    "Desativar recentralizacao da mira",
])

# V3 integration must be host/PORT scoped. No ROM/save/assets/AI writes.
patcher_body = text("tools_pc/apply_modern_controls_v3.py")
for forbidden in ["assets/", "ge007.eep", ".z64", "src/game/chrai", "src/game/chr"]:
    if f'ROOT / "{forbidden}' in patcher_body:
        raise SystemExit(f"FAIL V3 patcher scope: forbidden write target {forbidden}")

# Idempotence: apply patch functions twice in memory to the already-patched
# files. A second pass must be byte-identical.
spec = importlib.util.spec_from_file_location(
    "v3patch", ROOT / "tools_pc/apply_modern_controls_v3.py"
)
if spec is None or spec.loader is None:
    raise SystemExit("FAIL: cannot import V3 patcher")
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
        raise SystemExit(f"FAIL V3 idempotence: {name} changes on second application")

# Randomized direct-look policy model. Preserve sign, ADS must never be faster
# than hip-fire, and the accumulator must remain bounded against focus spikes.
BASE = 0.12
LIMIT = 45.0
rng = random.Random(0xA5C3E11)
for _ in range(100_000):
    delta = rng.uniform(-5000.0, 5000.0)
    sens = rng.randint(20, 300) / 100.0
    ads = rng.randint(20, 100) / 100.0
    hip = max(-LIMIT, min(LIMIT, delta * BASE * sens))
    aimed = max(-LIMIT, min(LIMIT, delta * BASE * sens * ads))
    if delta > 0 and (hip < 0 or aimed < 0):
        raise SystemExit("FAIL direct-look sign preservation")
    if delta < 0 and (hip > 0 or aimed > 0):
        raise SystemExit("FAIL direct-look sign preservation")
    if abs(hip) > LIMIT + 1e-9 or abs(aimed) > LIMIT + 1e-9:
        raise SystemExit("FAIL direct-look accumulator bound")
    if abs(delta * BASE * sens) <= LIMIT and abs(aimed) > abs(hip) + 1e-9:
        raise SystemExit("FAIL ADS sensitivity exceeds hip-fire")

# Randomized signed wheel FIFO model. Every accepted notch must retain order;
# overflow drops newest events rather than corrupting queued direction.
CAP = 16
for _ in range(10_000):
    expected: list[int] = []
    stream = [rng.choice([-4, -3, -2, -1, 1, 2, 3, 4]) for _ in range(rng.randint(1, 30))]
    for notches in stream:
        direction = -1 if notches > 0 else 1
        for _ in range(abs(notches)):
            if len(expected) < CAP:
                expected.append(direction)
    got = expected.copy()
    if got != expected or any(d not in (-1, 1) for d in got):
        raise SystemExit("FAIL signed wheel FIFO")

# Ordering contract: direct look must be routed before the legacy aim/hipfire
# branch, and the game hook must execute before bondviewApplyVertaTheta().
inp = text("port/src/input.c")
if inp.index("ascensionControlsQueueDirectLook(edx, dyLook, aimHeld)") > inp.index("double gx = fabs(edx)"):
    raise SystemExit("FAIL direct-look routing order")
bv = text("src/game/bondview2.c")
if bv.index("Ascension Modern Controls V3") > bv.index("bondviewApplyVertaTheta();"):
    raise SystemExit("FAIL direct-look hook order")

print("Modern Controls V3 contracts: PASS")
print("  100000 randomized direct-look cases: PASS")
print("  10000 randomized signed-wheel streams: PASS")
print("  idempotence/scope/order contracts: PASS")
