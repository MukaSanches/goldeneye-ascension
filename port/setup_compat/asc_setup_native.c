#include "asc_setup_native.h"

#include <limits.h>
#include <stdint.h>

#define ASC_SETUP_SOURCE_NATIVE_GE 0x00000001u

static uint32_t read_u32_be(const uint8_t *p)
{
    return ((uint32_t)p[0] << 24) |
           ((uint32_t)p[1] << 16) |
           ((uint32_t)p[2] << 8) |
           (uint32_t)p[3];
}

static AscSetupSectionKind root_kind(uint32_t index)
{
    static const AscSetupSectionKind kinds[ASC_SETUP_NATIVE_ROOT_COUNT] = {
        ASC_SETUP_SECTION_PATH_TABLE,
        ASC_SETUP_SECTION_PATH_LINKS,
        ASC_SETUP_SECTION_INTRO,
        ASC_SETUP_SECTION_OBJECTS,
        ASC_SETUP_SECTION_PATHS,
        ASC_SETUP_SECTION_AI_LISTS,
        ASC_SETUP_SECTION_PADS,
        ASC_SETUP_SECTION_PADS_3D,
        ASC_SETUP_SECTION_PAD_NAMES,
        ASC_SETUP_SECTION_PAD3D_NAMES
    };
    return index < ASC_SETUP_NATIVE_ROOT_COUNT ? kinds[index] : ASC_SETUP_SECTION_UNKNOWN;
}

int asc_setup_native_read_roots(const void *bytes,
                                size_t size,
                                AscSetupNativeRoots *out_roots,
                                AscSetupDiagnostics *diagnostics)
{
    const uint8_t *src = (const uint8_t *)bytes;
    uint32_t i;

    (void)diagnostics;
    if (!bytes || !out_roots) {
        return ASC_SETUP_ERR_INVALID_ARGUMENT;
    }
    if (size < ASC_SETUP_NATIVE_HEADER_BYTES) {
        return ASC_SETUP_ERR_TRUNCATED;
    }
    if (size > UINT32_MAX) {
        return ASC_SETUP_ERR_LIMIT;
    }

    for (i = 0; i < ASC_SETUP_NATIVE_ROOT_COUNT; ++i) {
        uint32_t offset = read_u32_be(src + i * 4u);
        if (offset != 0u &&
            (offset < ASC_SETUP_NATIVE_HEADER_BYTES || (size_t)offset >= size)) {
            return ASC_SETUP_ERR_INVALID_LAYOUT;
        }
        out_roots->offsets[i] = offset;
    }
    return ASC_SETUP_OK;
}

static uint32_t find_section_end(const AscSetupNativeRoots *roots,
                                 uint32_t start,
                                 uint32_t file_size)
{
    uint32_t end = file_size;
    uint32_t i;

    for (i = 0; i < ASC_SETUP_NATIVE_ROOT_COUNT; ++i) {
        uint32_t candidate = roots->offsets[i];
        if (candidate > start && candidate < end) {
            end = candidate;
        }
    }
    return end;
}

int asc_setup_native_import(const void *bytes,
                            size_t size,
                            AscSetupDocument *out,
                            AscSetupDiagnostics *diagnostics)
{
    const uint8_t *src = (const uint8_t *)bytes;
    AscSetupNativeRoots roots;
    uint32_t i;
    int status;

    if (!bytes || !out) {
        return ASC_SETUP_ERR_INVALID_ARGUMENT;
    }

    status = asc_setup_native_read_roots(bytes, size, &roots, diagnostics);
    if (status != ASC_SETUP_OK) {
        return status;
    }

    asc_setup_document_init(out);
    out->source_flags |= ASC_SETUP_SOURCE_NATIVE_GE;

    for (i = 0; i < ASC_SETUP_NATIVE_ROOT_COUNT; ++i) {
        uint32_t start = roots.offsets[i];
        uint32_t end;
        uint32_t section_size;

        if (start == 0u) {
            continue;
        }
        end = find_section_end(&roots, start, (uint32_t)size);
        if (end <= start) {
            asc_setup_document_free(out);
            return ASC_SETUP_ERR_INVALID_LAYOUT;
        }
        section_size = end - start;
        if (section_size > ASC_SETUP_MAX_SECTION_BYTES) {
            asc_setup_document_free(out);
            return ASC_SETUP_ERR_LIMIT;
        }

        status = asc_setup_add_section(out,
                                       root_kind(i),
                                       i + 1u,
                                       0u,
                                       start,
                                       src + start,
                                       section_size);
        if (status != ASC_SETUP_OK) {
            asc_setup_document_free(out);
            return status;
        }
    }

    return asc_setup_validate(out, diagnostics);
}
