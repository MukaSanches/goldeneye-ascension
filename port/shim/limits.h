/*
 * Host-port shim for <limits.h>.
 *
 * The decomp ships include/limits.h with N64/SGI assumptions. That file must
 * remain available to source that explicitly asks for "include/limits.h", but
 * host libraries such as Android's Bionic/zlib must see the toolchain limits
 * contract (SSIZE_MAX, LP64 LONG_MAX, etc.). The Android helper deliberately
 * resumes header lookup after android/include so it reaches Clang/NDK.
 *
 * Non-Android ports retain the decomp header path used by the existing build.
 */
#if defined(__ANDROID__)
#include "hostlimits.h"
#else
#include "include/limits.h"
#endif
