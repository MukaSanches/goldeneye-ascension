/*
 * Ascension PT-BR UTF-8 bridge.
 *
 * GoldenEye's retail Latin fonts contain printable ASCII only. The PC port can
 * still render proper Brazilian Portuguese without replacing the ROM fonts:
 * GNU ld --wrap redirects the four public text entry points here. We render an
 * ASCII base string with the original renderer, then add the accent mark using
 * glyphs already present in the same font. Measurement and wrapping operate on
 * the same base glyphs, so layout remains deterministic.
 *
 * This is deliberately port-only. The original N64 renderer/data remain
 * untouched and English follows the exact original path.
 */

#include <ultra64.h>
#include "textrelated.h"
#include "ascension_locale.h"

#include <stdlib.h>
#include <string.h>

enum AscAccent {
    ASC_ACCENT_NONE = 0,
    ASC_ACCENT_ACUTE,
    ASC_ACCENT_GRAVE,
    ASC_ACCENT_CIRC,
    ASC_ACCENT_TILDE,
    ASC_ACCENT_DIAERESIS,
    ASC_ACCENT_CEDILLA
};

struct AscAccentEvent {
    int shadow_index;
    int line_start;
    int line;
    unsigned char base;
    unsigned char accent;
};

extern Gfx *__real_textRender(Gfx *gdl, s32 *x, s32 *y, char *text,
        struct fontchar *chars, struct font *font, u32 colour,
        s32 width, s32 height, u32 yOffset, s32 lineheight);
extern Gfx *__real_textRenderOutlined(Gfx *gdl, s32 *x, s32 *y, char *text,
        struct fontchar *chars, struct font *font, u32 colour, u32 colour2,
        s32 width, s32 height, s32 yOffset, s32 lineheight);
extern void __real_textMeasure(s32 *textheight, s32 *textwidth, char *text,
        struct fontchar *font1, struct font *font2, s32 lineheight);
extern void __real_textWrap(s32 wrapwidth, char *src, char *dst,
        struct fontchar *chars, struct font *font);

static unsigned int ascUtf8Next(const unsigned char **pp)
{
    const unsigned char *p = *pp;
    unsigned int cp;

    if (*p < 0x80) {
        *pp = p + 1;
        return *p;
    }
    if ((p[0] & 0xe0) == 0xc0 && (p[1] & 0xc0) == 0x80) {
        cp = ((unsigned int)(p[0] & 0x1f) << 6) | (p[1] & 0x3f);
        *pp = p + 2;
        return cp;
    }
    if ((p[0] & 0xf0) == 0xe0 && (p[1] & 0xc0) == 0x80 &&
            (p[2] & 0xc0) == 0x80) {
        cp = ((unsigned int)(p[0] & 0x0f) << 12) |
             ((unsigned int)(p[1] & 0x3f) << 6) | (p[2] & 0x3f);
        *pp = p + 3;
        return cp;
    }

    /* Invalid/unsupported sequence: consume one byte and keep rendering. */
    *pp = p + 1;
    return '?';
}

