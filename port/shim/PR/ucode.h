/*
 * PC port shim for PR/ucode.h.
 *
 * Pass-through to the real header, plus — because ucode.h is the LAST include
 * in <ultra64.h> (after libaudio.h, whose partial-parse poisoning is the
 * reason pc_protos.h cannot anchor earlier, e.g. in gbi.h) — the D38
 * prototype header for implicitly declared game functions.
 *
 * Inert in the N64 build (port/shim is not on its include path).
 */
#ifndef _PORT_SHIM_UCODE_H_
#define _PORT_SHIM_UCODE_H_

#if defined(PORT)
#    include "include/PR/ucode.h"
/*
 * D38's prototype catalogue was originally gated to x86-64 because that was
 * the first 64-bit host port. Android V1 is AArch64 and has the exact same ABI
 * requirement: an undeclared pointer-returning function must never decay to
 * `int`. Keep the architecture compatibility shim local to this include so no
 * game or platform code is compiled as x86-64.
 */
#    if defined(__aarch64__) && !defined(__x86_64__)
#        define ASCENSION_PC_PROTOS_ARM64_BRIDGE 1
#        define __x86_64__ 1
#    endif
#    include "pc_protos.h"
#    if defined(ASCENSION_PC_PROTOS_ARM64_BRIDGE)
#        undef __x86_64__
#        undef ASCENSION_PC_PROTOS_ARM64_BRIDGE
#    endif
#else
#    include <PR/ucode.h>
#endif

#endif /* _PORT_SHIM_UCODE_H_ */
