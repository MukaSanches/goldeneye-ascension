#include "asc_setup.h"
#include "asc_setup_native.h"
#include "asc_setup_semantic.h"
#include "asc_setup_writer.h"

#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define ASC_CLI_MAX_FILE_BYTES (256u * 1024u * 1024u)

static const char *section_name(AscSetupSectionKind kind)
{
    switch (kind) {
    case ASC_SETUP_SECTION_PATH_TABLE: return "path-table";
    case ASC_SETUP_SECTION_PATH_LINKS: return "path-links";
    case ASC_SETUP_SECTION_INTRO: return "intro";
    case ASC_SETUP_SECTION_OBJECTS: return "objects";
    case ASC_SETUP_SECTION_PATHS: return "paths";
    case ASC_SETUP_SECTION_AI_LISTS: return "ai-lists";
    case ASC_SETUP_SECTION_PADS: return "pads";
    case ASC_SETUP_SECTION_PADS_3D: return "pads-3d";
    case ASC_SETUP_SECTION_PAD_NAMES: return "pad-names";
    case ASC_SETUP_SECTION_PAD3D_NAMES: return "pad3d-names";
    case ASC_SETUP_SECTION_OBJECTIVES: return "objectives";
    case ASC_SETUP_SECTION_METADATA: return "metadata";
    default: return "unknown";
    }
}

static int read_file(const char *path, unsigned char **out, size_t *out_size)
{
    FILE *fp;
    long length;
    unsigned char *data;
    size_t read_count;

    if (!path || !out || !out_size) return 0;
    *out = NULL;
    *out_size = 0;

    fp = fopen(path, "rb");
    if (!fp) {
        fprintf(stderr, "asc-setup: cannot open '%s': %s\n", path, strerror(errno));
        return 0;
    }
    if (fseek(fp, 0, SEEK_END) != 0 || (length = ftell(fp)) < 0 ||
        fseek(fp, 0, SEEK_SET) != 0) {
        fprintf(stderr, "asc-setup: cannot determine size of '%s'\n", path);
        fclose(fp);
        return 0;
    }
    if ((unsigned long)length > ASC_CLI_MAX_FILE_BYTES) {
        fprintf(stderr, "asc-setup: file exceeds %u MiB safety limit\n",
                (unsigned)(ASC_CLI_MAX_FILE_BYTES / (1024u * 1024u)));
        fclose(fp);
        return 0;
    }

    data = (unsigned char *)malloc(length ? (size_t)length : 1u);
    if (!data) {
        fprintf(stderr, "asc-setup: out of memory\n");
        fclose(fp);
        return 0;
    }
    read_count = length ? fread(data, 1, (size_t)length, fp) : 0;
    if (read_count != (size_t)length) {
        fprintf(stderr, "asc-setup: short read from '%s'\n", path);
        free(data);
        fclose(fp);
        return 0;
    }
    fclose(fp);
    *out = data;
    *out_size = (size_t)length;
    return 1;
}

static int write_file(const char *path, const void *data, size_t size)
{
    FILE *fp = fopen(path, "wb");
    if (!fp) {
        fprintf(stderr, "asc-setup: cannot create '%s': %s\n", path, strerror(errno));
        return 0;
    }
    if (size && fwrite(data, 1, size, fp) != size) {
        fprintf(stderr, "asc-setup: short write to '%s'\n", path);
        fclose(fp);
        return 0;
    }
    if (fclose(fp) != 0) {
        fprintf(stderr, "asc-setup: failed to finalize '%s'\n", path);
        return 0;
    }
    return 1;
}

static void print_diagnostics(const AscSetupDiagnostics *diagnostics)
{
    uint32_t i;
    if (!diagnostics) return;
    for (i = 0; i < diagnostics->count; ++i) {
        const AscSetupDiagnostic *d = &diagnostics->items[i];
        const char *severity = d->severity == ASC_SETUP_DIAG_ERROR ? "error" :
                               d->severity == ASC_SETUP_DIAG_WARNING ? "warning" : "info";
        fprintf(stderr, "%s: code=%d section=%u offset=0x%08x: %s\n",
                severity, d->code, d->section_index, d->source_offset, d->message);
    }
}

static int load_document(const char *path, AscSetupDocument *doc,
                         AscSetupDiagnostics *diagnostics)
{
    unsigned char *bytes = NULL;
    size_t size = 0;
    int status;

    if (!read_file(path, &bytes, &size)) return ASC_SETUP_ERR_INVALID_ARGUMENT;
    status = asc_setup_decode_ascsetup(bytes, size, doc, diagnostics);
    free(bytes);
    if (status != ASC_SETUP_OK)
        fprintf(stderr, "asc-setup: %s: %s\n", path, asc_setup_status_string(status));
    return status;
}

