#ifndef ASCENSION_POSTFX_H
#define ASCENSION_POSTFX_H

#ifdef __cplusplus
extern "C" {
#endif

/*
 * Final presentation pass for GoldenEye Ascension.
 *
 * Runs on the already-composited OpenGL back buffer immediately before the
 * SDL swap. The pass is deliberately isolated from Fast3D/RDP emulation: if
 * it is disabled or cannot initialize, the original frame is left untouched.
 */
void ascensionPostFxApply(void);
void ascensionPostFxShutdown(void);

#ifdef __cplusplus
}
#endif

#endif /* ASCENSION_POSTFX_H */
