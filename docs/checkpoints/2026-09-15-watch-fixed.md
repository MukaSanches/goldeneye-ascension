# Ascension checkpoint — 2026-09-15 — playable Q Watch / mouse / frontend return

This document records the first Ascension state explicitly accepted in manual play as **very good** after the Q Watch runtime fixes.

It is a recovery checkpoint, not a marketing release. Its purpose is to make this exact state understandable and reproducible months later, even if later experiments break controls, menus, the watch, the F10 layer, or the frontend transition.

## Identity

- Working branch at the time of the runtime acceptance: `ascension-watch-final-v1`
- Runtime checkpoint commit before documentation/CI-only follow-up: `682c543efe0fbfb46967504558204331c9f864ee`
- Runtime checkpoint commit message: `fix(watch): make capture guard contract idempotent`
- Date: 2026-09-15
- Target: Windows native PC port, NTSC final build
- Executable: `build-pc/ge007.x86_64.exe`
- Build command: `./build-pc.sh ntsc-final`

The documentation commits that follow this checkpoint do not intentionally change gameplay/runtime behavior. The Windows workflow was also corrected after the runtime checkpoint so that its final `diff --check` uses the explicit Git-for-Windows binary inside the MSYS2 runner.

## What was manually accepted

The project owner reported the game as **very good** after the latest Q Watch fixes. The important behaviors at this checkpoint are:

1. Modern mouse controls feel substantially better than the original port behavior.
2. Direct mouse camera look works during gameplay.
3. Opening the native GoldenEye Q Watch and returning to gameplay must not leave mouse-look dead.
4. The F10 systems layer remains separate from GoldenEye's native Q Watch.
5. `F10 -> Gameplay -> Return to main menu` is a convenience transition, not GoldenEye's stock `Abort Mission` action.
6. The convenience return must not restart the mission, must not call `sysRestart()`, and must not clear the selected save folder.
7. The normal GoldenEye stock `Abort Mission` behavior remains isolated and unchanged in intent.
8. Native menu pointer behavior remains available with the mouse; gameplay keeps direct mouse look.
9. PT-BR UI copy and the Q Watch identity remain installed.
10. The optional `All Missions` frontend override is reversible and must not write fake campaign progression into saves.

## Important distinction: repository source vs installed generated source

A large part of Ascension is intentionally integrated through fail-closed Python patchers in `tools_pc/` rather than by permanently rewriting every upstream-derived C source file in the branch.

That means the repository branch can look relatively close to the upstream/decomp source while CI and local builds apply the Ascension stack in a strict order before compiling.

**Do not assume a source marker is missing from the project just because it is not present in a pristine checkout before the patchers run.**

The authoritative install order for this checkpoint is:

```text
apply_modern_controls_v2.py
apply_modern_controls_v3.py
apply_modern_menu_guard.py
apply_ui_overhaul_v1.py
fix_ui_overhaul_text_state.py
install_ui_overhaul_v2.py
apply_persistent_f10_hint.py
apply_unlock_all_missions.py
apply_watch_ui_final_safe.py
apply_watch_runtime_fix.py
```

See `docs/ascension-patch-stack.md` for ownership, order, and failure modes.

## Exact local reproduction sequence

From the repository root in **MSYS2 MINGW64**:

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

python tools_pc/test_modern_controls_v2.py
python tools_pc/test_modern_controls_v3.py
python tools_pc/test_ui_overhaul_v1.py
python tools_pc/test_ui_overhaul_v2.py
python tools_pc/test_persistent_f10_hint.py
python tools_pc/test_unlock_all_missions.py
python tools_pc/test_watch_ui_final.py
python tools_pc/test_watch_runtime_fix.py

