#!/usr/bin/env python3
"""Safe entry point for the final Q Watch installer.

The main installer intentionally contains strong idempotence checks. This small
adapter performs the native-abort refactor first, before the installer adds the
shared helper body, so the original five-line sequence remains an unambiguous
single anchor on a pristine tree.

The quick-return menu guard is kept inside the port-owned overlay without
pulling GoldenEye's internal menu enum header into that translation unit. The
overlay already represents frontend context with small local GE_MENU_* aliases;
this adapter therefore installs ``GE_MENU_RUN_STAGE = 11`` beside the existing
file-select alias and uses it for the guard. Older generated trees that used the
bare ``MENU_RUN_STAGE`` spelling are normalized to this local alias.

The later runtime hotfix deliberately separates the convenience F10 return from
GoldenEye's stock Abort Mission path. Once that migration is present, this safe
entry point recognizes the fully-installed final-watch state and leaves the game
side byte-for-byte unchanged rather than trying to reconstruct the older bridge.
"""
from __future__ import annotations

import apply_watch_ui_final as impl

_ORIGINAL_PATCH_OPTIONS = impl.patch_options
_ORIGINAL_PATCH_OVERLAY = impl.patch_overlay
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
_LOCAL_RUN_STAGE_GUARD = "current_menu != GE_MENU_RUN_STAGE && current_menu != -1"
_BARE_RUN_STAGE_GUARD = "current_menu != MENU_RUN_STAGE && current_menu != -1"
_FILE_SELECT_DEFINE = "#define GE_MENU_FILE_SELECT 5"
_RUN_STAGE_DEFINE = "#define GE_MENU_RUN_STAGE 11"
_RUNTIME_FIX_MARKERS = (
    "int ascensionWatchIsActive(void)",
    "void ascensionWatchReturnToMainMenu(void)",
    "frontChangeMenu(MENU_MISSION_SELECT, FALSE);",
    "mission_failed_or_aborted = FALSE;",
)
_FINAL_WATCH_MARKERS = (
    "static void watchAbortMissionToFrontEnd(void)",
    "ascensionDrawWatchChrome",
    "Q WATCH / STATUS",
    "Q WATCH / EQUIPMENT",
    "Q WATCH / CONTROLS",
    "Q WATCH / SYSTEM",
    "Q WATCH / BRIEFING",
)


def patch_options_safe(text: str) -> str:
    # Runtime-fix state is a later, intentional evolution of the final-watch
    # bridge. Re-running the older generator must never overwrite it.
    if all(marker in text for marker in _RUNTIME_FIX_MARKERS):
        missing = [m for m in _FINAL_WATCH_MARKERS if m not in text]
        if missing:
            raise impl.PatchError(
                "runtime-fixed watch is missing final-watch markers: " + ", ".join(missing)
            )
        if "deleteCurrentSelectedFolder()" not in text:
            raise impl.PatchError("stock Abort Mission helper was lost")
        return text

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


def patch_overlay_safe(text: str) -> str:
    """Install/repair the F10 quick-return guard without game-header coupling."""
    if text.count(_LOCAL_RUN_STAGE_GUARD) > 1 or text.count(_BARE_RUN_STAGE_GUARD) > 1:
        raise impl.PatchError("quick-return menu guard appears more than once")

    # Normalize the older safe-adapter output before delegating to the original
    # installer. The original final-watch patch emits the GE_MENU_RUN_STAGE
    # spelling, so this also preserves its idempotence marker.
    canonical = text
    if _BARE_RUN_STAGE_GUARD in canonical and _LOCAL_RUN_STAGE_GUARD not in canonical:
        canonical = canonical.replace(
            _BARE_RUN_STAGE_GUARD, _LOCAL_RUN_STAGE_GUARD, 1
        )

    canonical = _ORIGINAL_PATCH_OVERLAY(canonical)

    if _LOCAL_RUN_STAGE_GUARD not in canonical:
        raise impl.PatchError("quick-return menu guard missing after install")
    if _BARE_RUN_STAGE_GUARD in canonical:
        raise impl.PatchError("bare MENU_RUN_STAGE guard survived normalization")

    # optionsoverlay.c intentionally uses port-local numeric aliases for the
    # small amount of menu context it needs. Keep the run-stage constant beside
    # GE_MENU_FILE_SELECT rather than importing bondconstants.h into the PC UI.
    if _RUN_STAGE_DEFINE not in canonical:
        count = canonical.count(_FILE_SELECT_DEFINE)
        if count != 1:
            raise impl.PatchError(
                f"file-select menu alias: expected exactly one anchor, found {count}"
            )
        canonical = canonical.replace(
            _FILE_SELECT_DEFINE,
            _FILE_SELECT_DEFINE + "\n" + _RUN_STAGE_DEFINE,
            1,
        )

    return canonical


impl.patch_options = patch_options_safe
impl.patch_overlay = patch_overlay_safe

if __name__ == "__main__":
    raise SystemExit(impl.main())
