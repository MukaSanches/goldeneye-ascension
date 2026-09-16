#!/usr/bin/env python3
"""Add conventional desktop fullscreen shortcuts to Ascension.

Alt+Enter and F11 both use the port's existing fullscreen request path. No
renderer or gameplay logic is replaced.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "port" / "src" / "video.c"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count == 0 and new in text:
        print(f"OK: {label} already applied")
        return text
    if count != 1:
        raise SystemExit(f"ERROR: {label}: expected exactly one anchor, found {count}; no file written")
    print(f"APPLY: {label}")
    return text.replace(old, new, 1)


def main() -> int:
    original = PATH.read_text(encoding="utf-8")
    text = original

    old = '''        case SDL_KEYDOWN:\n            if ((ev.key.keysym.sym == SDLK_F4) && (ev.key.keysym.mod & KMOD_ALT)) {\n                sysLogPrintf(LOG_INFO, "video: Alt+F4 -> quit");\n                exit(0);\n            } else if (ev.key.keysym.sym == SDLK_F12 && !ev.key.repeat) {\n'''
    new = '''        case SDL_KEYDOWN:\n            if ((ev.key.keysym.sym == SDLK_F4) && (ev.key.keysym.mod & KMOD_ALT)) {\n                sysLogPrintf(LOG_INFO, "video: Alt+F4 -> quit");\n                exit(0);\n            } else if (((ev.key.keysym.sym == SDLK_RETURN) &&\n                        (ev.key.keysym.mod & KMOD_ALT)) ||\n                       ev.key.keysym.sym == SDLK_F11) {\n                if (!ev.key.repeat) {\n                    int nextFullscreen = !videoIsFullscreen();\n                    videoRequestFullscreen(nextFullscreen);\n                    sysLogPrintf(LOG_INFO, "video: fullscreen shortcut -> %s",\n                                 nextFullscreen ? "on" : "off");\n                }\n            } else if (ev.key.keysym.sym == SDLK_F12 && !ev.key.repeat) {\n'''

    text = replace_once(text, old, new, "Alt+Enter/F11 fullscreen shortcuts")

    if text == original:
        print("No changes needed.")
        return 0

    backup = PATH.with_suffix(".c.ascension-before-fullscreen-shortcuts")
    if not backup.exists():
        backup.write_text(original, encoding="utf-8")
        print(f"BACKUP: {backup.relative_to(ROOT)}")

    PATH.write_text(text, encoding="utf-8")
    print("SUCCESS: Alt+Enter and F11 fullscreen shortcuts applied.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