static int command_validate(const char *path)
{
    AscSetupDocument doc;
    AscSetupDiagnostics diagnostics;
    int status;
    asc_setup_document_init(&doc);
    asc_setup_diagnostics_init(&diagnostics);
    status = load_document(path, &doc, &diagnostics);
    print_diagnostics(&diagnostics);
    if (status == ASC_SETUP_OK) printf("valid: %s (%u sections)\n", path, doc.section_count);
    asc_setup_diagnostics_free(&diagnostics);
    asc_setup_document_free(&doc);
    return status == ASC_SETUP_OK ? 0 : 2;
}

static int command_inspect(const char *path)
{
    AscSetupDocument doc;
    AscSetupDiagnostics diagnostics;
    uint32_t i;
    int status;
    asc_setup_document_init(&doc);
    asc_setup_diagnostics_init(&diagnostics);
    status = load_document(path, &doc, &diagnostics);
    print_diagnostics(&diagnostics);
    if (status != ASC_SETUP_OK) {
        asc_setup_diagnostics_free(&diagnostics);
        asc_setup_document_free(&doc);
        return 2;
    }

    printf("ASCSETUP v%u\n", doc.format_version);
    printf("source-flags: 0x%08x\n", doc.source_flags);
    printf("sections: %u\n", doc.section_count);
    for (i = 0; i < doc.section_count; ++i) {
        const AscSetupSection *s = &doc.sections[i];
        printf("[%02u] %-12s kind=%u id=%u flags=0x%08x source=0x%08x bytes=%u\n",
               i, section_name(s->kind), (unsigned)s->kind, s->stable_id,
               s->flags, s->source_offset, s->payload.size);
    }
    asc_setup_diagnostics_free(&diagnostics);
    asc_setup_document_free(&doc);
    return 0;
}

static int command_semantic(const char *path)
{
    AscSetupDocument doc;
    AscSetupDiagnostics diagnostics;
    AscSemanticDocument semantic;
    uint32_t i;
    int status;

    asc_setup_document_init(&doc);
    asc_setup_diagnostics_init(&diagnostics);
    asc_semantic_init(&semantic);
    status = load_document(path, &doc, &diagnostics);
    if (status == ASC_SETUP_OK)
        status = asc_semantic_decode(&doc, &semantic, &diagnostics);
    print_diagnostics(&diagnostics);
    if (status != ASC_SETUP_OK) {
        fprintf(stderr, "asc-setup: semantic decode failed: %s\n", asc_setup_status_string(status));
        asc_semantic_free(&semantic);
        asc_setup_diagnostics_free(&diagnostics);
        asc_setup_document_free(&doc);
        return 2;
    }

    printf("semantic-nodes: %u\n", semantic.count);
    for (i = 0; i < semantic.count; ++i) {
        const AscSemanticNode *n = &semantic.nodes[i];
        printf("[%04u] %-12s subtype=%u id=0x%08x source=0x%08x bytes=%u "
               "ref0=0x%08x v0=%d v1=%d v2=%d v3=%d\n",
               i, asc_semantic_kind_name(n->kind), n->subtype, n->stable_id,
               n->source_offset, n->byte_size, n->refs[0],
               n->values[0], n->values[1], n->values[2], n->values[3]);
    }

    asc_semantic_free(&semantic);
    asc_setup_diagnostics_free(&diagnostics);
    asc_setup_document_free(&doc);
    return 0;
}

static int command_repack(const char *input, const char *output)
{
    AscSetupDocument doc;
    AscSetupDiagnostics diagnostics;
    unsigned char *encoded = NULL;
    size_t encoded_size = 0;
    int status;
    int ok;

    asc_setup_document_init(&doc);
    asc_setup_diagnostics_init(&diagnostics);
    status = load_document(input, &doc, &diagnostics);
    if (status == ASC_SETUP_OK)
        status = asc_setup_encode_ascsetup(&doc, &encoded, &encoded_size, &diagnostics);
    print_diagnostics(&diagnostics);
    if (status != ASC_SETUP_OK) {
        fprintf(stderr, "asc-setup: repack failed: %s\n", asc_setup_status_string(status));
        free(encoded);
        asc_setup_diagnostics_free(&diagnostics);
        asc_setup_document_free(&doc);
        return 2;
    }
    ok = write_file(output, encoded, encoded_size);
    if (ok) printf("repacked: %s -> %s (%zu bytes)\n", input, output, encoded_size);
    free(encoded);
    asc_setup_diagnostics_free(&diagnostics);
    asc_setup_document_free(&doc);
    return ok ? 0 : 3;
}

