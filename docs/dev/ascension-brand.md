# Ascension visual identity

Status: experimental, for the `0.0.x` development line.

This document defines the first visual system for Ascension. It is deliberately restrained: the goal is to make the PC build identifiable and coherent without fighting GoldenEye's original art direction, touching gameplay, or introducing proprietary replacement assets.

## Core idea

Ascension should feel like a precise PC-native layer built around the original game rather than a separate skin pasted over it. The visual language is tactical, understated and technical: dark neutrals, warm metallic accents, concise labels, strong alignment and very little decorative noise.

The canonical short signature is:

`Ascension // 0.0.x`

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

1. Windows/SDL title: `Ascension // 0.0.2`.
2. File-select footer: the same centralized signature, rendered through the existing port-layer overlay.

### Next safe surfaces

1. F10 options header and version metadata.
2. A restrained accent rule or small brand mark on port-owned menus only.
3. Language selector and localized port-owned UI strings.
4. Optional accessibility/readability settings.

Branding should remain outside gameplay unless a future HUD redesign is explicitly being tested.

## Readability rules

- Small functional text should target strong luminance contrast; a 4.5:1 ratio is a useful minimum reference for normal-size text.
- Do not communicate a state by color alone; selection/focus should also have a shape, position or text cue.
- Avoid flashing, blinking or animated branding.
- Keep the signature clear at the native low-resolution game viewport before judging it at modern upscaled resolutions.

## Versioning

Ascension uses `MAJOR.MINOR.PATCH` notation. While the project is in the `0.y.z` range, it is explicitly an initial-development line and may change quickly. Runtime branding must always read its version from the central header.

For the current exploratory cadence:

- patch increments (`0.0.x`) identify small, testable development milestones;
- a future `0.1.0` should represent a coherent feature set rather than a cosmetic-only bump;
- `1.0.0` is reserved for a stable, distributable Ascension release with a documented compatibility contract.

## Engineering guardrails

- Prefer port-layer additions over invasive edits to original game logic.
- Branding changes must be reversible and individually testable.
- Do not modify ROM bytes for branding.
- Do not alter save format, AI, physics, mission scripts or level data as a side effect of visual work.
- Keep each visual milestone small enough that a failed playtest has an obvious rollback point.
- Preserve upstream coding style and keep Ascension-specific constants centralized.

The objective is not to make every screen say Ascension. The objective is to make every Ascension-owned surface look deliberate.
