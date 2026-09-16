# Ascension 0.0.3

Ascension 0.0.3 adds the first localization layer for PC-owned UI without changing GoldenEye ROM text, missions, assets, saves, AI or gameplay logic.

## Player-facing changes

- Runtime identity is now `Ascension 0.0.3`.
- Ascension Control supports English and Portuguese (Brazil).
- Open Ascension Control with `F10`, then press `F9` to switch language instantly.
- The selected language is saved as `Ascension.Language` in the existing `ge007.ini` configuration and persists across launches.
- The footer always advertises the language shortcut: English shows `F9 PT-BR`; Portuguese shows `F9 EN`.
- Port-owned labels, help text, values, confirmation messages and the file-select F10 discovery text are localized.

## Scope and safety

Localization is intentionally limited to Ascension-owned PC UI. Original GoldenEye text and data remain untouched.

PT-BR strings are ASCII-safe in 0.0.3 because the in-game overlay reuses GoldenEye's legacy Gothic text renderer. Accented glyphs should only be enabled after their encoding/rendering behavior has been verified across supported ROM regions.

The localization hook translates text immediately before the existing renderer and text-measurement calls. This keeps drawing, fonts, alignment and the display-list path unchanged while ensuring translated strings are measured with the same text that is rendered.

## Test checklist

1. Build with `./build-pc.sh ntsc-final`.
2. Confirm the title bar reads `Ascension 0.0.3` followed by the FPS suffix.
3. Reach file select and confirm the Ascension footer still renders correctly.
4. Press `F10` and confirm the footer shows `F9 PT-BR`.
5. Press `F9`; labels/help/status text should switch immediately to PT-BR and the footer should show `F9 EN`.
6. Close and relaunch the game; PT-BR should remain selected.
7. Press `F9` again inside Ascension Control to return to English.
8. Play a mission to confirm original GoldenEye text, HUD and gameplay are unchanged.
