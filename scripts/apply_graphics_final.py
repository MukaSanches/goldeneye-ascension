#!/usr/bin/env python3
"""Wire the final Ascension graphics presentation path into the source tree.

This patch is intentionally small and deterministic.  The large Fast3D/RDP
implementation remains normal source-controlled code; this script only owns
three narrow integration seams that are easy to verify and easy to fail closed:

  * SDL pre-swap hook -> Ascension GPU post-FX;
  * one-time final-quality defaults migration in video.c;
  * F10 UI rows for the new presentation controls.

The script is idempotent.  If an upstream/source change removes a known seam it
raises an error instead of guessing and silently producing a half-integrated
build.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: Path, old: str, new: str, marker: str) -> bool:
    text = path.read_text(encoding="utf-8")
    if marker in text:
        return False
    if old not in text:
        raise RuntimeError(f"{path.relative_to(ROOT)}: integration seam not found for {marker}")
    if text.count(old) != 1:
        raise RuntimeError(
            f"{path.relative_to(ROOT)}: expected exactly one seam for {marker}, found {text.count(old)}"
        )
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    return True


def apply() -> None:
    sdl = ROOT / "port/fast3d/gfx_sdl2.cpp"
    video = ROOT / "port/src/video.c"
    overlay = ROOT / "port/src/optionsoverlay.c"

    replace_once(
        sdl,
        '#include "input.h"\n',
        '#include "input.h"\n#include "ascension_postfx.h" /* ASCENSION_GRAPHICS_FINAL */\n',
        "ASCENSION_GRAPHICS_FINAL",
    )

    replace_once(
        sdl,
        "static void gfx_sdl_close(void) {\n    is_running = false;\n}\n",
        "static void gfx_sdl_close(void) {\n"
        "    ascensionPostFxShutdown(); /* ASCENSION_POSTFX_SHUTDOWN */\n"
        "    is_running = false;\n"
        "}\n",
        "ASCENSION_POSTFX_SHUTDOWN",
    )

    replace_once(
        sdl,
        "    if (gfx_pre_swap_hook) {\n        gfx_pre_swap_hook();\n    }\n    SDL_GL_SwapWindow(wnd);\n",
        "    /* Final presentation pass runs after Fast3D has composited the frame\n"
        "     * and before screenshots / swap. It is fail-open and presentation-only. */\n"
        "    ascensionPostFxApply(); /* ASCENSION_POSTFX_PRE_SWAP */\n"
        "    if (gfx_pre_swap_hook) {\n"
        "        gfx_pre_swap_hook();\n"
        "    }\n"
        "    SDL_GL_SwapWindow(wnd);\n",
        "ASCENSION_POSTFX_PRE_SWAP",
    )

    # Fresh-install quality defaults. Existing installations are handled by
    # the revisioned one-time migration below.
    text = video.read_text(encoding="utf-8")
    if "ASCENSION_GRAPHICS_QUALITY_REVISION" not in text:
        required = {
            "static int cfgMSAA          = 1;": "static int cfgMSAA          = 4;",
            "static int cfgTexFilter     = 1;": "static int cfgTexFilter     = 2;",
            "static int cfgAniso         = 4;": "static int cfgAniso         = 16;",
            "static int cfgFullscreen    = 0;": (
                "static int cfgFullscreen    = 0;\n"
                "static int cfgGraphicsQualityRevision = 0; /* ASCENSION_GRAPHICS_QUALITY_REVISION */"
            ),
        }
        for old, new in required.items():
            if old not in text:
                raise RuntimeError(f"port/src/video.c: default seam missing: {old}")
            text = text.replace(old, new, 1)

        register_old = '    configRegisterInt("Video.Fullscreen",    &cfgFullscreen, 0, 1);\n'
        register_new = (
            '    configRegisterInt("Video.Fullscreen",    &cfgFullscreen, 0, 1);\n'
            '    configRegisterInt("Ascension.GraphicsQualityRevision",\n'
            '                      &cfgGraphicsQualityRevision, 0, 100);\n'
        )
        if register_old not in text:
            raise RuntimeError("port/src/video.c: config registration seam missing")
        text = text.replace(register_old, register_new, 1)

        init_old = "    gfx_current_native_viewport.width = GE_NATIVE_W;\n"
        init_new = (
            "    /* Ascension Graphics Final: migrate existing ge007.ini files once.\n"
            "     * The older 0.0.2 migration intentionally restored the upstream\n"
            "     * low-cost baseline (1x MSAA/bilinear/4x AF). This revision is\n"
            "     * applied after configLoad and after that legacy migration, so an\n"
            "     * upgraded user actually receives the final-quality presentation.\n"
            "     * Revision >= 1 is never overwritten again. */\n"
            "    if (cfgGraphicsQualityRevision < 1) {\n"
            "        cfgMSAA = 4;\n"
            "        cfgTexFilter = 2;\n"
            "        cfgAniso = 16;\n"
            "        cfgFixMipTex = 1;\n"
            "        cfgGraphicsQualityRevision = 1;\n"
            "        sysLogPrintf(LOG_INFO,\n"
            "            \"graphics: applied Ascension final quality defaults (4x MSAA, 3-point, 16x AF)\");\n"
            "    }\n\n"
            "    gfx_current_native_viewport.width = GE_NATIVE_W;\n"
        )
        if init_old not in text:
            raise RuntimeError("port/src/video.c: videoInit seam missing")
        text = text.replace(init_old, init_new, 1)
        video.write_text(text, encoding="utf-8")

    # Keep Reset PC settings aligned with the new product defaults and expose
    # the post-FX controls in the same Display section.
    text = overlay.read_text(encoding="utf-8")
    if "ASCENSION_GRAPHICS_FINAL_UI" not in text:
        text = text.replace(
            '.kind=ROW_MSAA, .restart=1, .resetValue=1 },',
            '.kind=ROW_MSAA, .restart=1, .resetValue=4 },',
            1,
        )
        text = text.replace(
            '.kind=ROW_ENUM, .step=1, .names=kTexFilter, .resetValue=1 },',
            '.kind=ROW_ENUM, .step=1, .names=kTexFilter, .resetValue=2 },',
            1,
        )
        aniso_old = (
            '    { .key="Video.Anisotropy",     .label="Anisotropic",\n'
            '      .help="Sharper distant textures. 1-16.", .category=CAT_DISPLAY,\n'
            '      .kind=ROW_SLIDER, .step=1, .uiMin=1, .uiMax=16, .resetValue=4 },\n\n'
            '    { .key="Video.FovScale",       .label="FOV scale %",'
        )
        aniso_new = (
            '    { .key="Video.Anisotropy",     .label="Anisotropic",\n'
            '      .help="Sharper distant textures. 1-16.", .category=CAT_DISPLAY,\n'
            '      .kind=ROW_SLIDER, .step=1, .uiMin=1, .uiMax=16, .resetValue=16 },\n\n'
            '    /* ASCENSION_GRAPHICS_FINAL_UI */\n'
            '    { .key="Video.PostFX",         .label="Adaptive sharpen",\n'
            '      .help="GPU edge-adaptive detail recovery. Applies now.",\n'
            '      .category=CAT_DISPLAY, .kind=ROW_TOGGLE, .step=1,\n'
            '      .names=kOnOff, .resetValue=1 },\n\n'
            '    { .key="Video.Sharpen",        .label="Sharpness",\n'
            '      .help="Final image detail recovery. 0 disables it.",\n'
            '      .category=CAT_DISPLAY, .kind=ROW_SLIDER, .step=5,\n'
            '      .uiMin=0, .uiMax=100, .resetValue=35 },\n\n'
            '    { .key="Video.FovScale",       .label="FOV scale %",'
        )
        if aniso_old not in text:
            raise RuntimeError("port/src/optionsoverlay.c: anisotropy/FOV seam missing")
        text = text.replace(aniso_old, aniso_new, 1)
        overlay.write_text(text, encoding="utf-8")


def check() -> None:
    checks = {
        ROOT / "port/fast3d/gfx_sdl2.cpp": [
            "ASCENSION_GRAPHICS_FINAL",
            "ASCENSION_POSTFX_SHUTDOWN",
            "ASCENSION_POSTFX_PRE_SWAP",
            "ascensionPostFxApply();",
        ],
        ROOT / "port/src/video.c": [
            "ASCENSION_GRAPHICS_QUALITY_REVISION",
            "Ascension.GraphicsQualityRevision",
            "cfgMSAA = 4;",
            "cfgTexFilter = 2;",
            "cfgAniso = 16;",
        ],
        ROOT / "port/src/optionsoverlay.c": [
            "ASCENSION_GRAPHICS_FINAL_UI",
            'Video.PostFX',
            'Video.Sharpen',
            '.resetValue=16',
        ],
        ROOT / "port/src/ascension_postfx.cpp": [
            'configRegisterInt("Video.PostFX"',
            'configRegisterInt("Video.Sharpen"',
            "glCopyTexSubImage2D",
            "adaptiveGain",
        ],
        ROOT / "port/include/ascension_postfx.h": [
            "ascensionPostFxApply",
            "ascensionPostFxShutdown",
        ],
    }

    missing: list[str] = []
    for path, markers in checks.items():
        if not path.exists():
            missing.append(f"{path.relative_to(ROOT)}: missing file")
            continue
        text = path.read_text(encoding="utf-8")
        for marker in markers:
            if marker not in text:
                missing.append(f"{path.relative_to(ROOT)}: missing {marker!r}")

    if missing:
        raise RuntimeError("graphics integration check failed:\n  " + "\n  ".join(missing))

    print("ascension_graphics_final: integration contracts passed")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="verify integration without modifying files")
    args = parser.parse_args()

    try:
        if args.check:
            check()
        else:
            apply()
            check()
            print("ascension_graphics_final: integration applied")
        return 0
    except Exception as exc:  # fail closed with a concise build error
        print(f"ascension_graphics_final: ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
