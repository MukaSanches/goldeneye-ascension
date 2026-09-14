#include "asc_setup.h"
#include "asc_setup_native.h"

#include <assert.h>
#include <stdlib.h>
#include <string.h>

static void write_u32_be(unsigned char *p, unsigned int value)
{
    p[0] = (unsigned char)((value >> 24) & 0xffu);
    p[1] = (unsigned char)((value >> 16) & 0xffu);
    p[2] = (unsigned char)((value >> 8) & 0xffu);
    p[3] = (unsigned char)(value & 0xffu);
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

    /* Root 3 = objects @ 40, root 5 = AI @ 64. All other roots are null. */
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

int main(void)
{
    test_round_trip();
    test_rejects_bad_magic();
    test_duplicate_ids_fail_validation();
    test_rejects_truncated_directory();
    test_native_root_import();
    test_native_rejects_bad_root();
    return 0;
}
