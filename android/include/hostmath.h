#pragma once
/* Android C++ host-header trampoline.
 *
 * libc++ <cmath> deliberately includes its own <math.h> compatibility layer.
 * Because the decomp include tree precedes the NDK sysroot, the N64 math.h
 * would otherwise shadow that layer. This helper is resolved from
 * android/include and resumes lookup after that directory, reaching libc++.
 */
#include_next <math.h>
