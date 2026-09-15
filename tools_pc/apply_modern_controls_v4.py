#!/usr/bin/env python3
"""Ascension 0.0.4 / Modern Controls V4 integration.

Run after the validated 2026-09-15 Ascension stack. V4 deliberately leaves the
accepted mouse/Q-Watch/frontend paths intact and adds only:
- controller-0 Modern twin-stick routing;
- radial gamepad deadzone/response controls;
- frame-scaled analog gamepad camera look;
- analog strafe/walk through GoldenEye's existing MoveData channels;
- live keyboard rebinding rows in the F10 Controls page.

Classic and Hybrid retain the existing gamepad path. The patch is fail-closed
and idempotent and does not touch ROM, saves, mission logic, AI or assets.
"""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class PatchError(RuntimeError):
    pass


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise PatchError(f"{label}: required anchor missing: {needle!r}")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        return text
    count = text.count(old)
    if count != 1:
        raise PatchError(f"{label}: expected exactly one anchor, found {count}")
    return text.replace(old, new, 1)


def patch_input(text: str) -> str:
    require(text, "ascensionControlsQueueDirectLook", "V3 direct-look route")
    require(text, "wheelQueuePush", "V3 wheel queue")
    require(text, "static int actHeld", "keyboard bind core")

    bind_anchor = """static int actHeld(const Uint8 *ks, int act)
{"""
    bind_helpers = r'''/* Ascension 0.0.4: live keyboard rebinding.  Keep the existing
 * Input.Bind.* buffers as the single source of truth so ge007.ini remains
 * backward compatible and inputRebuildBinds() still owns parsing. */
static int inputBindingActionForKey(const char *configKey)
{
    if (!configKey)
        return -1;
    for (int a = 0; a < IA_COUNT; ++a) {
        if (strcmp(configKey, kBindDefs[a].key) == 0)
            return a;
    }
    return -1;
}

const char *inputBindingDisplay(const char *configKey)
{
    int a = inputBindingActionForKey(configKey);
    if (a < 0)
        return "N/A";
    return g_bindStr[a][0] ? g_bindStr[a] : kBindDefs[a].def;
}

int inputBindingSetScancode(const char *configKey, int scancode)
{
    int a = inputBindingActionForKey(configKey);
    if (a < 0 || scancode <= SDL_SCANCODE_UNKNOWN || scancode >= SDL_NUM_SCANCODES)
        return 0;

    const char *name = SDL_GetScancodeName((SDL_Scancode)scancode);
    if (!name || !*name)
        return 0;

    snprintf(g_bindStr[a], sizeof(g_bindStr[a]), "%s", name);
    inputRebuildBinds();
    configSave();
    return 1;
}

int inputBindingReset(const char *configKey)
{
    int a = inputBindingActionForKey(configKey);
    if (a < 0)
        return 0;
    snprintf(g_bindStr[a], sizeof(g_bindStr[a]), "%s", kBindDefs[a].def);
    inputRebuildBinds();
    configSave();
    return 1;
}

static int actHeld(const Uint8 *ks, int act)
{'''
    text = replace_once(text, bind_anchor, bind_helpers, "live keyboard binding API")

    old_axes = r'''        int px = scaleAxis(lx);
        int py = -scaleAxis(ly);       /* SDL up = negative -> N64 up = positive */
        if (px) sx = px;
        if (py) sy = py;

        if (padLookInvertY) ry = -ry;
        if (rx >  RSTICK_THRESHOLD) button |= GE_CONT_F;
        if (rx < -RSTICK_THRESHOLD) button |= GE_CONT_C;
        if (ry >  RSTICK_THRESHOLD) button |= GE_CONT_D;
        if (ry < -RSTICK_THRESHOLD) button |= GE_CONT_E;

        int trigPt = padTriggerPct * 327;   /* % of the 0..32767 trigger travel */'''
    new_axes = r'''        int trigPt = padTriggerPct * 327;   /* % of the 0..32767 trigger travel */
        int modernPad = idx == 0 && ascensionControlsModernGamepadEnabled();

        if (modernPad) {
            /* V4 keeps SDL raw axes out of the N64 stick/C-button emulation.
             * They are shaped radially in ascension_controls.c and consumed
             * through the narrow PORT bridge in bondview2.c. */
            int padAim = SDL_GameControllerGetAxis(
                pad, SDL_CONTROLLER_AXIS_TRIGGERLEFT) > trigPt;
            ascensionControlsQueueGamepadAxes(lx, ly, rx, ry, padAim);
        } else {
            int px = scaleAxis(lx);
            int py = -scaleAxis(ly);       /* SDL up = negative -> N64 up = positive */
            if (px) sx = px;
            if (py) sy = py;

            if (padLookInvertY) ry = -ry;
            if (rx >  RSTICK_THRESHOLD) button |= GE_CONT_F;
            if (rx < -RSTICK_THRESHOLD) button |= GE_CONT_C;
            if (ry >  RSTICK_THRESHOLD) button |= GE_CONT_D;
            if (ry < -RSTICK_THRESHOLD) button |= GE_CONT_E;
        }'''
    text = replace_once(text, old_axes, new_axes, "Modern gamepad axis routing")

    old_buttons = r'''        if (SDL_GameControllerGetButton(pad, SDL_CONTROLLER_BUTTON_A) ||
            SDL_GameControllerGetButton(pad, SDL_CONTROLLER_BUTTON_X))
            button |= GE_CONT_A;
        if (SDL_GameControllerGetButton(pad, SDL_CONTROLLER_BUTTON_B) ||
            SDL_GameControllerGetButton(pad, SDL_CONTROLLER_BUTTON_Y) ||
            SDL_GameControllerGetButton(pad, SDL_CONTROLLER_BUTTON_RIGHTSHOULDER))
            button |= GE_CONT_B;
        if (SDL_GameControllerGetButton(pad, SDL_CONTROLLER_BUTTON_LEFTSHOULDER))
            button |= GE_CONT_L;'''
    new_buttons = r'''        if (modernPad) {
            /* Familiar FPS face layout without changing GoldenEye's native
             * button semantics: A use, X reload/cancel, B crouch, Y next
             * weapon, LB previous weapon, RB alt/L. Crouch is translated via
             * the same native aim+stick-down gesture used by keyboard Modern. */
            if (SDL_GameControllerGetButton(pad, SDL_CONTROLLER_BUTTON_A))
                button |= GE_CONT_A;
            if (SDL_GameControllerGetButton(pad, SDL_CONTROLLER_BUTTON_X))
                button |= GE_CONT_B;
            if (SDL_GameControllerGetButton(pad, SDL_CONTROLLER_BUTTON_B)) {
                button |= GE_CONT_R;
                sy = -STICK_MAX;
            }
            if (SDL_GameControllerGetButton(pad, SDL_CONTROLLER_BUTTON_Y))
                button |= GE_CONT_A;
            if (SDL_GameControllerGetButton(pad, SDL_CONTROLLER_BUTTON_LEFTSHOULDER))
                button |= GE_CONT_A | GE_CONT_G;
            if (SDL_GameControllerGetButton(pad, SDL_CONTROLLER_BUTTON_RIGHTSHOULDER))
                button |= GE_CONT_L;
        } else {
            if (SDL_GameControllerGetButton(pad, SDL_CONTROLLER_BUTTON_A) ||
                SDL_GameControllerGetButton(pad, SDL_CONTROLLER_BUTTON_X))
                button |= GE_CONT_A;
            if (SDL_GameControllerGetButton(pad, SDL_CONTROLLER_BUTTON_B) ||
                SDL_GameControllerGetButton(pad, SDL_CONTROLLER_BUTTON_Y) ||
                SDL_GameControllerGetButton(pad, SDL_CONTROLLER_BUTTON_RIGHTSHOULDER))
                button |= GE_CONT_B;
            if (SDL_GameControllerGetButton(pad, SDL_CONTROLLER_BUTTON_LEFTSHOULDER))
                button |= GE_CONT_L;
        }'''
    text = replace_once(text, old_buttons, new_buttons, "Modern gamepad button layout")
    return text


