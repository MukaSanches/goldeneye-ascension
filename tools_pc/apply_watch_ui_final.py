#!/usr/bin/env python3
"""Install Ascension's final Q Watch polish and quick-return action.

Design constraints:
  * preserve GoldenEye's physical-watch presentation, five native pages,
    rotating 3D inventory, health/armor bars, static scanline and pause music;
  * improve hierarchy/feedback instead of replacing the watch with a PC panel;
  * route "Return to main menu" through the exact native mission-abort path;
  * keep the dangerous return action behind the F10 overlay's two-press guard;
  * keep the patch fail-closed and idempotent.

Run after UI Overhaul V2, persistent F10 hint and All Missions.
"""
from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OPTIONS = ROOT / "src/game/options.c"
OVERLAY = ROOT / "port/src/optionsoverlay.c"
LOCALE = ROOT / "port/src/ascension_locale.c"


class PatchError(RuntimeError):
    pass


def once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        return text
    count = text.count(old)
    if count != 1:
        raise PatchError(f"{label}: expected exactly one anchor, found {count}")
    return text.replace(old, new, 1)


def patch_options(text: str) -> str:
    if "Gfx *draw_watch_current_page" not in text or "watch_screen0_navigation" not in text:
        raise PatchError("native Q Watch implementation not found")

    text = once(
        text,
        '#include "assets/obseg/text/LoptionE.h"\n',
        '#include "assets/obseg/text/LoptionE.h"\n#ifdef PORT\n#include "ascension_watch.h"\n#include "ascension_locale.h"\n#endif\n',
        "PORT watch bridge includes",
    )

    nav_anchor = '''// initial pause screen: WATCH_INDEX_MISSION_STATUS
void watch_screen0_navigation(void)
{'''
    nav_replacement = '''/* Ascension final: keep a single authoritative path back to GoldenEye's
 * normal front end. The stock Q Watch abort confirmation and the PC F10
 * quick-return action both call this helper, so there is no parallel state
 * machine and no save/progression fabrication. */
static void watchAbortMissionToFrontEnd(void)
{
    D_800409A4 = 0;
    set_missionstate(MISSION_STATE_0);
    bossRunTitleStage();
    mission_failed_or_aborted = TRUE;
    deleteCurrentSelectedFolder();
}

#ifdef PORT
void ascensionWatchReturnToMainMenu(void)
{
    /* The F10 caller already limits this to an active stage. Keep a second
     * guard here so this bridge cannot accidentally become an MP exit path. */
    if (getPlayerCount() != 1)
    {
        return;
    }

    watch_item_is_actively_selected = 0;
    watchAbortMissionToFrontEnd();
}
#endif

// initial pause screen: WATCH_INDEX_MISSION_STATUS
void watch_screen0_navigation(void)
{'''
    text = once(text, nav_anchor, nav_replacement, "shared native abort helper")

    native_abort = '''        D_800409A4 = 0;
        set_missionstate(MISSION_STATE_0);
        bossRunTitleStage();
        mission_failed_or_aborted = TRUE;
        deleteCurrentSelectedFolder();'''
    text = once(text, native_abort, "        watchAbortMissionToFrontEnd();", "native abort delegates to helper")

    colors = '''void set_page_rectangle_colors(s32 watch_screen_index, struct WatchVertex *vertices)
{
    s32 i;

    // Unselected rectangles.
    for (i = 0; i < 20; i++)
    {
        vertices[i].color.r = 0x20;
        vertices[i].color.g = 0x70;
        vertices[i].color.b = 0x20;
    }

    // Currently selected page rectangle.
    for (i = watch_screen_index * 4; i <= watch_screen_index * 4 + 3; i++)
    {
        vertices[i].color.r = 0x50;
        vertices[i].color.g = 0xF0;
        vertices[i].color.b = 0x50;

        // Currently selected page rectangle, but something else is in focus e.g. toggling options or manipulating the controller on the controller screen.
        if (watch_item_is_actively_selected)
        {
            vertices[i].color.r = 0x30;
            vertices[i].color.g = 0xA0;
            vertices[i].color.b = 0x30;
        }
    }
}'''
    colors_new = '''void set_page_rectangle_colors(s32 watch_screen_index, struct WatchVertex *vertices)
{
    s32 i;

    // Unselected rectangles.
    for (i = 0; i < 20; i++)
    {
#ifdef PORT
        /* Dark phosphor: still unmistakably GoldenEye, but with enough
         * separation that the active page reads immediately on LCD/OLED. */
        vertices[i].color.r = 0x18;
        vertices[i].color.g = 0x58;
        vertices[i].color.b = 0x28;
#else
        vertices[i].color.r = 0x20;
        vertices[i].color.g = 0x70;
        vertices[i].color.b = 0x20;
#endif
    }

    // Currently selected page rectangle.
    for (i = watch_screen_index * 4; i <= watch_screen_index * 4 + 3; i++)
    {
#ifdef PORT
        vertices[i].color.r = 0x72;
        vertices[i].color.g = 0xF0;
        vertices[i].color.b = 0x82;
#else
        vertices[i].color.r = 0x50;
        vertices[i].color.g = 0xF0;
        vertices[i].color.b = 0x50;
#endif

        // Currently selected page rectangle, but something else is in focus e.g. toggling options or manipulating the controller on the controller screen.
        if (watch_item_is_actively_selected)
        {
#ifdef PORT
            vertices[i].color.r = 0x42;
            vertices[i].color.g = 0xB0;
            vertices[i].color.b = 0x52;
#else
            vertices[i].color.r = 0x30;
            vertices[i].color.g = 0xA0;
            vertices[i].color.b = 0x30;
#endif
        }
    }
}'''
    text = once(text, colors, colors_new, "watch page phosphor hierarchy")

    dispatcher_anchor = '''/**
 * Address: 7F0ACA28
 */
Gfx *draw_watch_current_page(Gfx *gdl, Mtx *arg1, s32 watch_transitioning)
{'''
    dispatcher_replacement = '''#ifdef PORT
/* A restrained field-instrument header is the only new chrome placed on the
 * watch. It uses GoldenEye's own Bank Gothic renderer and leaves every native
 * page, health/armor gauge and 3D inventory composition intact. */
static const char *ascensionWatchPageName(void)
{
    switch (watch_screen_index)
    {
        case WATCH_INDEX_MISSION_STATUS:   return "Q WATCH / STATUS";
        case WATCH_INDEX_INVENTORY:        return "Q WATCH / EQUIPMENT";
        case WATCH_INDEX_CONTROL_OPTIONS:  return "Q WATCH / CONTROLS";
        case WATCH_INDEX_GAME_OPTIONS:     return "Q WATCH / SYSTEM";
        case WATCH_INDEX_MISSION_BRIEFING: return "Q WATCH / BRIEFING";
        default:                           return "Q WATCH";
    }
}

static Gfx *ascensionDrawWatchChrome(Gfx *gdl)
{
    s32 x = 0x41;
    s32 y = 0x10;
    s32 h = 0;
    s32 w = 0;
    char pageCount[16];
    char *title = (char *)ascensionLocaleText(ascensionWatchPageName());

    gdl = microcode_constructor(gdl);
    textMeasure(&h, &w, title, ptrFontBankGothicChars, ptrFontBankGothic, 0);
    gdl = textRender(gdl, &x, &y, title,
                     ptrFontBankGothicChars, ptrFontBankGothic,
                     0xA0FFA0E8, viGetX(), viGetY(), 0, 0);

    snprintf(pageCount, sizeof(pageCount), "%u/5", (unsigned)watch_screen_index + 1U);
    x = 0xEE;
    y = 0x10;
    gdl = textRender(gdl, &x, &y, pageCount,
                     ptrFontBankGothicChars, ptrFontBankGothic,
                     0x70B878C8, viGetX(), viGetY(), 0, 0);

    x = 0xD7;
    y = 0x1B;
    gdl = textRender(gdl, &x, &y, (char *)ascensionLocaleText("F10 SYSTEM"),
                     ptrFontBankGothicChars, ptrFontBankGothic,
                     0x70B878B8, viGetX(), viGetY(), 0, 0);
    return gdl;
}
#endif

/**
 * Address: 7F0ACA28
 */
Gfx *draw_watch_current_page(Gfx *gdl, Mtx *arg1, s32 watch_transitioning)
{'''
    text = once(text, dispatcher_anchor, dispatcher_replacement, "watch field-instrument chrome")

    return_anchor = '''    return gdl;
}
'''
    # Restrict this replacement to draw_watch_current_page only.
    marker = "Gfx *draw_watch_current_page(Gfx *gdl, Mtx *arg1, s32 watch_transitioning)"
    head, tail = text.split(marker, 1)
    fn_end = tail.find("\n}\n")
    if fn_end < 0:
        raise PatchError("draw_watch_current_page end not found")
    fn = tail[:fn_end + 3]
    rest = tail[fn_end + 3:]
    if "ascensionDrawWatchChrome(gdl)" not in fn:
        old = "\n    return gdl;\n}\n"
        new = '''
#ifdef PORT
    if (watch_transitioning == TRUE)
    {
        gdl = ascensionDrawWatchChrome(gdl);
    }
#endif
    return gdl;
}
'''
        if old not in fn:
            raise PatchError("draw_watch_current_page return anchor missing")
        fn = fn.replace(old, new, 1)
        text = head + marker + fn + rest

    # Release contracts: the defining GoldenEye watch features must survive.
    required = (
        "WATCH_INDEX_MISSION_STATUS", "WATCH_INDEX_INVENTORY",
        "WATCH_INDEX_CONTROL_OPTIONS", "WATCH_INDEX_GAME_OPTIONS",
        "WATCH_INDEX_MISSION_BRIEFING", "draw_watch_inventory_page",
        "g_WatchStaticScanlineY", "draw_text_q_watch_v201_beta",
        "watchAbortMissionToFrontEnd", "ascensionDrawWatchChrome",
    )
    for needle in required:
        if needle not in text:
            raise PatchError(f"watch identity contract lost: {needle}")
    return text