static unsigned char ascLatinBase(unsigned int cp, unsigned char *accent)
{
    *accent = ASC_ACCENT_NONE;
    switch (cp) {
    case 0x00c0: *accent = ASC_ACCENT_GRAVE; return 'A';
    case 0x00c1: *accent = ASC_ACCENT_ACUTE; return 'A';
    case 0x00c2: *accent = ASC_ACCENT_CIRC; return 'A';
    case 0x00c3: *accent = ASC_ACCENT_TILDE; return 'A';
    case 0x00c4: *accent = ASC_ACCENT_DIAERESIS; return 'A';
    case 0x00c7: *accent = ASC_ACCENT_CEDILLA; return 'C';
    case 0x00c8: *accent = ASC_ACCENT_GRAVE; return 'E';
    case 0x00c9: *accent = ASC_ACCENT_ACUTE; return 'E';
    case 0x00ca: *accent = ASC_ACCENT_CIRC; return 'E';
    case 0x00cb: *accent = ASC_ACCENT_DIAERESIS; return 'E';
    case 0x00cc: *accent = ASC_ACCENT_GRAVE; return 'I';
    case 0x00cd: *accent = ASC_ACCENT_ACUTE; return 'I';
    case 0x00ce: *accent = ASC_ACCENT_CIRC; return 'I';
    case 0x00cf: *accent = ASC_ACCENT_DIAERESIS; return 'I';
    case 0x00d1: *accent = ASC_ACCENT_TILDE; return 'N';
    case 0x00d2: *accent = ASC_ACCENT_GRAVE; return 'O';
    case 0x00d3: *accent = ASC_ACCENT_ACUTE; return 'O';
    case 0x00d4: *accent = ASC_ACCENT_CIRC; return 'O';
    case 0x00d5: *accent = ASC_ACCENT_TILDE; return 'O';
    case 0x00d6: *accent = ASC_ACCENT_DIAERESIS; return 'O';
    case 0x00d9: *accent = ASC_ACCENT_GRAVE; return 'U';
    case 0x00da: *accent = ASC_ACCENT_ACUTE; return 'U';
    case 0x00db: *accent = ASC_ACCENT_CIRC; return 'U';
    case 0x00dc: *accent = ASC_ACCENT_DIAERESIS; return 'U';
    case 0x00e0: *accent = ASC_ACCENT_GRAVE; return 'a';
    case 0x00e1: *accent = ASC_ACCENT_ACUTE; return 'a';
    case 0x00e2: *accent = ASC_ACCENT_CIRC; return 'a';
    case 0x00e3: *accent = ASC_ACCENT_TILDE; return 'a';
    case 0x00e4: *accent = ASC_ACCENT_DIAERESIS; return 'a';
    case 0x00e7: *accent = ASC_ACCENT_CEDILLA; return 'c';
    case 0x00e8: *accent = ASC_ACCENT_GRAVE; return 'e';
    case 0x00e9: *accent = ASC_ACCENT_ACUTE; return 'e';
    case 0x00ea: *accent = ASC_ACCENT_CIRC; return 'e';
    case 0x00eb: *accent = ASC_ACCENT_DIAERESIS; return 'e';
    case 0x00ec: *accent = ASC_ACCENT_GRAVE; return 'i';
    case 0x00ed: *accent = ASC_ACCENT_ACUTE; return 'i';
    case 0x00ee: *accent = ASC_ACCENT_CIRC; return 'i';
    case 0x00ef: *accent = ASC_ACCENT_DIAERESIS; return 'i';
    case 0x00f1: *accent = ASC_ACCENT_TILDE; return 'n';
    case 0x00f2: *accent = ASC_ACCENT_GRAVE; return 'o';
    case 0x00f3: *accent = ASC_ACCENT_ACUTE; return 'o';
    case 0x00f4: *accent = ASC_ACCENT_CIRC; return 'o';
    case 0x00f5: *accent = ASC_ACCENT_TILDE; return 'o';
    case 0x00f6: *accent = ASC_ACCENT_DIAERESIS; return 'o';
    case 0x00f9: *accent = ASC_ACCENT_GRAVE; return 'u';
    case 0x00fa: *accent = ASC_ACCENT_ACUTE; return 'u';
    case 0x00fb: *accent = ASC_ACCENT_CIRC; return 'u';
    case 0x00fc: *accent = ASC_ACCENT_DIAERESIS; return 'u';
    default: break;
    }

    /* Smart punctuation is normalized, never dropped. */
    if (cp == 0x2018 || cp == 0x2019) return '\'';
    if (cp == 0x201c || cp == 0x201d) return '"';
    if (cp == 0x2013 || cp == 0x2014) return '-';
    if (cp < 0x80) return (unsigned char)cp;
    return '?';
}

static char *ascMakeShadow(const char *src, struct AscAccentEvent **events_out,
        int *event_count)
{
    const unsigned char *p = (const unsigned char *)src;
    size_t bytes = strlen(src);
    char *shadow = (char *)malloc(bytes + 1);
    struct AscAccentEvent *events = NULL;
    int cap = 0, count = 0, out = 0, line = 0, line_start = 0;

    if (!shadow) return NULL;

    while (*p) {
        unsigned int cp = ascUtf8Next(&p);
        unsigned char accent = ASC_ACCENT_NONE;
        unsigned char base = ascLatinBase(cp, &accent);

        if (base == '\r')
            continue;

        shadow[out] = (char)base;
        if (accent != ASC_ACCENT_NONE) {
            if (count == cap) {
                int newcap = cap ? cap * 2 : 16;
                struct AscAccentEvent *tmp = (struct AscAccentEvent *)realloc(
                    events, (size_t)newcap * sizeof(*events));
                if (!tmp) {
                    free(events);
                    free(shadow);
                    return NULL;
                }
                events = tmp;
                cap = newcap;
            }
            events[count].shadow_index = out;
            events[count].line_start = line_start;
            events[count].line = line;
            events[count].base = base;
            events[count].accent = accent;
            count++;
        }
        out++;
        if (base == '\n') {
            line++;
            line_start = out;
        }
    }
    shadow[out] = '\0';
    *events_out = events;
    *event_count = count;
    return shadow;
}

