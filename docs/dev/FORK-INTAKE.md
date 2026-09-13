# Fork engineering intake map

> Fork-maintainer research note. This file records candidates for review; it does **not** claim that a feature is present in this fork until it has been integrated and verified here.

Last reviewed: 2026-09-12

## Purpose

Keep ecosystem research actionable without mixing unverified functional changes into `main`. Each item is classified as **REUSE**, **ADAPT**, **LEARN**, or **AVOID**. Functional work still requires a dedicated branch, build/test evidence, and human playtest where visual/audio/input feel is involved.

## Immediate upstream intake

This fork currently shares base commit `3c87c1e` with upstream and should review the post-base upstream series before starting overlapping input/renderer work.

| Area | Upstream evidence | Classification | Fork action |
|---|---|---|---|
| Directional mouse-wheel weapon cycling | upstream `65b07c0` / PR #54; port-only input change, user-verified after timing fix | REUSE | Bring with upstream sync; re-run build and live cycling test locally. |
| Keyboard rebinding / PC QoL settings | merged upstream work in the post-base series | REUSE | Prefer upstream implementation over a fork-specific duplicate; verify defaults and config migration. |
| 16-bit texture byte order / fire particles | upstream `d52509c`; scoped to `PORT_PIXEL16`, with RGBA32 explicitly left unchanged | REUSE | Integrate only with its surrounding importer changes; verify fire plus unaffected HUD/muzzle-flash textures. |
| Renderer trivial reject with `w < 0` | upstream `4c7a039`; mechanism build-verified and later visually reported fixed | REUSE | Include through reviewed upstream sync; retain visual doorway/near-camera regression test. |
| Mouse frame/poll-rate decoupling | upstream PR #62 was still awaiting human feel testing when reviewed | ADAPT | Do not cherry-pick as “done”; track upstream result and require A/B playtest at multiple frame/poll rates. |
| Self-hosted Windows CI | upstream `96f59f7`, `e35aeed`; assumes maintainer-specific runner/ROM seed | AVOID | Do not inherit runner labels or ROM-cache assumptions. Keep fork CI on portable GitHub-hosted runners unless infrastructure is deliberately provisioned. |

## Modern Controls map

The port already has SDL2 keyboard/mouse/controller input in `port/`. Prefer extending that layer rather than adding another input framework.

### Safe/near-term candidates

- Preserve SDL2 as the input backend.
- Consume upstream keyboard rebinding instead of reimplementing it.
- Consume the upstream directional wheel fix instead of creating a parallel inventory path.
- Add configuration through the existing config/INI architecture where practical.
- Investigate configurable controller deadzones, independent X/Y sensitivity, aim sensitivity, controller rebinding, and per-player bindings as separate testable changes.
- Keep original/default behavior available; optional modern behavior must not silently change classic defaults.

### Required validation for input changes

1. Clean Windows build.
2. Keyboard + mouse live test.
3. SDL controller live test.
4. Aim-mode and normal-turn behavior.
5. Weapon cycling while aiming and not aiming.
6. Menus, pause/watch, cutscenes, and multiplayer input routing.
7. Low/high frame-rate and mouse-poll-rate A/B where timing is involved.

Input “feel” is not considered verified by headless tests alone.

## Renderer knowledge to preserve

### 16-bit image importer

The upstream D219 investigation is a useful negative-knowledge case. A blanket R/B swap appeared to repair fire but regressed correctly decoded RGBA32 content. The final fix scopes byte-order handling by pixel-format family. Future texture fixes should identify the structural format/path first, rather than keying on texture number, visual symptom, or compression method.

Classification: **LEARN + REUSE the reviewed upstream fix**.

### Sky investigation

The sky work demonstrates that automated frame/build tests can pass while a defect remains obvious in live motion. Rendering acceptance should combine deterministic captures with human playtest for view-dependent or temporal defects.

Classification: **LEARN**.

## Ecosystem references

These projects/tools are research inputs, not automatic code sources:

- `n64decomp/007` — original-game decompilation and behavior reference. **LEARN / ground truth**.
- `jkdansereau/goldeneye-pc-port` — direct upstream. **REUSE first when compatible**.
- `SegfaultEvan/goldeneye-native` — modern controls, launcher, modding and multiplayer architecture reference. **LEARN / ADAPT after license and architecture review**.
- `Graslu/1964GEPD` — mouse/input behavior reference. **LEARN**.
- GoldenEye Setup Editor / GoldEditor — format/tooling knowledge. **LEARN**; do not copy/adapt code without a specific license review.
- Patcher64+ — historical patch/QoL/translation precedent. **LEARN**; review each patch’s provenance and license separately.
- XBLA recompilation projects — renderer/network/settings ideas from a different codebase. **LEARN**, not drop-in code.

## Provenance rule

For any third-party-derived implementation, record before integration:

- project and URL;
- exact commit/PR/issue when practical;
- source files/functions involved;
- license and attribution obligations;
- whether the architecture is actually compatible;
- tests run in this fork;
- known regressions/failed approaches.

Never add ROMs, extracted proprietary assets, leaked SDK material, or other game content to the repository.

## Recommended order after upstream review

1. Review/synchronize upstream without importing maintainer-specific self-hosted CI assumptions.
2. Re-run the fork's Windows build and basic campaign/input smoke tests.
3. Reconcile README/status/build instructions with the synchronized code.
4. Land provenance/process documentation.
5. Build localization on the synchronized base.
6. Continue Modern Controls from upstream's current input foundation rather than the older pre-sync implementation.

This order is intentionally conservative: it reduces duplicate work and makes future localization/input branches easier to review and rebase.