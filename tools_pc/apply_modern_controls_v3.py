#!/usr/bin/env python3
"""Apply Ascension Modern Controls V3 on top of the validated V2 bridge.

V3 scope:
- direct mouse camera look in Modern (sub-pixel, FOV-independent host delta);
- ADS sensitivity multiplier for direct look;
- optional Modern auto-centre suppression;
- signed, FIFO mouse-wheel weapon cycling (up=previous, down=next);
- menu-safe wheel queue (never leaks weapon pulses into front-end menus);
- PORT-only bondview hook; N64/Classic/Hybrid behavior remains untouched.

The script is fail-closed and idempotent. It expects V2 integration to already
be present; run apply_modern_controls_v2.py first on a clean checkout.
"""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class PatchError(RuntimeError):
    pass


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        return text
    count = text.count(old)
    if count != 1:
        raise PatchError(f"{label}: expected exactly one anchor, found {count}")
    return text.replace(old, new, 1)


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise PatchError(f"{label}: required V2 anchor missing")


def patch_input(text: str) -> str:
    require(text, "ascensionControlsShapeMouseDelta", "V2 mouse response")
    require(text, "wheelQueue", "V2 wheel queue")

    old_state = """#define WHEEL_PULSE_POLLS 2
#define WHEEL_GAP_POLLS   1
#define WHEEL_QUEUE_MAX  12
static int wheelPulse = 0;
static int wheelGap   = 0;
static int wheelQueue = 0;
"""
    new_state = """#define WHEEL_PULSE_POLLS 2
#define WHEEL_GAP_POLLS   1
#define WHEEL_QUEUE_MAX  16
static int wheelPulse = 0;
static int wheelGap = 0;
static int wheelDirection = 1; /* +1 next/forward, -1 previous/back */
static signed char wheelQueue[WHEEL_QUEUE_MAX];
static int wheelQueueHead = 0;
static int wheelQueueCount = 0;

static void wheelQueueClear(void)
{
    wheelPulse = 0;
    wheelGap = 0;
    wheelDirection = 1;
    wheelQueueHead = 0;
    wheelQueueCount = 0;
}

static void wheelQueuePush(int direction)
{
    direction = direction < 0 ? -1 : 1;
    if (wheelQueueCount >= WHEEL_QUEUE_MAX)
        return;
    int tail = (wheelQueueHead + wheelQueueCount) % WHEEL_QUEUE_MAX;
    wheelQueue[tail] = (signed char)direction;
    wheelQueueCount++;
}

static int wheelQueuePop(void)
{
    if (wheelQueueCount <= 0)
        return 0;
    int direction = wheelQueue[wheelQueueHead] < 0 ? -1 : 1;
    wheelQueueHead = (wheelQueueHead + 1) % WHEEL_QUEUE_MAX;
    wheelQueueCount--;
    return direction;
}
"""
    text = replace_once(text, old_state, new_state, "V3 signed wheel FIFO state")

    old_poll = """        /* Modern V2: preserve every wheel notch and insert a release gap so
         * GoldenEye sees clean A-button edges even during fast scrolling. */
        if (wheelPulse > 0) {
            button |= GE_CONT_A;
            wheelPulse--;
            if (wheelPulse == 0) wheelGap = WHEEL_GAP_POLLS;
        } else if (wheelGap > 0) {
            wheelGap--;
        } else if (wheelQueue > 0) {
            wheelQueue--;
            wheelPulse = WHEEL_PULSE_POLLS - 1;
            button |= GE_CONT_A;
        }
"""
    new_poll = """        /* Modern V3: wheel input is stage-only and FIFO. A normal A pulse
         * advances inventory. A+Z is GoldenEye 1.1's native back-step chord;
         * A also suppresses triggerOn, so the reverse pulse does not fire. */
        if (menuMode) {
            wheelQueueClear();
        } else if (wheelPulse > 0) {
            button |= GE_CONT_A;
            if (wheelDirection < 0)
                button |= GE_CONT_G;
            wheelPulse--;
            if (wheelPulse == 0)
                wheelGap = WHEEL_GAP_POLLS;
        } else if (wheelGap > 0) {
            wheelGap--;
        } else if (wheelQueueCount > 0) {
            wheelDirection = wheelQueuePop();
            wheelPulse = WHEEL_PULSE_POLLS - 1;
            button |= GE_CONT_A;
            if (wheelDirection < 0)
                button |= GE_CONT_G;
        }
"""
    text = replace_once(text, old_poll, new_poll, "V3 directional wheel polling")

    old_look = """            } else if (aimHeld) {
                double gx = fabs(edx)    * (mouseAimSpeed / 100.0) * AIM_GAIN;
                double gy = fabs(dyLook) * (mouseAimSpeed / 100.0) * AIM_GAIN;
"""
    new_look = """            } else if (ascensionControlsDirectLookEnabled()) {
                /* V3 direct look: preserve fractional mouse motion and bypass
                 * GoldenEye's N64 stick turn/pitch quantisation. The PORT hook
                 * consumes these degrees once inside MoveBond. */
                ascensionControlsQueueDirectLook(edx, dyLook, aimHeld);
                hipPitchPhase = 0.0;
            } else if (aimHeld) {
                double gx = fabs(edx)    * (mouseAimSpeed / 100.0) * AIM_GAIN;
                double gy = fabs(dyLook) * (mouseAimSpeed / 100.0) * AIM_GAIN;
"""
    text = replace_once(text, old_look, new_look, "V3 direct look routing")

    old_suspend = """    ascensionControlsResetTransient();
    wheelPulse = wheelGap = wheelQueue = 0;
"""
    new_suspend = """    ascensionControlsResetTransient();
    wheelQueueClear();
"""
    text = replace_once(text, old_suspend, new_suspend, "V3 transient reset")

    old_post = """void inputPostWheel(int notches)
{
    if (notches < 0) notches = -notches;   /* native GE path cycles forward */
    if (notches <= 0) return;

    if (ascensionControlsWheelQueueEnabled()) {
        wheelQueue += notches;
        if (wheelQueue > WHEEL_QUEUE_MAX) wheelQueue = WHEEL_QUEUE_MAX;
    } else {
        wheelPulse = WHEEL_PULSE_POLLS;
        wheelGap = wheelQueue = 0;
    }
}
"""
    new_post = """void inputPostWheel(int notches)
{
    if (notches == 0)
        return;

    if (ascensionControlsWheelQueueEnabled()) {
        int count = notches < 0 ? -notches : notches;
        int direction = 1;
        if (ascensionControlsDirectionalWheelEnabled()) {
            /* SDL wheel up is positive: previous weapon. Down: next weapon. */
            direction = notches > 0 ? -1 : 1;
        }
        while (count-- > 0)
            wheelQueuePush(direction);
    } else {
        wheelQueueClear();
        wheelDirection = 1;
        wheelPulse = WHEEL_PULSE_POLLS;
    }
}
"""
    text = replace_once(text, old_post, new_post, "V3 signed wheel posting")
    return text