def patch_overlay(text: str) -> str:
    if "Ascension UI Overhaul V2 - Q Watch compact settings" not in text:
        raise PatchError("UI Overhaul V2 must be installed first")
    if 'key="Ascension.UnlockAllMissions"' not in text:
        raise PatchError("All Missions must be installed first")

    text = once(
        text,
        '#include "optionsoverlay.h"\n',
        '#include "optionsoverlay.h"\n#include "ascension_watch.h"\n',
        "quick-return bridge include",
    )

    text = once(
        text,
        '''enum RowAction {
    ACTION_NONE,
    ACTION_RESET,
    ACTION_RESTART,
};''',
        '''enum RowAction {
    ACTION_NONE,
    ACTION_RESET,
    ACTION_RESTART,
    ACTION_RETURN_MENU,
};''',
        "quick-return action enum",
    )

    mission_row = '''    { .key="Ascension.UnlockAllMissions", .label="All missions",
      .help="Show every solo mission without marking it completed.",
      .category=CAT_GAMEPLAY,
      .kind=ROW_TOGGLE, .step=1, .names=kOnOff, .resetValue=0 },

    /* SYSTEM */'''
    mission_row_new = '''    { .key="Ascension.UnlockAllMissions", .label="All missions",
      .help="Show every solo mission without marking it completed.",
      .category=CAT_GAMEPLAY,
      .kind=ROW_TOGGLE, .step=1, .names=kOnOff, .resetValue=0 },

    { .key="__ReturnMenu", .label="Return to main menu",
      .help="Abort the current mission and return to GoldenEye's normal menu.",
      .category=CAT_GAMEPLAY,
      .kind=ROW_ACTION, .action=ACTION_RETURN_MENU, .found=1 },

    /* SYSTEM */'''
    text = once(text, mission_row, mission_row_new, "Gameplay quick-return row")

    old_value = '''        else if (r->action == ACTION_RESET)
            snprintf(out, n, "RESET");
        else
            snprintf(out, n, "RESTART");'''
    new_value = '''        else if (r->action == ACTION_RESET)
            snprintf(out, n, "RESET");
        else if (r->action == ACTION_RETURN_MENU)
            snprintf(out, n, "MENU");
        else
            snprintf(out, n, "RESTART");'''
    text = once(text, old_value, new_value, "quick-return value copy")

    old_arm = '''        setStatus(r->action == ACTION_RESET ?
                  "PRESS AGAIN TO RESET" : "PRESS AGAIN TO RESTART");'''
    new_arm = '''        if (r->action == ACTION_RESET)
            setStatus("PRESS AGAIN TO RESET");
        else if (r->action == ACTION_RETURN_MENU)
            setStatus("PRESS AGAIN TO RETURN");
        else
            setStatus("PRESS AGAIN TO RESTART");'''
    text = once(text, old_arm, new_arm, "quick-return two-press guard")

    old_restart = '''    if (r->action == ACTION_RESTART) {
        configSave();
        setStatus("RESTARTING");
        if (sysRestart() != 0)
            setStatus("RESTART FAILED");
    }'''
    new_restart = '''    if (r->action == ACTION_RETURN_MENU) {
        if (current_menu != GE_MENU_RUN_STAGE && current_menu != -1) {
            setStatus("ALREADY IN MAIN MENU");
            return;
        }
        configSave();
        s_open = 0;
        ascensionWatchReturnToMainMenu();
        return;
    }

    if (r->action == ACTION_RESTART) {
        configSave();
        setStatus("RESTARTING");
        if (sysRestart() != 0)
            setStatus("RESTART FAILED");
    }'''
    text = once(text, old_restart, new_restart, "quick-return activation")

    return text


