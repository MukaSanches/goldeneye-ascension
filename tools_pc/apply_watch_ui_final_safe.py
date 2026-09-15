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
_SNPRINTF_PAGE_COUNT = (
    'snprintf(pageCount, sizeof(pageCount), "%u/5", '
    '(unsigned)watch_screen_index + 1U);'
)
_SPRINTF_PAGE_COUNT = 'sprintf(pageCount, "%u/5", (unsigned)watch_screen_index + 1U);'


def patch_options_safe(text: str) -> str:
    # The main installer identifies its complete generated chrome block to stay
    # idempotent. Local/CI builds use sprintf for compatibility with the rest of
    # options.c, so normalize that one generated line back to the installer's
    # canonical spelling while checking an already-integrated tree, then restore
    # the C89-friendly spelling before returning. The caller therefore receives
    # byte-for-byte identical text on a second application.
    if _SPRINTF_PAGE_COUNT in text and _SNPRINTF_PAGE_COUNT not in text:
        text = text.replace(_SPRINTF_PAGE_COUNT, _SNPRINTF_PAGE_COUNT, 1)

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
    text = text.replace(_SNPRINTF_PAGE_COUNT, _SPRINTF_PAGE_COUNT, 1)
    return text


impl.patch_options = patch_options_safe

if __name__ == "__main__":
    raise SystemExit(impl.main())
