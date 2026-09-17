#include <math.h>
#include <stdint.h>
#include <stdlib.h>

#include "mobile_input.h"
#include "input.h"

/* GoldenEye 1.1 controller bits. Kept local so this Android-only adapter does
 * not pull the decomp's PR/os.h into the mobile JNI surface. */
#define GE_CONT_A      0x8000u
#define GE_CONT_B      0x4000u
#define GE_CONT_G      0x2000u
#define GE_CONT_START  0x1000u
#define GE_CONT_L      0x0020u
#define GE_CONT_R      0x0010u
#define GE_CONT_C      0x0002u
#define GE_CONT_F      0x0001u
#define STICK_MAX      80

extern unsigned __real_inputComputePad(int idx, signed char *stick_x,
                                       signed char *stick_y);

static int axis80(float v)
{
    if (v > 1.0f) v = 1.0f;
    if (v < -1.0f) v = -1.0f;
    int out = (int)lrintf(v * (float)STICK_MAX);
    if (out > STICK_MAX) out = STICK_MAX;
    if (out < -STICK_MAX) out = -STICK_MAX;
    return out;
}

/*
 * Android is an input source, not an emulated N64 controller.
 *
 * Relative right-side swipe + gyro are injected BEFORE the regular controller
 * poll so Ascension's existing mode-aware mouse-look code handles yaw/pitch.
 * This gives Android the same smooth path as a modern mouse instead of
 * translating pitch back into a persistent virtual C-button stick.
 *
 * Movement/buttons are merged after the regular poll so a Bluetooth controller
 * and touch controls can coexist without either source zeroing the other.
 */
unsigned __wrap_inputComputePad(int idx, signed char *stick_x,
                                signed char *stick_y)
{
    MobileInputSnapshot m = {0};
    int haveMobile = 0;

    if (idx == 0) {
        mobileInputSnapshot(&m, 1);
        haveMobile = m.touch_active != 0;

        if (haveMobile &&
            (m.look_x != 0.0f || m.look_y != 0.0f ||
             m.gyro_x != 0.0f || m.gyro_y != 0.0f ||
             (m.buttons & MOBILE_BTN_AIM))) {
            inputInjectRelativeLook(
                (double)m.look_x + (double)m.gyro_x,
                (double)m.look_y + (double)m.gyro_y,
                (m.buttons & MOBILE_BTN_AIM) != 0);
        }
    }

    signed char base_x = 0, base_y = 0;
    unsigned button = __real_inputComputePad(idx, &base_x, &base_y);
    int sx = base_x;
    int sy = base_y;

    if (idx == 0 && haveMobile) {
        int moveY = axis80(-m.move_y);
        if (abs(moveY) > abs(sy)) sy = moveY;
        if (m.move_x < -0.16f) button |= GE_CONT_C;
        if (m.move_x >  0.16f) button |= GE_CONT_F;

        if (m.buttons & MOBILE_BTN_FIRE)        button |= GE_CONT_G;
        if (m.buttons & MOBILE_BTN_AIM)         button |= GE_CONT_R;
        if (m.buttons & MOBILE_BTN_USE)         button |= GE_CONT_A;
        if (m.buttons & MOBILE_BTN_RELOAD)      button |= GE_CONT_B;
        if (m.buttons & MOBILE_BTN_PAUSE)       button |= GE_CONT_START;
        if (m.buttons & MOBILE_BTN_WATCH)       button |= GE_CONT_L;
        if (m.buttons & MOBILE_BTN_NEXT_WEAPON) button |= GE_CONT_A;
        if (m.buttons & MOBILE_BTN_PREV_WEAPON) button |= GE_CONT_A;

        /* Dedicated crouch deliberately maps into the original crouch
         * gesture so gameplay restrictions remain authoritative. */
        if (m.buttons & MOBILE_BTN_CROUCH) {
            button |= GE_CONT_R;
            sy = -STICK_MAX;
        }
    }

    if (sx > STICK_MAX) sx = STICK_MAX;
    if (sx < -STICK_MAX) sx = -STICK_MAX;
    if (sy > STICK_MAX) sy = STICK_MAX;
    if (sy < -STICK_MAX) sy = -STICK_MAX;
    if (stick_x) *stick_x = (signed char)sx;
    if (stick_y) *stick_y = (signed char)sy;
    return button;
}
