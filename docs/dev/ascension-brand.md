# Ascension visual identity

Status: experimental, for the `0.0.x` development line.

This document defines the first visual system for Ascension. It is deliberately restrained: the goal is to make the PC build identifiable and coherent without fighting GoldenEye's original art direction, touching gameplay, or introducing proprietary replacement assets.

## Core idea

Ascension should feel like a precise PC-native layer built around the original game rather than a separate skin pasted over it. The visual language is tactical, understated and technical: dark neutrals, warm metallic accents, concise labels, strong alignment and very little decorative noise.

The canonical short signature is:

`Ascension 0.0.x`

The version is never typed independently into runtime surfaces. It comes from `port/include/ascension_version.h` so the window title, menu footer and future overlays cannot drift apart.

## Palette

These values are the reference palette for future port-owned UI. They are not a request to recolor original game assets.

| Role | Reference | Purpose |
| --- | --- | --- |
| Carbon | `#080A0C` | primary panel/background neutral |
| Warm gold | `#D2B65C` | brand accent, rules and selected emphasis |
| Ivory | `#E8E2D3` | high-priority readable text |
| Slate | `#8D9396` | secondary labels and metadata |
| Signal green | existing game green | gameplay/status information, not the primary Ascension brand color |

The palette should remain sparse. Warm gold is an accent, not a flood fill. Original GoldenEye status colors keep their existing semantic meaning.

## Typography and assets

- Reuse the game's existing text renderer and fonts for in-game Ascension labels whenever possible.
- Use the platform-native title-bar rendering for the window title.
- Do not bundle a new font merely for branding.
- Do not replace or modify Nintendo, Rare, GoldenEye, Bond, legal or copyright screens as part of Ascension branding.
- Do not add proprietary game assets to the repository.

This keeps the identity lightweight, legally cleaner and consistent with the port's existing rendering stack.

## Runtime surfaces

### 0.0.2

1. Windows/SDL title: `Ascension 0.0.2`.
2. File-select footer: the same centralized signature, rendered through the existing port-layer overlay.
3. File-select discovery affordance: `F10 CONTROL` remains visible as a compact PC-native cue.
4. First-use discovery prompt: `PRESS F10 TO CONFIGURE` appears on file select until the player opens Ascension Control once. The acknowledgement is persisted in `ge007.ini` and the stronger prompt then retires permanently.
5. F10 Ascension Control: carbon panel, restrained gold rule, gold focus marker, ivory active text and slate secondary text.
6. Categories: `DISPLAY`, `INPUT` and `GAMEPLAY` keep a growing settings surface understandable without turning it into a wall of options.
7. Real scrolling: arrow keys and mouse wheel move selection while the visible window follows it. A small gold scroll thumb shows when additional rows exist above or below.
8. Contextual help: the selected option gets one short plain-language explanation at the top of the panel.
9. Safe ranges: risky port-owned values are constrained before they can produce unusable views. Current 0.0.2 limits include FOV 70-120, frame cap OFF/30/60/90/120 and screen shake 0-3.
10. Visible feedback: live changes say `APPLIED`; delayed changes say `RESTART REQUIRED`.
11. Destructive/session actions require confirmation: `Reset PC settings` restores only Ascension PC options and never touches save data; `Restart game` saves and relaunches the current executable with the same command line.
12. Previously hidden PC options `Display FPS` and `Skip intro` remain exposed in the panel.

Branding remains outside gameplay HUD surfaces in 0.0.2. The discovery cue lives on file select, where a new player is already making a setup decision, rather than interrupting a mission.

## Settings UX principles

Ascension Control follows a few rules deliberately:

- discovery should happen inside the game, not in a README;
- the stronger onboarding message appears only until it has done its job;
- a small persistent entry-point cue remains for recall;
- option changes that can apply live should do so immediately;
- delayed changes must say so before the player leaves the menu;
- technical labels stay concise, while the selected row provides a plain-language explanation;
- settings remain keyboard- and mouse-operable;
- `Tab` moves quickly between categories while arrows and mouse wheel handle normal navigation;
- configuration is saved through the existing `ge007.ini` system rather than a parallel store;
- defaults remain conservative and preserve the port's established behaviour unless a change has been explicitly tested;
- reset and restart actions require a second activation so an accidental click cannot wipe preferences or relaunch the game.

The control panel should help a first-time player without slowing down an experienced one.

## Safe-range policy

A port setting is not considered good UX merely because the underlying variable accepts a large numeric range. Ascension exposes a narrower range when testing shows that extreme values can create broken framing, uncomfortable camera motion or timing behaviour that does not represent the intended PC experience.

For 0.0.2:

- FOV scale is exposed as 70-120 percent. Existing out-of-range values are normalized when the overlay initializes.
- Frame cap is exposed as OFF, 30, 60, 90 or 120 FPS. Values below 30 are not offered because the port's own video layer warns that they throttle the simulation.
- Screen shake is exposed as 0-3 instead of the much wider internal registration range.
- MSAA remains 1x/off, 2x, 4x or 8x and is clearly marked as restart-required.

These are UX guardrails, not changes to mission logic or game physics.

## Readability rules

- Small functional text should target strong luminance contrast; a 4.5:1 ratio is a useful minimum reference for normal-size text.
- Do not communicate a state by color alone; selection/focus uses both a darker row background and a gold position marker.
- Avoid flashing, blinking or animated branding.
- Keep the signature and settings legible at the native low-resolution game viewport before judging them at modern upscaled resolutions.
- Avoid long prose inside the panel. Context help should explain one concept in one short line.
- At lower virtual heights the menu must scroll instead of shrinking text or allowing rows to fall outside the panel.

## Accessibility direction

0.0.2 does not attempt to become a complete accessibility layer. It makes the controls already present easier to discover and understand. In particular, screen-shake intensity, FOV, mouse inversion and mouse-capture behaviour are surfaced with contextual explanations.

Future work should add accessibility features only when they can be tested as real player-facing behaviour. Do not add decorative toggles that do not materially change the experience.

## Performance notes

The FPS shown by the host title bar measures submitted/rendered frames. Some original presentation sequences can intentionally submit frames at a lower cadence than normal gameplay. A short low reading during an intro is therefore not, by itself, proof of a GPU performance regression. Ascension must not hide or fabricate the measured value; performance work should change code only after a reproducible gameplay bottleneck is identified.

## Versioning

Ascension uses `MAJOR.MINOR.PATCH` notation. While the project is in the `0.y.z` range, it is explicitly an initial-development line and may change quickly. Runtime branding must always read its version from the central header.

For the current exploratory cadence:

- patch increments (`0.0.x`) identify small, testable development milestones;
- a future `0.1.0` should represent a coherent feature set rather than a cosmetic-only bump;
- `1.0.0` is reserved for a stable, distributable Ascension release with a documented compatibility contract.

## Engineering guardrails

- Prefer port-layer additions over invasive edits to original game logic.
- Branding and UX changes must be reversible and individually testable.
- Do not modify ROM bytes for branding.
- Do not alter save format, AI, physics, mission scripts or level data as a side effect of visual work.
- Keep each milestone small enough that a failed playtest has an obvious rollback point.
- Preserve upstream coding style and keep Ascension-specific constants centralized.
- A new setting must either reuse the existing config system or justify why it cannot.
- Do not mask an observed FPS value or a visual fault just to make a build look healthier; diagnose the cause first.

The objective is not to make every screen say Ascension. The objective is to make every Ascension-owned surface look and behave deliberately.
