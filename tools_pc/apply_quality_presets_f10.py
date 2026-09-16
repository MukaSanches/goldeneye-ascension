#!/usr/bin/env python3
"""Add conservative video quality presets to Ascension's F10 overlay.

The presets only change existing port-side Video.* options. They do not touch
GoldenEye simulation, ROM data, missions, saves, PT-BR assets, or input logic.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "port" / "src" / "optionsoverlay.c"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    applied = text.count(new)
    if applied == 1:
        print(f"OK: {label} already applied")
        return text
    if applied > 1:
        raise SystemExit(f"ERROR: {label}: duplicate patched result found {applied} times; no write")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"ERROR: {label}: expected one anchor, found {count}; no write")
    print(f"APPLY: {label}")
    return text.replace(old, new, 1)


def main() -> int:
    original = PATH.read_text(encoding="utf-8")
    text = original

    text = replace_once(
        text,
        '''enum RowAction {\n    ACTION_NONE,\n    ACTION_RESET,\n    ACTION_RESTART,\n};\n''',
        '''enum RowAction {\n    ACTION_NONE,\n    ACTION_RESET,\n    ACTION_RESTART,\n    ACTION_QUALITY_PERFORMANCE,\n    ACTION_QUALITY_BALANCED,\n    ACTION_QUALITY_QUALITY,\n};\n''',
        "quality preset action enum",
    )

    anchor = '''    { .key="Video.FovScale",       .label="FOV scale %",\n      .help="View width. Safe range 70-120.", .category=CAT_DISPLAY,\n      .kind=ROW_SLIDER, .step=5, .uiMin=70, .uiMax=120, .resetValue=100 },\n'''
    replacement = anchor + '''\n    { .key="__QualityPerformance", .label="Quality preset: Performance",\n      .help="Fast preset: 1x MSAA, bilinear, 2x anisotropic.", .category=CAT_DISPLAY,\n      .kind=ROW_ACTION, .action=ACTION_QUALITY_PERFORMANCE, .found=1 },\n\n    { .key="__QualityBalanced", .label="Quality preset: Balanced",\n      .help="Recommended preset: 2x MSAA, 3-point, 4x anisotropic.", .category=CAT_DISPLAY,\n      .kind=ROW_ACTION, .action=ACTION_QUALITY_BALANCED, .found=1 },\n\n    { .key="__QualityQuality", .label="Quality preset: Quality",\n      .help="Sharper preset: 4x MSAA, 3-point, 8x anisotropic.", .category=CAT_DISPLAY,\n      .kind=ROW_ACTION, .action=ACTION_QUALITY_QUALITY, .found=1 },\n'''
    if '.key="__QualityPerformance"' in text:
        print("OK: quality preset rows already applied")
    else:
        text = replace_once(text, anchor, replacement, "quality preset rows")

    helper_anchor = '''static void activateAction(struct Row *r)\n{\n'''
    helper = '''static struct Row *findRowByKey(const char *key)\n{\n    for (int i = 0; i < NUM_ROWS; i++)\n        if (rows[i].key && strcmp(rows[i].key, key) == 0)\n            return &rows[i];\n    return NULL;\n}\n\nstatic void applyQualityPreset(int action)\n{\n    struct Row *msaa = findRowByKey("Video.MSAA");\n    struct Row *filter = findRowByKey("Video.TextureFilter");\n    struct Row *aniso = findRowByKey("Video.Anisotropy");\n    struct Row *mip = findRowByKey("Video.FixMipTextures");\n    struct Row *wrap = findRowByKey("Video.WrapFix");\n\n    if (!msaa || !filter || !aniso) {\n        setStatus("PRESET UNAVAILABLE");\n        return;\n    }\n\n    double msaaV = 2, filterV = 2, anisoV = 4;\n    const char *name = "BALANCED";\n    if (action == ACTION_QUALITY_PERFORMANCE) {\n        msaaV = 1; filterV = 1; anisoV = 2; name = "PERFORMANCE";\n    } else if (action == ACTION_QUALITY_QUALITY) {\n        msaaV = 4; filterV = 2; anisoV = 8; name = "QUALITY";\n    }\n\n    applyRowValue(msaa, msaaV, 0);\n    applyRowValue(filter, filterV, 0);\n    applyRowValue(aniso, anisoV, 0);\n    if (mip) applyRowValue(mip, 1, 0);\n    if (wrap) applyRowValue(wrap, 0, 0);\n    configSave();\n    setStatus("%s - RESTART FOR MSAA", name);\n}\n\nstatic void activateAction(struct Row *r)\n{\n'''
    text = replace_once(text, helper_anchor, helper, "quality preset helper")

    action_anchor = '''    uint64_t now = sysGetMicroseconds();\n\n    if (!pendingActionIs(r->action)) {\n'''
    action_replacement = '''    uint64_t now = sysGetMicroseconds();\n\n    if (r->action == ACTION_QUALITY_PERFORMANCE ||\n        r->action == ACTION_QUALITY_BALANCED ||\n        r->action == ACTION_QUALITY_QUALITY) {\n        applyQualityPreset(r->action);\n        return;\n    }\n\n    if (!pendingActionIs(r->action)) {\n'''
    text = replace_once(text, action_anchor, action_replacement, "quality preset activation")

    value_anchor = '''        else if (r->action == ACTION_RESET)\n            snprintf(out, n, "RESET");\n        else\n            snprintf(out, n, "RESTART");\n'''
    value_replacement = '''        else if (r->action == ACTION_RESET)\n            snprintf(out, n, "RESET");\n        else if (r->action == ACTION_RESTART)\n            snprintf(out, n, "RESTART");\n        else\n            snprintf(out, n, "APPLY");\n'''
    text = replace_once(text, value_anchor, value_replacement, "quality preset action label")

    if text == original:
        print("No changes needed.")
        return 0

    backup = PATH.with_suffix(".c.ascension-before-quality-presets")
    if not backup.exists():
        backup.write_text(original, encoding="utf-8")
        print(f"BACKUP: {backup.relative_to(ROOT)}")

    PATH.write_text(text, encoding="utf-8")
    print("SUCCESS: F10 quality presets added.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
