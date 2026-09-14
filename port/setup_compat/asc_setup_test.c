#include "asc_setup.h"
#include "asc_setup_native.h"
#include "asc_setup_semantic.h"
#include "asc_setup_writer.h"
#include "asc_setup_hotreload.h"

#include <assert.h>
#include <stdlib.h>
#include <string.h>

static void write_u16_be(unsigned char *p, unsigned int value)
{
    p[0] = (unsigned char)((value >> 8) & 0xffu);
    p[1] = (unsigned char)(value & 0xffu);
}

static void write_u32_be(unsigned char *p, unsigned int value)
{
    p[0] = (unsigned char)((value >> 24) & 0xffu);
    p[1] = (unsigned char)((value >> 16) & 0xffu);
    p[2] = (unsigned char)((value >> 8) & 0xffu);
    p[3] = (unsigned char)(value & 0xffu);
}

static unsigned int read_u32_be(const unsigned char *p)
{
    return ((unsigned int)p[0] << 24) | ((unsigned int)p[1] << 16) |
           ((unsigned int)p[2] << 8) | (unsigned int)p[3];
}

static void test_round_trip(void)
{
    static const unsigned char objects[] = {0x01, 0x02, 0x03, 0x04};
    static const unsigned char ai[] = {0x10, 0x20, 0x30};
    AscSetupDocument src;
    AscSetupDocument decoded;
    AscSetupDiagnostics diagnostics;
    const AscSetupSection *section;
    unsigned char *encoded = NULL;
    size_t encoded_size = 0;

    asc_setup_document_init(&src);
    asc_setup_document_init(&decoded);
    asc_setup_diagnostics_init(&diagnostics);

    assert(asc_setup_add_section(&src, ASC_SETUP_SECTION_OBJECTS, 100, 0, 0,
                                 objects, sizeof(objects)) == ASC_SETUP_OK);
    assert(asc_setup_add_section(&src, ASC_SETUP_SECTION_AI_LISTS, 101, 0, 0,
                                 ai, sizeof(ai)) == ASC_SETUP_OK);
    assert(asc_setup_encode_ascsetup(&src, &encoded, &encoded_size,
                                     &diagnostics) == ASC_SETUP_OK);
    assert(encoded != NULL);
    assert(encoded_size > 16);

    assert(asc_setup_decode_ascsetup(encoded, encoded_size, &decoded,
                                     &diagnostics) == ASC_SETUP_OK);
    assert(decoded.section_count == 2);

    section = asc_setup_find_section(&decoded, ASC_SETUP_SECTION_OBJECTS, 0);
    assert(section != NULL);
    assert(section->stable_id == 100);
    assert(section->payload.size == sizeof(objects));
    assert(memcmp(section->payload.data, objects, sizeof(objects)) == 0);

    free(encoded);
    asc_setup_document_free(&decoded);
    asc_setup_document_free(&src);
    asc_setup_diagnostics_free(&diagnostics);
}

static void test_rejects_bad_magic(void)
{
    unsigned char data[16] = {0};
    AscSetupDocument doc;

    asc_setup_document_init(&doc);
    assert(asc_setup_decode_ascsetup(data, sizeof(data), &doc, NULL) ==
           ASC_SETUP_ERR_BAD_MAGIC);
    asc_setup_document_free(&doc);
}

static void test_duplicate_ids_fail_validation(void)
{
    AscSetupDocument doc;
    AscSetupDiagnostics diagnostics;
    unsigned char a = 1;
    unsigned char b = 2;

    asc_setup_document_init(&doc);
    asc_setup_diagnostics_init(&diagnostics);
    assert(asc_setup_add_section(&doc, ASC_SETUP_SECTION_OBJECTS, 7, 0, 0,
                                 &a, 1) == ASC_SETUP_OK);
    assert(asc_setup_add_section(&doc, ASC_SETUP_SECTION_AI_LISTS, 7, 0, 0,
                                 &b, 1) == ASC_SETUP_OK);
    assert(asc_setup_validate(&doc, &diagnostics) == ASC_SETUP_ERR_INVALID_LAYOUT);
    assert(diagnostics.count > 0);

    asc_setup_diagnostics_free(&diagnostics);
    asc_setup_document_free(&doc);
}

static void test_rejects_truncated_directory(void)
{
    unsigned char data[16] = {'A','S','C','S','E','T','U','P', 1,0,0,0, 1,0,0,0};
    AscSetupDocument doc;

    asc_setup_document_init(&doc);
    assert(asc_setup_decode_ascsetup(data, sizeof(data), &doc, NULL) ==
           ASC_SETUP_ERR_TRUNCATED);
    asc_setup_document_free(&doc);
}

static void test_native_root_import(void)
{
    unsigned char native[96] = {0};
    AscSetupNativeRoots roots;
    AscSetupDocument doc;
    const AscSetupSection *objects;
    const AscSetupSection *ai;

    write_u32_be(native + 3u * 4u, 40u);
    write_u32_be(native + 5u * 4u, 64u);
    native[40] = 0xaa;
    native[63] = 0xbb;
    native[64] = 0xcc;
    native[95] = 0xdd;

    assert(asc_setup_native_read_roots(native, sizeof(native), &roots, NULL) == ASC_SETUP_OK);
    assert(roots.offsets[3] == 40u);
    assert(roots.offsets[5] == 64u);

    asc_setup_document_init(&doc);
    assert(asc_setup_native_import(native, sizeof(native), &doc, NULL) == ASC_SETUP_OK);
    assert(doc.section_count == 2u);

    objects = asc_setup_find_section(&doc, ASC_SETUP_SECTION_OBJECTS, 0);
    ai = asc_setup_find_section(&doc, ASC_SETUP_SECTION_AI_LISTS, 0);
    assert(objects != NULL && objects->source_offset == 40u && objects->payload.size == 24u);
    assert(ai != NULL && ai->source_offset == 64u && ai->payload.size == 32u);
    assert(objects->payload.data[0] == 0xaa && objects->payload.data[23] == 0xbb);
    assert(ai->payload.data[0] == 0xcc && ai->payload.data[31] == 0xdd);

    asc_setup_document_free(&doc);
}

