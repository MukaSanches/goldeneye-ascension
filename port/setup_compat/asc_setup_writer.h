#ifndef ASCENSION_SETUP_WRITER_H
#define ASCENSION_SETUP_WRITER_H

#include "asc_setup.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef enum AscSetupNativeWriteMode {
    ASC_SETUP_NATIVE_WRITE_PRESERVE_LAYOUT = 0,
    ASC_SETUP_NATIVE_WRITE_COMPACT_RELOCATE = 1
} AscSetupNativeWriteMode;

/*
 * Rebuild an extracted GoldenEye setup blob from AscSetupDocument.
 *
 * PRESERVE_LAYOUT keeps every imported section at its original source offset.
 * COMPACT_RELOCATE packs root sections after the 40-byte root table and
 * relocates the setup-relative references whose layouts are explicitly known.
 */
int asc_setup_native_write(const AscSetupDocument *doc,
                           AscSetupNativeWriteMode mode,
                           uint8_t **out_bytes,
                           size_t *out_size,
                           AscSetupDiagnostics *diagnostics);

#ifdef __cplusplus
}
#endif

#endif /* ASCENSION_SETUP_WRITER_H */
