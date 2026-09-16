#!/usr/bin/env python3
"""Hotfix the two runtime regressions found in the final Q Watch pass.

Fixes:
  * Escape while the native Q Watch is active must not disarm PC mouse capture.
    Escape is also a normal GoldenEye Cancel binding, so the SDL shell should
    leave capture ownership alone while the watch owns the pause interaction.
  * The F10 quick-return action must go directly to the normal solo mission
    selector. It must not reuse the stock Q Watch Abort Mission path, because
    that path deliberately marks the mission aborted and clears the selected
    folder in this codebase.

Run after apply_watch_ui_final_safe.py. The patch is fail-closed and idempotent.
"""
from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OPTIONS = ROOT / "src/game/options.c"
VIDEO = ROOT / "port/src/video.c"
HEADER = ROOT / "port/include/ascension_watch.h"
WATCH_GUARD_MARKER = "/* Ascension watch capture guard:"


class PatchError(RuntimeError):
    pass


def patch_options(text: str) -> str:
    marker = "void ascensionWatchReturnToMainMenu(void)"
    if marker not in text:
        raise PatchError("final Q Watch bridge is not installed")

    # Already fixed. These are semantic markers of the newer bridge, not a
    # formatting-dependent comment, so a second run is byte-for-byte stable.
    if (
        "int ascensionWatchIsActive(void)" in text
        and "frontChangeMenu(MENU_MISSION_SELECT, FALSE);" in text
        and "mission_failed_or_aborted = FALSE;" in text
    ):
        return text

    block_start = text.find("#ifdef PORT\nvoid ascensionWatchReturnToMainMenu(void)")
    if block_start < 0:
        raise PatchError("quick-return PORT block start not found")

    block_end_anchor = "#endif\n\n// initial pause screen: WATCH_INDEX_MISSION_STATUS"
    block_end = text.find(block_end_anchor, block_start)
    if block_end < 0:
        raise PatchError("quick-return PORT block end not found")

    old_block = text[block_start:block_end + len("#endif")]
    if old_block.count("ascensionWatchReturnToMainMenu") != 1:
        raise PatchError("quick-return bridge is ambiguous")

    new_block = '''#ifdef PORT
/* Ascension runtime fix: expose the native watch state to the SDL shell so
 * Escape can keep its normal GoldenEye meaning without dropping mouse capture. */
int ascensionWatchIsActive(void)
{
    return g_CurrentPlayer != NULL &&
           g_CurrentPlayer->watch_animation_state != WATCH_ANIMATION_0x0;
}

void ascensionWatchReturnToMainMenu(void)
{
    /* This is intentionally NOT the stock Abort Mission action. The stock
     * watch path marks the mission failed/aborted and clears the selected
     * folder. For the F10 convenience action we only stop the active mission,
     * queue GoldenEye's native solo mission selector, then ask the boss loop
     * to load the title/frontend stage. */
    if (getPlayerCount() != 1)
    {
        return;
    }

    watch_item_is_actively_selected = 0;
    D_800409A4 = 0;
    set_missionstate(MISSION_STATE_0);
    mission_failed_or_aborted = FALSE;
    frontChangeMenu(MENU_MISSION_SELECT, FALSE);
    bossRunTitleStage();
}
#endif'''

    return text[:block_start] + new_block + text[block_end + len("#endif"):]


def patch_header(text: str) -> str:
    if "void ascensionWatchReturnToMainMenu(void);" not in text:
        raise PatchError("ascension_watch.h return bridge declaration not found")
    if "int ascensionWatchIsActive(void);" in text:
        return text
    return text.replace(
        "void ascensionWatchReturnToMainMenu(void);",
        "int ascensionWatchIsActive(void);\nvoid ascensionWatchReturnToMainMenu(void);",
        1,
    )


def patch_video(text: str) -> str:
    include_anchor = '#include "optionsoverlay.h"\n'
    if '#include "ascension_watch.h"\n' not in text:
        count = text.count(include_anchor)
        if count != 1:
            raise PatchError(
                f"video watch include anchor: expected exactly one, found {count}"
            )
        text = text.replace(
            include_anchor,
            include_anchor + '#include "ascension_watch.h"\n',
            1,
        )

    if WATCH_GUARD_MARKER in text:
        return text

    # Keep the anchor limited to the Escape branch but ignore its outer
    # indentation; the current video.c uses 12 spaces at switch depth.
    old = '''} else if (ev.key.keysym.sym == SDLK_ESCAPE && !ev.key.repeat) {
                if (optionsOverlayIsOpen()) {
                    optionsOverlayToggle();
                } else {
                    inputReleaseCapture();
                }
            }'''
    new = '''} else if (ev.key.keysym.sym == SDLK_ESCAPE && !ev.key.repeat) {
                if (optionsOverlayIsOpen()) {
                    optionsOverlayToggle();
                } else if (ascensionWatchIsActive()) {
                    /* Ascension watch capture guard: Escape is still
                     * delivered through SDL_GetKeyboardState to GoldenEye,
                     * but it must not clear captureArmed while the native
                     * Q Watch owns the pause interaction. Otherwise the
                     * player returns to gameplay with dead mouse-look. */
                } else {
                    inputReleaseCapture();
                }
            }'''

    count = text.count(old)
    if count != 1:
        raise PatchError(f"video Escape capture anchor: expected exactly one, found {count}")
    return text.replace(old, new, 1)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--no-backup", action="store_true")
    args = ap.parse_args()

    originals = {
        OPTIONS: OPTIONS.read_text(encoding="utf-8"),
        VIDEO: VIDEO.read_text(encoding="utf-8"),
        HEADER: HEADER.read_text(encoding="utf-8"),
    }

    try:
        updated = {
            OPTIONS: patch_options(originals[OPTIONS]),
            VIDEO: patch_video(originals[VIDEO]),
            HEADER: patch_header(originals[HEADER]),
        }
    except Exception as exc:
        raise SystemExit(f"ERROR: {exc}; no file written")

    contracts = (
        (updated[OPTIONS], "int ascensionWatchIsActive(void)"),
        (updated[OPTIONS], "frontChangeMenu(MENU_MISSION_SELECT, FALSE);"),
        (updated[VIDEO], WATCH_GUARD_MARKER),
        (updated[HEADER], "int ascensionWatchIsActive(void);"),
    )
    for haystack, needle in contracts:
        if needle not in haystack:
            raise SystemExit(f"ERROR: runtime-fix contract missing {needle!r}; no file written")

    changed = [str(p.relative_to(ROOT)) for p in originals if originals[p] != updated[p]]

    if args.check:
        print("Ascension Watch Runtime Fix preflight: PASS")
        print("Q Watch Escape preserves mouse capture: PASS")
        print("Quick return targets native mission selector: PASS")
        print("Quick return avoids stock Abort Mission save-clear path: PASS")
        print("Would update:", ", ".join(changed) if changed else "nothing")
        return 0

    if not args.no_backup:
        for path in originals:
            if originals[path] == updated[path]:
                continue
            backup = path.with_suffix(path.suffix + ".before-watch-runtime-fix")
            if not backup.exists():
                backup.write_text(originals[path], encoding="utf-8")
                print("BACKUP:", backup.relative_to(ROOT))

    for path in originals:
        if originals[path] != updated[path]:
            path.write_text(updated[path], encoding="utf-8")
            print("UPDATED:", path.relative_to(ROOT))

    if not changed:
        print("No changes needed; watch runtime fix is already installed.")
    print("Ascension Watch Runtime Fix installed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
