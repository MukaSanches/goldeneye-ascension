#ifndef ASCENSION_VERSION_H
#define ASCENSION_VERSION_H

/* Ascension identity/version is intentionally centralized here. */
#define ASCENSION_NAME "Ascension"
#define ASCENSION_VERSION_MAJOR 0
#define ASCENSION_VERSION_MINOR 0
#define ASCENSION_VERSION_PATCH 4
#define ASCENSION_VERSION "0.0.4"
#define ASCENSION_SIGNATURE ASCENSION_NAME " " ASCENSION_VERSION
#define ASCENSION_WINDOW_TITLE ASCENSION_SIGNATURE

/* Ascension-owned UI is localized immediately before GoldenEye's existing
 * text renderer. The renderer, font banks and game-owned text stay native. */
#include "ascension_locale.h"

#define textRender(gdl, x, y, text, chars, font, colour, width, height, yOffset, lineheight) \
    textRender((gdl), (x), (y), (char *)ascensionLocaleText((const char *)(text)), \
               (chars), (font), (colour), (width), (height), (yOffset), (lineheight))

#define textMeasure(textheight, textwidth, text, chars, font, lineheight) \
    textMeasure((textheight), (textwidth), \
                (char *)ascensionLocaleText((const char *)(text)), \
                (chars), (font), (lineheight))

#endif
