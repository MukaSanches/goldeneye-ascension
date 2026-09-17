#include <math.h>
#include <stdint.h>
#include <sys/mman.h>

#include "dram.h"
#include "input.h"
#include "mobile_input.h"
#include "system.h"
#include "video.h"

#define SELFTEST_CART_BASE ((void *)(uintptr_t)0x10000000u)
#define SELFTEST_CART_SIZE ((size_t)0x00010000u)

static int cartAddressAvailable(void)
{
    void *p = MAP_FAILED;

#ifdef MAP_FIXED_NOREPLACE
    p = mmap(SELFTEST_CART_BASE, SELFTEST_CART_SIZE, PROT_NONE,
             MAP_PRIVATE | MAP_ANONYMOUS | MAP_FIXED_NOREPLACE, -1, 0);
    if (p != MAP_FAILED) {
        int exact = p == SELFTEST_CART_BASE;
        munmap(p, SELFTEST_CART_SIZE);
        return exact;
    }
#endif

    p = mmap(SELFTEST_CART_BASE, SELFTEST_CART_SIZE, PROT_NONE,
             MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (p == MAP_FAILED) return 0;
    int exact = p == SELFTEST_CART_BASE;
    munmap(p, SELFTEST_CART_SIZE);
    return exact;
}

static int mobileInputRoundTrip(void)
{
    MobileInputSnapshot a = {0};
    MobileInputSnapshot b = {0};

    mobileInputReset();
    mobileInputSetTouchActive(1);
    mobileInputSetMove(0.5f, -0.25f);
    mobileInputSetLook(3.0f, -2.0f);
    mobileInputAddGyro(1.0f, -0.5f);
    mobileInputSetButton(MOBILE_BTN_FIRE, 1);

    mobileInputSnapshot(&a, 1);
    mobileInputSnapshot(&b, 0);

    if (!a.touch_active || !(a.buttons & MOBILE_BTN_FIRE)) return 0;
    if (fabsf(a.move_x - 0.5f) > 0.001f ||
        fabsf(a.move_y + 0.25f) > 0.001f) return 0;
    if (fabsf(a.look_x - 3.0f) > 0.001f ||
        fabsf(a.look_y + 2.0f) > 0.001f) return 0;
    if (fabsf(a.gyro_x - 1.0f) > 0.001f ||
        fabsf(a.gyro_y + 0.5f) > 0.001f) return 0;
    if (b.look_x != 0.0f || b.look_y != 0.0f ||
        b.gyro_x != 0.0f || b.gyro_y != 0.0f) return 0;
    if (fabsf(b.move_x - 0.5f) > 0.001f ||
        !(b.buttons & MOBILE_BTN_FIRE)) return 0;

    mobileInputReset();
    return 1;
}

int androidRunSelfTest(void)
{
    sysLogPrintf(LOG_INFO, "ASCENSION_ANDROID_SELFTEST_BEGIN");

    if (!mobileInputRoundTrip()) {
        sysLogPrintf(LOG_ERROR, "android selftest: mobile input round-trip failed");
        return 90;
    }

    if (!cartAddressAvailable()) {
        sysLogPrintf(LOG_ERROR,
                     "android selftest: required cart address 0x10000000 unavailable");
        return 91;
    }

    if (!dramReserve()) {
        sysLogPrintf(LOG_ERROR, "android selftest: DRAM alias reservation failed");
        return 92;
    }

    if (videoInit() != 0) {
        sysLogPrintf(LOG_ERROR, "android selftest: SDL/GLES video init failed");
        return 93;
    }

    if (inputInit() != 0) {
        sysLogPrintf(LOG_ERROR, "android selftest: SDL input init failed");
        videoDestroy();
        return 94;
    }

    videoPumpEvents();
    inputDestroy();
    videoDestroy();

    sysLogPrintf(LOG_INFO, "ASCENSION_ANDROID_SELFTEST_OK");
    return 0;
}
