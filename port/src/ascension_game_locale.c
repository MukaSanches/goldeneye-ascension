/*
 * Ascension community-patch localization bridge.
 *
 * No GoldenEye game text is translated here. PT-BR strings are imported from
 * the user's own community-patched ROM by tools_pc/import_ptbr_patch.py and
 * written to data/ascension_ptbr.bin. English always falls back to the
 * original, verified ROM loaded by the PC port.
 */

#include <stdlib.h>
#include <string.h>

#include "ascension_locale.h"
#include "fs.h"
#include "system.h"

#define PTBR_MAGIC "ASPTBR1"
#define PTBR_MAGIC_LEN 7
#define PTBR_HEADER_SIZE 12u
#define PTBR_RECORD_SIZE 8u

static unsigned char *s_catalog;
static unsigned int s_catalog_size;
static unsigned int s_record_count;
static int s_load_attempted;

static unsigned int read_le32(const unsigned char *p)
{
    return ((unsigned int)p[0]) |
           ((unsigned int)p[1] << 8) |
           ((unsigned int)p[2] << 16) |
           ((unsigned int)p[3] << 24);
}

static int catalog_string_valid(unsigned int off)
{
    unsigned int i;

    if (!s_catalog || off >= s_catalog_size)
        return 0;

    for (i = off; i < s_catalog_size; i++) {
        if (s_catalog[i] == 0)
            return 1;
    }

    return 0;
}

static void load_catalog_once(void)
{
    FSFile *f;
    int32_t size;
    unsigned int count;

    if (s_load_attempted)
        return;
    s_load_attempted = 1;

    f = fsOpen(sysResolvePath("$S/ascension_ptbr.bin"), "rb");
    if (!f) {
        sysLogPrintf(LOG_WARNING,
                     "PT-BR: data/ascension_ptbr.bin not found; using original English text");
        return;
    }

    size = fsSize(f);
    if (size < (int32_t)PTBR_HEADER_SIZE) {
        fsClose(f);
        sysLogPrintf(LOG_WARNING, "PT-BR: localization catalog is truncated");
        return;
    }

    s_catalog = (unsigned char *)malloc((size_t)size);
    if (!s_catalog || fsRead(f, s_catalog, size) != size) {
        fsClose(f);
        free(s_catalog);
        s_catalog = NULL;
        sysLogPrintf(LOG_WARNING, "PT-BR: failed to read localization catalog");
        return;
    }
    fsClose(f);

    s_catalog_size = (unsigned int)size;

    if (memcmp(s_catalog, PTBR_MAGIC, PTBR_MAGIC_LEN) != 0 || s_catalog[7] != 0) {
        free(s_catalog);
        s_catalog = NULL;
        s_catalog_size = 0;
        sysLogPrintf(LOG_WARNING, "PT-BR: invalid localization catalog magic");
        return;
    }

    count = read_le32(s_catalog + 8);
    if (count == 0 || count > (s_catalog_size - PTBR_HEADER_SIZE) / PTBR_RECORD_SIZE) {
        free(s_catalog);
        s_catalog = NULL;
        s_catalog_size = 0;
        sysLogPrintf(LOG_WARNING, "PT-BR: invalid localization catalog index");
        return;
    }

    s_record_count = count;
    sysLogPrintf(LOG_INFO, "PT-BR: loaded community patch catalog (%u strings)", count);
}

const char *ascensionLocaleGameText(int slotID, const char *fallback)
{
    unsigned int lo;
    unsigned int hi;
    unsigned int key = (unsigned int)slotID;

    if (!fallback || ascensionLocaleGet() != 1)
        return fallback;

    load_catalog_once();
    if (!s_catalog)
        return fallback;

    lo = 0;
    hi = s_record_count;

    while (lo < hi) {
        unsigned int mid = lo + (hi - lo) / 2;
        const unsigned char *rec = s_catalog + PTBR_HEADER_SIZE + mid * PTBR_RECORD_SIZE;
        unsigned int rec_id = read_le32(rec);

        if (rec_id < key) {
            lo = mid + 1;
        } else if (rec_id > key) {
            hi = mid;
        } else {
            unsigned int off = read_le32(rec + 4);
            if (catalog_string_valid(off))
                return (const char *)(s_catalog + off);
            return fallback;
        }
    }

    return fallback;
}
