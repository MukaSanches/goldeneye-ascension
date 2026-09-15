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

/* V4: controller-0 twin-stick bridge. Raw SDL axes are shaped with a radial
 * deadzone, then movement is consumed through GoldenEye's native analogWalk /
 * analogStrafe channels. Look is a frame-scaled camera rate. */
int ascensionControlsModernGamepadEnabled(void);
int ascensionControlsPadResponse(void);
void ascensionControlsQueueGamepadAxes(int lx, int ly, int rx, int ry, int aiming);
int ascensionControlsConsumeGamepadMove(float *strafe, float *walk);
int ascensionControlsConsumeGamepadLook(float *yawDegreesPerTick,
                                        float *pitchDegreesPerTick);

#ifdef __cplusplus
}
#endif

#endif /* ASCENSION_CONTROLS_H */
