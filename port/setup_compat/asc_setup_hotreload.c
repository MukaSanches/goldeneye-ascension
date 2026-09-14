#include "asc_setup_hotreload.h"

#include "asc_setup_native.h"
#include "asc_setup_semantic.h"
#include "asc_setup_writer.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define ASC_HOTRELOAD_MAX_BYTES (64u * 1024u * 1024u)

typedef struct AscHotReloadState {
    uint8_t *bytes;
    size_t size;
    char target[160];
    uint64_t generation;
    uint64_t consumed_generation;
} AscHotReloadState;

static AscHotReloadState g_state;

static int looks_like_setup_resource(const char *resource)
{
    const char *p;
    if (!resource) return 0;
    p = strstr(resource, "setup");
    return p != NULL;
}

static int target_matches(const char *target, const char *resource)
{
    if (!resource) return 0;
    if (!target || !target[0]) return looks_like_setup_resource(resource);
    return strcmp(target, resource) == 0;
}

static int read_file(const char *path, uint8_t **out, size_t *out_size)
{
    FILE *fp;
    long len;
    uint8_t *bytes;
    if (!path || !out || !out_size) return 0;
    *out = NULL; *out_size = 0;
    fp = fopen(path, "rb");
    if (!fp) return 0;
    if (fseek(fp, 0, SEEK_END) != 0 || (len = ftell(fp)) < 0 ||
        fseek(fp, 0, SEEK_SET) != 0 || (unsigned long)len > ASC_HOTRELOAD_MAX_BYTES) {
        fclose(fp); return 0;
    }
    bytes = (uint8_t *)malloc(len ? (size_t)len : 1u);
    if (!bytes) { fclose(fp); return 0; }
    if (len && fread(bytes, 1, (size_t)len, fp) != (size_t)len) {
        free(bytes); fclose(fp); return 0;
    }
    fclose(fp);
    *out = bytes; *out_size = (size_t)len;
    return 1;
}

int asc_setup_hotreload_stage_bytes(const char *target_resource,
                                    const void *bytes,
                                    size_t size)
{
    AscSetupDocument doc;
    AscSetupDiagnostics diagnostics;
    AscSemanticDocument semantic;
    uint8_t *normalized = NULL;
    size_t normalized_size = 0;
    int status;

    if (!bytes || size < ASC_SETUP_NATIVE_HEADER_BYTES || size > ASC_HOTRELOAD_MAX_BYTES)
        return ASC_SETUP_ERR_INVALID_ARGUMENT;

    asc_setup_document_init(&doc);
    asc_setup_diagnostics_init(&diagnostics);
    asc_semantic_init(&semantic);

    status = asc_setup_native_import(bytes, size, &doc, &diagnostics);
    if (status == ASC_SETUP_OK)
        status = asc_semantic_decode(&doc, &semantic, &diagnostics);
    if (status == ASC_SETUP_OK)
        status = asc_setup_native_write(&doc, ASC_SETUP_NATIVE_WRITE_PRESERVE_LAYOUT,
                                        &normalized, &normalized_size, &diagnostics);

    if (status == ASC_SETUP_OK) {
        free(g_state.bytes);
        g_state.bytes = normalized;
        g_state.size = normalized_size;
        normalized = NULL;
        if (target_resource && target_resource[0]) {
            snprintf(g_state.target, sizeof(g_state.target), "%s", target_resource);
        } else {
            g_state.target[0] = '\0';
        }
        ++g_state.generation;
        if (g_state.generation == 0) ++g_state.generation;
    }

    free(normalized);
    asc_semantic_free(&semantic);
    asc_setup_diagnostics_free(&diagnostics);
    asc_setup_document_free(&doc);
    return status;
}

int asc_setup_hotreload_stage_file(const char *target_resource,
                                   const char *path)
{
    uint8_t *bytes = NULL;
    size_t size = 0;
    int status;
    if (!read_file(path, &bytes, &size)) return ASC_SETUP_ERR_INVALID_ARGUMENT;
    status = asc_setup_hotreload_stage_bytes(target_resource, bytes, size);
    free(bytes);
    return status;
}

void asc_setup_hotreload_clear(void)
{
    free(g_state.bytes);
    memset(&g_state, 0, sizeof(g_state));
}

const void *asc_setup_hotreload_acquire(const char *resource,
                                        size_t *out_size,
                                        uint64_t *out_generation)
{
    if (out_size) *out_size = 0;
    if (out_generation) *out_generation = 0;
    if (!g_state.bytes || !target_matches(g_state.target, resource)) return NULL;
    if (out_size) *out_size = g_state.size;
    if (out_generation) *out_generation = g_state.generation;
    return g_state.bytes;
}

void asc_setup_hotreload_consumed(uint64_t generation)
{
    if (generation && generation == g_state.generation)
        g_state.consumed_generation = generation;
}

void asc_setup_hotreload_refresh_environment(const char *resource)
{
    const char *path = getenv("GE_SETUP_OVERRIDE");
    const char *target = getenv("GE_SETUP_TARGET");
    if (!path || !path[0] || !looks_like_setup_resource(resource)) return;
    if (target && target[0] && strcmp(target, resource) != 0) return;
    (void)asc_setup_hotreload_stage_file(target && target[0] ? target : resource, path);
}
