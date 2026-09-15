#include <math.h>
#include <string.h>

#include <SDL.h>

#include "platform.h"
#include "config.h"
#include "ascension_controls.h"

/* 0 = Classic, 1 = Hybrid, 2 = Modern. Classic remains the safe default for
 * new configs; the F10 preset row opts into V2/V3 without mutating ROM/save
 * data or the original GoldenEye controller ABI. */
static int s_controlPreset = ASCENSION_CONTROLS_CLASSIC;
static int s_dedicatedCrouch = 1;

/* Modern Controls V2 policy. */
static int s_modernAimToggle = 0;
static int s_modernRawMouse = 1;
static int s_modernMouseResponse = ASCENSION_MOUSE_PRECISION;
static int s_modernWheelQueue = 1;

/* Modern Controls V3 policy. Direct look bypasses the N64 stick-turn curve for
 * mouse camera motion only. Keyboard movement, weapons, collision, AI and all
 * N64 gameplay state remain authoritative in the original game code. */
static int s_modernDirectLook = 1;
static int s_modernLookSensitivity = 100; /* percent of the tuned base */
static int s_modernAdsScale = 65;          /* percent of hip-fire look */
static int s_modernDirectionalWheel = 1;
static int s_modernDisableAutoCenter = 1;

/* Transient state is deliberately not serialized. */
static int s_aimLatched = 0;
static int s_prevPhysicalAim = 0;
static double s_pendingYawDegrees = 0.0;
static double s_pendingPitchDegrees = 0.0;

#define ASCENSION_DIRECT_LOOK_DEG_PER_COUNT 0.12
#define ASCENSION_DIRECT_LOOK_ACCUM_LIMIT   45.0

static double clampDouble(double value, double lo, double hi)
{
    if (value < lo) return lo;
    if (value > hi) return hi;
    return value;
}

PD_CONSTRUCTOR static void ascensionControlsConfigInit(void)
{
    configRegisterInt("Input.ControlPreset", &s_controlPreset, 0, 2);
    configRegisterInt("Input.DedicatedCrouch", &s_dedicatedCrouch, 0, 1);
    configRegisterInt("Input.ModernAimToggle", &s_modernAimToggle, 0, 1);
    configRegisterInt("Input.ModernRawMouse", &s_modernRawMouse, 0, 1);
    configRegisterInt("Input.ModernMouseResponse", &s_modernMouseResponse,
                      ASCENSION_MOUSE_LEGACY, ASCENSION_MOUSE_PRECISION);
    configRegisterInt("Input.ModernWheelQueue", &s_modernWheelQueue, 0, 1);

    configRegisterInt("Input.ModernDirectLook", &s_modernDirectLook, 0, 1);
    configRegisterInt("Input.ModernLookSensitivity", &s_modernLookSensitivity, 20, 300);
    configRegisterInt("Input.ModernAdsScale", &s_modernAdsScale, 20, 100);
    configRegisterInt("Input.ModernDirectionalWheel", &s_modernDirectionalWheel, 0, 1);
    configRegisterInt("Input.ModernDisableAutoCenter", &s_modernDisableAutoCenter, 0, 1);
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
    if (!ks) return 0;

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
    s_pendingYawDegrees = 0.0;
    s_pendingPitchDegrees = 0.0;
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
 * linear, and large flicks retain/slightly gain speed. There is no dead zone. */
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

int ascensionControlsDirectLookEnabled(void)
{
    return ascensionControlsIsModern() && s_modernDirectLook;
}

int ascensionControlsDirectionalWheelEnabled(void)
{
    return ascensionControlsIsModern() && s_modernDirectionalWheel;
}

int ascensionControlsDisableAutoCenter(void)
{
    return ascensionControlsDirectLookEnabled() && s_modernDisableAutoCenter;
}

void ascensionControlsQueueDirectLook(double dx, double dy, int aiming)
{
    if (!ascensionControlsDirectLookEnabled())
        return;

    double sensitivity = (double)s_modernLookSensitivity / 100.0;
    double adsScale = aiming ? (double)s_modernAdsScale / 100.0 : 1.0;
    double degreesPerCount = ASCENSION_DIRECT_LOOK_DEG_PER_COUNT * sensitivity * adsScale;

    s_pendingYawDegrees += dx * degreesPerCount;
    s_pendingPitchDegrees += dy * degreesPerCount;

    /* A focus/capture transition must never create a giant camera snap. The
     * normal input path drains SDL deltas too; this is an independent final
     * safety bound on the host/game bridge. */
    s_pendingYawDegrees = clampDouble(s_pendingYawDegrees,
                                      -ASCENSION_DIRECT_LOOK_ACCUM_LIMIT,
                                       ASCENSION_DIRECT_LOOK_ACCUM_LIMIT);
    s_pendingPitchDegrees = clampDouble(s_pendingPitchDegrees,
                                        -ASCENSION_DIRECT_LOOK_ACCUM_LIMIT,
                                         ASCENSION_DIRECT_LOOK_ACCUM_LIMIT);
}

int ascensionControlsConsumeDirectLook(float *yawDegrees, float *pitchDegrees)
{
    double yaw = s_pendingYawDegrees;
    double pitch = s_pendingPitchDegrees;
    s_pendingYawDegrees = 0.0;
    s_pendingPitchDegrees = 0.0;

    if (yawDegrees) *yawDegrees = 0.0f;
    if (pitchDegrees) *pitchDegrees = 0.0f;

    if (!ascensionControlsDirectLookEnabled())
        return 0;

    if (yawDegrees) *yawDegrees = (float)yaw;
    if (pitchDegrees) *pitchDegrees = (float)pitch;
    return yaw != 0.0 || pitch != 0.0;
}
