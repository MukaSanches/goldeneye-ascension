#include "asc_setup_semantic.h"

#include <stdlib.h>
#include <string.h>

#define PROPDEF_END 48u
#define AI_END_LIST_OPCODE 0x04u

static uint16_t be16(const uint8_t *p)
{
    return (uint16_t)(((uint16_t)p[0] << 8) | p[1]);
}

static uint32_t be32(const uint8_t *p)
{
    return ((uint32_t)p[0] << 24) | ((uint32_t)p[1] << 16) |
           ((uint32_t)p[2] << 8) | (uint32_t)p[3];
}

static int bytes_zero(const uint8_t *p, uint32_t size)
{
    uint32_t i;
    for (i = 0; i < size; ++i) {
        if (p[i] != 0) return 0;
    }
    return 1;
}

static int push_node(AscSemanticDocument *doc, const AscSemanticNode *node)
{
    AscSemanticNode *next;
    uint32_t capacity;
    if (!doc || !node) return ASC_SETUP_ERR_INVALID_ARGUMENT;
    if (doc->count == doc->capacity) {
        capacity = doc->capacity ? doc->capacity * 2u : 64u;
        if (capacity > ASC_SETUP_MAX_RECORDS) capacity = ASC_SETUP_MAX_RECORDS;
        if (capacity <= doc->count) return ASC_SETUP_ERR_LIMIT;
        next = (AscSemanticNode *)realloc(doc->nodes, (size_t)capacity * sizeof(*next));
        if (!next) return ASC_SETUP_ERR_NO_MEMORY;
        doc->nodes = next;
        doc->capacity = capacity;
    }
    doc->nodes[doc->count++] = *node;
    return ASC_SETUP_OK;
}

void asc_semantic_init(AscSemanticDocument *doc)
{
    if (doc) memset(doc, 0, sizeof(*doc));
}

void asc_semantic_free(AscSemanticDocument *doc)
{
    if (!doc) return;
    free(doc->nodes);
    memset(doc, 0, sizeof(*doc));
}

const char *asc_semantic_kind_name(AscSemanticKind kind)
{
    switch (kind) {
    case ASC_SEM_DOOR: return "door";
    case ASC_SEM_GUARD: return "guard";
    case ASC_SEM_WEAPON: return "weapon";
    case ASC_SEM_OBJECTIVE: return "objective";
    case ASC_SEM_CAMERA: return "camera";
    case ASC_SEM_MONITOR: return "monitor";
    case ASC_SEM_TAG: return "tag";
    case ASC_SEM_PRESET: return "preset/link";
    case ASC_SEM_INTRO: return "intro";
    case ASC_SEM_PAD: return "pad";
    case ASC_SEM_BOUND_PAD: return "bound-pad";
    case ASC_SEM_PATH: return "path";
    case ASC_SEM_WAYPOINT: return "waypoint";
    case ASC_SEM_WAYGROUP: return "waygroup";
    case ASC_SEM_AI_SCRIPT: return "ai-script";
    case ASC_SEM_OBJECT_RAW: return "object";
    default: return "unknown";
    }
}

/* Exact serialized N64 record sizes from sizepropdef(); never host sizeof(). */
static uint32_t propdef_size(uint8_t type)
{
    static const uint16_t sizes[49] = {
        4, 0x100, 8, 0x80, 0x84, 0x80, 0xec, 0x84, 0x88, 0x1c,
        0x100, 0x254, 0x80, 0xd8, 12, 4, 4, 0x80, 12, 16,
        0xb4, 0x88, 16, 16, 4, 8, 8, 8, 8, 8,
        16, 4, 16, 20, 4, 16, 0x80, 40, 16, 0xb0,
        0xb4, 4, 0x80, 0x80, 20, 0xe0, 28, 0x94, 4
    };
    return type <= PROPDEF_END ? sizes[type] : 0;
}

