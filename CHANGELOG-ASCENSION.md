# Ascension changelog

This file tracks Ascension-specific work layered on top of the GoldenEye PC port. It intentionally does not duplicate the upstream project's full history.

## Unreleased

Pending work after the 0.0.4 test candidate belongs here.

## v0.0.4 — 2026-09-15 — test candidate

### Controls

- Added an opt-in Modern controller-0 twin-stick path while preserving Classic and Hybrid behavior.
- Added radial analog-stick deadzone processing with full-range rescaling after the deadzone.
- Added Linear and Precision response curves for Modern gamepad look.
- Added independent Modern gamepad look sensitivity and ADS sensitivity scale.
- Added independent Modern gamepad X/Y inversion.
- Added Southpaw stick layout and an optional LT/RT fire-aim swap.
- Routed Modern left-stick movement through GoldenEye's existing native analog strafe/walk channels instead of inventing a second movement model.
- Routed Modern right-stick look through the existing PORT camera bridge with frame-scaled application.
- Added live keyboard rebinding to the F10 Controls page using the existing `Input.Bind.*` configuration buffers.
- Added live Modern gamepad button rebinding for action, cancel/reload, crouch, next/previous weapon, alternate action and start/pause.
- Kept the accepted Modern mouse V3 direct-look, ADS, wheel and menu-routing behavior unchanged.

### PC UX

- Added `tools_pc/ascension.py` as the canonical prepare/test/assets/build entry point for the complete 0.0.4 stack.
- Kept the F10 systems layer separate from GoldenEye's native Q Watch.
- Preserved the accepted native frontend mouse-pointer behavior and Q Watch capture handoff.
- Preserved the safe F10 convenience return to the mission selector as a separate path from stock Abort Mission.
- Added a port-local run-stage alias for the F10 quick-return guard so the PC overlay does not depend on an undeclared GoldenEye menu enum.

### Safety and compatibility

- Started the release branch from `checkpoint/2026-09-15-watch-fixed`; the checkpoint remains unchanged as the recovery baseline.
- Kept ROM data, save format, campaign progression, AI, collision, weapons and mission logic outside the V4 feature scope.
- Kept All Missions as a reversible frontend availability override without writing fake progression.
- Kept Classic as the safe default for new configurations.
- Preserved Classic/Hybrid controller routing and local-multiplayer controller behavior outside the Modern player-1 path.
- Kept patchers fail-closed/idempotent and added compatibility-aware regression coverage between V3 and V4.

### Validation

- Added complete release validation on Windows/MSYS2 plus Linux GCC 13 and GCC 14.
- Added retained per-platform regression reports and compiler logs.
- The complete stack passes preparation, all control/UI/watch/save-isolation regression contracts, ROM symbol generation and native compilation on all three CI targets.
- Windows CI verifies creation of `build-pc/ge007.x86_64.exe`; Linux jobs verify their native executable.
- V3 randomized direct-look and signed-wheel contracts remain active beneath the V4 extension, and V4 has its own randomized radial/gamepad and remapping contracts.
- Real-controller feel remains a manual release gate; 0.0.4 is a test candidate until the Windows smoke-test matrix is accepted.

## Earlier Ascension controls foundation

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

Until the first stable Ascension release is cut, pre-1.0 releases may remain explicitly marked as test candidates while manual runtime acceptance is outstanding. A code-complete candidate must not be described as validated merely because it compiles.

Gameplay-affecting entries should say whether they are **Classic-safe**, **opt-in**, or require a migration. Save-format changes must never be hidden inside a generic changelog entry.
