/*
 * Ascension native-game localization bridge.
 *
 * GoldenEye identifies text as (bank << 10) | slot. PT-BR therefore uses the
 * same stable identity instead of comparing English strings. This matters for
 * repeated English text whose Portuguese wording can differ by context.
 *
 * The ROM remains the English source of truth and the fallback for languages
 * other than PT-BR. A complete PT-BR release is gated by the localization
 * coverage audit in tools/ascension_l10n_audit.py.
 */

#include <stddef.h>

#include "ascension_locale.h"

enum AscensionTextBank {
    LAME = 1,
    LARCH,
    LARK,
    LASH,
    LAZT,
    LCAT,
    LCAVE,
    LAREC,
    LCRAD,
    LCRYP,
    LDAM,
    LDEPO,
    LDEST,
    LDISH,
    LEAR,
    LELD,
    LIMP,
    LJUN,
    LLEE,
    LLEN,
    LLIP,
    LLUE,
    LOAT,
    LPAM,
    LPETE,
    LREF,
    LRIT,
    LRUN,
    LSEVB,
    LSEV,
    LSEVX,
    LSEVXB,
    LSHO,
    LSILO,
    LSTAT,
    LTRA,
    LWAX,
    LGUN,
    LTITLE,
    LMPMENU,
    LPROPOBJ,
    LMPWEAPONS,
    LOPTIONS,
    LMISC
};

struct AscensionGameString {
    unsigned int id;
    const char *pt_br;
};

#define ASC_TEXT_ID(bank, slot) ((((unsigned int)(bank)) << 10) | ((unsigned int)(slot) & 0x3ffu))
#define PT(bank, slot, text) { ASC_TEXT_ID((bank), (slot)), (text) },
#define KEEP(bank, slot)

static const struct AscensionGameString kPtBrGame[] = {
#include "localization/pt_br_title.inc"
};

#undef KEEP
#undef PT

#define NUM_PTBR_GAME ((int)(sizeof(kPtBrGame) / sizeof(kPtBrGame[0])))

const char *ascensionLocaleGameText(int slotID, const char *fallback)
{
    int i;

    if (fallback == NULL || ascensionLocaleGet() != 1)
        return fallback;

    for (i = 0; i < NUM_PTBR_GAME; i++) {
        if (kPtBrGame[i].id == (unsigned int)slotID)
            return kPtBrGame[i].pt_br;
    }

    return fallback;
}
