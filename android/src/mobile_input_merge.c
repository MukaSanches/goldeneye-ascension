#include <math.h>
#include <stdint.h>

#include "mobile_input.h"

/* GoldenEye 1.1 controller bits. Kept local so this Android-only adapter does
 * not pull the decomp's PR/os.h into the mobile JNI surface. */
#define GE_CONT_A      0x8000u
#define GE_CONT_B      0x4000u
#define GE_CONT_G      0x2000u
#define GE_CONT_START  0x1000u
#define GE_CONT_L      0x0020u
#define GE_CONT_R      0x0010u
#define GE_CONT_E      0x0008u
#define GE_CONT_D      0x0004u
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
 * Android touch is intentionally translated at the same boundary used by
 * SDL controllers. This means the GoldenEye simulation never knows whether a
 * command came from a touchscreen, gyro, Bluetooth pad or the desktop paths.
 *
 * Left stick:
 *   Y -> native analog forward/back
 *   X -> native C-left/right strafe
 * Right stick + gyro:
 *   X -> native analog yaw
 *   Y -> native C-up/down pitch (aim mode remains owned by the original game)
 */
unsigned __wrap_inputComputePad(int idx, signed char *stick_x,
                                signed char *stick_y)
{
    signed char base_x = 0, base_y = 0;
    unsigned button = __real_inputComputePad(idx, &base_x, &base_y);
    int sx = base_x;
    int sy = base_y;

    if (idx == 0) {
        MobileInputSnapshot m;
        mobileInputSnapshot(&m, 1);
        if (m.touch_active) {
            /* Forward/back is analog. Horizontal movement is strafe because
             * the right side owns yaw on a modern mobile FPS layout. */
            int moveY = axis80(-m.move_y);
            if (abs(moveY) > abs(sy)) sy = moveY;
            if (m.move_x < -0.16f) button |= GE_CONT_C;
            if (m.move_x >  0.16f) button |= GE_CONT_F;

            /* Gyro is an additive fine-look source. Java sends small deltas;
             * clamp after adding them to the touch right-stick vector. */
            float lookX = m.look_x + m.gyro_x;
            float lookY = m.look_y + m.gyro_y;
            if (lookX > 1.0f) lookX = 1.0f;
            if (lookX < -1.0f) lookX = -1.0f;
            if (lookY > 1.0f) lookY = 1.0f;
            if (lookY < -1.0f) lookY = -1.0f;

            int lookYaw = axis80(lookX);
            if (abs(lookYaw) > abs(sx)) sx = lookYaw;
            if (lookY < -0.12f) button |= GE_CONT_E;
            if (lookY >  0.12f) button |= GE_CONT_D;

            if (m.buttons & MOBILE_BTN_FIRE)        button |= GE_CONT_G;
            if (m.buttons & MOBILE_BTN_AIM)         button |= GE_CONT_R;
            if (m.buttons & MOBILE_BTN_USE)         button |= GE_CONT_A;
            if (m.buttons & MOBILE_BTN_RELOAD)      button |= GE_CONT_B;
            if (m.buttons & MOBILE_BTN_PAUSE)       button |= GE_CONT_START;
            if (m.buttons & MOBILE_BTN_WATCH)       button |= GE_CONT_L;
            if (m.buttons & MOBILE_BTN_NEXT_WEAPON) button |= GE_CONT_A;
            if (m.buttons & MOBILE_BTN_PREV_WEAPON) button |= GE_CONT_A;

            /* Dedicated crouch is represented with GoldenEye's native 1.1
             * aim + stick-down gesture so the original crouch restrictions
             * and state machine remain authoritative. */
            if (m.buttons & MOBILE_BTN_CROUCH) {
                button |= GE_CONT_R;
                sy = -STICK_MAX;
            }
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
