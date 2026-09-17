#ifndef ASCENSION_ANDROID_MOBILE_INPUT_H
#define ASCENSION_ANDROID_MOBILE_INPUT_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

enum MobileButton {
    MOBILE_BTN_FIRE        = 1u << 0,
    MOBILE_BTN_AIM         = 1u << 1,
    MOBILE_BTN_USE         = 1u << 2,
    MOBILE_BTN_RELOAD      = 1u << 3,
    MOBILE_BTN_CROUCH      = 1u << 4,
    MOBILE_BTN_NEXT_WEAPON = 1u << 5,
    MOBILE_BTN_PREV_WEAPON = 1u << 6,
    MOBILE_BTN_PAUSE       = 1u << 7,
    MOBILE_BTN_WATCH       = 1u << 8,
};

typedef struct MobileInputSnapshot {
    float move_x, move_y;
    float look_x, look_y;
    float gyro_x, gyro_y;
    uint32_t buttons;
    int touch_active;
} MobileInputSnapshot;

void mobileInputSetMove(float x, float y);
void mobileInputSetLook(float x, float y);
void mobileInputAddGyro(float x, float y);
void mobileInputSetButton(uint32_t button, int down);
void mobileInputSetTouchActive(int active);
void mobileInputSnapshot(MobileInputSnapshot *out, int consumeMotion);
void mobileInputReset(void);

#ifdef __cplusplus
}
#endif

#endif
