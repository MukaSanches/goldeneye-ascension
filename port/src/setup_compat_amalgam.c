/*
 * GoldenEye Ascension setup tooling runtime bridge.
 *
 * The PC build already glob-compiles port/src/*.c. Keeping this tiny
 * amalgamation here makes the compatibility core available to the runtime
 * without touching the N64 Makefile or duplicating the tooling implementation.
 * Standalone tooling still compiles the same source files normally through
 * port/setup_compat/CMakeLists.txt.
 */
#ifdef PORT
#include "../setup_compat/asc_setup.c"
#include "../setup_compat/asc_setup_native.c"
#include "../setup_compat/asc_setup_semantic.c"
#include "../setup_compat/asc_setup_writer.c"
#include "../setup_compat/asc_setup_hotreload.c"
#endif
