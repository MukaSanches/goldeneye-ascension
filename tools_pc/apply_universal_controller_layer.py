#!/usr/bin/env python3
"""Ascension 0.0.4 universal controller compatibility layer.

This patch runs after Modern Controls V4 + live pad bindings.  It deliberately
normalizes physical controllers *before* V4 sees them, so accepted mouse,
keyboard, Q-Watch, F10 and Modern look/movement code remain authoritative.

Layers:
1) SDL2 built-in/XInput mappings (preferred, zero heuristics).
2) Optional local SDL_GameControllerDB + user mapping files.
3) Conservative raw-joystick fallback for unknown generic USB pads.
4) Packed logical controller slots + hot-plug/remap support.

Unknown hardware can never be semantically inferred with mathematical
certainty; the fallback uses a common DirectInput layout, persists it separately
from user mappings, and is always lower priority than community/user mappings.
"""
from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "port/src/input.c"
VIDEO = ROOT / "port/src/video.c"


class PatchError(RuntimeError):
    pass


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        return text
    count = text.count(old)
    if count != 1:
        raise PatchError(f"{label}: expected exactly one anchor, found {count}")
    return text.replace(old, new, 1)


def patch_input(text: str) -> str:
    if "ascensionControlsQueueGamepadAxes" not in text:
        raise PatchError("Modern Controls V4 core is not installed")
    if "inputPadBindingCapturePressed" not in text:
        raise PatchError("Modern Controls V4 pad bindings are not installed")
    if "ASCENSION UNIVERSAL CONTROLLER LAYER" in text:
        return text

    text = replace_once(
        text,
        "#include <math.h>\n#include <stdlib.h>\n#include <string.h>\n",
        "#include <math.h>\n#include <stdio.h>\n#include <stdlib.h>\n#include <string.h>\n",
        "stdio include",
    )

    old_state = """static int numControllers = 1;
static int connectedMask   = 0x1;   /* controller 0 always present */

static SDL_GameController *pads[MAX_PADS];
"""
    new_state = r'''/* ASCENSION UNIVERSAL CONTROLLER LAYER
 *
 * SDL_GameController is the normalization boundary.  Xbox/XInput, HIDAPI and
 * every controller SDL already knows take the exact standard path.  Only raw
 * joysticks that are still unknown after external databases are loaded reach
 * the conservative generic mapper below. */
static int numControllers = 1;
static int connectedMask   = 0x1;   /* controller 0 always exists via KB/mouse */
static int controllerDbEnabled = 1;
static int autoMapUnknownGamepads = 1;

static SDL_GameController *pads[MAX_PADS];
static char padNames[MAX_PADS][96];
static char padFamilies[MAX_PADS][24];
static char padGuids[MAX_PADS][33];
'''
    text = replace_once(text, old_state, new_state, "universal controller state")

    old_open = r'''static void inputOpenPads(void)
{
    connectedMask = 0x1;
    int n = SDL_NumJoysticks();
    for (int i = 0; i < n && i < MAX_PADS; ++i) {
        if (!SDL_IsGameController(i)) {
            continue;
        }
        if (pads[i]) {
            continue;
        }
        pads[i] = SDL_GameControllerOpen(i);
        if (pads[i]) {
            connectedMask |= (1 << i);
            sysLogPrintf(LOG_NOTE, "input: opened gamepad %d '%s' as controller %d",
                         i, SDL_GameControllerName(pads[i]), i);
        }
    }
    for (int i = 0; i < MAX_PADS; ++i) {
        if (pads[i]) {
            connectedMask |= (1 << i);
        }
    }
    numControllers = 1;
    for (int i = 1; i < MAX_PADS; ++i) {
        if (connectedMask & (1 << i)) {
            numControllers = i + 1;
        }
    }
}
'''
    universal = r'''static int strContainsNoCase(const char *haystack, const char *needle)
{
    if (!haystack || !needle || !*needle)
        return 0;
    size_t n = strlen(needle);
    for (const char *p = haystack; *p; ++p) {
        if (SDL_strncasecmp(p, needle, n) == 0)
            return 1;
    }
    return 0;
}

static const char *controllerFamilyFromName(const char *name)
{
    if (!name || !*name) return "GENERIC";
    if (strContainsNoCase(name, "xbox") || strContainsNoCase(name, "xinput"))
        return "XBOX";
    if (strContainsNoCase(name, "dualsense") || strContainsNoCase(name, "dualshock") ||
        strContainsNoCase(name, "playstation") || strContainsNoCase(name, "ps4") ||
        strContainsNoCase(name, "ps5"))
        return "PLAYSTATION";
    if (strContainsNoCase(name, "switch") || strContainsNoCase(name, "joy-con") ||
        strContainsNoCase(name, "nintendo"))
        return "NINTENDO";
    if (strContainsNoCase(name, "8bitdo"))
        return "8BITDO";
    if (strContainsNoCase(name, "steam"))
        return "STEAM";
    if (strContainsNoCase(name, "logitech"))
        return "LOGITECH";
    return "GENERIC";
}

static int mappingFileExists(const char *path)
{
    FILE *f = fopen(path, "rb");
    if (!f) return 0;
    fclose(f);
    return 1;
}

static int loadControllerMappingFile(const char *path, const char *label)
{
    if (!controllerDbEnabled || !mappingFileExists(path))
        return 0;
    int n = SDL_GameControllerAddMappingsFromFile(path);
    if (n < 0) {
        sysLogPrintf(LOG_WARNING, "input: could not load %s mappings '%s': %s",
                     label, path, SDL_GetError());
        return -1;
    }
    sysLogPrintf(LOG_INFO, "input: loaded %d %s controller mapping(s) from %s",
                 n, label, path);
    return n;
}

static void inputLoadControllerMappings(void)
{
    if (!controllerDbEnabled)
        return;

    /* Priority is deliberate.  Auto-generated heuristics are lowest;
     * community mappings override them; explicit user mappings win last. */
    loadControllerMappingFile("data/ascension-auto-mappings.txt", "auto");
    loadControllerMappingFile("gamecontrollerdb.txt", "community");
    loadControllerMappingFile("data/gamecontrollerdb.txt", "community");
    loadControllerMappingFile("data/ascension-controller-mappings.txt", "user");
}

static int autoMappingAlreadySaved(const char *guid)
{
    FILE *f = fopen("data/ascension-auto-mappings.txt", "rb");
    if (!f) return 0;
    char line[1536];
    size_t n = strlen(guid);
    while (fgets(line, sizeof(line), f)) {
        if (strncmp(line, guid, n) == 0 && line[n] == ',') {
            fclose(f);
            return 1;
        }
    }
    fclose(f);
    return 0;
}

static void persistAutoMapping(const char *guid, const char *mapping)
{
    if (!guid || !mapping || autoMappingAlreadySaved(guid))
        return;
    FILE *f = fopen("data/ascension-auto-mappings.txt", "ab");
    if (!f) {
        sysLogPrintf(LOG_INFO,
                     "input: generic mapping active for this run (could not persist auto map)");
        return;
    }
    fprintf(f, "%s\n", mapping);
    fclose(f);
    sysLogPrintf(LOG_INFO, "input: persisted generic fallback mapping for GUID %s", guid);
}

static void sanitizeMappingName(char *dst, size_t cap, const char *src)
{
    if (!dst || cap == 0) return;
    size_t j = 0;
    if (!src) src = "Unknown Generic Controller";
    for (size_t i = 0; src[i] && j + 1 < cap; ++i) {
        unsigned char c = (unsigned char)src[i];
        dst[j++] = (c == ',' || c < 32) ? ' ' : (char)c;
    }
    dst[j] = 0;
}

static int inputInstallGenericMapping(int deviceIndex)
{
    if (SDL_IsGameController(deviceIndex))
        return 1;
    if (!autoMapUnknownGamepads)
        return 0;

    SDL_Joystick *joy = SDL_JoystickOpen(deviceIndex);
    if (!joy) {
        sysLogPrintf(LOG_WARNING, "input: raw joystick %d could not open: %s",
                     deviceIndex, SDL_GetError());
        return 0;
    }

    int axes = SDL_JoystickNumAxes(joy);
    int buttons = SDL_JoystickNumButtons(joy);
    int hats = SDL_JoystickNumHats(joy);
    SDL_JoystickGUID guid = SDL_JoystickGetGUID(joy);
    char guidText[33];
    SDL_JoystickGetGUIDString(guid, guidText, sizeof(guidText));
    char safeName[96];
    sanitizeMappingName(safeName, sizeof(safeName), SDL_JoystickName(joy));

    /* A device without a directional pair + four digital buttons is too
     * ambiguous to pretend it is a gamepad (wheel, pedals, HOTAS, etc.). */
    if (axes < 2 || buttons < 4 || !guidText[0]) {
        sysLogPrintf(LOG_NOTE,
                     "input: joystick %d '%s' left raw (axes=%d buttons=%d hats=%d)",
                     deviceIndex, safeName, axes, buttons, hats);
        SDL_JoystickClose(joy);
        return 0;
    }

    char map[1536];
    size_t used = (size_t)snprintf(map, sizeof(map),
        "%s,%s,a:b0,b:b1,x:b2,y:b3,leftx:a0,lefty:a1",
        guidText, safeName[0] ? safeName : "Ascension Generic Controller");
#define MAP_ADD(...) do { \
    if (used < sizeof(map)) { \
        int _n = snprintf(map + used, sizeof(map) - used, __VA_ARGS__); \
        if (_n > 0) used += (size_t)_n; \
    } \
} while (0)

    if (buttons >= 6)
        MAP_ADD(",leftshoulder:b4,rightshoulder:b5");
    if (buttons >= 8)
        MAP_ADD(",back:b6,start:b7");
    if (buttons >= 10)
        MAP_ADD(",leftstick:b8,rightstick:b9");

    if (axes >= 6) {
        /* Most otherwise-unmapped DirectInput dual-stick pads expose
         * LX/LY,RX,LT,RT,RY as axes 0..5. Known exceptions are caught by the
         * SDL/community DB before this fallback is ever considered. */
        MAP_ADD(",rightx:a2,righty:a5,lefttrigger:a3,righttrigger:a4");
    } else if (axes >= 4) {
        MAP_ADD(",rightx:a2,righty:a3");
        if (buttons >= 6)
            MAP_ADD(",lefttrigger:b4,righttrigger:b5");
    } else if (buttons >= 6) {
        /* Two-axis legacy pads remain playable: shoulders double as triggers. */
        MAP_ADD(",lefttrigger:b4,righttrigger:b5");
    }

    if (hats > 0)
        MAP_ADD(",dpup:h0.1,dpright:h0.2,dpdown:h0.4,dpleft:h0.8");

    MAP_ADD(",platform:%s,", SDL_GetPlatform());
#undef MAP_ADD
    SDL_JoystickClose(joy);

    if (used >= sizeof(map)) {
        sysLogPrintf(LOG_WARNING, "input: generic mapping overflow for '%s'", safeName);
        return 0;
    }

    int rc = SDL_GameControllerAddMapping(map);
    if (rc < 0 || !SDL_IsGameController(deviceIndex)) {
        sysLogPrintf(LOG_WARNING, "input: generic mapping rejected for '%s': %s",
                     safeName, SDL_GetError());
        return 0;
    }

    persistAutoMapping(guidText, map);
    sysLogPrintf(LOG_NOTE,
        "input: AUTO-MAPPED unknown controller '%s' (axes=%d buttons=%d hats=%d guid=%s)",
        safeName, axes, buttons, hats, guidText);
    return 1;
}

static void clearPadMetadata(void)
{
    for (int i = 0; i < MAX_PADS; ++i) {
        padNames[i][0] = 0;
        padFamilies[i][0] = 0;
        padGuids[i][0] = 0;
    }
}

static void inputOpenPads(void)
{
    connectedMask = 0x1;
    clearPadMetadata();

    int logical = 0;
    int n = SDL_NumJoysticks();
    for (int device = 0; device < n && logical < MAX_PADS; ++device) {
        if (!SDL_IsGameController(device) && !inputInstallGenericMapping(device))
            continue;

        SDL_GameController *pad = SDL_GameControllerOpen(device);
        if (!pad)
            continue;

        /* Physical SDL device indices can contain skipped wheels/HOTAS/raw
         * joysticks. Pack recognized gamepads into contiguous GoldenEye slots. */
        pads[logical] = pad;
        connectedMask |= (1 << logical);

        const char *name = SDL_GameControllerName(pad);
        snprintf(padNames[logical], sizeof(padNames[logical]), "%s",
                 name && *name ? name : "SDL Game Controller");
        snprintf(padFamilies[logical], sizeof(padFamilies[logical]), "%s",
                 controllerFamilyFromName(padNames[logical]));

        SDL_Joystick *joy = SDL_GameControllerGetJoystick(pad);
        if (joy) {
            SDL_JoystickGUID guid = SDL_JoystickGetGUID(joy);
            SDL_JoystickGetGUIDString(guid, padGuids[logical], sizeof(padGuids[logical]));
        }

        sysLogPrintf(LOG_NOTE,
            "input: controller %d <- SDL device %d '%s' family=%s guid=%s",
            logical, device, padNames[logical], padFamilies[logical],
            padGuids[logical][0] ? padGuids[logical] : "unknown");
        logical++;
    }

    numControllers = logical > 0 ? logical : 1;
    if (logical == 0)
        sysLogPrintf(LOG_INFO, "input: controller 0 = keyboard/mouse (no gamepad connected)");
}
'''
    text = replace_once(text, old_open, universal, "universal controller resolver")

    init_anchor = r'''    for (int i = 0; i < MAX_PADS; ++i) {
        pads[i] = NULL;
    }
    inputOpenPads();'''
    init_new = r'''    for (int i = 0; i < MAX_PADS; ++i) {
        pads[i] = NULL;
    }
    inputLoadControllerMappings();
    inputOpenPads();'''
    text = replace_once(text, init_anchor, init_new, "mapping DB startup load")

    old_rescan = r'''void inputRescanPads(void)
{
    for (int i = 0; i < MAX_PADS; ++i) {
        if (pads[i]) {
            SDL_GameControllerClose(pads[i]);
            pads[i] = NULL;
        }
    }
    inputOpenPads();
    sysLogPrintf(LOG_NOTE, "input: rescanned pads (mask=0x%x, %d controller(s))",
                 connectedMask, numControllers);
}'''
    new_rescan = r'''void inputRescanPads(void)
{
    for (int i = 0; i < MAX_PADS; ++i) {
        if (pads[i]) {
            SDL_GameControllerClose(pads[i]);
            pads[i] = NULL;
        }
    }
    /* Re-read local files: a mapping dropped into data/ while the game is
     * running becomes active on the next hot-plug/rescan. */
    inputLoadControllerMappings();
    inputOpenPads();
    sysLogPrintf(LOG_NOTE, "input: rescanned pads (mask=0x%x, %d controller(s))",
                 connectedMask, numControllers);
}'''
    text = replace_once(text, old_rescan, new_rescan, "hotplug mapping reload")

    config_anchor = r'''    configRegisterInt("Input.PadLookInvertY", &padLookInvertY, 0, 1);
'''
    config_new = config_anchor + r'''    configRegisterInt("Input.ControllerDbEnabled", &controllerDbEnabled, 0, 1);
    configRegisterInt("Input.AutoMapUnknownGamepads", &autoMapUnknownGamepads, 0, 1);
'''
    text = replace_once(text, config_anchor, config_new, "universal input config")
    return text


