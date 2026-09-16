#ifndef ASCENSION_DEFAULTS_H
#define ASCENSION_DEFAULTS_H

#ifdef __cplusplus
extern "C" {
#endif

/*
 * One-time Ascension 0.0.2 migration.
 *
 * Restores only the PC port's visual/window settings to the upstream
 * GoldenEye PC-port defaults. Input, audio, saves and gameplay progression
 * are deliberately left untouched. The migration is persisted in ge007.ini
 * so later player changes are never overwritten on subsequent launches.
 */
void ascensionRestoreOriginalVisualDefaultsOnce(void);

#ifdef __cplusplus
}
#endif

#endif /* ASCENSION_DEFAULTS_H */
