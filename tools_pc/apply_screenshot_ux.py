#!/usr/bin/env python3
"""Improve F12 screenshot UX without touching rendering or game logic.

Screenshots are stored under ./screenshots with timestamped PPM filenames. The
underlying framebuffer dump path remains unchanged for maximum safety.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "port" / "src" / "video.c"


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
        '#include <string.h>\n',
        '#include <string.h>\n#include <time.h>\n',
        'time include',
    )

    old = '''    if (screenshotReq) {\n        screenshotReq = 0;\n        static int shotNum = 0;\n        char path[128];\n        GE_MKDIR("ppm");\n        snprintf(path, sizeof(path), "ppm/shot_%03d.ppm", shotNum++);\n        if (gfx_opengl_dump_bound_fbo((uint32_t)gfx_current_dimensions.width,\n                                      (uint32_t)gfx_current_dimensions.height, path)) {\n            sysLogPrintf(LOG_INFO, "video: screenshot -> %s "\n                         "(view with tools_pc/ppm2bmp.py)", path);\n        } else {\n            sysLogPrintf(LOG_WARNING, "video: screenshot failed");\n        }\n    }\n'''
    new = '''    if (screenshotReq) {\n        screenshotReq = 0;\n        static int shotNum = 0;\n        char path[160];\n        char stamp[32] = "capture";\n        time_t now = time(NULL);\n        struct tm *lt = localtime(&now);\n        if (lt)\n            strftime(stamp, sizeof(stamp), "%Y%m%d_%H%M%S", lt);\n        GE_MKDIR("screenshots");\n        snprintf(path, sizeof(path), "screenshots/ascension_%s_%03d.ppm", stamp, shotNum++);\n        if (gfx_opengl_dump_bound_fbo((uint32_t)gfx_current_dimensions.width,\n                                      (uint32_t)gfx_current_dimensions.height, path)) {\n            sysLogPrintf(LOG_INFO, "video: F12 screenshot saved -> %s", path);\n        } else {\n            sysLogPrintf(LOG_WARNING, "video: screenshot failed");\n        }\n    }\n'''
    text = replace_once(text, old, new, 'timestamped screenshot path')

    if text == original:
        print('No changes needed.')
        return 0

    backup = PATH.with_suffix('.c.ascension-before-screenshot-ux')
    if not backup.exists():
        backup.write_text(original, encoding='utf-8')
        print(f"BACKUP: {backup.relative_to(ROOT)}")
    PATH.write_text(text, encoding='utf-8')
    print('SUCCESS: F12 screenshots now use ./screenshots with timestamps.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