def patch_bondview(text: str) -> str:
    require(text, "Ascension Modern Controls V3", "V3 camera hook")
    require(text, '#include "ascension_controls.h"', "PORT controls include")

    text = replace_once(
        text,
        "if (ascensionControlsDirectLookEnabled() && g_PlayerIsInTank == 0) {",
        "if ((ascensionControlsDirectLookEnabled() || ascensionControlsModernGamepadEnabled()) && g_PlayerIsInTank == 0) {",
        "V4 camera bridge gate",
    )

    old_vars = r'''        float ascYaw = 0.0f;
        float ascPitch = 0.0f;
'''
    new_vars = r'''        float ascYaw = 0.0f;
        float ascPitch = 0.0f;
        float padYaw = 0.0f;
        float padPitch = 0.0f;
        int ascHaveLook = ascensionControlsConsumeDirectLook(&ascYaw, &ascPitch);
        if (ascensionControlsConsumeGamepadLook(&padYaw, &padPitch)) {
            ascYaw += padYaw * g_GlobalTimerDelta;
            ascPitch += padPitch * g_GlobalTimerDelta;
            ascHaveLook = 1;
        }
'''
    text = replace_once(text, old_vars, new_vars, "V4 frame-scaled pad look")

    old_cond = r'''        if (g_CurrentPlayer->watch_animation_state == WATCH_ANIMATION_0x0
            && lvlGetControlsLockedFlag() == 0
            && ascensionControlsConsumeDirectLook(&ascYaw, &ascPitch)) {'''
    new_cond = r'''        if (g_CurrentPlayer->watch_animation_state == WATCH_ANIMATION_0x0
            && lvlGetControlsLockedFlag() == 0
            && ascHaveLook) {'''
    text = replace_once(text, old_cond, new_cond, "V4 combined look consume")

    move_anchor = "    g_CurrentPlayer->field_D0 = 0;\n"
    move_hook = r'''#ifdef PORT
    /* Ascension Modern Controls V4: use GoldenEye's existing analog movement
     * channels instead of synthesizing digital C-button strafing. This hook is
     * active only when controller 0 has a Modern left-stick value outside the
     * radial deadzone. Collision, acceleration and speed limits stay native. */
    if (ascensionControlsModernGamepadEnabled() && g_PlayerIsInTank == 0) {
        float padStrafe = 0.0f;
        float padWalk = 0.0f;
        if (ascensionControlsConsumeGamepadMove(&padStrafe, &padWalk)) {
            moveData.analogStrafe = (s32)(padStrafe * 70.0f);
            moveData.analogWalk = (s32)(padWalk * 70.0f);
            moveData.digitalStepLeft = 0;
            moveData.digitalStepRight = 0;
            moveData.digitalStepForward = 0;
            moveData.digitalStepBack = 0;
            moveData.canTurnTank = 1;
            moveData.canLookAhead = 1;
        }
    }
#endif

    g_CurrentPlayer->field_D0 = 0;
'''
    text = replace_once(text, move_anchor, move_hook, "V4 analog movement hook")
    return text


