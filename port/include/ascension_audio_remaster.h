#ifndef ASCENSION_AUDIO_REMASTER_H
#define ASCENSION_AUDIO_REMASTER_H

#include <stdint.h>

/* Transparent post-mix remaster for the PC port. No game/audio asset changes. */
int ascensionAudioRemasterInit(int sampleRate);
void ascensionAudioRemasterShutdown(void);
const int16_t *ascensionAudioRemasterProcess(const int16_t *stereoS16, uint32_t lenBytes);
int ascensionAudioRemasterActive(void);

#endif
