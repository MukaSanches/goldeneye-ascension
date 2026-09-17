#ifndef _STR_H_
#define _STR_H_

#include <ultra64.h>
/*#include <stddef.h>*/

/*
 * Android/Bionic declares strcpy/strncpy/strcat as Clang overloadable Fortify
 * entry points. The N64 codebase also ships private implementations of those
 * libc names (src/str.c), including PORT-specific NULL-source guards. A plain
 * redeclaration cannot legally coexist with Bionic's overload set, and making
 * the game implementations overloadable would change their C symbol ABI.
 *
 * Keep the game semantics without interposing on Bionic: Android translation
 * units that intentionally include this header use private ge_* symbols. The
 * macros also rename the definitions in src/str.c because it includes this
 * header first. Desktop/N64 names and ABI remain byte-for-byte unchanged.
 */
#if defined(__ANDROID__)
#define strcpy  ge_strcpy
#define strncpy ge_strncpy
#define strcat  ge_strcat
#endif

char *strcpy(char *dst, const char *src);
char *strncpy(char *dst, const char *src, size_t n);
char *strcat(char *dst, const char *src);
int strcmp(const char* str1, const char* str2);
int strncmp(const char *str1, const char *str2, size_t n);
long int strtol(const char *str, char **endptr, int base);

#endif