def patch_overlay(text: str) -> str:
    require(text, "Ascension UI Overhaul V2 - Q Watch compact settings", "final F10 UI")
    require(text, "Input.ModernDisableAutoCenter", "V3 F10 controls")
    if "ROW_BIND" in text and "Input.ModernPadDeadzone" in text and "s_bindingRow" in text:
        return text

    old_kind = r'''enum RowKind {
    ROW_TOGGLE,
    ROW_SLIDER,
    ROW_ENUM,
    ROW_MSAA,
    ROW_RES,
    ROW_ACTION,
};'''
    new_kind = r'''enum RowKind {
    ROW_TOGGLE,
    ROW_SLIDER,
    ROW_ENUM,
    ROW_MSAA,
    ROW_RES,
    ROW_BIND,
    ROW_ACTION,
};'''
    text = replace_once(text, old_kind, new_kind, "binding row kind")

    preset_anchor = 'static const char *const kControlPreset[] = { "CLASSIC", "HYBRID", "MODERN", NULL };\n'
    preset_add = preset_anchor + 'static const char *const kPadResponse[] = { "LINEAR", "PRECISION", NULL };\n'
    text = replace_once(text, preset_anchor, preset_add, "pad response names")

    row_anchor = r'''    { .key="Input.ModernDisableAutoCenter", .label="Disable look auto-center",
      .help="Modern direct look keeps pitch where the mouse leaves it.",
      .category=CAT_INPUT, .kind=ROW_TOGGLE, .step=1, .names=kOnOff, .resetValue=1 },

'''
    row_add = row_anchor + r'''    /* Modern Controls V4 - controller 0 twin-stick */
    { .key="Input.ModernGamepad", .label="Modern twin-stick gamepad",
      .help="Modern only: left stick moves and right stick controls the camera.",
      .category=CAT_INPUT, .kind=ROW_TOGGLE, .step=1, .names=kOnOff, .resetValue=1 },

    { .key="Input.ModernPadDeadzone", .label="Radial stick deadzone %",
      .help="Modern gamepad radial deadzone. Lower is more responsive.",
      .category=CAT_INPUT, .kind=ROW_SLIDER, .step=1,
      .uiMin=0, .uiMax=40, .resetValue=14 },

    { .key="Input.ModernPadLookSensitivity", .label="Gamepad look sensitivity",
      .help="Modern right-stick look speed percentage.",
      .category=CAT_INPUT, .kind=ROW_SLIDER, .step=5,
      .uiMin=20, .uiMax=300, .resetValue=100 },

    { .key="Input.ModernPadAdsScale", .label="Gamepad ADS sensitivity",
      .help="Right-stick sensitivity while aiming as a percentage of hip-fire.",
      .category=CAT_INPUT, .kind=ROW_SLIDER, .step=5,
      .uiMin=20, .uiMax=100, .resetValue=65 },

    { .key="Input.ModernPadResponse", .label="Gamepad response curve",
      .help="Linear or precision-focused radial stick response.",
      .category=CAT_INPUT, .kind=ROW_ENUM, .step=1, .names=kPadResponse,
      .uiMin=0, .uiMax=1, .resetValue=1 },

    { .key="Input.ModernPadInvertX", .label="Gamepad invert X",
      .help="Reverse horizontal right-stick camera look.",
      .category=CAT_INPUT, .kind=ROW_TOGGLE, .step=1, .names=kOnOff, .resetValue=0 },

    { .key="Input.ModernPadInvertY", .label="Gamepad invert Y",
      .help="Reverse vertical right-stick camera look.",
      .category=CAT_INPUT, .kind=ROW_TOGGLE, .step=1, .names=kOnOff, .resetValue=0 },

    /* Live keyboard bindings. Existing Input.Bind.* keys remain authoritative. */
    { .key="Input.Bind.Forward", .label="Bind: move forward",
      .help="Select, release the menu key, then press the new key.",
      .category=CAT_INPUT, .kind=ROW_BIND, .found=1 },
    { .key="Input.Bind.Back", .label="Bind: move back",
      .help="Select, release the menu key, then press the new key.",
      .category=CAT_INPUT, .kind=ROW_BIND, .found=1 },
    { .key="Input.Bind.StrafeLeft", .label="Bind: strafe left",
      .help="Select, release the menu key, then press the new key.",
      .category=CAT_INPUT, .kind=ROW_BIND, .found=1 },
    { .key="Input.Bind.StrafeRight", .label="Bind: strafe right",
      .help="Select, release the menu key, then press the new key.",
      .category=CAT_INPUT, .kind=ROW_BIND, .found=1 },
    { .key="Input.Bind.TurnLeft", .label="Bind: turn left",
      .help="Select, release the menu key, then press the new key.",
      .category=CAT_INPUT, .kind=ROW_BIND, .found=1 },
    { .key="Input.Bind.TurnRight", .label="Bind: turn right",
      .help="Select, release the menu key, then press the new key.",
      .category=CAT_INPUT, .kind=ROW_BIND, .found=1 },
    { .key="Input.Bind.Fire", .label="Bind: fire",
      .help="Keyboard fire binding; left mouse remains fire.",
      .category=CAT_INPUT, .kind=ROW_BIND, .found=1 },
    { .key="Input.Bind.Aim", .label="Bind: aim",
      .help="Keyboard aim binding; right mouse remains aim.",
      .category=CAT_INPUT, .kind=ROW_BIND, .found=1 },
    { .key="Input.Bind.Action", .label="Bind: action",
      .help="Use, interact and accept action binding.",
      .category=CAT_INPUT, .kind=ROW_BIND, .found=1 },
    { .key="Input.Bind.Cancel", .label="Bind: reload / cancel",
      .help="Reload and cancel action binding.",
      .category=CAT_INPUT, .kind=ROW_BIND, .found=1 },
    { .key="Input.Bind.LeanLeft", .label="Bind: left / alt action",
      .help="Existing L-trigger style keyboard action.",
      .category=CAT_INPUT, .kind=ROW_BIND, .found=1 },
    { .key="Input.Bind.Start", .label="Bind: start / pause",
      .help="Pause/start keyboard binding.",
      .category=CAT_INPUT, .kind=ROW_BIND, .found=1 },

'''
    text = replace_once(text, row_anchor, row_add, "V4 controls and binding rows")

    state_anchor = "static int s_scroll;\n"
    state_add = state_anchor + "static int s_bindingRow = -1;\nstatic int s_bindingWaitRelease;\n"
    text = replace_once(text, state_anchor, state_add, "binding capture state")

    text = replace_once(
        text,
        "if (rows[i].kind == ROW_ACTION || rows[i].kind == ROW_RES)\n            continue;",
        "if (rows[i].kind == ROW_ACTION || rows[i].kind == ROW_RES || rows[i].kind == ROW_BIND)\n            continue;",
        "skip bind rows in config resolver",
    )
    text = replace_once(
        text,
        "if (rows[i].kind != ROW_ACTION && rows[i].kind != ROW_RES)\n            configSetOptionMeta",
        "if (rows[i].kind != ROW_ACTION && rows[i].kind != ROW_RES && rows[i].kind != ROW_BIND)\n            configSetOptionMeta",
        "skip bind metadata",
    )
    text = replace_once(
        text,
        "if (rows[i].kind == ROW_RES || rows[i].kind == ROW_ACTION) {\n            rows[i].found = 1;",
        "if (rows[i].kind == ROW_RES || rows[i].kind == ROW_ACTION || rows[i].kind == ROW_BIND) {\n            rows[i].found = 1;",
        "bind rows are virtual UI rows",
    )

    old_restore = r'''        if (r->kind == ROW_ACTION || r->kind == ROW_RES || !r->found)
            continue;
        applyRowValue(r, r->resetValue, 0);'''
    new_restore = r'''        if (!r->found)
            continue;
        if (r->kind == ROW_BIND) {
            inputBindingReset(r->key);
            continue;
        }
        if (r->kind == ROW_ACTION || r->kind == ROW_RES)
            continue;
        applyRowValue(r, r->resetValue, 0);'''
    text = replace_once(text, old_restore, new_restore, "binding default restore")

    action_anchor = r'''static void rowAdjust(struct Row *r, int dir)
{
    if (!r->found)
        return;

    if (r->kind == ROW_ACTION) {'''
    action_add = r'''static void beginBindingCapture(struct Row *r)
{
    if (!r || r->kind != ROW_BIND)
        return;
    s_bindingRow = (int)(r - rows);
    s_bindingWaitRelease = 1;
    setStatus("PRESS A KEY - ESC CANCEL");
}

static int keyboardAnyDown(const Uint8 *ks)
{
    if (!ks)
        return 0;
    for (int sc = 1; sc < SDL_NUM_SCANCODES; ++sc) {
        if (ks[sc])
            return 1;
    }
    return 0;
}

static void handleBindingCapture(const Uint8 *ks)
{
    if (s_bindingRow < 0 || s_bindingRow >= NUM_ROWS)
        return;

    if (s_bindingWaitRelease) {
        if (!keyboardAnyDown(ks))
            s_bindingWaitRelease = 0;
        return;
    }

    if (ks && (ks[SDL_SCANCODE_ESCAPE] || ks[SDL_SCANCODE_F10])) {
        s_bindingRow = -1;
        s_bindingWaitRelease = 1;
        setStatus("BIND CANCELLED");
        return;
    }

    if (!ks)
        return;
    for (int sc = 1; sc < SDL_NUM_SCANCODES; ++sc) {
        if (!ks[sc])
            continue;
        if (inputBindingSetScancode(rows[s_bindingRow].key, sc))
            setStatus("BINDING SAVED");
        else
            setStatus("BINDING FAILED");
        s_bindingRow = -1;
        s_bindingWaitRelease = 1;
        return;
    }
}

static void rowAdjust(struct Row *r, int dir)
{
    if (!r->found)
        return;

    if (r->kind == ROW_BIND) {
        (void)dir;
        beginBindingCapture(r);
        return;
    }

    if (r->kind == ROW_ACTION) {'''
    text = replace_once(text, action_anchor, action_add, "binding capture helpers")

    value_anchor = r'''static void valueText(const struct Row *r, char *out, int n)
{
    if (r->kind == ROW_ACTION) {'''
    value_add = r'''static void valueText(const struct Row *r, char *out, int n)
{
    if (r->kind == ROW_BIND) {
        snprintf(out, n, "%s", inputBindingDisplay(r->key));
        return;
    }

    if (r->kind == ROW_ACTION) {'''
    text = replace_once(text, value_anchor, value_add, "binding value display")

    ks_anchor = r'''    const Uint8 *ks = SDL_GetKeyboardState(NULL);
    int mx = 0, my = 0;'''
    ks_add = r'''    const Uint8 *ks = SDL_GetKeyboardState(NULL);
    if (s_bindingRow >= 0) {
        handleBindingCapture(ks);
        prevUp = prevDn = prevLf = prevRt = prevTab = 0;
        prevLmb = prevRmb = 0;
        dragRow = -1;
        return;
    }

    int mx = 0, my = 0;'''
    text = replace_once(text, ks_anchor, ks_add, "binding capture input ownership")

    text = replace_once(
        text,
        "if (r->kind == ROW_ACTION) {\n                    activateAction(r);",
        "if (r->kind == ROW_ACTION || r->kind == ROW_BIND) {\n                    rowAdjust(r, +1);",
        "mouse activation for bind rows",
    )

    close_anchor = r'''    } else {
        clearPendingAction();
        configSave();
    }'''
    close_add = r'''    } else {
        s_bindingRow = -1;
        s_bindingWaitRelease = 1;
        clearPendingAction();
        configSave();
    }'''
    text = replace_once(text, close_anchor, close_add, "cancel bind capture on close")
    return text