static AscSemanticKind prop_kind(uint8_t type)
{
    if (type == 1 || type == 38) return ASC_SEM_DOOR;
    if (type == 9 || type == 18) return ASC_SEM_GUARD;
    if (type == 7 || type == 8 || type == 20) return ASC_SEM_WEAPON;
    if (type >= 23 && type <= 35) return ASC_SEM_OBJECTIVE;
    if (type == 6 || type == 46) return ASC_SEM_CAMERA;
    if (type == 10 || type == 11 || type == 12) return ASC_SEM_MONITOR;
    if (type == 22) return ASC_SEM_TAG;
    if (type == 14 || type == 19 || type == 37) return ASC_SEM_PRESET;
    return ASC_SEM_OBJECT_RAW;
}

static void decode_object_fields(const uint8_t *p, uint32_t size,
                                 AscSemanticNode *node)
{
    uint8_t type = p[3];
    node->subtype = type;

    if (type == 1 && size >= 0xa8) {
        node->refs[0] = be32(p + 0x80);       /* linked door */
        node->values[0] = (int32_t)be16(p + 0x98); /* flags */
        node->values[1] = (int32_t)be16(p + 0x9a); /* door type */
        node->values[2] = (int32_t)be32(p + 0x9c); /* key flags */
        node->values[3] = (int32_t)be32(p + 0xa0); /* auto close */
        node->values[4] = (int32_t)be32(p + 0xa4); /* open sound */
    } else if (type == 9 && size >= 0x1c) {
        node->values[0] = (int32_t)be16(p + 4);  /* chrnum */
        node->values[1] = (int32_t)be16(p + 6);  /* pad */
        node->values[2] = (int32_t)be16(p + 8);  /* body */
        node->values[3] = (int32_t)be16(p + 10); /* AI list */
        node->values[4] = (int32_t)be16(p + 12); /* preset */
        node->values[5] = (int32_t)be16(p + 14); /* chr preset */
        node->values[6] = (int32_t)be16(p + 16); /* health */
        node->values[7] = (int32_t)be16(p + 20); /* flags */
        node->refs[0] = be16(p + 24);             /* head */
    } else if (type == 8 && size >= 0x88) {
        node->values[0] = (int8_t)p[0x80];        /* weapon id */
        node->values[1] = (int8_t)p[0x81];        /* linked type */
        node->values[2] = (int16_t)be16(p + 0x82);/* timer */
        node->refs[0] = be32(p + 0x84);            /* dual weapon */
    } else if (type == 22 && size >= 8) {
        node->values[0] = (int32_t)be16(p + 4);   /* tag id */
        node->values[1] = (int16_t)be16(p + 6);   /* relative object offset */
    } else if ((type == 14 || type == 19 || type == 38) && size >= 12) {
        node->refs[0] = be32(p + 4);
        node->refs[1] = be32(p + 8);
    } else if (type == 18 && size >= 12) {
        node->values[0] = (int32_t)be32(p + 4);
        node->values[1] = (int16_t)be16(p + 8);
        node->values[2] = (int8_t)p[10];
        node->values[3] = (uint8_t)p[11];
    } else if (type == 23 && size >= 16) {
        node->refs[0] = be32(p + 4);               /* objective reference */
        node->values[0] = (int32_t)be32(p + 8);   /* text id */
        node->values[1] = (int32_t)be32(p + 12);  /* min difficulty */
    } else if (type >= 25 && type <= 29 && size >= 6) {
        node->refs[0] = be16(p + 4);
    } else if (type == 30 && size >= 12) {
        node->refs[0] = be16(p + 4);
        node->values[0] = be16(p + 6);
        node->values[1] = (int32_t)be32(p + 8);
    } else if (type == 46 && size >= 28) {
        node->values[0] = (int32_t)be32(p + 4);
        node->values[1] = (int32_t)be32(p + 8);
        node->values[2] = (int32_t)be32(p + 12);
        node->values[3] = (int32_t)be32(p + 16);
        node->values[4] = (int32_t)be32(p + 20);
        node->values[5] = (int32_t)be32(p + 24);  /* pad */
    } else if ((type == 6 || type == 10 || type == 11 || type == 12) && size >= 0x84) {
        /* Common object header is retained losslessly; expose the first
         * post-object word as the editor-visible semantic payload anchor. */
        node->values[0] = (int32_t)be32(p + 0x80);
    }
}

