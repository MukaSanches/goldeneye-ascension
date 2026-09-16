# Ascension UI Overhaul V2 — Q Watch

## Intent

V1 proved that adding more chrome does not make GoldenEye feel more premium. It made the options overlay denser, reduced the amount of usable space and competed with the original game's unusually strong visual identity.

V2 deliberately reverses that direction. The target is not a generic PC settings dashboard wearing a spy-film skin. The target is a compact PC configuration surface that could plausibly sit beside GoldenEye's own file folders, mission briefings and Q Watch.

## Research translated into engineering rules

### Preserve GoldenEye's strongest screens

The native file-select already communicates character, state and action through folders, photographs, typography and direct cursor interaction. V2 does not cover it with a second UI system. Ascension adds only a restrained signature and a one-time F10 discovery hint.

The same principle applies to gameplay: Ascension settings are a host-layer feature and must not mutate save data, mission progression, weapons, AI, ROM text or game balance.

### Use the game's own typography

GoldenEye's front-end uses the Zurich Bold bank extensively for folder names, mission/difficulty copy and file actions. V2 therefore uses `ptrFontZurichBold` for settings labels, values, hints and tabs. Gothic remains a small branding accent rather than the body face.

This is a design decision and a rendering decision: using the original font banks keeps the overlay inside the same Fast3D/text pipeline as the game and avoids importing a visually unrelated desktop UI toolkit.

### Q Watch, not SaaS dashboard

GoldenEye's watch is a small set of pages with direct navigation. V2 borrows that information architecture rather than reproducing its graphics literally:

- four top-level pages: Display, Controls, Gameplay, System;
- at most seven visible rows;
- one selected row;
- one contextual help line;
- one stable footer for input hints;
- no persistent right-side help panel;
- no oversized category sidebar;
- no cards, rounded mobile controls or decorative telemetry.

### Multiple inputs are peers

Mouse, keyboard and controller-style digital navigation must not require different mental models. The visual focus remains one-dimensional inside a page, while category changes remain horizontal.

PC behavior:

- mouse hover updates focus;
- LMB selects, toggles or drags sliders;
- RMB goes back/closes;
- W/S and Up/Down move vertically;
- A/D and Left/Right adjust;
- Tab changes category;
- F10 closes.

The native GoldenEye menu cursor remains authoritative outside the Ascension overlay.

### Render-state isolation is a release gate

V1 exposed a real Fast3D state failure: rectangle primitives emitted during the text pass caused subsequent glyphs to render as solid blocks on the Windows build.

V2 has a hard rule:

1. all translucent panels, highlights, tracks and separators are emitted in the geometry phase;
2. `microcode_constructor()` restores the text pipeline exactly once for the text phase;
3. no `fillRect()` call is allowed after the text-pass boundary.

The regression suite checks this invariant automatically.

### Density is bounded, not guessed

The layout is verified against several virtual viewport classes from the native 320x240 scale through widescreen layouts. The tests enforce:

- 4–7 visible rows;
- non-overlapping tabs;
- a dedicated label corridor;
- a minimum slider interaction span;
- separate list, context and footer regions.

Text is measured with GoldenEye's own font metrics and truncated with an ellipsis when necessary instead of drawing through neighboring controls.

## Palette

The overlay is intentionally dark and subordinate to the game:

- black / charcoal: main surface;
- ivory: primary focused text;
- muted gray: secondary text;
- GoldenEye gold (`0xEBD879FF`): active focus and thin structural accents;
- restrained red: destructive actions only.

Large beige dossier panels from V1 are intentionally removed. Paper belongs to the native file/briefing language; the Q Watch settings surface should feel like equipment.

## Out of scope

V2 does not replace GoldenEye's native file-select renderer and does not introduce a third-party runtime UI framework. Libraries such as RmlUi/RecompUI demonstrate useful separation of input and presentation, but importing a second renderer here would add build/runtime complexity and create a visual discontinuity with GoldenEye's own font and Fast3D paths.

## Validation

The branch must pass before handoff:

- Modern Controls V2 regressions;
- Modern Controls V3 randomized regressions;
- UI V1 baseline migration checks;
- V2 patch idempotence;
- PT-BR editorial copy contracts;
- layout matrix tests;
- geometry/text render-state invariant;
- `git diff --check`;
- ROM symbol generation;
- Linux GCC 13 build;
- Linux GCC 14 build;
- Windows/MSYS2 build and executable verification.

Runtime ROM/gameplay feel is still verified on a real user build after CI; CI does not contain the user's ROM.

## Research references

- Microsoft Xbox Accessibility Guidelines — UI Navigation: https://learn.microsoft.com/en-us/gaming/accessibility/xbox-accessibility-guidelines/112
- Microsoft Xbox Accessibility Guidelines — Input: https://learn.microsoft.com/en-us/xbox/accessibility/xbox-accessibility-guidelines/107
- N64Recomp/RecompFrontend: https://github.com/N64Recomp/RecompFrontend
- Perfect Dark PC port configuration variables (`MenuMouseControl`, menu-aware mouse lock): https://github.com/perfect-dark-pc-port/perfect_dark/wiki/Config-variables
