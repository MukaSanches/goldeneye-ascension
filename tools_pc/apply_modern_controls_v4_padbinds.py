#!/usr/bin/env python3
"""Finish Ascension 0.0.4 with live Modern gamepad remapping.

Run after apply_modern_controls_v4.py. This is deliberately an extension patch:
V4's accepted mouse/gamepad routing blocks remain byte-identical, while this
adds controller-button capture helpers and F10 binding rows around them.
"""
from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "port/src/input.c"
OVERLAY = ROOT / "port/src/optionsoverlay.c"
LOCALE = ROOT / "port/src/ascension_locale.c"


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
    if "inputBindingSetScancode" not in text or "ascensionControlsQueueGamepadAxes" not in text:
        raise PatchError("Modern Controls V4 core is not installed")
    if "inputPadBindingCapturePressed" in text:
        return text

    anchor = "/* Fill button mask + stick for controller idx. Returns the 16-bit mask. */\n"
    addition = r'''/* Ascension 0.0.4: F10 gamepad binding bridge.  `pads[0]` remains
 * owned here; persistent mapping state remains owned by ascension_controls.c. */
const char *inputPadBindingDisplay(const char *configKey)
{
    return ascensionControlsPadBindingDisplay(configKey);
}

int inputPadBindingReset(const char *configKey)
{
    return ascensionControlsPadBindingReset(configKey);
}

int inputPadBindingCapturePressed(const char *configKey)
{
    static char captureKey[64];
    static int waitRelease = 1;

    if (!configKey || !pads[0])
        return -1;

    if (strcmp(captureKey, configKey) != 0) {
        snprintf(captureKey, sizeof(captureKey), "%s", configKey);
        waitRelease = 1;
    }

    int firstDown = -1;
    for (int button = 0; button < SDL_CONTROLLER_BUTTON_MAX; ++button) {
        /* Guide/Home is commonly reserved by the OS/driver. Do not advertise
         * a binding that Windows may intercept before the game sees it. */
        if (button == SDL_CONTROLLER_BUTTON_GUIDE)
            continue;
        if (ascensionControlsRawGamepadButton(pads[0], button)) {
            firstDown = button;
            break;
        }
    }

    if (waitRelease) {
        if (firstDown < 0)
            waitRelease = 0;
        return 0;
    }

    if (firstDown < 0)
        return 0;

    int ok = ascensionControlsPadBindingSet(configKey, firstDown);
    captureKey[0] = '\0';
    waitRelease = 1;
    return ok ? 1 : -1;
}

'''
    return replace_once(text, anchor, addition + anchor, "gamepad binding bridge")