static int decode_objects(const AscSetupSection *section,
                          AscSemanticDocument *out)
{
    uint32_t offset = 0;
    uint32_t index = 0;
    while (offset + 4 <= section->payload.size) {
        const uint8_t *p = section->payload.data + offset;
        uint8_t type = p[3];
        uint32_t size = propdef_size(type);
        AscSemanticNode node;
        if (type == PROPDEF_END) return ASC_SETUP_OK;
        if (!size || size > section->payload.size - offset)
            return ASC_SETUP_ERR_TRUNCATED;
        memset(&node, 0, sizeof(node));
        node.kind = prop_kind(type);
        node.stable_id = 0x10000000u | index;
        node.source_offset = section->source_offset + offset;
        node.byte_size = size;
        decode_object_fields(p, size, &node);
        if (push_node(out, &node) != ASC_SETUP_OK) return ASC_SETUP_ERR_NO_MEMORY;
        offset += size;
        ++index;
    }
    return ASC_SETUP_OK;
}

static uint32_t intro_size(uint32_t type)
{
    static const uint8_t sizes[10] = {12,16,16,32,8,8,40,12,8,4};
    return type < 10 ? sizes[type] : 0;
}

static int decode_intro(const AscSetupSection *section,
                        AscSemanticDocument *out)
{
    uint32_t offset = 0;
    uint32_t index = 0;
    while (offset + 4 <= section->payload.size) {
        uint32_t type = be32(section->payload.data + offset);
        uint32_t size = intro_size(type);
        AscSemanticNode node;
        if (!size || size > section->payload.size - offset)
            return ASC_SETUP_ERR_TRUNCATED;
        memset(&node, 0, sizeof(node));
        node.kind = ASC_SEM_INTRO;
        node.subtype = type;
        node.stable_id = 0x20000000u | index;
        node.source_offset = section->source_offset + offset;
        node.byte_size = size;
        if (size >= 8) node.values[0] = (int32_t)be32(section->payload.data + offset + 4);
        if (size >= 12) node.values[1] = (int32_t)be32(section->payload.data + offset + 8);
        if (size >= 16) node.values[2] = (int32_t)be32(section->payload.data + offset + 12);
        if (push_node(out, &node) != ASC_SETUP_OK) return ASC_SETUP_ERR_NO_MEMORY;
        offset += size;
        ++index;
        if (type == 9) return ASC_SETUP_OK;
    }
    return ASC_SETUP_ERR_TRUNCATED;
}

static int decode_waypoints(const AscSetupSection *section,
                            AscSemanticDocument *out)
{
    uint32_t offset = 0, index = 0;
    while (offset + 16 <= section->payload.size) {
        const uint8_t *p = section->payload.data + offset;
        AscSemanticNode node;
        if (be32(p) == 0xffffffffu && be32(p + 4) == 0 &&
            be32(p + 8) == 0 && be32(p + 12) == 0) return ASC_SETUP_OK;
        memset(&node, 0, sizeof(node));
        node.kind = ASC_SEM_WAYPOINT;
        node.stable_id = 0x30000000u | index;
        node.source_offset = section->source_offset + offset;
        node.byte_size = 16;
        node.values[0] = (int32_t)be32(p);
        node.refs[0] = be32(p + 4);
        node.values[1] = (int32_t)be32(p + 8);
        node.values[2] = (int32_t)be32(p + 12);
        if (push_node(out, &node) != ASC_SETUP_OK) return ASC_SETUP_ERR_NO_MEMORY;
        offset += 16; ++index;
    }
    return ASC_SETUP_ERR_TRUNCATED;
}