def patch_locale(text: str) -> str:
    if '"All missions", "Todas as missoes"' not in text:
        raise PatchError("All Missions locale must be installed first")
    if '"Return to main menu", "Voltar ao menu principal"' in text:
        return text

    anchor = '''    { "All missions", "Todas as missoes" },
    { "Show every solo mission without marking it completed.", "Mostra todas as missoes sem marca-las como concluidas." },
'''
    replacement = '''    { "All missions", "Todas as missoes" },
    { "Show every solo mission without marking it completed.", "Mostra todas as missoes sem marca-las como concluidas." },
    { "Return to main menu", "Voltar ao menu principal" },
    { "Abort the current mission and return to GoldenEye's normal menu.", "Abandona a missao atual e volta ao menu normal do GoldenEye." },
    { "PRESS AGAIN TO RETURN", "PRESSIONE NOVAMENTE PARA VOLTAR" },
    { "ALREADY IN MAIN MENU", "VOCE JA ESTA NO MENU" },
    { "MENU", "MENU" },
    { "Q WATCH / STATUS", "Q WATCH / STATUS" },
    { "Q WATCH / EQUIPMENT", "Q WATCH / EQUIPAMENTO" },
    { "Q WATCH / CONTROLS", "Q WATCH / CONTROLES" },
    { "Q WATCH / SYSTEM", "Q WATCH / SISTEMA" },
    { "Q WATCH / BRIEFING", "Q WATCH / BRIEFING" },
    { "F10 SYSTEM", "F10 SISTEMA" },
'''
    return once(text, anchor, replacement, "final watch PT-BR copy")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--no-backup", action="store_true")
    args = ap.parse_args()

    originals = {
        OPTIONS: OPTIONS.read_text(encoding="utf-8"),
        OVERLAY: OVERLAY.read_text(encoding="utf-8"),
        LOCALE: LOCALE.read_text(encoding="utf-8"),
    }
    try:
        updated = {
            OPTIONS: patch_options(originals[OPTIONS]),
            OVERLAY: patch_overlay(originals[OVERLAY]),
            LOCALE: patch_locale(originals[LOCALE]),
        }
    except Exception as exc:
        raise SystemExit(f"ERROR: {exc}; no file written")

    contracts = (
        (updated[OPTIONS], "watchAbortMissionToFrontEnd"),
        (updated[OPTIONS], "ascensionDrawWatchChrome"),
        (updated[OVERLAY], "ACTION_RETURN_MENU"),
        (updated[OVERLAY], 'key="__ReturnMenu"'),
        (updated[LOCALE], '"Return to main menu", "Voltar ao menu principal"'),
    )
    for haystack, needle in contracts:
        if needle not in haystack:
            raise SystemExit(f"ERROR: final contract missing {needle!r}; no file written")

    changed = [str(p.relative_to(ROOT)) for p in originals if originals[p] != updated[p]]
    if args.check:
        print("Ascension Final Q Watch preflight: PASS")
        print("Native five-page watch identity: PRESERVED")
        print("Native abort/front-end path reuse: PASS")
        print("Two-press quick-return guard: PASS")
        print("Q Watch field-instrument hierarchy: PASS")
        print("Would update:", ", ".join(changed) if changed else "nothing")
        return 0

    if not args.no_backup:
        for path in originals:
            if originals[path] == updated[path]:
                continue
            backup = path.with_suffix(path.suffix + ".before-watch-final")
            if not backup.exists():
                backup.write_text(originals[path], encoding="utf-8")
                print("BACKUP:", backup.relative_to(ROOT))

    for path in originals:
        if originals[path] != updated[path]:
            path.write_text(updated[path], encoding="utf-8")
            print("UPDATED:", path.relative_to(ROOT))

    if not changed:
        print("No changes needed; final Q Watch polish is already installed.")
    print("Ascension Final Q Watch installed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
