#pragma once
/* Android host-header trampoline.
 *
 * port/shim/limits.h is found before the NDK because the decomp include tree
 * intentionally precedes the sysroot. Resolve this helper from android/include
 * and continue the search *after* that directory, which reaches Clang/NDK's
 * real <limits.h> instead of the N64 compatibility header.
 */
#include_next <limits.h>