git diff --check
python scripts/gen_romassets.py u
./build-pc.sh ntsc-final
```

Then run:

```bash
./build-pc/ge007.x86_64.exe
```

The runtime hotfix preflight should report:

```text
Ascension Watch Runtime Fix preflight: PASS
Q Watch Escape preserves mouse capture: PASS
Quick return targets native mission selector: PASS
Quick return avoids stock Abort Mission save-clear path: PASS
Would update: nothing
```

## Manual smoke test for this checkpoint

Always test the following before calling a later revision equivalent to this checkpoint:

- Start a solo mission and verify mouse yaw/pitch.
- Fire, aim, use/action, reload/cancel, crouch, weapon wheel, movement and strafe.
- Open the Q Watch, navigate at least two watch pages, close it with the normal GoldenEye cancel path, and immediately move the mouse. Mouse-look must still work without an extra recovery click.
- Open F10 during gameplay and close it; gameplay mouse-look must resume.
- Open a normal frontend screen and verify the mouse behaves as a menu pointer rather than camera input.
- Verify LMB selects and RMB backs out in native menus.
- Use `F10 -> Gameplay -> Return to main menu`, confirm it, and verify that the game reaches the normal mission selector instead of restarting the mission.
- Reopen the current save/profile and verify the selected folder still exists.
- Verify stock Q Watch `Abort Mission` still behaves as a stock abort, separately from the F10 convenience return.
- Toggle `All Missions` on/off and verify it changes frontend availability without permanently writing completion state.
- Run at least one mission after toggling settings to catch stale input/capture state.

## Non-negotiable invariants

When repairing future regressions, preserve these invariants unless a deliberate redesign is being made:

- Gameplay mouse-look and frontend mouse-pointer routing are separate modes.
- Q Watch `Escape/Cancel` must not accidentally disarm PC mouse capture.
- The stock `Abort Mission` path and the F10 convenience return are different operations.
- The F10 convenience return must not call `deleteCurrentSelectedFolder()`.
- The F10 convenience return must not call `sysRestart()`.
- The F10 convenience return must not set `mission_failed_or_aborted = TRUE`.
- The F10 convenience return remains solo-only.
- `frontChangeMenu(MENU_MISSION_SELECT, FALSE)` is the intended native frontend target for the convenience return at this checkpoint.
- `bossRunTitleStage()` is still used to ask the boss loop to load the frontend/title stage.
- The native Q Watch identity remains present; F10 is a PC systems layer, not a replacement for the watch.
- Ascension patchers should be idempotent or fail closed; they must never silently perform a best-effort destructive rewrite.
- Save/progression changes must be explicit. UI convenience features should not counterfeit campaign progress.

## Known CI note at the moment this checkpoint was recorded

The Windows watch workflow successfully applied the full Ascension stack and all control/UI/watch runtime contract tests passed, including the randomized Modern Controls V3 tests. The job then failed at the final `git diff --check` because the MSYS2 shell could not find `git` in PATH.

That was an infrastructure/path failure, not a gameplay-contract failure. The workflow was subsequently changed to call:

```bash
"/c/Program Files/Git/bin/git.exe" diff --check
```

Do not interpret the older red workflow badge at commit `682c543...` as evidence that the runtime contracts failed; the logs show the test suite reached `ALL PASS` before the missing-Git error.

## Recovery rule

If a later branch becomes badly broken, do not use destructive cleanup first. Preserve the work, compare against this checkpoint, and restore behavior subsystem by subsystem.

Preferred recovery sequence:

1. `git status --short`
2. preserve uncommitted work with a normal commit or `git stash push -u -m "..."` if needed
3. fetch origin
4. compare the broken branch with the saved checkpoint branch
5. inspect only the affected subsystem and its patcher/test pair
6. re-run the patch stack and contract tests
7. rebuild
8. repeat the manual smoke test above

Never use `git reset --hard`, `git clean -fd`, or an equivalent destructive command as the default repair procedure.

## Companion documentation

- `docs/ascension-patch-stack.md` — exact stack order and ownership map.
- `docs/ascension-recovery-playbook.md` — symptom-driven repair manual.
- `docs/ascension-ui-art-bible.md` — visual identity and GoldenEye/1995 espionage art direction.

This checkpoint exists specifically so that later experimentation can be aggressive without losing the first version the project owner explicitly described as working very well.
