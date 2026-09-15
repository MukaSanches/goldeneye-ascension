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
- Added a Universal Controller Layer ahead of V4 using SDL2's normalized GameController path for known/XInput controllers, optional SDL_GameControllerDB mappings and a conservative fallback for otherwise-unknown generic USB gamepads.
- Added contiguous logical controller-slot packing so skipped/non-gamepad SDL devices can no longer shift a recognized controller into the wrong GoldenEye slot.
- Added controller identity diagnostics (logical slot, physical SDL device, reported name, family and GUID).
- Added runtime hot-plug/unplug/remap rescans for both SDL controller events and raw joystick add/remove events.
- Added persistent low-priority fallback mappings in `data/ascension-auto-mappings.txt` and highest-priority user corrections in `data/ascension-controller-mappings.txt`.
- Kept the accepted Modern mouse V3 direct-look, ADS, wheel and menu-routing behavior unchanged.

### PC UX

- Added `tools_pc/ascension.py` as the canonical prepare/test/controllerdb/assets/build/play entry point for the complete 0.0.4 stack.
- Added `tools_pc/update_controller_db.py` for a validated, pinned SDL_GameControllerDB developer snapshot; runtime remains fully offline-capable.
- Kept the F10 systems layer separate from GoldenEye's native Q Watch.
- Preserved the accepted native frontend mouse-pointer behavior and Q Watch capture handoff.
- Preserved the safe F10 convenience return to the mission selector as a separate path from stock Abort Mission.
- Added a port-local run-stage alias for the F10 quick-return guard so the PC overlay does not depend on an undeclared GoldenEye menu enum.

### Safety and compatibility

- Started the release branch from `checkpoint/2026-09-15-watch-fixed`; the checkpoint remains unchanged as the recovery baseline.
- Kept ROM data, save format, campaign progression, AI, collision, weapons and mission logic outside the V4 feature scope.
- Kept All Missions as a reversible frontend availability override without writing fake progression.
- Kept Classic as the safe default for new configurations.
- Preserved Classic/Hybrid gameplay routing and local-multiplayer controller behavior after physical-device normalization.
- The generic-controller fallback refuses obviously under-specified raw devices instead of blindly claiming every joystick/HID as a gamepad; unusual hardware can be corrected with an explicit user SDL mapping.
- Controller mapping priority is generated fallback < community DB < explicit user override, so heuristic guesses can never override a deliberate correction.
- Kept patchers fail-closed/idempotent and added compatibility-aware regression coverage between V3, V4 and the Universal Controller Layer.

### Validation

- Added complete release validation on Windows/MSYS2 plus Linux GCC 13 and GCC 14.
- Added retained per-platform regression reports and compiler logs.
- Added a dedicated Universal Controller Layer regression contract covering mapping-source priority, safe fallback gating, logical-slot packing, hot-plug/remap events, V4/mouse/F10 path preservation and patcher idempotence.
- The release gate covers preparation, all control/UI/watch/save-isolation regression contracts, ROM symbol generation and native compilation on all three CI targets.
- Windows CI verifies creation of `build-pc/ge007.x86_64.exe`; Linux jobs verify their native executable.
- V3 randomized direct-look and signed-wheel contracts remain active beneath the V4 extension, and V4 has its own randomized radial/gamepad and remapping contracts.
- Real-controller feel and unusual generic-device semantics remain manual release gates; 0.0.4 is a test candidate until the Windows smoke-test matrix is accepted.

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