static const char *ascAccentMark(unsigned char accent)
{
    switch (accent) {
    case ASC_ACCENT_ACUTE: return "'";
    case ASC_ACCENT_GRAVE: return "`";
    case ASC_ACCENT_CIRC: return "^";
    case ASC_ACCENT_TILDE: return "~";
    case ASC_ACCENT_DIAERESIS: return "\"";
    case ASC_ACCENT_CEDILLA: return ",";
    default: return "";
    }
}

static int ascLineHeight(struct fontchar *chars, int lineheight)
{
    if (lineheight != 0) return lineheight;
    return chars['['].height + chars['['].baseline;
}

static int ascPrefixWidth(char *shadow, const struct AscAccentEvent *ev,
        struct fontchar *chars, struct font *font)
{
    s32 h = 0, w = 0;
    int end = ev->shadow_index + 1;
    char saved = shadow[end];
    shadow[end] = '\0';
    __real_textMeasure(&h, &w, shadow + ev->line_start, chars, font, 0);
    shadow[end] = saved;
    return w;
}

static Gfx *ascDrawMarks(Gfx *gdl, char *shadow,
        const struct AscAccentEvent *events, int count,
        s32 startx, s32 starty, struct fontchar *chars, struct font *font,
        u32 colour, u32 colour2, s32 width, s32 height, u32 yOffset,
        s32 lineheight, int outlined)
{
    int lh = ascLineHeight(chars, lineheight);

    for (int i = 0; i < count; i++) {
        const struct AscAccentEvent *ev = &events[i];
        const char *mark = ascAccentMark(ev->accent);
        int prefixw = ascPrefixWidth(shadow, ev, chars, font);
        int base_index = (int)ev->base - 0x21;
        int basew = (base_index >= 0 && base_index < 94) ? chars[base_index].width : 6;
        s32 mh = 0, mw = 0;
        s32 ax, ay;

        __real_textMeasure(&mh, &mw, (char *)mark, chars, font, 0);
        ax = startx + prefixw - (basew / 2) - (mw / 2);
        ay = starty + ev->line * lh;

        if (ev->accent == ASC_ACCENT_CEDILLA)
            ay += chars[base_index].baseline + chars[base_index].height - 2;
        else
            ay -= 3;

        if (outlined) {
            gdl = __real_textRenderOutlined(gdl, &ax, &ay, (char *)mark,
                chars, font, colour, colour2, width, height, yOffset, lineheight);
        } else {
            gdl = __real_textRender(gdl, &ax, &ay, (char *)mark,
                chars, font, colour, width, height, yOffset, lineheight);
        }
    }
    return gdl;
}

Gfx *__wrap_textRender(Gfx *gdl, s32 *x, s32 *y, char *text,
        struct fontchar *chars, struct font *font, u32 colour,
        s32 width, s32 height, u32 yOffset, s32 lineheight)
{
    struct AscAccentEvent *events = NULL;
    int count = 0;
    s32 startx, starty;
    char *shadow;

    if (!text || ascensionLocaleGet() != 1)
        return __real_textRender(gdl, x, y, text, chars, font, colour,
                                 width, height, yOffset, lineheight);

    shadow = ascMakeShadow(text, &events, &count);
    if (!shadow)
        return __real_textRender(gdl, x, y, text, chars, font, colour,
                                 width, height, yOffset, lineheight);

    startx = *x;
    starty = *y;
    gdl = __real_textRender(gdl, x, y, shadow, chars, font, colour,
                            width, height, yOffset, lineheight);
    if (count)
        gdl = ascDrawMarks(gdl, shadow, events, count, startx, starty,
                           chars, font, colour, 0, width, height,
                           yOffset, lineheight, 0);
    free(events);
    free(shadow);
    return gdl;
}

