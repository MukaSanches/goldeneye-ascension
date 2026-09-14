#include "asc_setup_writer.h"
#include "asc_setup_native.h"

#include <stdlib.h>
#include <string.h>

static uint32_t read_be32(const uint8_t *p)
{
    return ((uint32_t)p[0] << 24) | ((uint32_t)p[1] << 16) |
           ((uint32_t)p[2] << 8) | (uint32_t)p[3];
}

static void write_be32(uint8_t *p, uint32_t value)
{
    p[0] = (uint8_t)(value >> 24);
    p[1] = (uint8_t)(value >> 16);
    p[2] = (uint8_t)(value >> 8);
    p[3] = (uint8_t)value;
}

static uint32_t align4(uint32_t value)
{
    return (value + 3u) & ~3u;
}

static int root_index(AscSetupSectionKind kind)
{
    switch (kind) {
    case ASC_SETUP_SECTION_PATH_TABLE: return 0;
    case ASC_SETUP_SECTION_PATH_LINKS: return 1;
    case ASC_SETUP_SECTION_INTRO: return 2;
    case ASC_SETUP_SECTION_OBJECTS: return 3;
    case ASC_SETUP_SECTION_PATHS: return 4;
    case ASC_SETUP_SECTION_AI_LISTS: return 5;
    case ASC_SETUP_SECTION_PADS: return 6;
    case ASC_SETUP_SECTION_PADS_3D: return 7;
    case ASC_SETUP_SECTION_PAD_NAMES: return 8;
    case ASC_SETUP_SECTION_PAD3D_NAMES: return 9;
    default: return -1;
    }
}

typedef struct Mapping {
    uint32_t old_start;
    uint32_t old_end;
    uint32_t new_start;
} Mapping;

static int relocate_value(uint32_t value, const Mapping *maps, uint32_t count,
                          uint32_t *out)
{
    uint32_t i;
    if (value == 0) { *out = 0; return 1; }
    for (i = 0; i < count; ++i) {
        if (value >= maps[i].old_start && value < maps[i].old_end) {
            *out = maps[i].new_start + (value - maps[i].old_start);
            return 1;
        }
    }
    return 0;
}

static int patch_pointer(uint8_t *base, uint32_t offset, uint32_t size,
                         const Mapping *maps, uint32_t map_count)
{
    uint32_t old_value, new_value;
    if (offset > size || size - offset < 4) return 0;
    old_value = read_be32(base + offset);
    if (!relocate_value(old_value, maps, map_count, &new_value)) return 0;
    write_be32(base + offset, new_value);
    return 1;
}

static int relocate_known_section(AscSetupSectionKind kind, uint8_t *data,
                                  uint32_t size, const Mapping *maps,
                                  uint32_t map_count)
{
    uint32_t off;
    switch (kind) {
    case ASC_SETUP_SECTION_PATH_TABLE:
        for (off = 0; off + 16 <= size; off += 16) {
            uint32_t ptr = read_be32(data + off + 4);
            if (!ptr) break;
            if (!patch_pointer(data, off + 4, size, maps, map_count)) return 0;
        }
        return 1;
    case ASC_SETUP_SECTION_PATH_LINKS:
        for (off = 0; off + 12 <= size; off += 12) {
            if (!read_be32(data + off)) break;
            if (!patch_pointer(data, off, size, maps, map_count) ||
                !patch_pointer(data, off + 4, size, maps, map_count)) return 0;
        }
        return 1;
    case ASC_SETUP_SECTION_PATHS:
        for (off = 0; off + 8 <= size; off += 8) {
            if (!read_be32(data + off)) break;
            if (!patch_pointer(data, off, size, maps, map_count)) return 0;
        }
        return 1;
    case ASC_SETUP_SECTION_AI_LISTS:
        for (off = 0; off + 8 <= size; off += 8) {
            if (!read_be32(data + off)) break;
            if (!patch_pointer(data, off, size, maps, map_count)) return 0;
        }
        return 1;
    case ASC_SETUP_SECTION_PADS:
        for (off = 0; off + 44 <= size; off += 44) {
            if (!read_be32(data + off + 36)) break;
            if (!patch_pointer(data, off + 36, size, maps, map_count)) return 0;
        }
        return 1;
    case ASC_SETUP_SECTION_PADS_3D:
        for (off = 0; off + 68 <= size; off += 68) {
            if (!read_be32(data + off + 36)) break;
            if (!patch_pointer(data, off + 36, size, maps, map_count)) return 0;
        }
        return 1;
    case ASC_SETUP_SECTION_PAD_NAMES:
    case ASC_SETUP_SECTION_PAD3D_NAMES:
        for (off = 0; off + 4 <= size; off += 4) {
            if (!read_be32(data + off)) break;
            if (!patch_pointer(data, off, size, maps, map_count)) return 0;
        }
        return 1;
    case ASC_SETUP_SECTION_INTRO:
        off = 0;
        while (off + 4 <= size) {
            uint32_t type = read_be32(data + off);
            static const uint8_t lengths[10] = {12,16,16,32,8,8,40,12,8,4};
            uint32_t len;
            if (type >= 10) return 0;
            len = lengths[type];
            if (len > size - off) return 0;
            /* Credits entry stores a setup-relative credits table pointer. */
            if (type == 8 && !patch_pointer(data, off + 4, size, maps, map_count)) return 0;
            off += len;
            if (type == 9) break;
        }
        return 1;
    default:
        /* Object streams and unknown roots are copied exactly. */
        return 1;
    }
}