static int decode_pointer_directory(const AscSetupSection *section,
                                    AscSemanticDocument *out,
                                    AscSemanticKind kind,
                                    uint32_t stride, uint32_t id_base)
{
    uint32_t offset = 0, index = 0;
    while (offset + stride <= section->payload.size) {
        const uint8_t *p = section->payload.data + offset;
        AscSemanticNode node;
        if (be32(p) == 0) return ASC_SETUP_OK;
        memset(&node, 0, sizeof(node));
        node.kind = kind;
        node.stable_id = id_base | index;
        node.source_offset = section->source_offset + offset;
        node.byte_size = stride;
        node.refs[0] = be32(p);
        if (kind == ASC_SEM_WAYGROUP) {
            node.refs[1] = be32(p + 4);
            node.values[0] = (int32_t)be32(p + 8);
        } else if (kind == ASC_SEM_PATH) {
            node.values[0] = p[4];
            node.values[1] = p[5];
            node.values[2] = be16(p + 6);
        }
        if (push_node(out, &node) != ASC_SETUP_OK) return ASC_SETUP_ERR_NO_MEMORY;
        offset += stride; ++index;
    }
    return ASC_SETUP_ERR_TRUNCATED;
}

static int decode_pads(const AscSetupSection *section,
                       AscSemanticDocument *out,
                       AscSemanticKind kind,
                       uint32_t stride, uint32_t id_base)
{
    uint32_t offset = 0, index = 0;
    while (offset + stride <= section->payload.size) {
        const uint8_t *p = section->payload.data + offset;
        AscSemanticNode node;
        if (bytes_zero(p, stride)) return ASC_SETUP_OK;
        memset(&node, 0, sizeof(node));
        node.kind = kind;
        node.stable_id = id_base | index;
        node.source_offset = section->source_offset + offset;
        node.byte_size = stride;
        node.values[0] = (int32_t)be32(p + 0); /* float bits x */
        node.values[1] = (int32_t)be32(p + 4); /* float bits y */
        node.values[2] = (int32_t)be32(p + 8); /* float bits z */
        node.refs[0] = be32(p + 36);            /* plink */
        node.refs[1] = be32(p + 40);            /* serialized stan/runtime slot */
        if (push_node(out, &node) != ASC_SETUP_OK) return ASC_SETUP_ERR_NO_MEMORY;
        offset += stride; ++index;
    }
    return ASC_SETUP_ERR_TRUNCATED;
}

static const uint8_t *source_at(const AscSetupDocument *setup,
                                uint32_t absolute_offset,
                                uint32_t *available)
{
    uint32_t i;
    for (i = 0; i < setup->section_count; ++i) {
        const AscSetupSection *s = &setup->sections[i];
        uint32_t end;
        if (s->payload.size > UINT32_MAX - s->source_offset) continue;
        end = s->source_offset + s->payload.size;
        if (absolute_offset >= s->source_offset && absolute_offset < end) {
            uint32_t delta = absolute_offset - s->source_offset;
            if (available) *available = s->payload.size - delta;
            return s->payload.data + delta;
        }
    }
    return NULL;
}

static uint32_t next_ai_boundary(const AscSetupSection *directory,
                                 uint32_t script_offset,
                                 uint32_t fallback_end)
{
    uint32_t off = 0;
    uint32_t best = fallback_end;
    while (off + 8 <= directory->payload.size) {
        uint32_t ptr = be32(directory->payload.data + off);
        if (ptr == 0) break;
        if (ptr > script_offset && ptr < best) best = ptr;
        off += 8;
    }
    if (directory->source_offset > script_offset && directory->source_offset < best)
        best = directory->source_offset;
    return best;
}

