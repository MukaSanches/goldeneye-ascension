#ifndef ASCENSION_SETUP_SEMANTIC_H
#define ASCENSION_SETUP_SEMANTIC_H

#include "asc_setup.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef enum AscSemanticKind {
    ASC_SEM_UNKNOWN = 0,
    ASC_SEM_DOOR,
    ASC_SEM_GUARD,
    ASC_SEM_WEAPON,
    ASC_SEM_OBJECTIVE,
    ASC_SEM_CAMERA,
    ASC_SEM_MONITOR,
    ASC_SEM_TAG,
    ASC_SEM_PRESET,
    ASC_SEM_INTRO,
    ASC_SEM_PAD,
    ASC_SEM_BOUND_PAD,
    ASC_SEM_PATH,
    ASC_SEM_WAYPOINT,
    ASC_SEM_WAYGROUP,
    ASC_SEM_AI_SCRIPT,
    ASC_SEM_OBJECT_RAW
} AscSemanticKind;

typedef struct AscSemanticNode {
    AscSemanticKind kind;
    uint32_t subtype;
    uint32_t stable_id;
    uint32_t source_offset;
    uint32_t byte_size;
    uint32_t refs[4];
    int32_t values[8];
} AscSemanticNode;

typedef struct AscSemanticDocument {
    AscSemanticNode *nodes;
    uint32_t count;
    uint32_t capacity;
} AscSemanticDocument;

void asc_semantic_init(AscSemanticDocument *doc);
void asc_semantic_free(AscSemanticDocument *doc);

/* Decode all supported semantic families from an imported setup document. */
int asc_semantic_decode(const AscSetupDocument *setup,
                        AscSemanticDocument *out,
                        AscSetupDiagnostics *diagnostics);

const char *asc_semantic_kind_name(AscSemanticKind kind);

#ifdef __cplusplus
}
#endif

#endif /* ASCENSION_SETUP_SEMANTIC_H */
