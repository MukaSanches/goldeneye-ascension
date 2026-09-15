#include <math.h>
#include <string.h>

#include <SDL.h>

#include "platform.h"
#include "config.h"
#include "ascension_controls.h"

/* 0 = Classic, 1 = Hybrid, 2 = Modern. Classic remains the safe default for
 * new configs; the F10 preset row can opt into V2 without mutating ROM/save
 * data or the original GoldenEye controller ABI. */
static int s_controlPreset = ASCENSION_CONTROLS_CLASSIC;
static int s_dedicatedCrouch = 1;

/* Modern Controls V2: host-input policy only. */
static int s_modernAimToggle = 0;
static int s_modernRawMouse = 1;
static int s_modernMouseResponse = ASCENSION_MOUSE_PRECISION;
static int s_modernWheelQueue = 1;

/* Transient state is deliberately not serialized. */
static int s_aimLatched = 0;
static int s_prevPhysicalAim = 0;

PD_CONSTRUCTOR static void ascensionControlsConfigInit(void)
{
    configRegisterInt("Input.ControlPreset", &s_controlPreset,
                      ASCENSION_CONTROLS_CLASSIC, ASCENSION_CONTROLS_MODERN);
    configRegisterInt("Input.DedicatedCrouch", &s_dedicatedCrouch, 0, 1);
    configRegisterInt("Input.ModernAimToggle", &s_modernAimToggle, 0, 1);
    configRegisterInt("Input.ModernRawMouse", &s_modernRawMouse, 0, 1);
    configRegisterInt("Input.ModernMouseResponse", &s_modernMouseResponse,
                      ASCENSION_MOUSE_LEGACY, ASCENSION_MOUSE_PRECISION);
    configRegisterInt("Input.ModernWheelQueue", &s_modernWheelQueue, 0, 1);
}

int ascensionControlsPreset(void)
{
    return s_controlPreset;
}

int ascensionControlsIsModern(void)
{
    return s_controlPreset == ASCENSION_CONTROLS_MODERN;
}

int ascensionControlsDedicatedCrouchHeld(void)
{
    if (!s_dedicatedCrouch || s_controlPreset == ASCENSION_CONTROLS_CLASSIC)
        return 0;

    const Uint8 *ks = SDL_GetKeyboardState(NULL);
    if (!ks)
        return 0;

    /* Hybrid: C only, preserving legacy Left Ctrl fire.
     * Modern: either Ctrl or C becomes a dedicated crouch hold. */
    if (s_controlPreset == ASCENSION_CONTROLS_HYBRID)
        return ks[SDL_SCANCODE_C] != 0;

    return ks[SDL_SCANCODE_LCTRL] || ks[SDL_SCANCODE_RCTRL] ||
           ks[SDL_SCANCODE_C];
}

void ascensionControlsResetTransient(void)
{
    s_aimLatched = 0;
    s_prevPhysicalAim = 0;
}

int ascensionControlsResolveAim(int physicalAimHeld, int forceAimHeld, int menuMode)
{
    physicalAimHeld = physicalAimHeld ? 1 : 0;
    forceAimHeld = forceAimHeld ? 1 : 0;

    if (menuMode) {
        ascensionControlsResetTransient();
        return forceAimHeld;
    }

    if (!ascensionControlsIsModern() || !s_modernAimToggle) {
        s_prevPhysicalAim = physicalAimHeld;
        s_aimLatched = 0;
        return physicalAimHeld || forceAimHeld;
    }

    /* Toggle only on a fresh physical aim edge. Forced aim (crouch bridge) is
     * intentionally excluded so crouching never flips the player's ADS latch. */
    if (physicalAimHeld && !s_prevPhysicalAim)
        s_aimLatched = !s_aimLatched;
    s_prevPhysicalAim = physicalAimHeld;

    return s_aimLatched || forceAimHeld;
}

/* Adaptive-precision response for raw mouse deltas. It only runs in Modern.
 * Small deltas are damped for pixel-level aiming, medium motion stays close to
 * linear, and large flicks retain/slightly gain speed. There is no dead zone,
 * so stopping the mouse still releases immediately. */
double ascensionControlsShapeMouseDelta(double delta, int aiming)
{
    if (!ascensionControlsIsModern() || s_modernMouseResponse == ASCENSION_MOUSE_LEGACY)
        return delta;
    if (s_modernMouseResponse == ASCENSION_MOUSE_LINEAR)
        return delta;

    double a = fabs(delta);
    if (a <= 0.0)
        return 0.0;

    double scale;
    if (a < 1.0) {
        scale = aiming ? 0.52 : 0.62;
    } else if (a < 4.0) {
        double t = (a - 1.0) / 3.0;
        double lo = aiming ? 0.52 : 0.62;
        scale = lo + (0.90 - lo) * t;
    } else if (a < 10.0) {
        double t = (a - 4.0) / 6.0;
        scale = 0.90 + 0.10 * t;
    } else {
        double t = (a - 10.0) / 30.0;
        if (t > 1.0) t = 1.0;
        scale = 1.0 + 0.12 * t;
    }

    return delta < 0.0 ? -(a * scale) : (a * scale);
}

int ascensionControlsWantsRawMouse(void)
{
    return ascensionControlsIsModern() && s_modernRawMouse;
}

int ascensionControlsWheelQueueEnabled(void)
{
    return ascensionControlsIsModern() && s_modernWheelQueue;
}

int ascensionControlsMouseResponse(void)
{
    return s_modernMouseResponse;
}

int ascensionControlsAimToggleEnabled(void)
{
    return ascensionControlsIsModern() && s_modernAimToggle;
}