def patch_bondview(text: str) -> str:
    old_include = """#ifdef PORT
#include <stdio.h>
#include <stdlib.h>
#endif
"""
    new_include = """#ifdef PORT
#include <stdio.h>
#include <stdlib.h>
#include "ascension_controls.h"
#endif
"""
    text = replace_once(text, old_include, new_include, "V3 PORT controls include")

    old_hook = """    bondviewApplyVertaTheta();

    // Handle crouching, and animation between standing and crouching.
"""
    new_hook = """#ifdef PORT
    /* Ascension Modern Controls V3: apply physical mouse displacement directly
     * to the view in degrees. This happens after the original N64 input model
     * has produced its movement state but before the orientation matrix is
     * rebuilt, so movement/collision/weapons remain native while mouse look is
     * no longer quantised through an 8-bit N64 stick. */
    if (ascensionControlsDirectLookEnabled() && g_PlayerIsInTank == 0) {
        float ascYaw = 0.0f;
        float ascPitch = 0.0f;

        if (ascensionControlsDisableAutoCenter()) {
            g_CurrentPlayer->docentreupdown = FALSE;
            g_CurrentPlayer->automovecentre = FALSE;
            g_CurrentPlayer->movecentrerelease = TRUE;
        }

        if (g_CurrentPlayer->watch_animation_state == WATCH_ANIMATION_0x0
            && lvlGetControlsLockedFlag() == 0
            && ascensionControlsConsumeDirectLook(&ascYaw, &ascPitch)) {
            g_CurrentPlayer->vv_theta += ascYaw;
            g_CurrentPlayer->vv_verta += ascPitch;

            while (g_CurrentPlayer->vv_theta < 0.0f)
                g_CurrentPlayer->vv_theta += 360.0f;
            while (g_CurrentPlayer->vv_theta >= 360.0f)
                g_CurrentPlayer->vv_theta -= 360.0f;

            if (g_CurrentPlayer->vv_verta > 90.0f)
                g_CurrentPlayer->vv_verta = 90.0f;
            else if (g_CurrentPlayer->vv_verta < -90.0f)
                g_CurrentPlayer->vv_verta = -90.0f;

            /* Direct displacement should stop when the mouse stops; discard
             * residual vertical acceleration from the legacy pitch model. */
            g_CurrentPlayer->speedverta = 0.0f;
        }
    }
#endif

    bondviewApplyVertaTheta();

    // Handle crouching, and animation between standing and crouching.
"""
    return replace_once(text, old_hook, new_hook, "V3 direct-look game hook")