Gfx *__wrap_textRenderOutlined(Gfx *gdl, s32 *x, s32 *y, char *text,
        struct fontchar *chars, struct font *font, u32 colour, u32 colour2,
        s32 width, s32 height, s32 yOffset, s32 lineheight)
{
    struct AscAccentEvent *events = NULL;
    int count = 0;
    s32 startx, starty;
    char *shadow;

    if (!text || ascensionLocaleGet() != 1)
        return __real_textRenderOutlined(gdl, x, y, text, chars, font,
                colour, colour2, width, height, yOffset, lineheight);

    shadow = ascMakeShadow(text, &events, &count);
    if (!shadow)
        return __real_textRenderOutlined(gdl, x, y, text, chars, font,
                colour, colour2, width, height, yOffset, lineheight);

    startx = *x;
    starty = *y;
    gdl = __real_textRenderOutlined(gdl, x, y, shadow, chars, font,
            colour, colour2, width, height, yOffset, lineheight);
    if (count)
        gdl = ascDrawMarks(gdl, shadow, events, count, startx, starty,
                chars, font, colour, colour2, width, height,
                (u32)yOffset, lineheight, 1);
    free(events);
    free(shadow);
    return gdl;
}

void __wrap_textMeasure(s32 *textheight, s32 *textwidth, char *text,
        struct fontchar *font1, struct font *font2, s32 lineheight)
{
    struct AscAccentEvent *events = NULL;
    int count = 0;
    char *shadow;

    if (!text || ascensionLocaleGet() != 1) {
        __real_textMeasure(textheight, textwidth, text, font1, font2, lineheight);
        return;
    }

    shadow = ascMakeShadow(text, &events, &count);
    if (!shadow) {
        __real_textMeasure(textheight, textwidth, text, font1, font2, lineheight);
        return;
    }
    __real_textMeasure(textheight, textwidth, shadow, font1, font2, lineheight);
    free(events);
    free(shadow);
}

/* UTF-8-aware word wrapping. It preserves the original UTF-8 bytes in dst,
 * but measures a Latin-base shadow through GoldenEye's original metrics. */
void __wrap_textWrap(s32 wrapwidth, char *src, char *dst,
        struct fontchar *chars, struct font *font)
{
    char *word;
    char *shadow;
    int wordcap = 256;
    int linewidth = 0;
    int indent = 0;

    if (!src || !dst || ascensionLocaleGet() != 1) {
        __real_textWrap(wrapwidth, src, dst, chars, font);
        return;
    }

    word = (char *)malloc((size_t)wordcap);
    shadow = (char *)malloc((size_t)wordcap);
    if (!word || !shadow) {
        free(word); free(shadow);
        __real_textWrap(wrapwidth, src, dst, chars, font);
        return;
    }

    while (*src) {
        int n = 0, sn = 0;
        char sep;
        s32 h = 0, w = 0;

        while (*src && *src > ' ') {
            const unsigned char *p = (const unsigned char *)src;
            const unsigned char *before = p;
            unsigned int cp = ascUtf8Next(&p);
            unsigned char accent = ASC_ACCENT_NONE;
            unsigned char base = ascLatinBase(cp, &accent);
            int raw = (int)(p - before);

            if (n + raw + 1 >= wordcap || sn + 2 >= wordcap) {
                int newcap = wordcap * 2;
                char *nw = (char *)realloc(word, (size_t)newcap);
                char *ns = (char *)realloc(shadow, (size_t)newcap);
                if (!nw || !ns) {
                    free(nw ? nw : word);
                    free(ns ? ns : shadow);
                    *dst = '\0';
                    return;
                }
                word = nw; shadow = ns; wordcap = newcap;
            }
            while (before < p) word[n++] = (char)*before++;
            shadow[sn++] = (char)base;
            src = (char *)p;
        }
        word[n] = '\0';
        shadow[sn] = '\0';
        sep = *src;

        __real_textMeasure(&h, &w, shadow, chars, font, 0);

        if (n > 0 && linewidth > 0 && linewidth + w > wrapwidth) {
            *dst++ = '\n';
            for (int i = 0; i < indent; i++) *dst++ = ' ';
            linewidth = indent * 5;
        }

        if (n > 0) {
            memcpy(dst, word, (size_t)n);
            dst += n;
            linewidth += w;
        }

        if (sep == '\n') {
            *dst++ = '\n';
            linewidth = 0;
            src++;
        } else if (sep == ' ') {
            *dst++ = ' ';
            linewidth += 5;
            src++;
        } else if (sep != '\0') {
            *dst++ = sep;
            src++;
        }
    }
    *dst = '\0';
    free(word);
    free(shadow);
}
