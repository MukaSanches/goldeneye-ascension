#ifndef ASCENSION_WATCH_H
#define ASCENSION_WATCH_H

#ifdef __cplusplus
extern "C" {
#endif

/*
 * Ascension's narrow bridge into GoldenEye's native solo-watch flow.
 *
 * This deliberately does not expose save/progression internals. The
 * implementation in src/game/options.c reuses the exact mission-abort path
 * already used by the Q Watch, so a PC UI can return to the normal front end
 * without inventing a second state transition.
 */
void ascensionWatchReturnToMainMenu(void);

#ifdef __cplusplus
}
#endif

#endif /* ASCENSION_WATCH_H */
