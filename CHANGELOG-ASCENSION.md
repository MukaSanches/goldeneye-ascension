# Ascension changelog

This file tracks Ascension-specific work layered on top of the GoldenEye PC port. It intentionally does not duplicate the upstream project's full history.

## Unreleased

### Controls

- Added Classic / Hybrid / Modern control presets.
- Kept Classic as the default for new configurations.
- Preserved previously saved control-preset choices.
- Added dedicated crouch support for Ascension presets while keeping Classic behavior unchanged.
- Added an in-game F10 control-preset selector.

### PC UX

- Added conservative F10 input/display quality-of-life options.
- Added conventional fullscreen shortcuts.
- Added screenshot organization and subtle overlay/front-end polish.
- Added conservative PC-oriented FOV, mouse and gamepad presets.

### Safety and validation

- Added an Ascension smoke-test checklist covering Classic / Hybrid / Modern behavior and preset persistence.
- Added a reversible low-risk patcher manifest with preflight validation.
- Added a safe test runner with dependency checks before patch application.
- Added `tools_pc/verify_ascension_contracts.py` for ROM-free static contract checks.
- Added a written compatibility contract covering ROM requirements, saves, Classic behavior, PT-BR preservation and repository hygiene.
- Ignored local `*.ascension-before-*` patcher backups so they cannot accidentally pollute commits.

### GitHub and contributor UX

- Improved bug reports with Ascension control-preset and Classic-reproduction fields.
- Expanded pull-request verification for controls and save compatibility.
- Updated issue guidance to reflect the current Ascension development phase.

## Versioning policy

Until the first stable Ascension release is cut, changes remain under **Unreleased**. When a release is prepared, move the relevant entries into a dated `## vX.Y.Z — YYYY-MM-DD` section and keep only pending work under Unreleased.

Gameplay-affecting entries should say whether they are **Classic-safe**, **opt-in**, or require a migration. Save-format changes must never be hidden inside a generic changelog entry.
