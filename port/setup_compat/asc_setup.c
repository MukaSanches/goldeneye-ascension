#include "asc_setup.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define ASC_MAGIC_0 'A'
#define ASC_MAGIC_1 'S'
#define ASC_MAGIC_2 'C'
#define ASC_MAGIC_3 'S'
#define ASC_MAGIC_4 'E'
#define ASC_MAGIC_5 'T'
#define ASC_MAGIC_6 'U'
#define ASC_MAGIC_7 'P'
#define ASC_HEADER_SIZE 16u
#define ASC_ENTRY_SIZE 20u

static uint32_t read_u32_le(const uint8_t *p)
{
    return ((uint32_t)p[0]) |
           ((uint32_t)p[1] << 8) |
           ((uint32_t)p[2] << 16) |
           ((uint32_t)p[3] << 24);
}

static void write_u32_le(uint8_t *p, uint32_t value)
{
    p[0] = (uint8_t)(value & 0xffu);
    p[1] = (uint8_t)((value >> 8) & 0xffu);
    p[2] = (uint8_t)((value >> 16) & 0xffu);
    p[3] = (uint8_t)((value >> 24) & 0xffu);
}

static int checked_add_size(size_t a, size_t b, size_t *out)
{
    if (a > SIZE_MAX - b) {
        return 0;
    }
    *out = a + b;
    return 1;
}

static int push_diag(AscSetupDiagnostics *diagnostics,
                     AscSetupSeverity severity,
                     int32_t code,
                     uint32_t section_index,
                     uint32_t source_offset,
                     const char *message)
{
    AscSetupDiagnostic *next;
    uint32_t new_capacity;

    if (!diagnostics) {
        return ASC_SETUP_OK;
    }

    if (diagnostics->count == diagnostics->capacity) {
        new_capacity = diagnostics->capacity ? diagnostics->capacity * 2u : 8u;
        next = (AscSetupDiagnostic *)realloc(diagnostics->items,
                                             (size_t)new_capacity * sizeof(*next));
        if (!next) {
            return ASC_SETUP_ERR_NO_MEMORY;
        }
        diagnostics->items = next;
        diagnostics->capacity = new_capacity;
    }

    next = &diagnostics->items[diagnostics->count++];
    memset(next, 0, sizeof(*next));
    next->severity = severity;
    next->code = code;
    next->section_index = section_index;
    next->source_offset = source_offset;
    if (message) {
        snprintf(next->message, sizeof(next->message), "%s", message);
    }
    return ASC_SETUP_OK;
}

void asc_setup_document_init(AscSetupDocument *doc)
{
    if (!doc) {
        return;
    }
    memset(doc, 0, sizeof(*doc));
    doc->format_version = ASC_SETUP_FORMAT_VERSION;
}

void asc_setup_document_free(AscSetupDocument *doc)
{
    uint32_t i;

    if (!doc) {
        return;
    }

    for (i = 0; i < doc->section_count; ++i) {
        free(doc->sections[i].payload.data);
    }
    free(doc->sections);
    asc_setup_document_init(doc);
}

void asc_setup_diagnostics_init(AscSetupDiagnostics *diagnostics)
{
    if (diagnostics) {
        memset(diagnostics, 0, sizeof(*diagnostics));
    }
}

void asc_setup_diagnostics_free(AscSetupDiagnostics *diagnostics)
{
    if (!diagnostics) {
        return;
    }
    free(diagnostics->items);
    memset(diagnostics, 0, sizeof(*diagnostics));
}