def patch_overlay(text: str) -> str:
    if "ROW_BIND" not in text or "Input.ModernPadDeadzone" not in text:
        raise PatchError("Modern Controls V4 F10 rows are not installed")
    if "Input.ModernPadBind.Action" in text and "Input.ModernPadSouthpaw" in text:
        return text

    invert_anchor = r'''    { .key="Input.ModernPadInvertY", .label="Gamepad invert Y",
      .help="Reverse vertical right-stick camera look.",
      .category=CAT_INPUT, .kind=ROW_TOGGLE, .step=1, .names=kOnOff, .resetValue=0 },

'''
    invert_add = invert_anchor + r'''    { .key="Input.ModernPadSouthpaw", .label="Southpaw stick layout",
      .help="Swap movement and camera sticks in Modern gamepad mode.",
      .category=CAT_INPUT, .kind=ROW_TOGGLE, .step=1, .names=kOnOff, .resetValue=0 },

    { .key="Input.ModernPadSwapTriggers", .label="Swap fire / aim triggers",
      .help="Swap LT and RT roles in Modern gamepad mode.",
      .category=CAT_INPUT, .kind=ROW_TOGGLE, .step=1, .names=kOnOff, .resetValue=0 },

'''
    text = replace_once(text, invert_anchor, invert_add, "Modern pad layout toggles")

    bind_anchor = r'''    { .key="Input.Bind.Start", .label="Bind: start / pause",
      .help="Pause/start keyboard binding.",
      .category=CAT_INPUT, .kind=ROW_BIND, .found=1 },

'''
    bind_add = bind_anchor + r'''    /* Modern gamepad digital actions. RT/LT remain analog fire/aim axes; the
     * swap-trigger option covers the common reversed-trigger preference. */
    { .key="Input.ModernPadBind.Action", .label="Pad bind: action",
      .help="Select, release any held button, then press the new gamepad button.",
      .category=CAT_INPUT, .kind=ROW_BIND, .found=1 },
    { .key="Input.ModernPadBind.Cancel", .label="Pad bind: reload / cancel",
      .help="Select, release any held button, then press the new gamepad button.",
      .category=CAT_INPUT, .kind=ROW_BIND, .found=1 },
    { .key="Input.ModernPadBind.Crouch", .label="Pad bind: crouch",
      .help="Dedicated Modern crouch through GoldenEye's native posture path.",
      .category=CAT_INPUT, .kind=ROW_BIND, .found=1 },
    { .key="Input.ModernPadBind.NextWeapon", .label="Pad bind: next weapon",
      .help="Bind the native forward inventory edge.",
      .category=CAT_INPUT, .kind=ROW_BIND, .found=1 },
    { .key="Input.ModernPadBind.PrevWeapon", .label="Pad bind: previous weapon",
      .help="Bind the native reverse inventory chord.",
      .category=CAT_INPUT, .kind=ROW_BIND, .found=1 },
    { .key="Input.ModernPadBind.AltAction", .label="Pad bind: alternate action",
      .help="Bind GoldenEye's native L-style alternate action.",
      .category=CAT_INPUT, .kind=ROW_BIND, .found=1 },
    { .key="Input.ModernPadBind.Start", .label="Pad bind: start / pause",
      .help="Bind the pause/start button for Modern gameplay.",
      .category=CAT_INPUT, .kind=ROW_BIND, .found=1 },

'''
    text = replace_once(text, bind_anchor, bind_add, "Modern pad binding rows")

    old_reset = r'''        if (r->kind == ROW_BIND) {
            inputBindingReset(r->key);
            continue;
        }'''
    new_reset = r'''        if (r->kind == ROW_BIND) {
            if (strncmp(r->key, "Input.ModernPadBind.", 20) == 0)
                inputPadBindingReset(r->key);
            else
                inputBindingReset(r->key);
            continue;
        }'''
    text = replace_once(text, old_reset, new_reset, "pad binding reset routing")

    old_value = r'''    if (r->kind == ROW_BIND) {
        snprintf(out, n, "%s", inputBindingDisplay(r->key));
        return;
    }'''
    new_value = r'''    if (r->kind == ROW_BIND) {
        const char *binding = strncmp(r->key, "Input.ModernPadBind.", 20) == 0
            ? inputPadBindingDisplay(r->key)
            : inputBindingDisplay(r->key);
        snprintf(out, n, "%s", binding);
        return;
    }'''
    text = replace_once(text, old_value, new_value, "pad binding display routing")

    capture_anchor = r'''    if (!ks)
        return;
    for (int sc = 1; sc < SDL_NUM_SCANCODES; ++sc) {'''
    capture_add = r'''    if (strncmp(rows[s_bindingRow].key, "Input.ModernPadBind.", 20) == 0) {
        int result = inputPadBindingCapturePressed(rows[s_bindingRow].key);
        if (result > 0) {
            setStatus("GAMEPAD BINDING SAVED");
            s_bindingRow = -1;
            s_bindingWaitRelease = 1;
        } else if (result < 0) {
            setStatus("NO GAMEPAD CONNECTED");
        }
        return;
    }

    if (!ks)
        return;
    for (int sc = 1; sc < SDL_NUM_SCANCODES; ++sc) {'''
    text = replace_once(text, capture_anchor, capture_add, "pad binding capture routing")
    return text


