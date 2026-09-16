#ifndef ASCENSION_WATCH_H
#define ASCENSION_WATCH_H

#ifdef __cplusplus
extern "C" {
#endif

/* Narrow bridge into GoldenEye's native solo-watch flow. The implementation
 * is installed by apply_watch_runtime_fix.py before Ascension 0.0.4 builds. */
int ascensionWatchIsActive(void);
void ascensionWatchReturnToMainMenu(void);

#ifdef __cplusplus
}
#endif

#endif /* ASCENSION_WATCH_H */
