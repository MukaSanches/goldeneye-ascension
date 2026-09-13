#ifndef PORT_HUMAN_AI_H
#define PORT_HUMAN_AI_H

#ifdef __cplusplus
extern "C" {
#endif

/*
 * GoldenEye Ascension — Human AI overlay.
 *
 * The original game AI remains untouched in src/game/. This port-layer module
 * observes the real ChrRecord state and adds optional perception/memory/
 * psychology/tactical behaviour on top. Human AI is OFF by default and can be
 * toggled at runtime without replacing any stage AI list.
 */
void humanAiInit(void);
void humanAiShutdown(void);
void humanAiTick(void);

/* Attach after videoInit(): chains fast3d's existing pre-swap callback so the
 * Human AI tick runs on the game scheduler/render thread. */
void humanAiAttachRenderHook(void);
void humanAiDetachRenderHook(void);

/* Thread-safe requests. The transition is consumed by humanAiTick(). */
void humanAiToggle(void);
void humanAiSetEnabled(int enabled);
int  humanAiIsEnabled(void);
const char *humanAiModeName(void);

#ifdef __cplusplus
}
#endif

#endif /* PORT_HUMAN_AI_H */
