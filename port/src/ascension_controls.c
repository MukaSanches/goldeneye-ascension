#include <math.h>
#include <string.h>

#include <SDL.h>

#include "platform.h"
#include "config.h"
#include "ascension_controls.h"

static int s_controlPreset = ASCENSION_CONTROLS_CLASSIC;
static int s_dedicatedCrouch = 1;

/* Modern Controls V2 policy. */
static int s_modernAimToggle = 0;
static int s_modernRawMouse = 1;
static int s_modernMouseResponse = ASCENSION_MOUSE_PRECISION;
static int s_modernWheelQueue = 1;

/* Modern Controls V3 policy. */
static int s_modernDirectLook = 1;
static int s_modernLookSensitivity = 100;
static int s_modernAdsScale = 65;
static int s_modernDirectionalWheel = 1;
static int s_modernDisableAutoCenter = 1;

/* Modern Controls V4 policy. These affect controller 0 only and are ignored
 * outside the Modern preset. The legacy gamepad path is byte-for-byte owned by
 * input.c when this bridge is disabled. */
static int s_modernGamepad = 1;
static int s_modernPadDeadzone = 14;          /* radial percent */
static int s_modernPadResponse = ASCENSION_PAD_PRECISION;
static int s_modernPadLookSensitivity = 100; /* percent */
static int s_modernPadAdsScale = 65;          /* percent of hip-fire */
static int s_modernPadInvertX = 0;
static int s_modernPadInvertY = 0;

/* Transient state is deliberately not serialized. */
static int s_aimLatched = 0;
static int s_prevPhysicalAim = 0;
static double s_pendingYawDegrees = 0.0;
static double s_pendingPitchDegrees = 0.0;
static float s_padMoveX = 0.0f;
static float s_padMoveY = 0.0f;
static float s_padLookYaw = 0.0f;
static float s_padLookPitch = 0.0f;

#define ASCENSION_DIRECT_LOOK_DEG_PER_COUNT 0.12
#define ASCENSION_DIRECT_LOOK_ACCUM_LIMIT   45.0
/* Degrees applied at full stick for one nominal 60 Hz game tick. bondview2.c
 * multiplies this rate by g_GlobalTimerDelta, keeping stick look rate-based. */
#define ASCENSION_PAD_LOOK_DEG_PER_TICK      2.75

static double clampDouble(double value, double lo, double hi)
{
    if (value < lo) return lo;
    if (value > hi) return hi;
    return value;
}

static void clearPadTransient(void)
{
    s_padMoveX = 0.0f;
    s_padMoveY = 0.0f;
    s_padLookYaw = 0.0f;
    s_padLookPitch = 0.0f;
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

    configRegisterInt("Input.ModernGamepad", &s_modernGamepad, 0, 1);
    configRegisterInt("Input.ModernPadDeadzone", &s_modernPadDeadzone, 0, 40);
    configRegisterInt("Input.ModernPadResponse", &s_modernPadResponse,
                      ASCENSION_PAD_LINEAR, ASCENSION_PAD_PRECISION);
    configRegisterInt("Input.ModernPadLookSensitivity", &s_modernPadLookSensitivity, 20, 300);
    configRegisterInt("Input.ModernPadAdsScale", &s_modernPadAdsScale, 20, 100);
    configRegisterInt("Input.ModernPadInvertX", &s_modernPadInvertX, 0, 1);
    configRegisterInt("Input.ModernPadInvertY", &s_modernPadInvertY, 0, 1);
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
    clearPadTransient();
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

    if (physicalAimHeld && !s_prevPhysicalAim)
        s_aimLatched = !s_aimLatched;
    s_prevPhysicalAim = physicalAimHeld;
    return s_aimLatched || forceAimHeld;
}

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
    return ascensionControlsIsModern() && s_modernDisableAutoCenter &&
           (s_modernDirectLook || s_modernGamepad);
}