static void test_native_rejects_bad_root(void)
{
    unsigned char native[64] = {0};
    AscSetupNativeRoots roots;

    write_u32_be(native, 0x1000u);
    assert(asc_setup_native_read_roots(native, sizeof(native), &roots, NULL) ==
           ASC_SETUP_ERR_INVALID_LAYOUT);
}

static void test_semantic_guard_decode(void)
{
    unsigned char objects[32] = {0};
    AscSetupDocument setup;
    AscSemanticDocument semantic;

    objects[3] = 9; /* PROPDEF_GUARD */
    write_u16_be(objects + 4, 7);
    write_u16_be(objects + 6, 123);
    write_u16_be(objects + 8, 4);
    write_u16_be(objects + 10, 0x0401);
    write_u16_be(objects + 12, 9);
    write_u16_be(objects + 16, 100);
    objects[28 + 3] = 48; /* PROPDEF_END */

    asc_setup_document_init(&setup);
    asc_semantic_init(&semantic);
    assert(asc_setup_add_section(&setup, ASC_SETUP_SECTION_OBJECTS, 1, 0, 40,
                                 objects, sizeof(objects)) == ASC_SETUP_OK);
    assert(asc_semantic_decode(&setup, &semantic, NULL) == ASC_SETUP_OK);
    assert(semantic.count == 1);
    assert(semantic.nodes[0].kind == ASC_SEM_GUARD);
    assert(semantic.nodes[0].values[0] == 7);
    assert(semantic.nodes[0].values[1] == 123);
    assert(semantic.nodes[0].values[3] == 0x0401);
    assert(semantic.nodes[0].values[4] == 9);
    assert(semantic.nodes[0].values[6] == 100);

    asc_semantic_free(&semantic);
    asc_setup_document_free(&setup);
}

static void test_native_writer_preserves_layout(void)
{
    unsigned char native[44] = {0};
    AscSetupDocument setup;
    unsigned char *written = NULL;
    size_t written_size = 0;

    write_u32_be(native + 2u * 4u, 40u);
    write_u32_be(native + 40, 9u); /* INTRO_END */
    asc_setup_document_init(&setup);
    assert(asc_setup_native_import(native, sizeof(native), &setup, NULL) == ASC_SETUP_OK);
    assert(asc_setup_native_write(&setup, ASC_SETUP_NATIVE_WRITE_PRESERVE_LAYOUT,
                                  &written, &written_size, NULL) == ASC_SETUP_OK);
    assert(written_size == sizeof(native));
    assert(memcmp(written, native, sizeof(native)) == 0);
    free(written);
    asc_setup_document_free(&setup);
}

static void test_native_writer_relocates_paths(void)
{
    unsigned char paths[16] = {0};
    AscSetupDocument setup;
    unsigned char *written = NULL;
    size_t written_size = 0;

    /* Old section lives at 100; first path points to data at old offset 108. */
    write_u32_be(paths, 108u);
    paths[4] = 3;
    paths[5] = 1;
    write_u16_be(paths + 6, 2);

    asc_setup_document_init(&setup);
    assert(asc_setup_add_section(&setup, ASC_SETUP_SECTION_PATHS, 5, 0, 100,
                                 paths, sizeof(paths)) == ASC_SETUP_OK);
    assert(asc_setup_native_write(&setup, ASC_SETUP_NATIVE_WRITE_COMPACT_RELOCATE,
                                  &written, &written_size, NULL) == ASC_SETUP_OK);
    assert(read_u32_be(written + 4u * 4u) == 40u);
    assert(read_u32_be(written + 40) == 48u);
    assert(written_size == 56u);

    free(written);
    asc_setup_document_free(&setup);
}

static void test_hotreload_transaction(void)
{
    unsigned char native[44] = {0};
    const void *candidate;
    size_t candidate_size = 0;
    uint64_t generation = 0;

    write_u32_be(native + 2u * 4u, 40u);
    write_u32_be(native + 40, 9u);
    asc_setup_hotreload_clear();
    assert(asc_setup_hotreload_stage_bytes("UsetupdamZ", native, sizeof(native)) == ASC_SETUP_OK);
    candidate = asc_setup_hotreload_acquire("UsetupdamZ", &candidate_size, &generation);
    assert(candidate != NULL);
    assert(candidate_size == sizeof(native));
    assert(generation != 0);
    assert(memcmp(candidate, native, sizeof(native)) == 0);
    asc_setup_hotreload_consumed(generation);

    native[8] = 0xff; /* invalid intro root offset */
    native[9] = 0xff;
    native[10] = 0xff;
    native[11] = 0xff;
    assert(asc_setup_hotreload_stage_bytes("UsetupdamZ", native, sizeof(native)) != ASC_SETUP_OK);
    /* Failed candidate must not replace the previously validated generation. */
    candidate = asc_setup_hotreload_acquire("UsetupdamZ", &candidate_size, &generation);
    assert(candidate != NULL && candidate_size == 44u);
    asc_setup_hotreload_clear();
}

int main(void)
{
    test_round_trip();
    test_rejects_bad_magic();
    test_duplicate_ids_fail_validation();
    test_rejects_truncated_directory();
    test_native_root_import();
    test_native_rejects_bad_root();
    test_semantic_guard_decode();
    test_native_writer_preserves_layout();
    test_native_writer_relocates_paths();
    test_hotreload_transaction();
    return 0;
}
