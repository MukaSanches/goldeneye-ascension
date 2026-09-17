/*
 * Host-port shim for <math.h>.
 *
 * The decomp's include/math.h contains N64/game-specific constants and helper
 * macros and remains the correct header for C game code. Android C++ code,
 * however, reaches <math.h> through libc++ <cmath>; libc++ must see its own
 * compatibility header before the Bionic C header. Route only that case to
 * the toolchain and preserve the historical header everywhere else.
 */
#if defined(__ANDROID__) && defined(__cplusplus)
#include "hostmath.h"
#else
#include "include/math.h"
#endif
