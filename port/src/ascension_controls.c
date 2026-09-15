#include <math.h>
#include <stdio.h>
#include <string.h>

#include <SDL.h>

#include "platform.h"
#include "config.h"
#include "ascension_watch.h"
#define ASCENSION_CONTROLS_NO_SDL_HOOK
#include "ascension_controls.h"

/* current_menu is the same frontend/stage mode gate already used by input.c. */
extern int current_menu;
extern int lvlGetControlsLockedFlag(void);
#define GE_MENU_RUN_STAGE 11
#define GE_MENU_INVALID   (-1)

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

/* Modern Controls V4 policy. */
static int s_modernGamepad = 1;
static int s_modernPadDeadzone = 14;
static int s_modernPadResponse = ASCENSION_PAD_PRECISION;
static int s_modernPadLookSensitivity = 100;
static int s_modernPadAdsScale = 65;
static int s_modernPadInvertX = 0;
static int s_modernPadInvertY = 0;
static int s_modernPadSouthpaw = 0;
static int s_modernPadSwapTriggers = 0;

enum AscensionPadBind {
    ASC_PAD_BIND_ACTION,
    ASC_PAD_BIND_CANCEL,
    ASC_PAD_BIND_CROUCH,
    ASC_PAD_BIND_NEXT_WEAPON,
    ASC_PAD_BIND_PREV_WEAPON,
    ASC_PAD_BIND_ALT_ACTION,
    ASC_PAD_BIND_START,
    ASC_PAD_BIND_COUNT,
};

static const struct {
    const char *key;
    int def;
} kPadBindDefs[ASC_PAD_BIND_COUNT] = {
    { "Input.ModernPadBind.Action",     SDL_CONTROLLER_BUTTON_A },
    { "Input.ModernPadBind.Cancel",     SDL_CONTROLLER_BUTTON_X },
    { "Input.ModernPadBind.Crouch",     SDL_CONTROLLER_BUTTON_B },
    { "Input.ModernPadBind.NextWeapon", SDL_CONTROLLER_BUTTON_Y },
    { "Input.ModernPadBind.PrevWeapon", SDL_CONTROLLER_BUTTON_LEFTSHOULDER },
    { "Input.ModernPadBind.AltAction",  SDL_CONTROLLER_BUTTON_RIGHTSHOULDER },
    { "Input.ModernPadBind.Start",      SDL_CONTROLLER_BUTTON_START },
};

static int s_padBind[ASC_PAD_BIND_COUNT] = {
    SDL_CONTROLLER_BUTTON_A,
    SDL_CONTROLLER_BUTTON_X,
    SDL_CONTROLLER_BUTTON_B,
    SDL_CONTROLLER_BUTTON_Y,
    SDL_CONTROLLER_BUTTON_LEFTSHOULDER,
    SDL_CONTROLLER_BUTTON_RIGHTSHOULDER,
    SDL_CONTROLLER_BUTTON_START,
};

/* Transient host state; never serialized into GoldenEye saves. */
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
    configRegisterInt("Input.ModernPadSouthpaw", &s_modernPadSouthpaw, 0, 1);
    configRegisterInt("Input.ModernPadSwapTriggers", &s_modernPadSwapTriggers, 0, 1);

    for (int i = 0; i < ASC_PAD_BIND_COUNT; ++i)
        configRegisterInt(kPadBindDefs[i].key, &s_padBind[i],
                          0, SDL_CONTROLLER_BUTTON_MAX - 1);
}

int ascensionControlsPreset(void) { return s_controlPreset; }
int ascensionControlsIsModern(void) { return s_controlPreset == ASCENSION_CONTROLS_MODERN; }

