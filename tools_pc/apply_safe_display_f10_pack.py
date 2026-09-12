#!/usr/bin/env python3
"""Expose low-risk display/input compatibility options in Ascension's F10.

The patch only surfaces existing port options plus an optional clean window-title
toggle. No ROM, PT-BR, physics, AI or save-format changes.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
OVERLAY = ROOT / "port" / "src" / "optionsoverlay.c"
VIDEO = ROOT / "port" / "src" / "video.c"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count == 0 and new in text:
        print(f"OK: {label} already applied")
        return text
    if count != 1:
        raise SystemExit(f"ERROR: {label}: expected exactly one anchor, found {count}; no file written")
    print(f"APPLY: {label}")
    return text.replace(old, new, 1)


def patch_video() -> None:
    original = VIDEO.read_text(encoding="utf-8")
    text = original
    text = replace_once(
        text,
        'static int cfgFullscreen    = 0;\n',
        'static int cfgFullscreen    = 0;\nstatic int cfgFpsInTitle     = 1;  /* desktop QoL; 0 keeps a clean static title */\n',
        "FPS-title option storage",
    )
    text = replace_once(
        text,
        '    configRegisterInt("Video.Fullscreen",    &cfgFullscreen, 0, 1);\n',
        '    configRegisterInt("Video.Fullscreen",    &cfgFullscreen, 0, 1);\n'
        '    configRegisterInt("Video.FpsInTitle",    &cfgFpsInTitle,  0, 1);\n',
        "FPS-title config",
    )
    text = replace_once(
        text,
        '            snprintf(title, sizeof(title), ASCENSION_WINDOW_TITLE "  -  %.0f fps", vidAvgFPS);\n',
        '            if (cfgFpsInTitle)\n'
        '                snprintf(title, sizeof(title), ASCENSION_WINDOW_TITLE "  -  %.0f fps", vidAvgFPS);\n'
        '            else\n'
        '                snprintf(title, sizeof(title), "%s", ASCENSION_WINDOW_TITLE);\n',
        "clean/FPS window title",
    )
    if text != original:
        VIDEO.write_text(text, encoding="utf-8")


def patch_overlay() -> None:
    original = OVERLAY.read_text(encoding="utf-8")
    text = original

    display_anchor = '''    { .key="Video.TextureFilter",  .label="Texture filter",\n      .help="Texture sharpness and smoothing.", .category=CAT_DISPLAY,\n      .kind=ROW_ENUM, .step=1, .names=kTexFilter, .resetValue=1 },\n'''
    display_replacement = display_anchor + '''\n    { .key="Video.FixMipTextures", .label="Mipmap compatibility fix",\n      .help="Keep the port's mipmapped-texture compatibility fix enabled.", .category=CAT_DISPLAY,\n      .kind=ROW_TOGGLE, .step=1, .names=kOnOff, .resetValue=1 },\n\n    { .key="Video.WrapFix", .label="Texture wrap fix",\n      .help="Optional texture-edge compatibility fix. Leave OFF unless needed.", .category=CAT_DISPLAY,\n      .kind=ROW_TOGGLE, .step=1, .names=kOnOff, .resetValue=0 },\n'''
    text = replace_once(text, display_anchor, display_replacement, "safe display compatibility rows")

    fps_anchor = '''    { .key="Video.DisplayFPS",     .label="Display FPS",\n      .help="Show a small FPS counter.", .category=CAT_DISPLAY,\n      .kind=ROW_TOGGLE, .step=1, .names=kOnOff, .resetValue=0 },\n'''
    fps_replacement = fps_anchor + '''\n    { .key="Video.FpsInTitle", .label="FPS in window title",\n      .help="Show live FPS beside the Ascension window title.", .category=CAT_DISPLAY,\n      .kind=ROW_TOGGLE, .step=1, .names=kOnOff, .resetValue=1 },\n'''
    text = replace_once(text, fps_anchor, fps_replacement, "FPS title row")

    input_anchor = '''    /* INPUT */\n    { .key="Input.MouseAimSpeed",  .label="Mouse aim speed",\n'''
    input_replacement = '''    /* INPUT */\n    { .key="Input.MouseEnabled", .label="Mouse input",\n      .help="Enable or disable mouse input without changing keyboard/gamepad.", .category=CAT_INPUT,\n      .kind=ROW_TOGGLE, .step=1, .names=kOnOff, .resetValue=1 },\n\n    { .key="Input.MouseAimSpeed",  .label="Mouse aim speed",\n'''
    text = replace_once(text, input_anchor, input_replacement, "mouse enabled row")

    if text != original:
        OVERLAY.write_text(text, encoding="utf-8")


def main() -> int:
    patch_video()
    patch_overlay()
    print("SUCCESS: safe display/input compatibility pack applied.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
