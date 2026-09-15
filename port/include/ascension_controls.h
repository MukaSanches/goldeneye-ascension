#ifndef ASCENSION_CONTROLS_H
#define ASCENSION_CONTROLS_H

#ifdef __cplusplus
extern "C" {
#endif

enum AscensionControlPreset {
    ASCENSION_CONTROLS_CLASSIC = 0,
    ASCENSION_CONTROLS_HYBRID  = 1,
    ASCENSION_CONTROLS_MODERN  = 2,
};

enum AscensionMouseResponse {
    ASCENSION_MOUSE_LEGACY    = 0,
    ASCENSION_MOUSE_LINEAR    = 1,
    ASCENSION_MOUSE_PRECISION = 2,
};

enum AscensionPadResponse {
    ASCENSION_PAD_LINEAR    = 0,
    ASCENSION_PAD_PRECISION = 1,
};

int ascensionControlsPreset(void);
int ascensionControlsIsModern(void);
int ascensionControlsDedicatedCrouchHeld(void);

int ascensionControlsResolveAim(int physicalAimHeld, int forceAimHeld, int menuMode);
void ascensionControlsResetTransient(void);
double ascensionControlsShapeMouseDelta(double delta, int aiming);
int ascensionControlsWantsRawMouse(void);
int ascensionControlsWheelQueueEnabled(void);
int ascensionControlsMouseResponse(void);
int ascensionControlsAimToggleEnabled(void);

int ascensionControlsDirectLookEnabled(void);
int ascensionControlsDirectionalWheelEnabled(void);
int ascensionControlsDisableAutoCenter(void);
void ascensionControlsQueueDirectLook(double dx, double dy, int aiming);
int ascensionControlsConsumeDirectLook(float *yawDegrees, float *pitchDegrees);

/* Modern V4 gamepad bridge. */
int ascensionControlsModernGamepadEnabled(void);
int ascensionControlsPadResponse(void);
void ascensionControlsQueueGamepadAxes(int lx, int ly, int rx, int ry, int aiming);
int ascensionControlsConsumeGamepadMove(float *strafe, float *walk);
int ascensionControlsConsumeGamepadLook(float *yawDegreesPerTick,
                                        float *pitchDegreesPerTick);

/* Modern V4 configurable pad mapping. These use SDL's stable logical button
 * and axis IDs but keep SDL types out of this public header. */
const char *ascensionControlsPadBindingDisplay(const char *configKey);
int ascensionControlsPadBindingSet(const char *configKey, int button);
int ascensionControlsPadBindingReset(const char *configKey);
int ascensionControlsRawGamepadButton(void *controller, int button);
int ascensionControlsGamepadButton(void *controller, int logicalButton);
int ascensionControlsGamepadAxis(void *controller, int logicalAxis);

#ifdef __cplusplus
}
#endif

/* input.c includes SDL before this header. Interpose only its normalized
 * GameController reads so Modern can remap buttons/sticks while Classic,
 * Hybrid, frontend and Q Watch transparently pass through to SDL unchanged.
 * ascension_controls.c defines ASCENSION_CONTROLS_NO_SDL_HOOK so the wrapper
 * implementation itself always reaches the real SDL functions. */
#ifndef ASCENSION_CONTROLS_NO_SDL_HOOK
#define SDL_GameControllerGetButton(controller, button) \
    ascensionControlsGamepadButton((void *)(controller), (int)(button))
#define SDL_GameControllerGetAxis(controller, axis) \
    ascensionControlsGamepadAxis((void *)(controller), (int)(axis))
#endif

#endif /* ASCENSION_CONTROLS_H */
