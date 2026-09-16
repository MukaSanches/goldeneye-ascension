#include <signal.h>
#include <stdlib.h>
#include <unistd.h>

#include "crash.h"
#include "system.h"

static void androidCrashSignal(int sig)
{
    sysLogPrintf(LOG_ERROR, "fatal native signal %d; see Android tombstone/logcat for unwind", sig);
    signal(sig, SIG_DFL);
    raise(sig);
}

void crashInit(void)
{
    signal(SIGABRT, androidCrashSignal);
    signal(SIGBUS, androidCrashSignal);
    signal(SIGFPE, androidCrashSignal);
    signal(SIGILL, androidCrashSignal);
    signal(SIGSEGV, androidCrashSignal);
}

void crashShutdown(void) { }

void crashDumpThreads(const unsigned long *tids, const char **names, int count)
{
    (void)tids; (void)names; (void)count;
    sysLogPrintf(LOG_WARNING, "thread dump requested; use Android native tombstone/perfetto tooling");
}
