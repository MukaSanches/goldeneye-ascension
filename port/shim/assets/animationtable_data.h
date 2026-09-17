/*
 * Android/AArch64 compatibility shim for assets/animationtable_data.h.
 *
 * The upstream header names its host-offset branch `__x86_64__`, but the
 * branch is not x86 instruction- or ABI-specific: it makes ANIM_DATA_* an
 * address-only lvalue at g_pc_animdata_base + ROM-segment offset so the
 * legacy `(s32)&ANIM_DATA_x + ptr_animation_table` arithmetic keeps the N64
 * VMA-0 semantics on a 64-bit host. romdata.c provides the same 4-GiB-aligned
 * g_pc_animdata_base on Android/AArch64.
 *
 * Keep the architecture compatibility local to this one legacy generated
 * header. The macro is restored immediately after include_next, so no x86
 * assumptions can leak into Android headers or translation units. This shim
 * can disappear once the generated header keys that branch on PORT/host-64
 * rather than the historical x86_64 spelling.
 */
#ifndef ASCENSION_ANDROID_ANIMATIONTABLE_DATA_SHIM_H
#define ASCENSION_ANDROID_ANIMATIONTABLE_DATA_SHIM_H

#if defined(__ANDROID__) && defined(__aarch64__) && !defined(__x86_64__)
#    pragma push_macro("__x86_64__")
#    define __x86_64__ 1
#    include_next <assets/animationtable_data.h>
#    pragma pop_macro("__x86_64__")
#else
#    include_next <assets/animationtable_data.h>
#endif

#endif /* ASCENSION_ANDROID_ANIMATIONTABLE_DATA_SHIM_H */
