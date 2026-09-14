#ifndef ASCENSION_SETUP_NATIVE_H
#define ASCENSION_SETUP_NATIVE_H

#include "asc_setup.h"

#ifdef __cplusplus
extern "C" {
#endif

#define ASC_SETUP_NATIVE_ROOT_COUNT 10u
#define ASC_SETUP_NATIVE_HEADER_BYTES 40u

/*
 * Serialized GoldenEye setup root table.
 *
 * The original setup stores ten 32-bit big-endian offsets relative to the
 * beginning of the loaded setup file.  Keep them as integers here: converting
 * them directly to host pointers is incorrect on a 64-bit PC.
 */
typedef struct AscSetupNativeRoots {
    uint32_t offsets[ASC_SETUP_NATIVE_ROOT_COUNT];
} AscSetupNativeRoots;

/* Decode and bounds-check only the ten root offsets. */
int asc_setup_native_read_roots(const void *bytes,
                                size_t size,
                                AscSetupNativeRoots *out_roots,
                                AscSetupDiagnostics *diagnostics);

/*
 * Lossless coarse import of a native extracted setup blob into AscSetupDocument.
 * Each root becomes one raw IR section extending to the next root offset (or
 * end-of-file). Semantic record decoding is deliberately a separate layer.
 */
int asc_setup_native_import(const void *bytes,
                            size_t size,
                            AscSetupDocument *out,
                            AscSetupDiagnostics *diagnostics);

#ifdef __cplusplus
}
#endif

#endif /* ASCENSION_SETUP_NATIVE_H */
