#include <android/log.h>
#include <SDL.h>
#include <SDL_system.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

#include "platform.h"
#include "system.h"

static int g_argc;
static char **g_argv;
static volatile int g_restartRequested;
static char g_root[1024];

static const char *androidRoot(void)
{
    if (!g_root[0]) {
        const char *p = SDL_AndroidGetInternalStoragePath();
        if (!p || !*p) p = ".";
        snprintf(g_root, sizeof(g_root), "%s", p);
    }
    return g_root;
}

uint64_t sysGetMicroseconds(void)
{
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (uint64_t)ts.tv_sec * 1000000ull + (uint64_t)ts.tv_nsec / 1000ull;
}

uintptr_t sysImageBase(void) { return 0; }
int64_t sysGetTime(void) { return (int64_t)time(NULL); }

void sysSleep(uint32_t micros)
{
    struct timespec req = {
        .tv_sec = micros / 1000000u,
        .tv_nsec = (long)(micros % 1000000u) * 1000L,
    };
    while (nanosleep(&req, &req) != 0) { }
}

void sysLogPrintf(enum LogLevel level, const char *fmt, ...)
{
    static const int prio[] = {
        ANDROID_LOG_ERROR, ANDROID_LOG_WARN, ANDROID_LOG_INFO,
        ANDROID_LOG_INFO, ANDROID_LOG_DEBUG
    };
    char buf[2048];
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(buf, sizeof(buf), fmt, ap);
    va_end(ap);
    int i = (int)level;
    if (i < 0) i = 0;
    if (i > 4) i = 4;
    __android_log_write(prio[i], "Ascension", buf);
}

void sysFatalError(const char *fmt, ...)
{
    char buf[2048];
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(buf, sizeof(buf), fmt, ap);
    va_end(ap);
    __android_log_write(ANDROID_LOG_FATAL, "Ascension", buf);
    abort();
}

void sysSetArgs(int argc, char **argv) { g_argc = argc; g_argv = argv; }

int sysArgCheck(const char *arg)
{
    for (int i = 1; i < g_argc; ++i)
        if (g_argv[i] && strcmp(g_argv[i], arg) == 0) return 1;
    return 0;
}

const char *sysArgGetString(const char *arg)
{
    for (int i = 1; i + 1 < g_argc; ++i)
        if (g_argv[i] && strcmp(g_argv[i], arg) == 0) return g_argv[i + 1];
    return NULL;
}

const char *sysGetTokenString(void)
{
    static char buf[256];
    static int built;
    if (!built) {
        size_t n = 0;
        for (int i = 1; i < g_argc && g_argv[i]; ++i) {
            size_t len = strlen(g_argv[i]);
            if (n + len + 2 >= sizeof(buf)) break;
            if (n) buf[n++] = ' ';
            memcpy(buf + n, g_argv[i], len);
            n += len;
        }
        buf[n] = 0;
        built = 1;
    }
    return buf;
}

void sysCpuRelax(void)
{
#if defined(__aarch64__)
    __asm__ __volatile__("yield" ::: "memory");
#endif
}

const char *sysGetExeDir(void) { return androidRoot(); }

const char *sysResolvePath(const char *path)
{
    static _Thread_local char out[1536];
    const char *root = androidRoot();
    if (!strncmp(path, "$S/", 3)) {
        snprintf(out, sizeof(out), "%s/data/%s", root, path + 3);
    } else if (!strncmp(path, "$E/", 3)) {
        snprintf(out, sizeof(out), "%s/%s", root, path + 3);
    } else if (path[0] == '/') {
        snprintf(out, sizeof(out), "%s", path);
    } else {
        snprintf(out, sizeof(out), "%s/%s", root, path);
    }
    return out;
}

void sysExit(int code) { exit(code); }
int sysRestart(void) { g_restartRequested = 1; return 0; }
int sysRestartRequested(void) { return g_restartRequested != 0; }

/* Android owns process/activity relaunch. The Java host can recreate the game
 * Activity; native code must never execv() itself inside an APK sandbox. */
int sysRelaunch(void)
{
    sysLogPrintf(LOG_WARNING, "restart requested; Android host must recreate GameActivity");
    return -1;
}
