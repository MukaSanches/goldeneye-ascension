#!/usr/bin/env python3
"""Add conservative Ascension PC-polish presets.

This patcher only composes existing port-side configuration knobs. It does not
change GoldenEye simulation, ROM data, saves, PT-BR assets, AI, weapon timing,
or mission logic. The generated presets remain optional and reversible.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "port" / "src" / "optionsoverlay.c"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count == 0 and new in text:
        print(f"OK: {label} already applied")
        return text
    if count != 1:
        raise SystemExit(
            f"ERROR: {label}: expected exactly one anchor, found {count}; no file written"
        )
    print(f"APPLY: {label}")
    return text.replace(old, new, 1)


def main() -> int:
    original = PATH.read_text(encoding="utf-8")
    text = original

    text = replace_once(
        text,
        'static const char *const kLanguage[]  = { "ENGLISH", "PORTUGUESE (BRAZIL)", NULL };\n',
        'static const char *const kLanguage[]  = { "ENGLISH", "PORTUGUESE (BRAZIL)", NULL };\n'
        'static const char *const kFovPreset[] = { "ORIGINAL", "MODERN", "WIDE", "CUSTOM", NULL };\n'
        'static const char *const kMousePreset[] = { "CLASSIC", "SMOOTH", "MODERN", "RAW", "CUSTOM", NULL };\n'
        'static const char *const kPadPreset[] = { "CLASSIC", "MODERN", "SOUTHPAW", "CUSTOM", NULL };\n',
        "preset names",
    )

    anchor = '''    { .key="Video.FovScale",       .label="FOV scale %",\n      .help="View width. Safe range 70-120.", .category=CAT_DISPLAY,\n      .kind=ROW_SLIDER, .step=5, .uiMin=70, .uiMax=120, .resetValue=100 },\n'''
    repl = anchor + '''\n    { .key="Ascension.FovPreset", .label="FOV preset",\n      .help="Original, Modern or Wide view; Custom keeps manual FOV.", .category=CAT_DISPLAY,\n      .kind=ROW_ENUM, .step=1, .names=kFovPreset, .resetValue=0 },\n'''
    text = replace_once(text, anchor, repl, "FOV preset row")

    anchor = '''    { .key="Input.MouseCaptureMode", .label="Mouse capture",\n      .help="Choose how mouse lock activates.", .category=CAT_INPUT,\n      .kind=ROW_TOGGLE, .step=1, .names=kCapture, .resetValue=1 },\n'''
    repl = anchor + '''\n    { .key="Ascension.MousePreset", .label="Mouse feel",\n      .help="Classic, Smooth, Modern or Raw PC mouse tuning.", .category=CAT_INPUT,\n      .kind=ROW_ENUM, .step=1, .names=kMousePreset, .resetValue=2 },\n\n    { .key="Ascension.GamepadPreset", .label="Gamepad preset",\n      .help="Conservative gamepad tuning presets; Custom preserves manual values.", .category=CAT_INPUT,\n      .kind=ROW_ENUM, .step=1, .names=kPadPreset, .resetValue=1 },\n'''
    text = replace_once(text, anchor, repl, "mouse/gamepad preset rows")

    marker = '''static int  s_showFps;\nstatic int  s_controlHintSeen;\n'''
    replacement = '''static int  s_showFps;\nstatic int  s_controlHintSeen;\nstatic int  s_fovPreset = 0;\nstatic int  s_mousePreset = 2;\nstatic int  s_gamepadPreset = 1;\n'''
    text = replace_once(text, marker, replacement, "preset state")

    marker = '''    configRegisterInt("Video.DisplayFPS", &s_showFps, 0, 1);\n    configRegisterInt("Ascension.ControlHintSeen", &s_controlHintSeen, 0, 1);\n'''
    replacement = '''    configRegisterInt("Video.DisplayFPS", &s_showFps, 0, 1);\n    configRegisterInt("Ascension.ControlHintSeen", &s_controlHintSeen, 0, 1);\n    configRegisterInt("Ascension.FovPreset", &s_fovPreset, 0, 3);\n    configRegisterInt("Ascension.MousePreset", &s_mousePreset, 0, 4);\n    configRegisterInt("Ascension.GamepadPreset", &s_gamepadPreset, 0, 3);\n'''
    text = replace_once(text, marker, replacement, "preset config registration")

    hook = '''    if (strcmp(r->key, "Video.Fullscreen") == 0) {\n        videoRequestFullscreen((int)lround(v));\n    } else if (strncmp(r->key, "Video.", 6) == 0 && !r->restart) {\n        videoRequestLiveConfig();\n    }\n'''
    hook_repl = '''    if (strcmp(r->key, "Ascension.FovPreset") == 0) {\n        int p = (int)lround(v);\n        for (int i = 0; i < NUM_ROWS; i++) {\n            if (strcmp(rows[i].key, "Video.FovScale") == 0) {\n                if (p == 0) applyRowValue(&rows[i], 100, 0);\n                else if (p == 1) applyRowValue(&rows[i], 105, 0);\n                else if (p == 2) applyRowValue(&rows[i], 115, 0);\n                break;\n            }\n        }\n    } else if (strcmp(r->key, "Ascension.MousePreset") == 0) {\n        int p = (int)lround(v);\n        for (int i = 0; i < NUM_ROWS; i++) {\n            struct Row *q = &rows[i];\n            if (p == 4) break;\n            if (strcmp(q->key, "Input.MouseRawInput") == 0) applyRowValue(q, p == 3 ? 1 : 0, 0);\n            else if (strcmp(q->key, "Input.MouseSmoothing") == 0) applyRowValue(q, p == 1 ? 20 : 0, 0);\n            else if (strcmp(q->key, "Input.MouseYScale") == 0) applyRowValue(q, 100, 0);\n            else if (strcmp(q->key, "Input.AimBand") == 0) applyRowValue(q, p == 0 ? 20 : 16, 0);\n            else if (strcmp(q->key, "Input.HipfirePitchSpeed") == 0) applyRowValue(q, p == 0 ? 100 : 110, 0);\n        }\n    } else if (strcmp(r->key, "Ascension.GamepadPreset") == 0) {\n        int p = (int)lround(v);\n        for (int i = 0; i < NUM_ROWS; i++) {\n            struct Row *q = &rows[i];\n            if (p == 3) break;\n            if (strcmp(q->key, "Input.PadDeadzone") == 0) applyRowValue(q, p == 0 ? 7000 : 5000, 0);\n            else if (strcmp(q->key, "Input.PadTriggerPct") == 0) applyRowValue(q, p == 0 ? 23 : 18, 0);\n            else if (strcmp(q->key, "Input.PadLookInvertY") == 0) applyRowValue(q, p == 2 ? 1 : 0, 0);\n        }\n    } else if (strcmp(r->key, "Video.Fullscreen") == 0) {\n        videoRequestFullscreen((int)lround(v));\n    } else if (strncmp(r->key, "Video.", 6) == 0 && !r->restart) {\n        videoRequestLiveConfig();\n    }\n'''
    text = replace_once(text, hook, hook_repl, "preset application")

    if text == original:
        print("No changes needed.")
        return 0

    backup = PATH.with_suffix(".c.ascension-before-pc-polish-presets")
    if not backup.exists():
        backup.write_text(original, encoding="utf-8")
        print(f"BACKUP: {backup.relative_to(ROOT)}")

    PATH.write_text(text, encoding="utf-8")
    print("SUCCESS: safe PC-polish presets added to F10.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
