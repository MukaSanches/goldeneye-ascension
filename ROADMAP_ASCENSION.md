# Ascension roadmap

This roadmap describes direction, not promises. A feature moves to completed only after implementation and appropriate validation.

## Foundation — current

- Maintain reversible, coherent commits on `main`.
- Preserve a known-good rollback branch before major migrations.
- Recover Ascension-owned work from historical development branches onto the current codebase without discarding newer fixes.
- Keep provenance and licensing explicit.

## Localization

- Rebase/reintegrate the existing Ascension PT-BR localization architecture onto the current main line.
- Preserve English as a reliable fallback.
- Validate accented glyphs, encoding, wrapping and layout.
- Expand mission/UI coverage with human editorial QA.
- Keep graphical-text replacement separate until its asset pipeline is safe and visually validated.

## Controls and PC experience

- Consolidate existing PC input improvements.
- Classic / Modern / Custom control presets.
- Gamepad rebinding and configurable deadzones.
- Independent mouse axes and aim-specific tuning where technically justified.
- Discoverable in-game settings using the existing configuration system.

## Presentation and accessibility

- Optional modern presentation layer.
- Widescreen/HUD behavior based on reproducible tests.
- FOV and visual settings with safe ranges.
- Accessibility options that materially change player experience and are testable.

## Stability

- Campaign-wide regression matrix.
- Deterministic/headless tests where possible.
- Human playtest gates for rendering, audio and input feel.
- Document negative findings so failed approaches are not repeated.

## Creator platform — long term

- Stable mod manifest and loading model.
- Localization packs.
- Mission/creator SDK research.
- Community content tooling.
- Semantic input/state interfaces suitable for tools and mods.

## Release principle

`1.0.0` is reserved for a stable, distributable Ascension release with documented compatibility, tested core campaign behavior, clear installation/build instructions, provenance and rollback expectations.
