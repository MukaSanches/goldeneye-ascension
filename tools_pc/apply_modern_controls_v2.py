#!/usr/bin/env python3
"""Apply Ascension Modern Controls V2 integration to the PC host layer.

The V2 policy engine lives in port/src/ascension_controls.c.  This patcher is
only the narrow integration bridge for the large host input/UI files so we can
validate the patch in CI before committing generated diffs permanently.

Properties:
- all anchors are validated before any file is written;
- idempotent (safe to run twice);
- Classic/Hybrid remain on the legacy input path;
- no ROM, save, mission, AI or asset files are touched.
"""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


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
    text = replace_once(
        text,
        """#define WHEEL_PULSE_POLLS 2\nstatic int wheelPulse = 0;\n""",
        """#define WHEEL_PULSE_POLLS 2\n#define WHEEL_GAP_POLLS   1\n#define WHEEL_QUEUE_MAX  12\nstatic int wheelPulse = 0;\nstatic int wheelGap   = 0;\nstatic int wheelQueue = 0;\n""",
        "reliable wheel queue state",
    )

    text = replace_once(
        text,
        """        if (mouseRawInput) {\n""",
        """        if (mouseRawInput || ascensionControlsWantsRawMouse()) {\n""",
        "Modern raw mouse policy",
    )

    old_aim = """        int aimHeld = (mb & SDL_BUTTON(SDL_BUTTON_RIGHT)) ||\n                      actHeld(ks, IA_AIM) || dedicatedCrouch;\n        if (aimHeld)\n            button |= GE_CONT_R;\n"""
    new_aim = """        int physicalAimHeld = (mb & SDL_BUTTON(SDL_BUTTON_RIGHT)) ||\n                              actHeld(ks, IA_AIM);\n        int aimHeld = ascensionControlsResolveAim(physicalAimHeld,\n                                                   dedicatedCrouch, menuMode);\n        if (aimHeld)\n            button |= GE_CONT_R;\n"""
    text = replace_once(text, old_aim, new_aim, "Modern aim resolver")

    old_wheel_poll = """        if (wheelPulse > 0) {           /* mouse-wheel weapon cycle -> A pulse */\n            button |= GE_CONT_A;\n            wheelPulse--;\n        }\n"""
    new_wheel_poll = """        /* Modern V2: preserve every wheel notch and insert a release gap so\n         * GoldenEye sees clean A-button edges even during fast scrolling. */\n        if (wheelPulse > 0) {\n            button |= GE_CONT_A;\n            wheelPulse--;\n            if (wheelPulse == 0) wheelGap = WHEEL_GAP_POLLS;\n        } else if (wheelGap > 0) {\n            wheelGap--;\n        } else if (wheelQueue > 0) {\n            wheelQueue--;\n            wheelPulse = WHEEL_PULSE_POLLS - 1;\n            button |= GE_CONT_A;\n        }\n"""
    text = replace_once(text, old_wheel_poll, new_wheel_poll, "reliable wheel polling")

    old_shape = """            edy *= mouseYScale / 100.0;\n\n            double dyLook = edy * invert;   /* >0 => look down */\n"""
    new_shape = """            /* Modern V2 adaptive precision is deliberately applied after the\n             * optional legacy smoothing but before per-axis sensitivity. */\n            if (!menuMode && ascensionControlsIsModern()) {\n                edx = ascensionControlsShapeMouseDelta(edx, aimHeld);\n                edy = ascensionControlsShapeMouseDelta(edy, aimHeld);\n            }\n\n            edy *= mouseYScale / 100.0;\n\n            double dyLook = edy * invert;   /* >0 => look down */\n"""
    text = replace_once(text, old_shape, new_shape, "adaptive precision mouse response")

    old_suspend = """void inputSuspendForOverlay(void)\n{\n    if (mouseGrabbed) {\n"""
    new_suspend = """void inputSuspendForOverlay(void)\n{\n    ascensionControlsResetTransient();\n    wheelPulse = wheelGap = wheelQueue = 0;\n    if (mouseGrabbed) {\n"""
    text = replace_once(text, old_suspend, new_suspend, "overlay transient reset")

    old_wheel_post = """void inputPostWheel(int notches)\n{\n    if (notches < 0) notches = -notches;   /* both directions cycle forward */\n    if (notches > 0) wheelPulse = WHEEL_PULSE_POLLS;\n}\n"""
    new_wheel_post = """void inputPostWheel(int notches)\n{\n    if (notches < 0) notches = -notches;   /* native GE path cycles forward */\n    if (notches <= 0) return;\n\n    if (ascensionControlsWheelQueueEnabled()) {\n        wheelQueue += notches;\n        if (wheelQueue > WHEEL_QUEUE_MAX) wheelQueue = WHEEL_QUEUE_MAX;\n    } else {\n        wheelPulse = WHEEL_PULSE_POLLS;\n        wheelGap = wheelQueue = 0;\n    }\n}\n"""
    text = replace_once(text, old_wheel_post, new_wheel_post, "wheel event queue")

    return text


