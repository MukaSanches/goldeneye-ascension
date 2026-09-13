# Ascension visual identity

Status: active development identity.

Ascension is the project's independent development line. It preserves proper attribution and license history while making its own product, UX, localization, input, accessibility, tooling and release decisions.

## Core idea

Ascension should feel like a precise PC-native layer built around the original game rather than a skin pasted over it. The visual language is tactical, understated and technical: dark neutrals, warm metallic accents, concise labels, strong alignment and little decorative noise.

The canonical short signature is `Ascension` plus the centralized project version.

## Palette

| Role | Reference | Purpose |
| --- | --- | --- |
| Carbon | `#080A0C` | primary panel/background neutral |
| Warm gold | `#D2B65C` | brand accent and selected emphasis |
| Ivory | `#E8E2D3` | high-priority readable text |
| Slate | `#8D9396` | secondary labels and metadata |
| Signal green | existing game green | gameplay/status information |

Warm gold is an accent, not a flood fill. Original game status colors retain their semantic meaning.

## Product rules

- Do not replace Nintendo, Rare, GoldenEye, Bond, legal or copyright screens merely for branding.
- Do not add proprietary ROM or game assets to the repository.
- Prefer port-owned surfaces for Ascension UI.
- Keep original/classic behavior available where practical.
- Ascension-owned features must be independently reversible.
- Runtime version strings should come from one centralized version source.
- Configuration should extend the existing PC configuration path unless there is a documented reason not to.

## Engineering guardrails

- Prefer port-layer additions over invasive edits to original game logic.
- Branding and UX changes must be reversible and individually testable.
- Do not modify ROM bytes for branding.
- Do not alter save format, AI, physics, mission scripts or level data as a side effect of visual work.
- Keep milestones small enough that a failed playtest has an obvious rollback point.
- Preserve attribution for inherited work even when Ascension later diverges architecturally.
- Never hide a visual, input or performance fault merely to make a build look healthier.

## Independence model

Ascension does not treat any external PC port as a branch that must be mirrored. External projects are engineering references. Candidate changes are reviewed for provenance, license, compatibility, regression risk and test evidence before being independently adopted.

The objective is not to make every screen say Ascension. The objective is to make every Ascension-owned surface look and behave deliberately.