def patch_video(text: str) -> str:
    if "ASCENSION UNIVERSAL CONTROLLER EVENTS" in text:
        return text
    old = r'''        case SDL_CONTROLLERDEVICEADDED:
        case SDL_CONTROLLERDEVICEREMOVED:
            inputRescanPads();
            break;'''
    new = r'''        /* ASCENSION UNIVERSAL CONTROLLER EVENTS: raw joystick events are
         * required because an unknown generic pad is not a GameController until
         * our fallback mapping has been installed. REMAPPED picks up driver/DB
         * changes without a restart. Duplicate add events are safe: rescan is
         * idempotent and owns every SDL_GameController handle. */
        case SDL_CONTROLLERDEVICEADDED:
        case SDL_CONTROLLERDEVICEREMOVED:
        case SDL_CONTROLLERDEVICEREMAPPED:
        case SDL_JOYDEVICEADDED:
        case SDL_JOYDEVICEREMOVED:
            inputRescanPads();
            break;'''
    return replace_once(text, old, new, "universal controller event pump")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    originals = {
        INPUT: INPUT.read_text(encoding="utf-8"),
        VIDEO: VIDEO.read_text(encoding="utf-8"),
    }
    try:
        updated = {
            INPUT: patch_input(originals[INPUT]),
            VIDEO: patch_video(originals[VIDEO]),
        }
    except PatchError as exc:
        raise SystemExit(f"ERROR: {exc}; no file written")

    required = {
        INPUT: [
            "ASCENSION UNIVERSAL CONTROLLER LAYER",
            "SDL_GameControllerAddMappingsFromFile",
            "data/ascension-controller-mappings.txt",
            "data/ascension-auto-mappings.txt",
            "inputInstallGenericMapping",
            "Input.AutoMapUnknownGamepads",
            "controller %d <- SDL device %d",
            "ascensionControlsQueueGamepadAxes",
            "inputPadBindingCapturePressed",
        ],
        VIDEO: [
            "ASCENSION UNIVERSAL CONTROLLER EVENTS",
            "SDL_CONTROLLERDEVICEREMAPPED",
            "SDL_JOYDEVICEADDED",
            "SDL_JOYDEVICEREMOVED",
        ],
    }
    for path, needles in required.items():
        for needle in needles:
            if needle not in updated[path]:
                raise SystemExit(f"ERROR: {path.name} missing {needle!r}; no file written")

    changed = [p for p in originals if originals[p] != updated[p]]
    if args.check:
        print("Universal Controller Layer preflight: PASS")
        print("Would update:", ", ".join(str(p.relative_to(ROOT)) for p in changed) or "nothing")
        return 0

    for path in changed:
        path.write_text(updated[path], encoding="utf-8")
        print("UPDATED:", path.relative_to(ROOT))
    if not changed:
        print("No changes needed; Universal Controller Layer already installed.")
    print("Universal Controller Layer: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