def patch_locale(text: str) -> str:
    if "Controle twin-stick moderno" not in text:
        raise PatchError("Modern Controls V4 PT-BR copy is not installed")
    if "Botao: agachar" in text:
        return text
    anchor = '    /* Gameplay rows */\n'
    addition = r'''    /* Ascension 0.0.4 gamepad remapping */
    { "Southpaw stick layout", "Layout de analogicos canhoto" },
    { "Swap movement and camera sticks in Modern gamepad mode.", "Troca os analogicos de movimento e camera no modo Moderno." },
    { "Swap fire / aim triggers", "Trocar gatilhos de tiro / mira" },
    { "Swap LT and RT roles in Modern gamepad mode.", "Troca as funcoes de LT e RT no modo Moderno." },
    { "Pad bind: action", "Botao: acao" },
    { "Pad bind: reload / cancel", "Botao: recarregar / voltar" },
    { "Pad bind: crouch", "Botao: agachar" },
    { "Pad bind: next weapon", "Botao: proxima arma" },
    { "Pad bind: previous weapon", "Botao: arma anterior" },
    { "Pad bind: alternate action", "Botao: acao alternativa" },
    { "Pad bind: start / pause", "Botao: iniciar / pausar" },
    { "Select, release any held button, then press the new gamepad button.", "Selecione, solte os botoes e pressione o novo botao do controle." },
    { "Dedicated Modern crouch through GoldenEye's native posture path.", "Agachar Moderno usando o sistema nativo de postura do GoldenEye." },
    { "Bind the native forward inventory edge.", "Define o comando nativo de avancar no inventario." },
    { "Bind the native reverse inventory chord.", "Define o comando nativo de voltar no inventario." },
    { "Bind GoldenEye's native L-style alternate action.", "Define a acao alternativa nativa equivalente ao L." },
    { "Bind the pause/start button for Modern gameplay.", "Define o botao de pausa/inicio no modo Moderno." },
    { "GAMEPAD BINDING SAVED", "BOTAO DO CONTROLE SALVO" },
    { "NO GAMEPAD CONNECTED", "NENHUM CONTROLE CONECTADO" },

'''
    return replace_once(text, anchor, addition + anchor, "gamepad remapping PT-BR copy")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    originals = {
        INPUT: INPUT.read_text(encoding="utf-8"),
        OVERLAY: OVERLAY.read_text(encoding="utf-8"),
        LOCALE: LOCALE.read_text(encoding="utf-8"),
    }
    try:
        updated = {
            INPUT: patch_input(originals[INPUT]),
            OVERLAY: patch_overlay(originals[OVERLAY]),
            LOCALE: patch_locale(originals[LOCALE]),
        }
    except PatchError as exc:
        raise SystemExit(f"ERROR: {exc}; no file written")

    required = {
        INPUT: ["inputPadBindingCapturePressed", "ascensionControlsRawGamepadButton"],
        OVERLAY: ["Input.ModernPadBind.Action", "Input.ModernPadSouthpaw", "GAMEPAD BINDING SAVED"],
        LOCALE: ["Botao: agachar", "NENHUM CONTROLE CONECTADO"],
    }
    for path, needles in required.items():
        for needle in needles:
            if needle not in updated[path]:
                raise SystemExit(f"ERROR: {path.name} missing {needle!r}; no file written")

    changed = [p for p in originals if originals[p] != updated[p]]
    if args.check:
        print("Modern Controls V4 gamepad binding preflight: PASS")
        print("Would update:", ", ".join(str(p.relative_to(ROOT)) for p in changed) or "nothing")
        return 0

    for path in changed:
        path.write_text(updated[path], encoding="utf-8")
        print("UPDATED:", path.relative_to(ROOT))
    if not changed:
        print("No changes needed; V4 gamepad bindings already installed.")
    print("Modern Controls V4 gamepad bindings: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