def patch_overlay(text: str) -> str:
    text = replace_once(
        text,
        'static const char *const kControlPreset[] = { "CLASSIC", "HYBRID", "MODERN", NULL };\n',
        'static const char *const kControlPreset[] = { "CLASSIC", "HYBRID", "MODERN", NULL };\n'
        'static const char *const kMouseResponse[] = { "LEGACY", "LINEAR", "PRECISION", NULL };\n',
        "V2 response enum",
    )

    old = """    { .key=\"Input.ControlPreset\", .label=\"Control preset\",\n      .help=\"Choose Classic, Hybrid or Modern Ascension controls.\",\n      .category=CAT_INPUT,\n      .kind=ROW_ENUM, .step=1, .names=kControlPreset,\n      .uiMin=0, .uiMax=2, .resetValue=2 },\n\n"""
    new = old + """    { .key=\"Input.DedicatedCrouch\", .label=\"Dedicated crouch\",\n      .help=\"Ctrl/C crouches through GoldenEye's native crouch state machine.\",\n      .category=CAT_INPUT, .kind=ROW_TOGGLE, .step=1, .names=kOnOff, .resetValue=1 },\n\n    { .key=\"Input.ModernAimToggle\", .label=\"Modern aim toggle\",\n      .help=\"Modern only: click aim to toggle ADS instead of holding it.\",\n      .category=CAT_INPUT, .kind=ROW_TOGGLE, .step=1, .names=kOnOff, .resetValue=0 },\n\n    { .key=\"Input.ModernRawMouse\", .label=\"Modern raw mouse\",\n      .help=\"Modern only: bypass OS pointer scaling for mouse-look.\",\n      .category=CAT_INPUT, .kind=ROW_TOGGLE, .step=1, .names=kOnOff, .resetValue=1 },\n\n    { .key=\"Input.ModernMouseResponse\", .label=\"Mouse response\",\n      .help=\"Modern only: Legacy, Linear or adaptive Precision response.\",\n      .category=CAT_INPUT, .kind=ROW_ENUM, .step=1, .names=kMouseResponse,\n      .uiMin=0, .uiMax=2, .resetValue=2 },\n\n    { .key=\"Input.ModernWheelQueue\", .label=\"Reliable weapon wheel\",\n      .help=\"Modern only: queues fast wheel notches as clean weapon-cycle taps.\",\n      .category=CAT_INPUT, .kind=ROW_TOGGLE, .step=1, .names=kOnOff, .resetValue=1 },\n\n"""
    return replace_once(text, old, new, "V2 F10 input rows")


def patch_locale(text: str) -> str:
    anchor = '    { "Enable the Ascension crouch shortcut for Hybrid/Modern.", "Ativa o atalho de agachar do Ascension em Hibrido/Moderno." },\n'
    addition = anchor + """    { "Modern aim toggle", "Alternar mira moderna" },\n    { "Modern only: click aim to toggle ADS instead of holding it.", "Somente Moderno: clique para alternar a mira em vez de segurar." },\n    { "Modern raw mouse", "Mouse bruto moderno" },\n    { "Modern only: bypass OS pointer scaling for mouse-look.", "Somente Moderno: ignora a escala do ponteiro do sistema ao mirar." },\n    { "Mouse response", "Resposta do mouse" },\n    { "Modern only: Legacy, Linear or adaptive Precision response.", "Somente Moderno: resposta Legada, Linear ou Precisao adaptativa." },\n    { "Reliable weapon wheel", "Troca de arma confiavel" },\n    { "Modern only: queues fast wheel notches as clean weapon-cycle taps.", "Somente Moderno: enfileira o scroll rapido como trocas de arma limpas." },\n    { "Ctrl/C crouches through GoldenEye's native crouch state machine.", "Ctrl/C agacha usando o sistema nativo de postura do GoldenEye." },\n"""
    return replace_once(text, anchor, addition, "V2 PT-BR strings")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="validate patchability without writing")
    ap.add_argument("--no-backup", action="store_true")
    args = ap.parse_args()

    paths = {
        "input": ROOT / "port/src/input.c",
        "overlay": ROOT / "port/src/optionsoverlay.c",
        "locale": ROOT / "port/src/ascension_locale.c",
    }
    original = {k: p.read_text(encoding="utf-8") for k, p in paths.items()}

    try:
        patched = {
            "input": patch_input(original["input"]),
            "overlay": patch_overlay(original["overlay"]),
            "locale": patch_locale(original["locale"]),
        }
    except PatchError as e:
        raise SystemExit(f"ERROR: {e}; no file written")

    required = {
        "input": ["ascensionControlsResolveAim", "ascensionControlsShapeMouseDelta", "wheelQueue"],
        "overlay": ["Input.ModernAimToggle", "Input.ModernRawMouse", "Input.ModernMouseResponse", "Input.ModernWheelQueue"],
        "locale": ["Alternar mira moderna", "Mouse bruto moderno", "Troca de arma confiavel"],
    }
    for kind, needles in required.items():
        for needle in needles:
            if needle not in patched[kind]:
                raise SystemExit(f"ERROR: validation failed: {kind} missing {needle!r}; no file written")

    changed = [k for k in paths if patched[k] != original[k]]
    if args.check:
        print("Modern Controls V2 preflight: PASS")
        print("Would update:", ", ".join(str(paths[k].relative_to(ROOT)) for k in changed) or "nothing (already applied)")
        return 0

    if not args.no_backup:
        for k in changed:
            bak = paths[k].with_suffix(paths[k].suffix + ".ascension-v2-backup")
            if not bak.exists():
                shutil.copy2(paths[k], bak)

    for k in changed:
        paths[k].write_text(patched[k], encoding="utf-8")

    print("Modern Controls V2 integration: PASS")
    for k in changed:
        print("UPDATED:", paths[k].relative_to(ROOT))
    if not changed:
        print("No changes needed; V2 integration already present.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
