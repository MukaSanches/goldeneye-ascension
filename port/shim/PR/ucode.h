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
 * x86/Windows net-order prototypes: Android is LP64 and Bionic declares
 * ntohl(uint32_t), whereas unsigned long is 64-bit there.
 *
 * Bridge only the catalogue gate. Rename the two legacy net-order declarations
 * while pc_protos.h is parsed, then publish the ABI-correct AArch64 prototypes.
 * No game/platform translation unit is otherwise compiled as x86-64.
 */
#    if defined(__aarch64__) && !defined(__x86_64__)
#        define ASCENSION_PC_PROTOS_ARM64_BRIDGE 1
#        define __x86_64__ 1
#        define ntohs ascension_pc_protos_ntohs_legacy
#        define ntohl ascension_pc_protos_ntohl_legacy
#    endif
#    include "pc_protos.h"
#    if defined(ASCENSION_PC_PROTOS_ARM64_BRIDGE)
#        undef ntohl
#        undef ntohs
#        undef __x86_64__
#        undef ASCENSION_PC_PROTOS_ARM64_BRIDGE
unsigned short ntohs(unsigned short);
unsigned int ntohl(unsigned int);
#    endif
#else
#    include <PR/ucode.h>
#endif

#endif /* _PORT_SHIM_UCODE_H_ */
