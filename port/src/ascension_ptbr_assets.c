/*
 * Runtime bridge for graphics imported from the community PT-BR patch.
 *
 * The PC port must keep the verified original ROM mapped at 0x10000000. The
 * offline importer builds data/ascension_ptbr_images.bin with exactly the
 * original image-segment layout, replacing only texture payloads that can be
 * transplanted without changing an original slot boundary. This module serves
 * those bytes only while PT-BR is selected. Any failure is fail-open: romCopy
 * simply continues with the original ROM.
 */

#include <stdint.h>
#include <string.h>

#include "ascension_locale.h"
#include "ascension_ptbr_assets.h"
#include "fs.h"
#include "system.h"

/* C TUs see the N64 libc stubs first; match the explicit host declarations
 * used by the rest of the port layer. */
extern void *malloc(size_t size);
extern void free(void *ptr);

extern unsigned char _imagesSegmentRomStart;
extern unsigned char _imagesSegmentRomEnd;

static unsigned char *s_image_shadow;
static unsigned int s_image_shadow_size;
static int s_image_load_attempted;

static void load_image_shadow_once(void)
{
    FSFile *f;
    int32_t size;
    uintptr_t start;
    uintptr_t end;
    unsigned int expected;

    if (s_image_load_attempted)
        return;
    s_image_load_attempted = 1;

    start = (uintptr_t)&_imagesSegmentRomStart;
    end = (uintptr_t)&_imagesSegmentRomEnd;
    if (end <= start || end - start > 0x01000000u) {
        sysLogPrintf(LOG_WARNING, "PT-BR: invalid image segment bounds");
        return;
    }
    expected = (unsigned int)(end - start);

    f = fsOpen(sysResolvePath("$S/ascension_ptbr_images.bin"), "rb");
    if (!f)
        return;

    size = fsSize(f);
    if (size != (int32_t)expected) {
        fsClose(f);
        sysLogPrintf(LOG_WARNING,
                     "PT-BR: image sidecar size mismatch (%d, expected %u); ignored",
                     (int)size, expected);
        return;
    }

    s_image_shadow = (unsigned char *)malloc((size_t)size);
    if (!s_image_shadow || fsRead(f, s_image_shadow, size) != size) {
        fsClose(f);
        free(s_image_shadow);
        s_image_shadow = NULL;
        sysLogPrintf(LOG_WARNING, "PT-BR: failed to read image sidecar; ignored");
        return;
    }
    fsClose(f);

    s_image_shadow_size = (unsigned int)size;
    sysLogPrintf(LOG_INFO, "PT-BR: loaded community image sidecar (%u bytes)",
                 s_image_shadow_size);
}

int ascensionPtbrImageCopy(void *target, const void *source, unsigned int size)
{
    uintptr_t start;
    uintptr_t end;
    uintptr_t src;
    unsigned int off;

    if (!target || !source || !size || ascensionLocaleGet() != 1)
        return 0;

    load_image_shadow_once();
    if (!s_image_shadow)
        return 0;

    start = (uintptr_t)&_imagesSegmentRomStart;
    end = (uintptr_t)&_imagesSegmentRomEnd;
    src = (uintptr_t)source;

    if (src < start || src >= end)
        return 0;
    if ((uintptr_t)size > end - src)
        return 0;

    off = (unsigned int)(src - start);
    if (off > s_image_shadow_size || size > s_image_shadow_size - off)
        return 0;

    memcpy(target, s_image_shadow + off, size);
    return 1;
}
