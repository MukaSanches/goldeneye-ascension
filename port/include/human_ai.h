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

/* Thread-safe request. The actual transition is consumed on the scheduler
 * thread by humanAiTick(). */
void humanAiToggle(void);
void humanAiSetEnabled(int enabled);
int  humanAiIsEnabled(void);
const char *humanAiModeName(void);

#ifdef __cplusplus
}
#endif

#endif /* PORT_HUMAN_AI_H */
