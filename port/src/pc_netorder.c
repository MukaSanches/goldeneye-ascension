/*
 * pc_netorder.c - D38: host byte-order helpers (see docs/internals.md).
 *
 * src/bondconstants.h implements ntohl()/ntohs() as function-like macros over
 * CharArrayTo16/32 ("rewrite these to use char array as system provided funcs
 * do not"). Those macros expand <winsock.h>'s own `u_long WSAAPI ntohl(u_long)`
 * declarations into garbage in any TU that parses both, so
 * port/shim/bondconstants.h neutralizes them on PC. This file provides the
 * real functions those calls now bind to (declared in pc_protos.h / the
 * AArch64 bridge in port/shim/PR/ucode.h).
 *
 * On little-endian 64-bit hosts a byte swap is exactly what CharArrayTo16/32
 * computed:
 *   CharArrayTo16(v,0) = v[1] | v[0]<<8        == ntohs(v) on LE
 *   CharArrayTo32(v,0) = v[1]<<16|v[2]<<8|v[3]|v[0]<<24 == ntohl(v) on LE
 */

#include <PR/ultratypes.h>

unsigned short ntohs(unsigned short v)
{
    return (unsigned short)((v >> 8) | (v << 8));
}

/* Windows' u_long is 32-bit even on x64, but Android/Linux LP64 makes
 * unsigned long 64-bit. Match Bionic's uint32_t ABI on AArch64 so including
 * SDL/system endian headers and the Ascension prototype catalogue is safe. */
#if defined(__aarch64__)
unsigned int ntohl(unsigned int v)
{
    return __builtin_bswap32(v);
}
#else
unsigned long ntohl(unsigned long v)
{
    return __builtin_bswap32((unsigned int)v);
}
#endif
