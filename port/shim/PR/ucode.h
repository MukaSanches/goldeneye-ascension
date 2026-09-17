/*
 * Host-port shim for PR/ucode.h.
 *
 * Pass-through to the real header, plus — because ucode.h is the LAST include
 * in <ultra64.h> (after libaudio.h, whose partial-parse poisoning is the
 * reason pc_protos.h cannot anchor earlier, e.g. in gbi.h) — the D38
 * prototype catalogue for implicitly declared game functions.
 *
 * pc_protos.h is ABI-aware for x86-64 and AArch64. Do not spoof architecture
 * macros here: doing so leaks x86/Windows type assumptions into Android LP64.
 * Inert in the N64 build (port/shim is not on its include path).
 */
#ifndef _PORT_SHIM_UCODE_H_
#define _PORT_SHIM_UCODE_H_

#if defined(PORT)
#    include "include/PR/ucode.h"
#    include "pc_protos.h"
#else
#    include <PR/ucode.h>
#endif

#endif /* _PORT_SHIM_UCODE_H_ */
