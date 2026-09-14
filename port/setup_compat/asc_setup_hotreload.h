#ifndef ASCENSION_SETUP_HOTRELOAD_H
#define ASCENSION_SETUP_HOTRELOAD_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/*
 * Developer-only transactional setup override.
 * A candidate is fully parsed, semantically decoded and normalized before it
 * becomes visible to the game loader. Live StageSetup state is never mutated.
 */
int asc_setup_hotreload_stage_bytes(const char *target_resource,
                                    const void *bytes,
                                    size_t size);
int asc_setup_hotreload_stage_file(const char *target_resource,
                                   const char *path);
void asc_setup_hotreload_clear(void);

/* Called only from the PORT resource loader at a stage-load boundary. */
const void *asc_setup_hotreload_acquire(const char *resource,
                                        size_t *out_size,
                                        uint64_t *out_generation);
void asc_setup_hotreload_consumed(uint64_t generation);

/*
 * Optional development workflow:
 *   GE_SETUP_OVERRIDE=/absolute/path/to/Usetup*.bin
 *   GE_SETUP_TARGET=Usetup*.bin     (optional; defaults to any setup resource)
 * The file is revalidated on every setup resource load, so replacing it on
 * disk takes effect on the next safe stage load/restart.
 */
void asc_setup_hotreload_refresh_environment(const char *resource);

#ifdef __cplusplus
}
#endif

#endif /* ASCENSION_SETUP_HOTRELOAD_H */