int asc_setup_add_section(AscSetupDocument *doc,
                          AscSetupSectionKind kind,
                          uint32_t stable_id,
                          uint32_t flags,
                          uint32_t source_offset,
                          const void *data,
                          uint32_t size)
{
    AscSetupSection *sections;
    AscSetupSection *section;
    uint32_t capacity;

    if (!doc || (size && !data)) {
        return ASC_SETUP_ERR_INVALID_ARGUMENT;
    }
    if (doc->section_count >= ASC_SETUP_MAX_SECTIONS || size > ASC_SETUP_MAX_SECTION_BYTES) {
        return ASC_SETUP_ERR_LIMIT;
    }

    if (doc->section_count == doc->section_capacity) {
        capacity = doc->section_capacity ? doc->section_capacity * 2u : 8u;
        if (capacity > ASC_SETUP_MAX_SECTIONS) {
            capacity = ASC_SETUP_MAX_SECTIONS;
        }
        sections = (AscSetupSection *)realloc(doc->sections,
                                               (size_t)capacity * sizeof(*sections));
        if (!sections) {
            return ASC_SETUP_ERR_NO_MEMORY;
        }
        doc->sections = sections;
        doc->section_capacity = capacity;
    }

    section = &doc->sections[doc->section_count];
    memset(section, 0, sizeof(*section));
    section->stable_id = stable_id;
    section->kind = kind;
    section->flags = flags;
    section->source_offset = source_offset;

    if (size) {
        section->payload.data = (uint8_t *)malloc(size);
        if (!section->payload.data) {
            return ASC_SETUP_ERR_NO_MEMORY;
        }
        memcpy(section->payload.data, data, size);
        section->payload.size = size;
    }

    ++doc->section_count;
    return ASC_SETUP_OK;
}

const AscSetupSection *asc_setup_find_section(const AscSetupDocument *doc,
                                               AscSetupSectionKind kind,
                                               uint32_t occurrence)
{
    uint32_t i;
    uint32_t found = 0;

    if (!doc) {
        return NULL;
    }
    for (i = 0; i < doc->section_count; ++i) {
        if (doc->sections[i].kind == kind) {
            if (found == occurrence) {
                return &doc->sections[i];
            }
            ++found;
        }
    }
    return NULL;
}

int asc_setup_validate(const AscSetupDocument *doc, AscSetupDiagnostics *diagnostics)
{
    uint32_t i;
    uint32_t j;
    int errors = 0;

    if (!doc) {
        return ASC_SETUP_ERR_INVALID_ARGUMENT;
    }
    if (doc->format_version != ASC_SETUP_FORMAT_VERSION) {
        push_diag(diagnostics, ASC_SETUP_DIAG_ERROR, ASC_SETUP_ERR_UNSUPPORTED_VERSION,
                  UINT32_MAX, 0, "unsupported Ascension setup format version");
        return ASC_SETUP_ERR_UNSUPPORTED_VERSION;
    }
    if (doc->section_count > ASC_SETUP_MAX_SECTIONS) {
        push_diag(diagnostics, ASC_SETUP_DIAG_ERROR, ASC_SETUP_ERR_LIMIT,
                  UINT32_MAX, 0, "section count exceeds safety limit");
        return ASC_SETUP_ERR_LIMIT;
    }

    for (i = 0; i < doc->section_count; ++i) {
        const AscSetupSection *section = &doc->sections[i];
        if (section->payload.size > ASC_SETUP_MAX_SECTION_BYTES) {
            push_diag(diagnostics, ASC_SETUP_DIAG_ERROR, ASC_SETUP_ERR_LIMIT,
                      i, section->source_offset, "section payload exceeds safety limit");
            ++errors;
        }
        if (section->payload.size && !section->payload.data) {
            push_diag(diagnostics, ASC_SETUP_DIAG_ERROR, ASC_SETUP_ERR_INVALID_LAYOUT,
                      i, section->source_offset, "non-empty section has no payload");
            ++errors;
        }
        for (j = i + 1; j < doc->section_count; ++j) {
            if (section->stable_id != 0 && section->stable_id == doc->sections[j].stable_id) {
                push_diag(diagnostics, ASC_SETUP_DIAG_ERROR, ASC_SETUP_ERR_INVALID_LAYOUT,
                          j, doc->sections[j].source_offset, "duplicate stable section id");
                ++errors;
            }
        }
    }

    if (!asc_setup_find_section(doc, ASC_SETUP_SECTION_OBJECTS, 0)) {
        push_diag(diagnostics, ASC_SETUP_DIAG_WARNING, 1001, UINT32_MAX, 0,
                  "document has no object section");
    }
    if (!asc_setup_find_section(doc, ASC_SETUP_SECTION_AI_LISTS, 0)) {
        push_diag(diagnostics, ASC_SETUP_DIAG_INFO, 1002, UINT32_MAX, 0,
                  "document has no AI-list section");
    }

    return errors ? ASC_SETUP_ERR_INVALID_LAYOUT : ASC_SETUP_OK;
}

