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
 * the first 64-bit host port. Android V1 is AArch64 and has the same ABI
 * requirement for pointer-returning functions, but it must not inherit the
 * legacy Windows/x86 net-order declarations: Android is LP64 and Bionic
 * declares ntohl(uint32_t), whereas unsigned long is 64-bit there.
 *
 * pc_protos.h already skips those two declarations when a Winsock declaration
 * is known. Reuse that guard strictly as a private include-time sentinel on
 * AArch64, then immediately remove it and publish the Bionic-compatible
 * signatures. No Windows header or Windows behavior is exposed to Android.
 */
#    if defined(__aarch64__) && !defined(__x86_64__)
#        define ASCENSION_PC_PROTOS_ARM64_BRIDGE 1
#        define __x86_64__ 1
#        if !defined(_WINSOCK2_H)
#            define ASCENSION_PC_PROTOS_NETORDER_SENTINEL 1
#            define _WINSOCK2_H 1
#        endif
#    endif
#    include "pc_protos.h"
#    if defined(ASCENSION_PC_PROTOS_ARM64_BRIDGE)
#        if defined(ASCENSION_PC_PROTOS_NETORDER_SENTINEL)
#            undef _WINSOCK2_H
#            undef ASCENSION_PC_PROTOS_NETORDER_SENTINEL
#        endif
#        undef __x86_64__
#        undef ASCENSION_PC_PROTOS_ARM64_BRIDGE
unsigned short ntohs(unsigned short);
unsigned int ntohl(unsigned int);
#    endif
#else
#    include <PR/ucode.h>
#endif

#endif /* _PORT_SHIM_UCODE_H_ */
