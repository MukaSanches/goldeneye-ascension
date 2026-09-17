#include <android/sharedmem.h>
#include <errno.h>
#include <stdint.h>
#include <sys/mman.h>
#include <unistd.h>

#include "dram.h"
#include "system.h"

#define DRAM_V1_BASE ((void *)(uintptr_t)0x70000000u)
#define DRAM_K0_BASE ((void *)(uintptr_t)0x80000000u)
#define DRAM_SIZE    ((size_t)0x00800000u)

static int addressRangeFree(void *addr, size_t len)
{
    void *p = MAP_FAILED;

#ifdef MAP_FIXED_NOREPLACE
    /* Some API-26-era kernels predate MAP_FIXED_NOREPLACE even when the NDK
     * headers expose the flag. Try it first, then fall back to a harmless
     * address hint. The fallback never uses MAP_FIXED, so it cannot clobber
     * an existing mapping. */
    p = mmap(addr, len, PROT_NONE,
             MAP_PRIVATE | MAP_ANONYMOUS | MAP_FIXED_NOREPLACE, -1, 0);
    if (p != MAP_FAILED) {
        int exact = p == addr;
        munmap(p, len);
        return exact;
    }
#endif

    p = mmap(addr, len, PROT_NONE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (p == MAP_FAILED) return 0;
    int exact = p == addr;
    munmap(p, len);
    return exact;
}

void *dramReserve(void)
{
    if (!addressRangeFree(DRAM_V1_BASE, DRAM_SIZE) ||
        !addressRangeFree(DRAM_K0_BASE, DRAM_SIZE)) {
        sysLogPrintf(LOG_ERROR, "android dram: required low address views are occupied");
        return NULL;
    }

    int fd = ASharedMemory_create("ge007-dram", DRAM_SIZE);
    if (fd < 0) {
        sysLogPrintf(LOG_ERROR, "android dram: ASharedMemory_create failed (%d)", errno);
        return NULL;
    }
    if (ASharedMemory_setProt(fd, PROT_READ | PROT_WRITE) != 0) {
        sysLogPrintf(LOG_ERROR, "android dram: ASharedMemory_setProt failed (%d)", errno);
        close(fd);
        return NULL;
    }

    void *v1 = mmap(DRAM_V1_BASE, DRAM_SIZE, PROT_READ | PROT_WRITE,
                    MAP_SHARED | MAP_FIXED, fd, 0);
    if (v1 == MAP_FAILED || v1 != DRAM_V1_BASE) {
        sysLogPrintf(LOG_ERROR, "android dram: map V1 failed (%d)", errno);
        if (v1 != MAP_FAILED) munmap(v1, DRAM_SIZE);
        close(fd);
        return NULL;
    }

    void *v2 = mmap(DRAM_K0_BASE, DRAM_SIZE, PROT_READ | PROT_WRITE,
                    MAP_SHARED | MAP_FIXED, fd, 0);
    close(fd);
    if (v2 == MAP_FAILED || v2 != DRAM_K0_BASE) {
        sysLogPrintf(LOG_ERROR, "android dram: map KSEG0 failed (%d)", errno);
        munmap(v1, DRAM_SIZE);
        if (v2 != MAP_FAILED) munmap(v2, DRAM_SIZE);
        return NULL;
    }

    ((volatile unsigned char *)v1)[0] = 0x5a;
    if (((volatile unsigned char *)v2)[0] != 0x5a) {
        sysLogPrintf(LOG_ERROR, "android dram: alias verification failed");
        munmap(v1, DRAM_SIZE);
        munmap(v2, DRAM_SIZE);
        return NULL;
    }
    ((volatile unsigned char *)v1)[0] = 0;

    sysLogPrintf(LOG_INFO, "android dram: aliased views mapped at 0x70000000/0x80000000");
    return v1;
}
