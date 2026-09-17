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
#    if defined(__ANDROID__) && defined(__aarch64__) && !defined(__cplusplus)
/* frontGetPlayersFavoriteWeaponInHand is a decomp 32-bit artifact: the source
 * spells the return type as int even though it forwards a langGet() text
 * pointer. Hide only that stale catalogue declaration on Android, then publish
 * the pointer-width-correct ABI used by the generated front_android.c TU. */
#        define frontGetPlayersFavoriteWeaponInHand ascension_legacy_frontGetPlayersFavoriteWeaponInHand
#        include "pc_protos.h"
#        undef frontGetPlayersFavoriteWeaponInHand
u8 *frontGetPlayersFavoriteWeaponInHand(int player, int hand);
#    else
#        include "pc_protos.h"
#    endif
#else
#    include <PR/ucode.h>
#endif

#endif /* _PORT_SHIM_UCODE_H_ */
