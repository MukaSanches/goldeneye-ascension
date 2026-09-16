# Ascension recovery playbook

This is the practical repair manual for the 2026-09-15 playable Ascension checkpoint.

Use it when a later experiment breaks controls, mouse capture, menus, the Q Watch, F10, campaign availability, localization, or frontend transitions.

The guiding rule is: **diagnose transitions first, then subsystems, then rendering.** Many Ascension bugs are not constant-state bugs; they happen when switching between gameplay, watch, F10, and frontend modes.

---

## 1. First response to any regression

Do not immediately rewrite the affected C file.

Start with:

```bash
git status --short
git branch --show-current
git log -1 --oneline
```

Record:

- current branch;
- current commit;
- whether the working tree already contains generated patch output;
- the exact action sequence that triggers the bug;
- whether the bug happens from a clean launch or only after a mode transition.

If local changes matter, preserve them before switching branches. Prefer a normal commit or:

```bash
git stash push -u -m "preserve-before-ascension-debug"
```

Do not make `git reset --hard`, `git clean -fd`, or mass `git restore` the first repair step.

---

## 2. Known-good runtime checkpoint

The runtime state accepted manually as very good is based on:

```text
682c543efe0fbfb46967504558204331c9f864ee
```

The saved checkpoint branch created from the fully documented state is named:

```text
checkpoint/2026-09-15-watch-fixed
```

The exact runtime code before documentation-only follow-up is identified in `docs/checkpoints/2026-09-15-watch-fixed.md`.

When debugging a later regression, compare the affected files and patchers against this checkpoint before trying a new architecture.

---

## 3. Canonical rebuild from a clean compatible checkout

Apply the stack in this exact order:

```bash
python tools_pc/apply_modern_controls_v2.py --no-backup
python tools_pc/apply_modern_controls_v3.py --no-backup
python tools_pc/apply_modern_menu_guard.py
python tools_pc/apply_ui_overhaul_v1.py
python tools_pc/fix_ui_overhaul_text_state.py
python tools_pc/install_ui_overhaul_v2.py --no-backup
python tools_pc/apply_persistent_f10_hint.py --no-backup
python tools_pc/apply_unlock_all_missions.py --no-backup
python tools_pc/apply_watch_ui_final_safe.py --no-backup
python tools_pc/apply_watch_runtime_fix.py --no-backup
python tools_pc/apply_watch_runtime_fix.py --check
```

Run all contracts:

```bash
python tools_pc/test_modern_controls_v2.py
python tools_pc/test_modern_controls_v3.py
python tools_pc/test_ui_overhaul_v1.py
python tools_pc/test_ui_overhaul_v2.py
python tools_pc/test_persistent_f10_hint.py
python tools_pc/test_unlock_all_missions.py
python tools_pc/test_watch_ui_final.py
python tools_pc/test_watch_runtime_fix.py
git diff --check
```

Then:

```bash
python scripts/gen_romassets.py u
./build-pc.sh ntsc-final
```

---

## 4. Symptom map

### Symptom: mouse works in gameplay, then dies after opening/closing the Q Watch

Most likely cause: Escape/Cancel reached the SDL shell and `inputReleaseCapture()` cleared gameplay capture while GoldenEye was closing the watch.

Inspect:

- `port/src/video.c`
- `port/include/ascension_watch.h`
- generated bridge in `src/game/options.c`
- `tools_pc/apply_watch_runtime_fix.py`
- `tools_pc/test_watch_runtime_fix.py`

Required logic order:

```text
ESC
 -> F10 open? close F10
 -> native watch active? leave capture alone
 -> otherwise release capture
```

The watch check must occur before `inputReleaseCapture()`.

Do not "fix" this by always forcing mouse capture after every Escape. That would make frontend/free-cursor behavior wrong.

---

### Symptom: mouse stops controlling native menus; only WASD/arrows work

Likely cause: the Modern menu guard disabled the whole mouse block instead of only clearing gameplay-look residue.

Inspect generated `port/src/input.c` and `tools_pc/apply_modern_menu_guard.py`.

Bad pattern:

```c
if (mouseEnabled && !(menuMode && ascensionControlsIsModern())) {
```

The outer mouse path should remain available. Menu mode should route into the native/absolute pointer branch, while direct gameplay look is naturally bypassed.

Regression tests protecting this behavior are in `test_ui_overhaul_v1.py`.

---

### Symptom: menu pointer moves but cannot reach the right/bottom edge

Likely cause: stale hard-coded 320x240 assumptions in the menu pointer estimator while GoldenEye's frontend virtual field is wider/taller.

Inspect:

- `getPlayer_c_screenwidth()`
- `getPlayer_c_screenheight()`
- `getPlayer_c_screenleft()`
- `getPlayer_c_screentop()`
- `cursor_h_pos`
- `cursor_v_pos`

The absolute pointer path should map the OS cursor into the live frontend cursor rectangle. The relative fallback estimator must use the same live bounds.

Do not fix only the target clamp while leaving the estimator clamped to an older rectangle; that creates drift and unreachable edges.