static int decode_ai(const AscSetupDocument *setup,
                     const AscSetupSection *directory,
                     AscSemanticDocument *out)
{
    uint32_t offset = 0, index = 0;
    while (offset + 8 <= directory->payload.size) {
        const uint8_t *entry = directory->payload.data + offset;
        uint32_t script_offset = be32(entry);
        uint32_t list_id = be32(entry + 4);
        uint32_t available = 0;
        uint32_t boundary;
        uint32_t span;
        uint32_t meaningful;
        const uint8_t *script;
        AscSemanticNode node;
        if (script_offset == 0) return ASC_SETUP_OK;
        script = source_at(setup, script_offset, &available);
        if (!script || available == 0) return ASC_SETUP_ERR_INVALID_LAYOUT;
        boundary = next_ai_boundary(directory, script_offset, script_offset + available);
        if (boundary <= script_offset || boundary - script_offset > available)
            return ASC_SETUP_ERR_INVALID_LAYOUT;
        span = boundary - script_offset;
        meaningful = span;
        while (meaningful > 0 && script[meaningful - 1] == 0) --meaningful;
        if (meaningful == 0 || script[meaningful - 1] != AI_END_LIST_OPCODE) {
            /* Preserve the exact safe span even when an unknown command family
             * prevents opcode-level interpretation. The directory/list ID is
             * still semantic and the bytes remain lossless. */
            meaningful = span;
        }
        memset(&node, 0, sizeof(node));
        node.kind = ASC_SEM_AI_SCRIPT;
        node.stable_id = 0x40000000u | index;
        node.source_offset = script_offset;
        node.byte_size = meaningful;
        node.refs[0] = directory->source_offset + offset; /* directory entry */
        node.values[0] = (int32_t)list_id;
        node.values[1] = (int32_t)span;
        node.values[2] = (meaningful < span || script[meaningful - 1] == AI_END_LIST_OPCODE) ? 1 : 0;
        if (push_node(out, &node) != ASC_SETUP_OK) return ASC_SETUP_ERR_NO_MEMORY;
        offset += 8; ++index;
    }
    return ASC_SETUP_ERR_TRUNCATED;
}

int asc_semantic_decode(const AscSetupDocument *setup,
                        AscSemanticDocument *out,
                        AscSetupDiagnostics *diagnostics)
{
    uint32_t i;
    int status = ASC_SETUP_OK;
    (void)diagnostics;
    if (!setup || !out) return ASC_SETUP_ERR_INVALID_ARGUMENT;
    asc_semantic_init(out);

    for (i = 0; i < setup->section_count; ++i) {
        const AscSetupSection *s = &setup->sections[i];
        switch (s->kind) {
        case ASC_SETUP_SECTION_OBJECTS:
            status = decode_objects(s, out); break;
        case ASC_SETUP_SECTION_INTRO:
            status = decode_intro(s, out); break;
        case ASC_SETUP_SECTION_PATH_TABLE:
            status = decode_waypoints(s, out); break;
        case ASC_SETUP_SECTION_PATH_LINKS:
            status = decode_pointer_directory(s, out, ASC_SEM_WAYGROUP, 12, 0x31000000u); break;
        case ASC_SETUP_SECTION_PATHS:
            status = decode_pointer_directory(s, out, ASC_SEM_PATH, 8, 0x32000000u); break;
        case ASC_SETUP_SECTION_AI_LISTS:
            status = decode_ai(setup, s, out); break;
        case ASC_SETUP_SECTION_PADS:
            status = decode_pads(s, out, ASC_SEM_PAD, 44, 0x50000000u); break;
        case ASC_SETUP_SECTION_PADS_3D:
            status = decode_pads(s, out, ASC_SEM_BOUND_PAD, 68, 0x51000000u); break;
        default:
            break;
        }
        if (status != ASC_SETUP_OK) {
            asc_semantic_free(out);
            return status;
        }
    }
    return ASC_SETUP_OK;
}
