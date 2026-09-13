#include <string.h>

#include <SDL.h>

#include "platform.h"
#include "config.h"
#include "ascension_controls.h"

/* 0 = Classic, 1 = Hybrid, 2 = Modern. The preset only changes Ascension's
 * PC-side interpretation; original GoldenEye control logic remains intact. */
static int s_controlPreset = 0;
static int s_dedicatedCrouch = 1;

PD_CONSTRUCTOR static void ascensionControlsConfigInit(void)
{
    configRegisterInt("Input.ControlPreset", &s_controlPreset, 0, 2);
    configRegisterInt("Input.DedicatedCrouch", &s_dedicatedCrouch, 0, 1);
}

int ascensionControlsDedicatedCrouchHeld(void)
{
    if (!s_dedicatedCrouch || s_controlPreset == 0)
        return 0;

    const Uint8 *ks = SDL_GetKeyboardState(NULL);
    if (!ks)
        return 0;

    /* Modern: Ctrl/C. Hybrid intentionally keeps C only so Left Ctrl can
     * continue acting as the legacy keyboard fire key. */
    if (s_controlPreset == 1)
        return ks[SDL_SCANCODE_C] != 0;

    return ks[SDL_SCANCODE_LCTRL] || ks[SDL_SCANCODE_RCTRL] ||
           ks[SDL_SCANCODE_C];
}
