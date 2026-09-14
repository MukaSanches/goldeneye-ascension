#include "asc_setup.h"

#include <assert.h>
#include <stdlib.h>
#include <string.h>

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

int main(void)
{
    test_round_trip();
    test_rejects_bad_magic();
    test_duplicate_ids_fail_validation();
    test_rejects_truncated_directory();
    return 0;
}