void ascensionControlsQueueDirectLook(double dx, double dy, int aiming)
{
    if (!ascensionControlsDirectLookEnabled())
        return;

    double sensitivity = (double)s_modernLookSensitivity / 100.0;
    double adsScale = aiming ? (double)s_modernAdsScale / 100.0 : 1.0;
    double degreesPerCount = ASCENSION_DIRECT_LOOK_DEG_PER_COUNT * sensitivity * adsScale;

    s_pendingYawDegrees += dx * degreesPerCount;
    s_pendingPitchDegrees -= dy * degreesPerCount;

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

int ascensionControlsModernGamepadEnabled(void)
{
    return ascensionControlsIsModern() && s_modernGamepad;
}

int ascensionControlsPadResponse(void)
{
    return s_modernPadResponse;
}

static void shapePadPair(int rawX, int rawY, float *outX, float *outY)
{
    double x = rawX < 0 ? (double)rawX / 32768.0 : (double)rawX / 32767.0;
    double y = rawY < 0 ? (double)rawY / 32768.0 : (double)rawY / 32767.0;
    double mag = sqrt(x * x + y * y);
    double deadzone = (double)s_modernPadDeadzone / 100.0;

    if (mag <= deadzone || mag <= 0.000001) {
        *outX = 0.0f;
        *outY = 0.0f;
        return;
    }

    if (mag > 1.0) {
        x /= mag;
        y /= mag;
        mag = 1.0;
    }

    double shaped = (mag - deadzone) / (1.0 - deadzone);
    shaped = clampDouble(shaped, 0.0, 1.0);
    if (s_modernPadResponse == ASCENSION_PAD_PRECISION)
        shaped = pow(shaped, 1.45);

    double scale = shaped / mag;
    *outX = (float)(x * scale);
    *outY = (float)(y * scale);
}

void ascensionControlsQueueGamepadAxes(int lx, int ly, int rx, int ry, int aiming)
{
    if (!ascensionControlsModernGamepadEnabled()) {
        clearPadTransient();
        return;
    }

    float moveX = 0.0f, moveY = 0.0f;
    float lookX = 0.0f, lookY = 0.0f;
    shapePadPair(lx, ly, &moveX, &moveY);
    shapePadPair(rx, ry, &lookX, &lookY);

    if (s_modernPadInvertX)
        lookX = -lookX;
    if (s_modernPadInvertY)
        lookY = -lookY;

    s_padMoveX = moveX;
    s_padMoveY = -moveY; /* SDL up is negative; GoldenEye forward is positive. */

    double sensitivity = (double)s_modernPadLookSensitivity / 100.0;
    double adsScale = aiming ? (double)s_modernPadAdsScale / 100.0 : 1.0;
    double degrees = ASCENSION_PAD_LOOK_DEG_PER_TICK * sensitivity * adsScale;
    s_padLookYaw = (float)((double)lookX * degrees);
    /* SDL down is positive; GoldenEye vv_verta decreases when looking down. */
    s_padLookPitch = (float)(-(double)lookY * degrees);
}

int ascensionControlsConsumeGamepadMove(float *strafe, float *walk)
{
    float x = s_padMoveX;
    float y = s_padMoveY;
    s_padMoveX = 0.0f;
    s_padMoveY = 0.0f;

    if (strafe) *strafe = 0.0f;
    if (walk) *walk = 0.0f;
    if (!ascensionControlsModernGamepadEnabled())
        return 0;

    if (strafe) *strafe = x;
    if (walk) *walk = y;
    return fabsf(x) > 0.0001f || fabsf(y) > 0.0001f;
}

int ascensionControlsConsumeGamepadLook(float *yawDegreesPerTick,
                                        float *pitchDegreesPerTick)
{
    float yaw = s_padLookYaw;
    float pitch = s_padLookPitch;
    s_padLookYaw = 0.0f;
    s_padLookPitch = 0.0f;

    if (yawDegreesPerTick) *yawDegreesPerTick = 0.0f;
    if (pitchDegreesPerTick) *pitchDegreesPerTick = 0.0f;
    if (!ascensionControlsModernGamepadEnabled())
        return 0;

    if (yawDegreesPerTick) *yawDegreesPerTick = yaw;
    if (pitchDegreesPerTick) *pitchDegreesPerTick = pitch;
    return fabsf(yaw) > 0.0001f || fabsf(pitch) > 0.0001f;
}
