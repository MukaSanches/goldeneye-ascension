#!/usr/bin/env python3
"""Safe entry point for the final Q Watch installer.

The main installer intentionally contains strong idempotence checks. This small
adapter performs the native-abort refactor first, before the installer adds the
shared helper body, so the original five-line sequence remains an unambiguous
single anchor on a pristine tree.
"""
from __future__ import annotations

import apply_watch_ui_final as impl

_ORIGINAL_PATCH_OPTIONS = impl.patch_options
_NATIVE_ABORT = '''        D_800409A4 = 0;
        set_missionstate(MISSION_STATE_0);
        bossRunTitleStage();
        mission_failed_or_aborted = TRUE;
        deleteCurrentSelectedFolder();'''
_DELEGATE = "        watchAbortMissionToFrontEnd();"


def patch_options_safe(text: str) -> str:
    if "static void watchAbortMissionToFrontEnd(void)" not in text:
        count = text.count(_NATIVE_ABORT)
        if count != 1:
            raise impl.PatchError(
                f"native abort pre-refactor: expected exactly one anchor, found {count}"
            )
        text = text.replace(_NATIVE_ABORT, _DELEGATE, 1)

    text = _ORIGINAL_PATCH_OPTIONS(text)
    # options.c already uses sprintf throughout; keep the generated page-count
    # copy on the same C89-friendly path instead of introducing snprintf here.
    text = text.replace(
        'snprintf(pageCount, sizeof(pageCount), "%u/5", (unsigned)watch_screen_index + 1U);',
        'sprintf(pageCount, "%u/5", (unsigned)watch_screen_index + 1U);',
        1,
    )
    return text


impl.patch_options = patch_options_safe

if __name__ == "__main__":
    raise SystemExit(impl.main())
