#ifndef ASCENSION_SETUP_COMPAT_H
#define ASCENSION_SETUP_COMPAT_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define ASC_SETUP_FORMAT_VERSION 1u
#define ASC_SETUP_MAX_SECTIONS 32u
#define ASC_SETUP_MAX_RECORDS 65535u
#define ASC_SETUP_MAX_SECTION_BYTES (64u * 1024u * 1024u)

/*
 * Ascension Setup Compatibility Layer
 *
 * Clean-room, editor-neutral representation for GoldenEye setup data.  This
 * module deliberately does not contain GoldEditor/Setup Editor source code.
 * It is the stable seam between tooling, converters and the game runtime.
 */

typedef enum AscSetupSectionKind {
    ASC_SETUP_SECTION_UNKNOWN = 0,
    ASC_SETUP_SECTION_PATH_TABLE = 1,
    ASC_SETUP_SECTION_PATH_LINKS = 2,
    ASC_SETUP_SECTION_INTRO = 3,
    ASC_SETUP_SECTION_OBJECTS = 4,
    ASC_SETUP_SECTION_PATHS = 5,
    ASC_SETUP_SECTION_AI_LISTS = 6,
    ASC_SETUP_SECTION_PADS = 7,
    ASC_SETUP_SECTION_PADS_3D = 8,
    ASC_SETUP_SECTION_PAD_NAMES = 9,
    ASC_SETUP_SECTION_PAD3D_NAMES = 10,
    ASC_SETUP_SECTION_OBJECTIVES = 11,
    ASC_SETUP_SECTION_METADATA = 12
} AscSetupSectionKind;

typedef enum AscSetupSeverity {
    ASC_SETUP_DIAG_INFO = 0,
    ASC_SETUP_DIAG_WARNING = 1,
    ASC_SETUP_DIAG_ERROR = 2
} AscSetupSeverity;

typedef enum AscSetupStatus {
    ASC_SETUP_OK = 0,
    ASC_SETUP_ERR_INVALID_ARGUMENT = -1,
    ASC_SETUP_ERR_NO_MEMORY = -2,
    ASC_SETUP_ERR_TRUNCATED = -3,
    ASC_SETUP_ERR_BAD_MAGIC = -4,
    ASC_SETUP_ERR_UNSUPPORTED_VERSION = -5,
    ASC_SETUP_ERR_LIMIT = -6,
    ASC_SETUP_ERR_OVERFLOW = -7,
    ASC_SETUP_ERR_INVALID_LAYOUT = -8
} AscSetupStatus;

typedef struct AscSetupSlice {
    uint8_t *data;
    uint32_t size;
} AscSetupSlice;

typedef struct AscSetupSection {
    uint32_t stable_id;
    AscSetupSectionKind kind;
    uint32_t flags;
    uint32_t source_offset;
    AscSetupSlice payload;
} AscSetupSection;

typedef struct AscSetupDocument {
    uint32_t format_version;
    uint32_t source_flags;
    AscSetupSection *sections;
    uint32_t section_count;
    uint32_t section_capacity;
} AscSetupDocument;

typedef struct AscSetupDiagnostic {
    AscSetupSeverity severity;
    int32_t code;
    uint32_t section_index;
    uint32_t source_offset;
    char message[160];
} AscSetupDiagnostic;

typedef struct AscSetupDiagnostics {
    AscSetupDiagnostic *items;
    uint32_t count;
    uint32_t capacity;
} AscSetupDiagnostics;

/* Runtime-neutral view of the ten canonical StageSetup roots. */
typedef struct AscSetupRuntimeRoots {
    const void *path_table;
    const void *path_links;
    const void *intro;
    const void *objects;
    const void *paths;
    const void *ai_lists;
    const void *pads;
    const void *pads_3d;
    const void *pad_names;
    const void *pad3d_names;
} AscSetupRuntimeRoots;

void asc_setup_document_init(AscSetupDocument *doc);
void asc_setup_document_free(AscSetupDocument *doc);
void asc_setup_diagnostics_init(AscSetupDiagnostics *diagnostics);
void asc_setup_diagnostics_free(AscSetupDiagnostics *diagnostics);

int asc_setup_add_section(AscSetupDocument *doc,
                          AscSetupSectionKind kind,
                          uint32_t stable_id,
                          uint32_t flags,
                          uint32_t source_offset,
                          const void *data,
                          uint32_t size);

const AscSetupSection *asc_setup_find_section(const AscSetupDocument *doc,
                                               AscSetupSectionKind kind,
                                               uint32_t occurrence);

/* Validates structural invariants without interpreting copyrighted assets. */
int asc_setup_validate(const AscSetupDocument *doc, AscSetupDiagnostics *diagnostics);

/*
 * ASCSETUP is an Ascension-owned interchange container.  It is intentionally
 * not the native ROM setup binary.  Native import/export adapters can map to
 * this representation without exposing runtime pointers to editor code.
 */
int asc_setup_decode_ascsetup(const void *bytes,
                              size_t size,
                              AscSetupDocument *out,
                              AscSetupDiagnostics *diagnostics);

int asc_setup_encode_ascsetup(const AscSetupDocument *doc,
                              uint8_t **out_bytes,
                              size_t *out_size,
                              AscSetupDiagnostics *diagnostics);

/* Creates an editor/runtime boundary view; it does not mutate game state. */
int asc_setup_runtime_roots_from_document(const AscSetupDocument *doc,
                                          AscSetupRuntimeRoots *out_roots);

const char *asc_setup_status_string(int status);

#ifdef __cplusplus
}
#endif

#endif /* ASCENSION_SETUP_COMPAT_H */