int asc_setup_decode_ascsetup(const void *bytes,
                              size_t size,
                              AscSetupDocument *out,
                              AscSetupDiagnostics *diagnostics)
{
    const uint8_t *src = (const uint8_t *)bytes;
    uint32_t version;
    uint32_t section_count;
    size_t directory_end;
    uint32_t i;
    int status;

    if (!bytes || !out) {
        return ASC_SETUP_ERR_INVALID_ARGUMENT;
    }
    if (size < ASC_HEADER_SIZE) {
        return ASC_SETUP_ERR_TRUNCATED;
    }
    if (src[0] != ASC_MAGIC_0 || src[1] != ASC_MAGIC_1 || src[2] != ASC_MAGIC_2 ||
        src[3] != ASC_MAGIC_3 || src[4] != ASC_MAGIC_4 || src[5] != ASC_MAGIC_5 ||
        src[6] != ASC_MAGIC_6 || src[7] != ASC_MAGIC_7) {
        return ASC_SETUP_ERR_BAD_MAGIC;
    }

    version = read_u32_le(src + 8);
    section_count = read_u32_le(src + 12);
    if (version != ASC_SETUP_FORMAT_VERSION) {
        return ASC_SETUP_ERR_UNSUPPORTED_VERSION;
    }
    if (section_count > ASC_SETUP_MAX_SECTIONS) {
        return ASC_SETUP_ERR_LIMIT;
    }
    if (!checked_add_size(ASC_HEADER_SIZE, (size_t)section_count * ASC_ENTRY_SIZE,
                          &directory_end) || directory_end > size) {
        return ASC_SETUP_ERR_TRUNCATED;
    }

    asc_setup_document_init(out);
    for (i = 0; i < section_count; ++i) {
        const uint8_t *entry = src + ASC_HEADER_SIZE + (size_t)i * ASC_ENTRY_SIZE;
        uint32_t kind = read_u32_le(entry + 0);
        uint32_t stable_id = read_u32_le(entry + 4);
        uint32_t flags = read_u32_le(entry + 8);
        uint32_t offset = read_u32_le(entry + 12);
        uint32_t payload_size = read_u32_le(entry + 16);
        size_t end;

        if (payload_size > ASC_SETUP_MAX_SECTION_BYTES ||
            !checked_add_size((size_t)offset, (size_t)payload_size, &end) ||
            offset < directory_end || end > size) {
            asc_setup_document_free(out);
            return ASC_SETUP_ERR_INVALID_LAYOUT;
        }

        status = asc_setup_add_section(out, (AscSetupSectionKind)kind, stable_id,
                                       flags, offset, src + offset, payload_size);
        if (status != ASC_SETUP_OK) {
            asc_setup_document_free(out);
            return status;
        }
    }

    return asc_setup_validate(out, diagnostics);
}