static int command_import_native(const char *input, const char *output)
{
    unsigned char *native_bytes = NULL;
    size_t native_size = 0;
    AscSetupDocument doc;
    AscSetupDiagnostics diagnostics;
    AscSemanticDocument semantic;
    unsigned char *encoded = NULL;
    size_t encoded_size = 0;
    int status;
    int ok = 0;

    asc_setup_document_init(&doc);
    asc_setup_diagnostics_init(&diagnostics);
    asc_semantic_init(&semantic);
    if (!read_file(input, &native_bytes, &native_size)) {
        status = ASC_SETUP_ERR_INVALID_ARGUMENT;
        goto done;
    }
    status = asc_setup_native_import(native_bytes, native_size, &doc, &diagnostics);
    if (status == ASC_SETUP_OK)
        status = asc_semantic_decode(&doc, &semantic, &diagnostics);
    if (status == ASC_SETUP_OK)
        status = asc_setup_encode_ascsetup(&doc, &encoded, &encoded_size, &diagnostics);
    print_diagnostics(&diagnostics);
    if (status != ASC_SETUP_OK) {
        fprintf(stderr, "asc-setup: native import failed: %s\n", asc_setup_status_string(status));
        goto done;
    }
    ok = write_file(output, encoded, encoded_size);
    if (ok) {
        printf("imported native setup: %s -> %s (%u roots, %u semantic nodes, %zu bytes)\n",
               input, output, doc.section_count, semantic.count, encoded_size);
    }

done:
    free(native_bytes);
    free(encoded);
    asc_semantic_free(&semantic);
    asc_setup_diagnostics_free(&diagnostics);
    asc_setup_document_free(&doc);
    return ok ? 0 : 2;
}

static int command_export_native(const char *input, const char *output,
                                 AscSetupNativeWriteMode mode)
{
    AscSetupDocument doc;
    AscSetupDiagnostics diagnostics;
    AscSemanticDocument semantic;
    unsigned char *native = NULL;
    size_t native_size = 0;
    int status;
    int ok = 0;

    asc_setup_document_init(&doc);
    asc_setup_diagnostics_init(&diagnostics);
    asc_semantic_init(&semantic);
    status = load_document(input, &doc, &diagnostics);
    if (status == ASC_SETUP_OK)
        status = asc_semantic_decode(&doc, &semantic, &diagnostics);
    if (status == ASC_SETUP_OK)
        status = asc_setup_native_write(&doc, mode, &native, &native_size, &diagnostics);
    print_diagnostics(&diagnostics);
    if (status != ASC_SETUP_OK) {
        fprintf(stderr, "asc-setup: native export failed: %s\n", asc_setup_status_string(status));
        goto done;
    }
    ok = write_file(output, native, native_size);
    if (ok)
        printf("exported native setup: %s -> %s (%zu bytes, %s)\n", input, output,
               native_size, mode == ASC_SETUP_NATIVE_WRITE_COMPACT_RELOCATE ? "compact-relocated" : "preserve-layout");

done:
    free(native);
    asc_semantic_free(&semantic);
    asc_setup_diagnostics_free(&diagnostics);
    asc_setup_document_free(&doc);
    return ok ? 0 : 2;
}

static void usage(const char *argv0)
{
    fprintf(stderr,
            "Ascension Setup Compatibility Tool\n"
            "usage:\n"
            "  %s validate      <file.ascsetup>\n"
            "  %s inspect       <file.ascsetup>\n"
            "  %s semantic      <file.ascsetup>\n"
            "  %s repack        <input.ascsetup> <output.ascsetup>\n"
            "  %s import-native <native-setup.bin> <output.ascsetup>\n"
            "  %s export-native <input.ascsetup> <native-setup.bin> [--compact]\n",
            argv0, argv0, argv0, argv0, argv0, argv0);
}

int main(int argc, char **argv)
{
    if (argc == 3 && strcmp(argv[1], "validate") == 0) return command_validate(argv[2]);
    if (argc == 3 && strcmp(argv[1], "inspect") == 0) return command_inspect(argv[2]);
    if (argc == 3 && strcmp(argv[1], "semantic") == 0) return command_semantic(argv[2]);
    if (argc == 4 && strcmp(argv[1], "repack") == 0) return command_repack(argv[2], argv[3]);
    if (argc == 4 && strcmp(argv[1], "import-native") == 0) return command_import_native(argv[2], argv[3]);
    if ((argc == 4 || argc == 5) && strcmp(argv[1], "export-native") == 0) {
        AscSetupNativeWriteMode mode = ASC_SETUP_NATIVE_WRITE_PRESERVE_LAYOUT;
        if (argc == 5) {
            if (strcmp(argv[4], "--compact") != 0) { usage(argv[0]); return 1; }
            mode = ASC_SETUP_NATIVE_WRITE_COMPACT_RELOCATE;
        }
        return command_export_native(argv[2], argv[3], mode);
    }
    usage(argv[0]);
    return 1;
}
