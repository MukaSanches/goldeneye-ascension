#!/usr/bin/env python3
"""Add subtle, low-risk visual polish to the F10 overlay.

Adds an optional Ascension front-end brand toggle and clearer selected-row
restart feedback. UI-only: no gameplay, ROM, mission, save, or rendering-core changes.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "port" / "src" / "optionsoverlay.c"


def replace_once(text, old, new, label):
    count = text.count(old)
    if count == 0 and new in text:
        print(f"OK: {label} already applied")
        return text
    if count != 1:
        raise SystemExit(f"ERROR: {label}: expected one anchor, found {count}; no write")
    print(f"APPLY: {label}")
    return text.replace(old, new, 1)


def main():
    original = PATH.read_text(encoding="utf-8")
    text = original

    text = replace_once(
        text,
        'static int  s_showFps;\nstatic int  s_controlHintSeen;\n',
        'static int  s_showFps;\nstatic int  s_showBrand = 1;\nstatic int  s_controlHintSeen;\n',
        'brand state',
    )

    text = replace_once(
        text,
        '    configRegisterInt("Video.DisplayFPS", &s_showFps, 0, 1);\n',
        '    configRegisterInt("Video.DisplayFPS", &s_showFps, 0, 1);\n    configRegisterInt("Ascension.ShowBrand", &s_showBrand, 0, 1);\n',
        'brand config',
    )

    gameplay_anchor = '''    { .key="Game.SkipIntro",       .label="Skip intro",\n      .help="Next launch starts at file select.", .category=CAT_GAMEPLAY,\n      .kind=ROW_TOGGLE, .step=1, .names=kOnOff, .restart=1, .resetValue=0 },\n'''
    gameplay_replacement = gameplay_anchor + '''\n    { .key="Ascension.ShowBrand", .label="Ascension front-end brand",\n      .help="Show the Ascension signature and F10 hint on file select.", .category=CAT_GAMEPLAY,\n      .kind=ROW_TOGGLE, .step=1, .names=kOnOff, .resetValue=1 },\n'''
    text = replace_once(text, gameplay_anchor, gameplay_replacement, 'brand F10 row')

    text = replace_once(
        text,
        '        const int showBrand = current_menu == GE_MENU_FILE_SELECT;\n',
        '        const int showBrand = s_showBrand && current_menu == GE_MENU_FILE_SELECT;\n',
        'brand visibility',
    )

    help_anchor = '''    gdl = drawText(gdl, OV_X0, OV_TOP + 2 * OV_LINE,\n                   rows[s_sel].help ? rows[s_sel].help : "PC settings",\n                   ASC_UI_SLATE);\n'''
    help_replacement = '''    {\n        char helpLine[160];\n        const char *baseHelp = rows[s_sel].help ? rows[s_sel].help : "PC settings";\n        if (rows[s_sel].restart)\n            snprintf(helpLine, sizeof(helpLine), "%s  [RESTART REQUIRED]", baseHelp);\n        else\n            snprintf(helpLine, sizeof(helpLine), "%s", baseHelp);\n        gdl = drawText(gdl, OV_X0, OV_TOP + 2 * OV_LINE, helpLine,\n                       rows[s_sel].restart ? ASC_UI_GOLD_DIM : ASC_UI_SLATE);\n    }\n'''
    text = replace_once(text, help_anchor, help_replacement, 'restart help feedback')

    if text == original:
        print('No changes needed.')
        return 0

    backup = PATH.with_suffix('.c.ascension-before-overlay-polish')
    if not backup.exists():
        backup.write_text(original, encoding='utf-8')
        print(f"BACKUP: {backup.relative_to(ROOT)}")
    PATH.write_text(text, encoding='utf-8')
    print('SUCCESS: subtle F10 visual polish applied.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