def patch_locale(text: str) -> str:
    require(text, "Mira direta moderna", "V3 PT-BR strings")
    if "Controle twin-stick moderno" in text:
        return text

    anchor = '    /* Gameplay rows */\n'
    addition = r'''    /* Ascension 0.0.4 controls */
    { "Modern twin-stick gamepad", "Controle twin-stick moderno" },
    { "Modern only: left stick moves and right stick controls the camera.", "Somente Moderno: esquerdo move e direito controla a camera." },
    { "Radial stick deadzone %", "Zona morta radial %" },
    { "Modern gamepad radial deadzone. Lower is more responsive.", "Zona morta radial do controle. Menor responde mais rapido." },
    { "Gamepad look sensitivity", "Sensibilidade da camera no controle" },
    { "Modern right-stick look speed percentage.", "Velocidade percentual da camera no analogico direito." },
    { "Gamepad ADS sensitivity", "Sensibilidade ADS no controle" },
    { "Right-stick sensitivity while aiming as a percentage of hip-fire.", "Sensibilidade do analogico ao mirar como porcentagem da normal." },
    { "Gamepad response curve", "Curva de resposta do controle" },
    { "Linear or precision-focused radial stick response.", "Resposta radial linear ou focada em precisao." },
    { "Gamepad invert X", "Inverter X do controle" },
    { "Reverse horizontal right-stick camera look.", "Inverte a camera horizontal no analogico direito." },
    { "Reverse vertical right-stick camera look.", "Inverte a camera vertical no analogico direito." },
    { "Bind: move forward", "Tecla: avancar" },
    { "Bind: move back", "Tecla: recuar" },
    { "Bind: strafe left", "Tecla: mover esquerda" },
    { "Bind: strafe right", "Tecla: mover direita" },
    { "Bind: turn left", "Tecla: virar esquerda" },
    { "Bind: turn right", "Tecla: virar direita" },
    { "Bind: fire", "Tecla: atirar" },
    { "Bind: aim", "Tecla: mirar" },
    { "Bind: action", "Tecla: acao" },
    { "Bind: reload / cancel", "Tecla: recarregar / voltar" },
    { "Bind: left / alt action", "Tecla: acao alternativa" },
    { "Bind: start / pause", "Tecla: iniciar / pausar" },
    { "Select, release the menu key, then press the new key.", "Selecione, solte a tecla do menu e pressione a nova tecla." },
    { "Keyboard fire binding; left mouse remains fire.", "Tecla de tiro; mouse esquerdo continua atirando." },
    { "Keyboard aim binding; right mouse remains aim.", "Tecla de mira; mouse direito continua mirando." },
    { "Use, interact and accept action binding.", "Tecla para usar, interagir e confirmar." },
    { "Reload and cancel action binding.", "Tecla para recarregar e voltar." },
    { "Existing L-trigger style keyboard action.", "Acao de teclado equivalente ao L nativo." },
    { "Pause/start keyboard binding.", "Tecla de pausa/inicio." },
    { "LINEAR", "LINEAR" },
    { "PRECISION", "PRECISAO" },
    { "PRESS A KEY - ESC CANCEL", "PRESSIONE UMA TECLA - ESC CANCELA" },
    { "BIND CANCELLED", "ALTERACAO CANCELADA" },
    { "BINDING SAVED", "TECLA SALVA" },
    { "BINDING FAILED", "FALHA AO SALVAR TECLA" },

'''
    return replace_once(text, anchor, addition + anchor, "V4 PT-BR copy")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="validate without writing")
    ap.add_argument("--no-backup", action="store_true")
    args = ap.parse_args()

    paths = {
        "input": ROOT / "port/src/input.c",
        "bondview": ROOT / "src/game/bondview2.c",
        "overlay": ROOT / "port/src/optionsoverlay.c",
        "locale": ROOT / "port/src/ascension_locale.c",
    }
    original = {k: p.read_text(encoding="utf-8") for k, p in paths.items()}

    try:
        patched = {
            "input": patch_input(original["input"]),
            "bondview": patch_bondview(original["bondview"]),
            "overlay": patch_overlay(original["overlay"]),
            "locale": patch_locale(original["locale"]),
        }
    except PatchError as exc:
        raise SystemExit(f"ERROR: {exc}; no file written")

    required = {
        "input": ["inputBindingSetScancode", "ascensionControlsQueueGamepadAxes", "modernPad"],
        "bondview": ["ascensionControlsConsumeGamepadMove", "ascensionControlsConsumeGamepadLook", "ascHaveLook"],
        "overlay": ["ROW_BIND", "Input.ModernPadDeadzone", "s_bindingRow", "inputBindingDisplay"],
        "locale": ["Controle twin-stick moderno", "Zona morta radial", "PRESSIONE UMA TECLA"],
    }
    for kind, needles in required.items():
        for needle in needles:
            if needle not in patched[kind]:
                raise SystemExit(f"ERROR: validation failed: {kind} missing {needle!r}; no file written")

    changed = [k for k in paths if patched[k] != original[k]]
    if args.check:
        print("Modern Controls V4 preflight: PASS")
        print("Would update:", ", ".join(str(paths[k].relative_to(ROOT)) for k in changed) or "nothing")
        return 0

    if not args.no_backup:
        for k in changed:
            bak = paths[k].with_suffix(paths[k].suffix + ".ascension-v4-backup")
            if not bak.exists():
                shutil.copy2(paths[k], bak)

    for k in changed:
        paths[k].write_text(patched[k], encoding="utf-8")
        print("UPDATED:", paths[k].relative_to(ROOT))
    if not changed:
        print("No changes needed; Modern Controls V4 is already installed.")
    print("Modern Controls V4 integration: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