int ascensionControlsDedicatedCrouchHeld(void)
{
    if (!s_dedicatedCrouch || s_controlPreset == ASCENSION_CONTROLS_CLASSIC)
        return 0;
    const Uint8 *ks = SDL_GetKeyboardState(NULL);
    if (!ks) return 0;
    if (s_controlPreset == ASCENSION_CONTROLS_HYBRID)
        return ks[SDL_SCANCODE_C] != 0;
    return ks[SDL_SCANCODE_LCTRL] || ks[SDL_SCANCODE_RCTRL] || ks[SDL_SCANCODE_C];
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
    if (a <= 0.0) return 0.0;
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

int ascensionControlsWantsRawMouse(void) { return ascensionControlsIsModern() && s_modernRawMouse; }
int ascensionControlsWheelQueueEnabled(void) { return ascensionControlsIsModern() && s_modernWheelQueue; }
int ascensionControlsMouseResponse(void) { return s_modernMouseResponse; }
int ascensionControlsAimToggleEnabled(void) { return ascensionControlsIsModern() && s_modernAimToggle; }
int ascensionControlsDirectLookEnabled(void) { return ascensionControlsIsModern() && s_modernDirectLook; }
int ascensionControlsDirectionalWheelEnabled(void) { return ascensionControlsIsModern() && s_modernDirectionalWheel; }

int ascensionControlsModernGamepadEnabled(void)
{
    if (!ascensionControlsIsModern() || !s_modernGamepad)
        return 0;
    if (current_menu != GE_MENU_RUN_STAGE && current_menu != GE_MENU_INVALID)
        return 0;
    /* The native Q Watch keeps the accepted legacy N64 gamepad semantics. */
    if (ascensionWatchIsActive())
        return 0;
    return 1;
}

int ascensionControlsDisableAutoCenter(void)
{
    return ascensionControlsIsModern() && s_modernDisableAutoCenter &&
           (s_modernDirectLook || ascensionControlsModernGamepadEnabled());
}

void ascensionControlsQueueDirectLook(double dx, double dy, int aiming)
{
    if (!ascensionControlsDirectLookEnabled()) return;
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
    if (!ascensionControlsDirectLookEnabled()) return 0;
    if (yawDegrees) *yawDegrees = (float)yaw;
    if (pitchDegrees) *pitchDegrees = (float)pitch;
    return yaw != 0.0 || pitch != 0.0;
}

int ascensionControlsPadResponse(void) { return s_modernPadResponse; }

static void shapePadPair(int rawX, int rawY, float *outX, float *outY)
{
    double x = rawX < 0 ? (double)rawX / 32768.0 : (double)rawX / 32767.0;
    double y = rawY < 0 ? (double)rawY / 32768.0 : (double)rawY / 32767.0;
    double mag = sqrt(x * x + y * y);
    double deadzone = (double)s_modernPadDeadzone / 100.0;
    if (mag <= deadzone || mag <= 0.000001) {
        *outX = 0.0f; *outY = 0.0f; return;
    }
    if (mag > 1.0) { x /= mag; y /= mag; mag = 1.0; }
    double shaped = clampDouble((mag - deadzone) / (1.0 - deadzone), 0.0, 1.0);
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
    float moveX = 0.0f, moveY = 0.0f, lookX = 0.0f, lookY = 0.0f;
    shapePadPair(lx, ly, &moveX, &moveY);
    shapePadPair(rx, ry, &lookX, &lookY);
    if (s_modernPadInvertX) lookX = -lookX;
    if (s_modernPadInvertY) lookY = -lookY;
    s_padMoveX = moveX;
    s_padMoveY = -moveY;
    double sensitivity = (double)s_modernPadLookSensitivity / 100.0;
    double adsScale = aiming ? (double)s_modernPadAdsScale / 100.0 : 1.0;
    double degrees = ASCENSION_PAD_LOOK_DEG_PER_TICK * sensitivity * adsScale;
    s_padLookYaw = (float)((double)lookX * degrees);
    s_padLookPitch = (float)(-(double)lookY * degrees);
}

int ascensionControlsConsumeGamepadMove(float *strafe, float *walk)
{
    float x = s_padMoveX, y = s_padMoveY;
    s_padMoveX = 0.0f; s_padMoveY = 0.0f;
    if (strafe) *strafe = 0.0f;
    if (walk) *walk = 0.0f;
    if (!ascensionControlsModernGamepadEnabled() || lvlGetControlsLockedFlag() != 0)
        return 0;
    if (strafe) *strafe = x;
    if (walk) *walk = y;
    return fabsf(x) > 0.0001f || fabsf(y) > 0.0001f;
}

int ascensionControlsConsumeGamepadLook(float *yawDegreesPerTick,
                                        float *pitchDegreesPerTick)
{
    float yaw = s_padLookYaw, pitch = s_padLookPitch;
    s_padLookYaw = 0.0f; s_padLookPitch = 0.0f;
    if (yawDegreesPerTick) *yawDegreesPerTick = 0.0f;
    if (pitchDegreesPerTick) *pitchDegreesPerTick = 0.0f;
    if (!ascensionControlsModernGamepadEnabled() || lvlGetControlsLockedFlag() != 0)
        return 0;
    if (yawDegreesPerTick) *yawDegreesPerTick = yaw;
    if (pitchDegreesPerTick) *pitchDegreesPerTick = pitch;
    return fabsf(yaw) > 0.0001f || fabsf(pitch) > 0.0001f;
}

static int padBindIndex(const char *configKey)
{
    if (!configKey) return -1;
    for (int i = 0; i < ASC_PAD_BIND_COUNT; ++i)
        if (strcmp(configKey, kPadBindDefs[i].key) == 0)
            return i;
    return -1;
}

const char *ascensionControlsPadBindingDisplay(const char *configKey)
{
    static char fallback[24];
    int i = padBindIndex(configKey);
    if (i < 0) return "N/A";
    const char *name = SDL_GameControllerGetStringForButton((SDL_GameControllerButton)s_padBind[i]);
    if (name && *name) return name;
    snprintf(fallback, sizeof(fallback), "BUTTON %d", s_padBind[i]);
    return fallback;
}

int ascensionControlsPadBindingSet(const char *configKey, int button)
{
    int i = padBindIndex(configKey);
    if (i < 0 || button < 0 || button >= SDL_CONTROLLER_BUTTON_MAX)
        return 0;
    s_padBind[i] = button;
    configSave();
    return 1;
}

int ascensionControlsPadBindingReset(const char *configKey)
{
    int i = padBindIndex(configKey);
    if (i < 0) return 0;
    s_padBind[i] = kPadBindDefs[i].def;
    configSave();
    return 1;
}

int ascensionControlsRawGamepadButton(void *controller, int button)
{
    if (!controller || button < 0 || button >= SDL_CONTROLLER_BUTTON_MAX)
        return 0;
    return SDL_GameControllerGetButton((SDL_GameController *)controller,
                                       (SDL_GameControllerButton)button) != 0;
}

static int physicalButtonForLogical(int logicalButton)
{
    switch (logicalButton) {
    case SDL_CONTROLLER_BUTTON_A:             return s_padBind[ASC_PAD_BIND_ACTION];
    case SDL_CONTROLLER_BUTTON_X:             return s_padBind[ASC_PAD_BIND_CANCEL];
    case SDL_CONTROLLER_BUTTON_B:             return s_padBind[ASC_PAD_BIND_CROUCH];
    case SDL_CONTROLLER_BUTTON_Y:             return s_padBind[ASC_PAD_BIND_NEXT_WEAPON];
    case SDL_CONTROLLER_BUTTON_LEFTSHOULDER:  return s_padBind[ASC_PAD_BIND_PREV_WEAPON];
    case SDL_CONTROLLER_BUTTON_RIGHTSHOULDER: return s_padBind[ASC_PAD_BIND_ALT_ACTION];
    case SDL_CONTROLLER_BUTTON_START:         return s_padBind[ASC_PAD_BIND_START];
    default:                                  return logicalButton;
    }
}

int ascensionControlsGamepadButton(void *controller, int logicalButton)
{
    if (!controller) return 0;
    int physical = logicalButton;
    if (ascensionControlsModernGamepadEnabled())
        physical = physicalButtonForLogical(logicalButton);
    return ascensionControlsRawGamepadButton(controller, physical);
}

int ascensionControlsGamepadAxis(void *controller, int logicalAxis)
{
    if (!controller || logicalAxis < 0 || logicalAxis >= SDL_CONTROLLER_AXIS_MAX)
        return 0;
    int physical = logicalAxis;
    if (ascensionControlsModernGamepadEnabled()) {
        if (s_modernPadSouthpaw) {
            if (logicalAxis == SDL_CONTROLLER_AXIS_LEFTX) physical = SDL_CONTROLLER_AXIS_RIGHTX;
            else if (logicalAxis == SDL_CONTROLLER_AXIS_LEFTY) physical = SDL_CONTROLLER_AXIS_RIGHTY;
            else if (logicalAxis == SDL_CONTROLLER_AXIS_RIGHTX) physical = SDL_CONTROLLER_AXIS_LEFTX;
            else if (logicalAxis == SDL_CONTROLLER_AXIS_RIGHTY) physical = SDL_CONTROLLER_AXIS_LEFTY;
        }
        if (s_modernPadSwapTriggers) {
            if (logicalAxis == SDL_CONTROLLER_AXIS_TRIGGERLEFT) physical = SDL_CONTROLLER_AXIS_TRIGGERRIGHT;
            else if (logicalAxis == SDL_CONTROLLER_AXIS_TRIGGERRIGHT) physical = SDL_CONTROLLER_AXIS_TRIGGERLEFT;
        }
    }
    return (int)SDL_GameControllerGetAxis((SDL_GameController *)controller,
                                          (SDL_GameControllerAxis)physical);
}