def patch_overlay(text: str) -> str:
    require(text, 'Input.ModernWheelQueue', "V2 F10 rows")
    anchor = """    { .key=\"Input.ModernWheelQueue\", .label=\"Reliable weapon wheel\",
      .help=\"Modern only: queues fast wheel notches as clean weapon-cycle taps.\",
      .category=CAT_INPUT, .kind=ROW_TOGGLE, .step=1, .names=kOnOff, .resetValue=1 },

"""
    addition = anchor + """    { .key=\"Input.ModernDirectLook\", .label=\"Modern direct look\",
      .help=\"Modern only: direct sub-pixel mouse camera control without N64 stick quantisation.\",
      .category=CAT_INPUT, .kind=ROW_TOGGLE, .step=1, .names=kOnOff, .resetValue=1 },

    { .key=\"Input.ModernLookSensitivity\", .label=\"Direct look sensitivity\",
      .help=\"Modern direct-look sensitivity percentage.\",
      .category=CAT_INPUT, .kind=ROW_SLIDER, .step=5,
      .uiMin=20, .uiMax=300, .resetValue=100 },

    { .key=\"Input.ModernAdsScale\", .label=\"ADS sensitivity scale\",
      .help=\"Modern direct-look sensitivity while aiming, as a percentage of hip-fire.\",
      .category=CAT_INPUT, .kind=ROW_SLIDER, .step=5,
      .uiMin=20, .uiMax=100, .resetValue=65 },

    { .key=\"Input.ModernDirectionalWheel\", .label=\"Directional weapon wheel\",
      .help=\"Modern only: wheel up selects previous, wheel down selects next weapon.\",
      .category=CAT_INPUT, .kind=ROW_TOGGLE, .step=1, .names=kOnOff, .resetValue=1 },

    { .key=\"Input.ModernDisableAutoCenter\", .label=\"Disable look auto-center\",
      .help=\"Modern direct look keeps pitch where the mouse leaves it.\",
      .category=CAT_INPUT, .kind=ROW_TOGGLE, .step=1, .names=kOnOff, .resetValue=1 },

"""
    return replace_once(text, anchor, addition, "V3 F10 input rows")


