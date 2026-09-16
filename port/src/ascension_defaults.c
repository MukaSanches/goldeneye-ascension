/*
 * Ascension 0.0.2 visual-defaults migration.
 *
 * The Ascension UI stays in place (F10 control center, discovery hint,
 * categories, restart action, etc.), but the actual visual/window defaults
 * are restored to the values used by the upstream GoldenEye PC port.
 *
 * This runs once per existing ge007.ini. It intentionally does not touch
 * audio, input, save data, mission progress or gameplay state.
 */

#include <string.h>

#include "platform.h"
#include "system.h"
#include "config.h"
#include "ascension_defaults.h"

static int s_originalVisualDefaultsApplied = 0;

PD_CONSTRUCTOR static void ascensionDefaultsConfigInit(void)
{
    configRegisterInt("Ascension.OriginalVisualDefaultsApplied",
                      &s_originalVisualDefaultsApplied, 0, 1);
}

struct VisualDefault {
    const char *key;
    double value;
};

/* Exact fresh-config visual/window defaults from the upstream PC port. */
static const struct VisualDefault kVisualDefaults[] = {
    { "Video.VSync",          1 },
    { "Video.FpsCap",         0 },
    { "Video.DisplayFPS",     0 },
    { "Video.MSAA",           1 },
    { "Video.TextureFilter",  1 },
    { "Video.FixMipTextures", 1 },
    { "Video.WrapFix",        0 },
    { "Video.FovScale",     100 },
    { "Video.Anisotropy",     4 },
    { "Video.Fullscreen",      0 },
    { "Window.Width",          0 },
    { "Window.Height",         0 },
    { "Window.X",             -1 },
    { "Window.Y",             -1 },
    { "Window.Maximized",      0 },
    { "Game.ScreenShakeIntensity", 1 },
};

static void applyVisualDefault(const char *key, int type, void *ptr,
                               double min, double max, double step,
                               const char *label,
                               const char *const *enumNames, void *ctx)
{
    (void)step;
    (void)label;
    (void)enumNames;
    (void)ctx;

    if (!key || !ptr)
        return;

    for (unsigned i = 0;
         i < sizeof(kVisualDefaults) / sizeof(kVisualDefaults[0]);
         ++i) {
        if (strcmp(key, kVisualDefaults[i].key) != 0)
            continue;

        double v = kVisualDefaults[i].value;
        if (min != max) {
            if (v < min) v = min;
            if (v > max) v = max;
        }

        switch (type) {
        case CONFIG_OPT_INT:
            *(int *)ptr = (int)v;
            break;
        case CONFIG_OPT_UINT:
            *(unsigned int *)ptr = (unsigned int)(v < 0 ? 0 : v);
            break;
        case CONFIG_OPT_FLOAT:
            *(float *)ptr = (float)v;
            break;
        default:
            break;
        }
        return;
    }
}

void ascensionRestoreOriginalVisualDefaultsOnce(void)
{
    if (s_originalVisualDefaultsApplied)
        return;

    configForEachOption(applyVisualDefault, NULL);
    s_originalVisualDefaultsApplied = 1;
    configSave();

    sysLogPrintf(LOG_INFO,
        "Ascension 0.0.2: restored upstream visual/window defaults once");
}