int asc_setup_native_write(const AscSetupDocument *doc,
                           AscSetupNativeWriteMode mode,
                           uint8_t **out_bytes,
                           size_t *out_size,
                           AscSetupDiagnostics *diagnostics)
{
    const AscSetupSection *roots[ASC_SETUP_NATIVE_ROOT_COUNT] = {0};
    Mapping maps[ASC_SETUP_NATIVE_ROOT_COUNT];
    uint32_t map_count = 0;
    uint32_t starts[ASC_SETUP_NATIVE_ROOT_COUNT] = {0};
    uint32_t total = ASC_SETUP_NATIVE_HEADER_BYTES;
    uint32_t i, j;
    uint8_t *dst;
    int status;

    if (!doc || !out_bytes || !out_size) return ASC_SETUP_ERR_INVALID_ARGUMENT;
    *out_bytes = NULL;
    *out_size = 0;
    status = asc_setup_validate(doc, diagnostics);
    if (status != ASC_SETUP_OK) return status;

    for (i = 0; i < doc->section_count; ++i) {
        int idx = root_index(doc->sections[i].kind);
        if (idx >= 0) {
            if (roots[idx]) return ASC_SETUP_ERR_INVALID_LAYOUT;
            roots[idx] = &doc->sections[i];
        }
    }

    if (mode == ASC_SETUP_NATIVE_WRITE_PRESERVE_LAYOUT) {
        for (i = 0; i < ASC_SETUP_NATIVE_ROOT_COUNT; ++i) {
            if (!roots[i]) continue;
            if (roots[i]->source_offset < ASC_SETUP_NATIVE_HEADER_BYTES) return ASC_SETUP_ERR_INVALID_LAYOUT;
            if (roots[i]->payload.size > UINT32_MAX - roots[i]->source_offset) return ASC_SETUP_ERR_OVERFLOW;
            starts[i] = roots[i]->source_offset;
            if (total < starts[i] + roots[i]->payload.size) total = starts[i] + roots[i]->payload.size;
        }
    } else if (mode == ASC_SETUP_NATIVE_WRITE_COMPACT_RELOCATE) {
        uint32_t cursor = ASC_SETUP_NATIVE_HEADER_BYTES;
        for (i = 0; i < ASC_SETUP_NATIVE_ROOT_COUNT; ++i) {
            if (!roots[i]) continue;
            cursor = align4(cursor);
            starts[i] = cursor;
            if (roots[i]->payload.size > UINT32_MAX - cursor) return ASC_SETUP_ERR_OVERFLOW;
            maps[map_count].old_start = roots[i]->source_offset;
            maps[map_count].old_end = roots[i]->source_offset + roots[i]->payload.size;
            maps[map_count].new_start = cursor;
            ++map_count;
            cursor += roots[i]->payload.size;
        }
        total = cursor;
    } else {
        return ASC_SETUP_ERR_INVALID_ARGUMENT;
    }

    /* Refuse overlapping root sections: source boundaries must be unambiguous. */
    for (i = 0; i < ASC_SETUP_NATIVE_ROOT_COUNT; ++i) {
        if (!roots[i]) continue;
        for (j = i + 1; j < ASC_SETUP_NATIVE_ROOT_COUNT; ++j) {
            uint32_t a0, a1, b0, b1;
            if (!roots[j]) continue;
            a0 = starts[i]; a1 = starts[i] + roots[i]->payload.size;
            b0 = starts[j]; b1 = starts[j] + roots[j]->payload.size;
            if (a0 < b1 && b0 < a1) return ASC_SETUP_ERR_INVALID_LAYOUT;
        }
    }

    dst = (uint8_t *)calloc(1, total ? total : 1u);
    if (!dst) return ASC_SETUP_ERR_NO_MEMORY;

    for (i = 0; i < ASC_SETUP_NATIVE_ROOT_COUNT; ++i) {
        write_be32(dst + i * 4u, starts[i]);
        if (!roots[i]) continue;
        memcpy(dst + starts[i], roots[i]->payload.data, roots[i]->payload.size);
    }

    if (mode == ASC_SETUP_NATIVE_WRITE_COMPACT_RELOCATE) {
        for (i = 0; i < ASC_SETUP_NATIVE_ROOT_COUNT; ++i) {
            if (!roots[i]) continue;
            if (!relocate_known_section(roots[i]->kind, dst + starts[i],
                                        roots[i]->payload.size, maps, map_count)) {
                free(dst);
                return ASC_SETUP_ERR_INVALID_LAYOUT;
            }
        }
    }

    *out_bytes = dst;
    *out_size = total;
    return ASC_SETUP_OK;
}