def patch_locale(text: str) -> str:
    require(text, "Troca de arma confiavel", "V2 PT-BR strings")
    anchor = '    { "Ctrl/C crouches through GoldenEye\'s native crouch state machine.", "Ctrl/C agacha usando o sistema nativo de postura do GoldenEye." },\n'
    addition = anchor + """    { "Modern direct look", "Mira direta moderna" },
    { "Modern only: direct sub-pixel mouse camera control without N64 stick quantisation.", "Somente Moderno: controle direto da camera sem quantizacao do analogico do N64." },
    { "Direct look sensitivity", "Sensibilidade da mira direta" },
    { "Modern direct-look sensitivity percentage.", "Porcentagem de sensibilidade da mira direta moderna." },
    { "ADS sensitivity scale", "Escala de sensibilidade ADS" },
    { "Modern direct-look sensitivity while aiming, as a percentage of hip-fire.", "Sensibilidade ao mirar como porcentagem da sensibilidade normal." },
    { "Directional weapon wheel", "Scroll de armas bidirecional" },
    { "Modern only: wheel up selects previous, wheel down selects next weapon.", "Somente Moderno: scroll para cima volta a arma e para baixo avanca." },
    { "Disable look auto-center", "Desativar recentralizacao da mira" },
    { "Modern direct look keeps pitch where the mouse leaves it.", "A mira direta mantem a altura onde o mouse foi deixado." },
"""
    return replace_once(text, anchor, addition, "V3 PT-BR strings")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="validate without writing")
    ap.add_argument("--no-backup", action="store_true")
    args = ap.parse_args()

    paths = {
        "input": ROOT / "port/src/input.c",
        "bondview": ROOT / "src/game/bondview2.c",
        "overlay": ROOT / "port/src/optionsoverlay.c",
        "locale": ROOT / "port/src/ascension_locale.c",
    }
    original = {k: p.read_text(encoding="utf-8") for k, p in paths.items()}

    try:
        patched = {
            "input": patch_input(original["input"]),
            "bondview": patch_bondview(original["bondview"]),
            "overlay": patch_overlay(original["overlay"]),
            "locale": patch_locale(original["locale"]),
        }
    except PatchError as exc:
        raise SystemExit(f"ERROR: {exc}; no file written")

    required = {
        "input": ["wheelQueuePush", "ascensionControlsQueueDirectLook", "ascensionControlsDirectionalWheelEnabled"],
        "bondview": ["ascensionControlsConsumeDirectLook", "Ascension Modern Controls V3"],
        "overlay": ["Input.ModernDirectLook", "Input.ModernLookSensitivity", "Input.ModernAdsScale",
                    "Input.ModernDirectionalWheel", "Input.ModernDisableAutoCenter"],
        "locale": ["Mira direta moderna", "Scroll de armas bidirecional", "Escala de sensibilidade ADS"],
    }
    for kind, needles in required.items():
        for needle in needles:
            if needle not in patched[kind]:
                raise SystemExit(f"ERROR: validation failed: {kind} missing {needle!r}; no file written")

    changed = [k for k in paths if patched[k] != original[k]]
    if args.check:
        print("Modern Controls V3 preflight: PASS")
        print("Would update:", ", ".join(str(paths[k].relative_to(ROOT)) for k in changed) or "nothing (already applied)")
        return 0

    if not args.no_backup:
        for k in changed:
            bak = paths[k].with_suffix(paths[k].suffix + ".ascension-v3-backup")
            if not bak.exists():
                shutil.copy2(paths[k], bak)

    for k in changed:
        paths[k].write_text(patched[k], encoding="utf-8")

    print("Modern Controls V3 integration: PASS")
    for k in changed:
        print("UPDATED:", paths[k].relative_to(ROOT))
    if not changed:
        print("No changes needed; V3 integration already present.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
