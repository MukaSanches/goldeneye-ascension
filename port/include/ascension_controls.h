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

enum AscensionCrouchMode {
    ASCENSION_CROUCH_HOLD   = 0,
    ASCENSION_CROUCH_TOGGLE = 1,
};

/* Ascension PC-only gameplay helpers. The original N64 input ABI and gameplay
 * code remain authoritative; these helpers shape host-side input and expose a
 * narrowly-scoped PORT bridge for modern mouse look. */
int ascensionControlsPreset(void);
int ascensionControlsIsModern(void);
int ascensionControlsDedicatedCrouchHeld(void);

/* Modern V2 helpers. */
int ascensionControlsResolveAim(int physicalAimHeld, int forceAimHeld, int menuMode);
void ascensionControlsResetTransient(void);
double ascensionControlsShapeMouseDelta(double delta, int aiming);
int ascensionControlsWantsRawMouse(void);
int ascensionControlsWheelQueueEnabled(void);
int ascensionControlsMouseResponse(void);
int ascensionControlsAimToggleEnabled(void);

/* Modern V3 direct-look bridge. Mouse displacement is queued in degrees and
 * consumed exactly once by the PORT build of bondview2.c. Classic/Hybrid never
 * enter this path. */
int ascensionControlsDirectLookEnabled(void);
int ascensionControlsDirectionalWheelEnabled(void);
int ascensionControlsDisableAutoCenter(void);
int ascensionControlsCrouchMode(void);
void ascensionControlsQueueDirectLook(double dx, double dy, int aiming);
int ascensionControlsConsumeDirectLook(float *yawDegrees, float *pitchDegrees);

#ifdef __cplusplus
}
#endif

#endif /* ASCENSION_CONTROLS_H */