int asc_setup_encode_ascsetup(const AscSetupDocument *doc,
                              uint8_t **out_bytes,
                              size_t *out_size,
                              AscSetupDiagnostics *diagnostics)
{
    uint8_t *dst;
    size_t total;
    size_t cursor;
    uint32_t i;
    int status;

    if (!doc || !out_bytes || !out_size) {
        return ASC_SETUP_ERR_INVALID_ARGUMENT;
    }
    *out_bytes = NULL;
    *out_size = 0;

    status = asc_setup_validate(doc, diagnostics);
    if (status != ASC_SETUP_OK) {
        return status;
    }

    total = ASC_HEADER_SIZE + (size_t)doc->section_count * ASC_ENTRY_SIZE;
    for (i = 0; i < doc->section_count; ++i) {
        if (!checked_add_size(total, doc->sections[i].payload.size, &total)) {
            return ASC_SETUP_ERR_OVERFLOW;
        }
    }

    dst = (uint8_t *)calloc(1, total);
    if (!dst) {
        return ASC_SETUP_ERR_NO_MEMORY;
    }

    memcpy(dst, "ASCSETUP", 8);
    write_u32_le(dst + 8, ASC_SETUP_FORMAT_VERSION);
    write_u32_le(dst + 12, doc->section_count);
    cursor = ASC_HEADER_SIZE + (size_t)doc->section_count * ASC_ENTRY_SIZE;

    for (i = 0; i < doc->section_count; ++i) {
        const AscSetupSection *section = &doc->sections[i];
        uint8_t *entry = dst + ASC_HEADER_SIZE + (size_t)i * ASC_ENTRY_SIZE;
        if (cursor > UINT32_MAX) {
            free(dst);
            return ASC_SETUP_ERR_OVERFLOW;
        }
        write_u32_le(entry + 0, (uint32_t)section->kind);
        write_u32_le(entry + 4, section->stable_id);
        write_u32_le(entry + 8, section->flags);
        write_u32_le(entry + 12, (uint32_t)cursor);
        write_u32_le(entry + 16, section->payload.size);
        if (section->payload.size) {
            memcpy(dst + cursor, section->payload.data, section->payload.size);
            cursor += section->payload.size;
        }
    }

    *out_bytes = dst;
    *out_size = total;
    return ASC_SETUP_OK;
}

int asc_setup_runtime_roots_from_document(const AscSetupDocument *doc,
                                          AscSetupRuntimeRoots *out_roots)
{
    const AscSetupSection *section;

    if (!doc || !out_roots) {
        return ASC_SETUP_ERR_INVALID_ARGUMENT;
    }
    memset(out_roots, 0, sizeof(*out_roots));

#define SET_ROOT(field, kind_value) \
    do { \
        section = asc_setup_find_section(doc, (kind_value), 0); \
        if (section) { \
            out_roots->field = section->payload.data; \
        } \
    } while (0)

    SET_ROOT(path_table, ASC_SETUP_SECTION_PATH_TABLE);
    SET_ROOT(path_links, ASC_SETUP_SECTION_PATH_LINKS);
    SET_ROOT(intro, ASC_SETUP_SECTION_INTRO);
    SET_ROOT(objects, ASC_SETUP_SECTION_OBJECTS);
    SET_ROOT(paths, ASC_SETUP_SECTION_PATHS);
    SET_ROOT(ai_lists, ASC_SETUP_SECTION_AI_LISTS);
    SET_ROOT(pads, ASC_SETUP_SECTION_PADS);
    SET_ROOT(pads_3d, ASC_SETUP_SECTION_PADS_3D);
    SET_ROOT(pad_names, ASC_SETUP_SECTION_PAD_NAMES);
    SET_ROOT(pad3d_names, ASC_SETUP_SECTION_PAD3D_NAMES);

#undef SET_ROOT
    return ASC_SETUP_OK;
}

const char *asc_setup_status_string(int status)
{
    switch (status) {
    case ASC_SETUP_OK: return "ok";
    case ASC_SETUP_ERR_INVALID_ARGUMENT: return "invalid argument";
    case ASC_SETUP_ERR_NO_MEMORY: return "out of memory";
    case ASC_SETUP_ERR_TRUNCATED: return "truncated input";
    case ASC_SETUP_ERR_BAD_MAGIC: return "bad ASCSETUP magic";
    case ASC_SETUP_ERR_UNSUPPORTED_VERSION: return "unsupported version";
    case ASC_SETUP_ERR_LIMIT: return "safety limit exceeded";
    case ASC_SETUP_ERR_OVERFLOW: return "integer/size overflow";
    case ASC_SETUP_ERR_INVALID_LAYOUT: return "invalid layout";
    default: return "unknown setup error";
    }
}
