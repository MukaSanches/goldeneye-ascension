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

/* Ascension PC-only gameplay helpers. The original N64 input ABI and gameplay
 * code remain authoritative; these helpers only shape host-side input before
 * it is translated to the native GoldenEye controller state. */
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

#ifdef __cplusplus
}
#endif

#endif /* ASCENSION_CONTROLS_H */
