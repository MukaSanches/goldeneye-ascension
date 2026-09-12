#ifndef ASCENSION_CONTROLS_H
#define ASCENSION_CONTROLS_H

#ifdef __cplusplus
extern "C" {
#endif

/* Ascension PC-only gameplay helpers. These are intentionally kept out of the
 * original N64 input ABI so the base game remains unchanged when disabled. */
int ascensionControlsDedicatedCrouchHeld(void);

#ifdef __cplusplus
}
#endif

#endif /* ASCENSION_CONTROLS_H */