---

### Symptom: mouse feels good in menus but camera no longer moves in gameplay

Check whether the runtime is incorrectly stuck in `menuMode`, whether capture is armed/grabbed, and whether V3 direct look is still installed in `src/game/bondview2.c`.

Inspect:

- `current_menu`
- `GE_MENU_RUN_STAGE` / native `MENU_RUN_STAGE` semantics
- `mouseGrabbed`
- `captureArmed`
- V3 direct-look hook markers

Run:

```bash
python tools_pc/test_modern_controls_v3.py
```

If the test passes but gameplay still fails only after a transition, suspect capture/state routing before changing sensitivity math.

---

### Symptom: vertical mouse look is inverted after a merge

GoldenEye's native vertical convention is opposite normal desktop-mouse expectations.

The checkpoint fixed the sign at the direct-look bridge. Inspect the V3 camera hook in `src/game/bondview2.c` before globally negating `mouseDY` in `input.c`.

A global sign flip can simultaneously break:

- aim-mode pitch;
- hipfire digital pitch;
- menu pointer Y.

Run `test_modern_controls_v3.py`; its randomized direct-look cases include pitch-sign coverage.

---

### Symptom: weapon wheel skips, reverses, or fires multiple changes unexpectedly

Inspect Modern Controls V3 wheel queue logic and signed-wheel tests.

The wheel is transition/edge sensitive. Avoid reducing it to a single persistent boolean. The test suite includes randomized signed wheel streams specifically because ordering and direction were fragile.

Run:

```bash
python tools_pc/test_modern_controls_v3.py
```

---

### Symptom: Q Watch list scrolls several items from one W/S press

The native watch contains a fast-scroll path designed around N64 analog-stick levels. Digital PC input can sit at full stick deflection and trigger that path every frame.

The PORT checkpoint disables only the raw sustained fast-scroll terms:

```text
GE_WATCH_STICK_FASTUP
GE_WATCH_STICK_FASTDOWN
```

while retaining normal latched watch navigation.

Inspect `src/game/options.c` generated final-watch state before changing keyboard repeat globally.

---

### Symptom: closing the Q Watch needs an extra mouse click before looking again

Treat this as a capture regression even if mouse motion eventually works after clicking.

Check:

- whether `captureArmed` was cleared;
- whether `ascensionWatchIsActive()` correctly detects any non-closed watch animation state;
- whether Escape is releasing capture during watch ownership.

The desired checkpoint behavior is immediate gameplay mouse response after closing the watch.

---

### Symptom: F10 "Return to main menu" restarts the current mission

This is a semantic routing failure.

The F10 convenience action must not reuse the stock Q Watch Abort Mission path and must not call `sysRestart()`.

The checkpoint route is:

```c
set_missionstate(MISSION_STATE_0);
mission_failed_or_aborted = FALSE;
frontChangeMenu(MENU_MISSION_SELECT, FALSE);
bossRunTitleStage();
```

with a solo-only guard and watch selection cleanup.

Run:

```bash
python tools_pc/test_watch_ui_final.py
python tools_pc/test_watch_runtime_fix.py
```

---

### Symptom: returning to menu removes or corrupts the selected save/profile

Immediately inspect the convenience-return block for accidental reuse of:

```c
deleteCurrentSelectedFolder();
```

That call belongs to the stock Abort Mission helper in this codebase and must not appear in the F10 convenience return.

Also check that no new `fileWriteSave`, unlock, or progression-write call was introduced as a shortcut.

---

### Symptom: normal Q Watch Abort Mission no longer behaves like GoldenEye

A previous convenience-return fix may have overwritten the stock abort semantics.

Checkpoint rule: keep two separate transitions.

Stock abort retains:

```c
mission_failed_or_aborted = TRUE;
deleteCurrentSelectedFolder();
```

F10 convenience return retains:

```c
mission_failed_or_aborted = FALSE;
frontChangeMenu(MENU_MISSION_SELECT, FALSE);
```

Do not deduplicate these into one helper unless the differing semantics are preserved explicitly.

---

### Symptom: F10 opens, but text/rectangles corrupt each other visually

Inspect `tools_pc/fix_ui_overhaul_text_state.py` and the resulting `port/src/optionsoverlay.c`.

The Q Branch overlay uses Fast3D stateful rendering. Text setup and rectangle primitives must not leak rendering state into each other.

Run:

```bash
python tools_pc/test_ui_overhaul_v2.py
```

If visual corruption remains with contracts passing, capture a screenshot and inspect render-state ordering rather than changing layout dimensions first.

---

### Symptom: F10 mouse clicks hit the wrong row or department

Inspect absolute mouse coordinate conversion, current page/department filtering, row hit-testing, and slider drag state.

The current overlay intentionally scopes hit-testing to the visible page/category. Hidden rows should never receive mouse focus.

Run both UI tests.

---

### Symptom: All Missions permanently unlocks campaign progress

This is a critical save-isolation violation.

The feature must only override solo frontend availability. It must not call:

- `fileWriteSave`
- `fileUnlockStageInFolderAtDifficulty`
- `fileSetDifficultyStageTime`
- `fileSetSaveCheatUnlocked`
- `joyGamePakLongWrite`

Run:

```bash
python tools_pc/test_unlock_all_missions.py
```

If the test fails, stop before playing on an important save.

---

### Symptom: disabling All Missions does not restore native campaign gating

Check:

- config value is actually off;
- frontend availability override is narrow and reversible;
- no progression write occurred earlier;
- the frontend has been re-entered/refreshed.

Do not "repair" this by editing the save to lock missions again; fix the policy layer first.

---

### Symptom: PT-BR text disappears or falls back to English

Inspect `port/src/ascension_locale.c` generated state and the patcher that owns the missing string.

Keep internal config keys stable. Visible labels/help can change without changing stored key names.

Relevant tests:

- `test_ui_overhaul_v2.py`
- `test_persistent_f10_hint.py`
- `test_unlock_all_missions.py`
- `test_watch_ui_final.py`

---

### Symptom: patcher says `expected exactly one anchor, found 0`

Do not loosen every anchor immediately.

Possible causes:

1. wrong stack order;
2. already-installed newer state;
3. upstream changed whitespace/source shape;
4. another patch already replaced the intended block;
5. wrong branch/base revision.

The preferred repair is to teach the patcher's safe layer to recognize both the old and new semantic state, then add an idempotence regression test.

---

### Symptom: patcher says `found 2` or more

Stop. Do not choose the first occurrence blindly.

Multiple anchors usually mean duplicated generated code or a pattern that became too broad. Inspect both blocks and tighten the semantic boundary.

---

### Symptom: GitHub Actions passes every Python test but job is red at `git diff --check`

On Windows/MSYS2, bare `git` may not exist in the shell PATH even though checkout used Git for Windows.

Use:

```bash
"/c/Program Files/Git/bin/git.exe" diff --check
```

This exact issue occurred at the runtime checkpoint: all Ascension controls/UI/watch contracts passed, then the job exited 127 because `git` was not found.

---

### Symptom: local branch switch is blocked by modified generated files

Do not discard them blindly.

First:

```bash
git status --short
```

If they are generated integration output you may still want to preserve the exact tested local state. Use a stash or local commit before switching.

Never instruct an interactive user to paste a block containing `exit` merely to stop on a dirty tree; it can close their MSYS2 terminal.

---

## 5. Debugging by state transition

For input/UI bugs, reproduce using minimal transition pairs:

```text
frontend -> gameplay
gameplay -> Q Watch
Q Watch -> gameplay
gameplay -> F10
F10 -> gameplay
gameplay -> frontend
frontend -> gameplay again
window focus lost -> focus gained
captured mouse -> released mouse -> captured mouse
```

If a bug appears only on one transition, inspect the ownership handoff between the two modes rather than the entire input stack.

Examples:

- Q Watch -> gameplay dead mouse = capture handoff.
- gameplay -> frontend camera-like pointer = menu routing handoff.
- frontend -> gameplay pointer remains free = capture re-arm handoff.
- F10 -> gameplay stale delta = transient mouse accumulator/reset handoff.

---

## 6. Manual regression matrix

Before promoting a future controls/UI/watch change, test at least:

| Area | Test |
|---|---|
| Gameplay | walk/strafe, yaw, pitch, aim, fire, action, cancel/reload, crouch |
| Mouse | slow movement, fast flick, stop movement, raw/smoothing option if changed |
| Wheel | up/down repeated and alternating |
| Q Watch | open, change page, inventory navigation, close, immediate mouse-look |
| F10 | open/close from gameplay, mouse navigation, keyboard navigation, sliders |
| Frontend | pointer reaches corners, LMB select, RMB back |
| Transition | mission -> watch -> mission -> F10 -> mission -> frontend -> mission |
| Return | F10 return reaches native mission selector, not restart |
| Save safety | selected folder remains available after convenience return |
| Abort | stock watch Abort Mission still follows stock behavior |
| Campaign | All Missions on/off is reversible |
| Localization | PT-BR labels/help remain readable and correctly scoped |
| Window | alt-tab/focus loss/focus gain does not permanently kill controls |

---

## 7. What not to combine

Several systems look similar but must stay distinct:

- native Q Watch vs F10 PC overlay;
- stock Abort Mission vs F10 convenience return;
- gameplay relative mouse vs frontend absolute pointer;
- campaign availability override vs save progression;
- config persistence vs game save writes;
- UI styling vs native game-state mutation.

Most severe regressions so far came from crossing one of these boundaries.

---

## 8. Safe future change pattern

For any substantial change:

1. identify the owning subsystem;
2. modify the patcher, not only generated output;
3. keep the patch fail-closed;
4. add/strengthen a contract test;
5. run idempotence;
6. run adjacent subsystem tests;
7. compile Windows;
8. perform the relevant transition smoke tests;
9. only then update the checkpoint documentation if behavior is intentionally superseded.

This keeps Ascension experimental without making it fragile.
