#ifndef ASCENSION_PTBR_ASSETS_H
#define ASCENSION_PTBR_ASSETS_H

#ifdef __cplusplus
extern "C" {
#endif

/*
 * Try to satisfy a ROM read from Ascension's validated PT-BR image sidecar.
 * Returns nonzero only when PT-BR is selected, the sidecar is valid, and the
 * requested source range lies completely inside GoldenEye's image segment.
 * Returning zero means the caller must use the original ROM normally.
 */
int ascensionPtbrImageCopy(void *target, const void *source, unsigned int size);

#ifdef __cplusplus
}
#endif

#endif /* ASCENSION_PTBR_ASSETS_H */
