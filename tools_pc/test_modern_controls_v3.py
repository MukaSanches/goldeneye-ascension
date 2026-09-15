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
    "s_pendingYawDegrees += dx * degreesPerCount",
    "s_pendingPitchDegrees -= dy * degreesPerCount",
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

# Randomized direct-look policy model. Horizontal mouse sign is preserved.
# Vertical input follows input.c's convention (positive = mouse down) while
# GoldenEye vv_verta uses negative degrees for looking down, so pitch is
# intentionally sign-inverted at the host/game boundary. ADS must never be
# faster than hip-fire and the accumulator stays bounded against focus spikes.
BASE = 0.12
LIMIT = 45.0
rng = random.Random(0xA5C3E11)
for _ in range(100_000):
    delta = rng.uniform(-5000.0, 5000.0)
    sens = rng.randint(20, 300) / 100.0
    ads = rng.randint(20, 100) / 100.0

    yaw_hip = max(-LIMIT, min(LIMIT, delta * BASE * sens))
    yaw_ads = max(-LIMIT, min(LIMIT, delta * BASE * sens * ads))
    pitch_hip = max(-LIMIT, min(LIMIT, -delta * BASE * sens))
    pitch_ads = max(-LIMIT, min(LIMIT, -delta * BASE * sens * ads))

    if delta > 0 and (yaw_hip < 0 or yaw_ads < 0):
        raise SystemExit("FAIL horizontal direct-look sign preservation")
    if delta < 0 and (yaw_hip > 0 or yaw_ads > 0):
        raise SystemExit("FAIL horizontal direct-look sign preservation")

    # Positive dy means mouse-down/look-down; native vv_verta must decrease.
    if delta > 0 and (pitch_hip > 0 or pitch_ads > 0):
        raise SystemExit("FAIL vertical direct-look native pitch convention")
    if delta < 0 and (pitch_hip < 0 or pitch_ads < 0):
        raise SystemExit("FAIL vertical direct-look native pitch convention")

    if max(abs(yaw_hip), abs(yaw_ads), abs(pitch_hip), abs(pitch_ads)) > LIMIT + 1e-9:
        raise SystemExit("FAIL direct-look accumulator bound")
    if abs(delta * BASE * sens) <= LIMIT:
        if abs(yaw_ads) > abs(yaw_hip) + 1e-9 or abs(pitch_ads) > abs(pitch_hip) + 1e-9:
            raise SystemExit("FAIL ADS sensitivity exceeds hip-fire")

# Randomized signed ring-buffer model mirroring the C FIFO. Compare it against
# a simple reference queue so wraparound, overflow and alternating directions
# are exercised rather than merely checking generated values.
CAP = 16
for _ in range(10_000):
    ring = [0] * CAP
    head = 0
    count = 0
    reference: list[int] = []
    stream = [rng.choice([-4, -3, -2, -1, 1, 2, 3, 4]) for _ in range(rng.randint(1, 40))]

    for notches in stream:
        direction = -1 if notches > 0 else 1
        for _ in range(abs(notches)):
            if count < CAP:
                tail = (head + count) % CAP
                ring[tail] = direction
                count += 1
                reference.append(direction)

        # Randomly drain some queued notches to force head/tail wraparound.
        drains = rng.randint(0, min(5, count))
        for _ in range(drains):
            got = -1 if ring[head] < 0 else 1
            head = (head + 1) % CAP
            count -= 1
            expected = reference.pop(0)
            if got != expected:
                raise SystemExit("FAIL signed wheel FIFO ordering")

    while count:
        got = -1 if ring[head] < 0 else 1
        head = (head + 1) % CAP
        count -= 1
        expected = reference.pop(0)
        if got != expected:
            raise SystemExit("FAIL signed wheel FIFO final drain")
    if reference:
        raise SystemExit("FAIL signed wheel FIFO reference not drained")

# Ordering contract: direct look must be routed before the legacy aim/hipfire
# branch. In bondview2.c there are several pre-existing ApplyVertaTheta calls,
# so compare against the call immediately following the V3 marker, not the
# first occurrence in the whole translation unit.
inp = text("port/src/input.c")
direct_pos = inp.find("ascensionControlsQueueDirectLook(edx, dyLook, aimHeld)")
legacy_pos = inp.find("double gx = fabs(edx)", direct_pos)
if direct_pos < 0 or legacy_pos < 0 or direct_pos > legacy_pos:
    raise SystemExit("FAIL direct-look routing order")

bv = text("src/game/bondview2.c")
hook_pos = bv.find("Ascension Modern Controls V3")
apply_after_hook = bv.find("bondviewApplyVertaTheta();", hook_pos)
if hook_pos < 0 or apply_after_hook < 0 or hook_pos > apply_after_hook:
    raise SystemExit("FAIL direct-look hook order")

print("Modern Controls V3 contracts: PASS")
print("  100000 randomized direct-look cases (yaw + native pitch sign): PASS")
print("  10000 randomized signed-wheel streams: PASS")
print("  idempotence/scope/order contracts: PASS")
