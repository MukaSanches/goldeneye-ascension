#ifndef ASCENSION_LOCALE_H
#define ASCENSION_LOCALE_H

#ifdef __cplusplus
extern "C" {
#endif

/*
 * Translate text owned by Ascension's PC overlay.
 *
 * The GoldenEye renderer is intentionally left untouched: callers still use
 * the original font and display-list path. Strings are kept ASCII-safe until
 * the legacy font's extended glyph coverage is verified across regions.
 */
const char *ascensionLocaleText(const char *text);

/* 0 = English, 1 = Portuguese (Brazil). */
int ascensionLocaleGet(void);

#ifdef __cplusplus
}
#endif

#endif /* ASCENSION_LOCALE_H */
