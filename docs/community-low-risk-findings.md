# Community-driven low-risk modernization notes

This note records small PC-quality improvements that are safe enough to consider for Ascension, and separates them from attractive changes that still need engine-level validation.

## Sources studied

- `jkdansereau/goldeneye-pc-port` — current native-port baseline and PC input/config architecture.
- `SegfaultEvan/goldeneye-native` — native controls, launcher/configuration, crouch key and documented timing/widescreen limitations.
- `martin2844/DesktopGoldenEye` — modern FPS profile, Hybrid/Classic profiles, predictable capture and conventional desktop shortcuts.
- The GoldenEye Depot archive of Martin Hollis's 1995 design document — historical design intent, including the strong Virtua Cop influence.
- Historical development/postmortem material — GoldenEye's analog aiming grew out of an uncertain N64-controller design process, while environmental shot feedback, hit reactions and mission objectives were deliberate parts of the game's identity.
- Speedrun community documentation — control style 1.2 became a staple because it preserves analogue camera control with sharp digital movement; movement/control quirks can materially affect established play.
- Recent GoldenEye community discussions — recurring interest in mouse/keyboard, controller support, centered reticle, FOV choices and retaining an authentic control option.

## Accepted low-risk principles

1. **Choice over replacement.** Modern controls must coexist with Hybrid and Classic.
2. **Expose existing knobs before inventing new algorithms.** F10 should surface input/video settings already implemented by the PC layer.
3. **Use the game's native state machine where possible.** Dedicated crouch translates into GoldenEye's existing crouch gesture rather than replacing movement code.
4. **Desktop conventions are welcome when they do not affect simulation.** Example: Alt+Enter fullscreen.
5. **Defaults stay conservative.** New tuning rows keep the port's current values unless the player changes them.
6. **Every experimental integration is idempotent and anchor-validated until gameplay-tested.**

## Authenticity guardrails from GoldenEye's history

GoldenEye's unusual feel is not just an obsolete control scheme. Several traits are historically central to the game and should be treated as compatibility contracts unless an explicit Ascension option says otherwise:

- **Preserve environmental feedback.** Bullet marks, impact reactions, ejected cases, destructible props and positional hit reactions are part of the deliberate shooting feedback loop; visual modernization must not suppress them for performance by default.
- **Preserve objective-driven exploration.** Do not add navigation arrows, objective auto-completion or forced routes as defaults. The original levels were built as spaces first and objectives were layered into them later, which contributes to their exploratory/non-linear character.
- **Preserve movement math in Classic.** Do not normalize diagonal/strafe movement or silently alter turning acceleration. Long-standing players and speedrunners depend on the original movement characteristics.
- **Preserve aiming behavior in Classic.** Centered reticle, aim lock or FPS-style permanent crosshair must remain opt-in if implemented; the original R-button aiming model was a deliberate Virtua Cop-influenced mechanic.
- **Preserve multiplayer quirks by default.** Character dimensions and other imperfect balance choices are part of the shipped game's behavior. Competitive rebalance belongs in an explicit ruleset, never the Classic baseline.
- **Prefer presentation improvements over simulation changes.** Better configuration, capture behavior, screenshots, scaling, diagnostics and optional visual polish are safer than changing AI cadence, weapon cadence, timers or movement.

## Safe input/UI improvements currently exposed

- Control profile: Classic / Hybrid / Modern.
- Dedicated crouch toggle.
- Mouse aim and turn sensitivity.
- Raw mouse input toggle.
- Mouse smoothing.
- Mouse vertical scale.
- Aim response band.
- Hipfire pitch response.
- Menu pointer speed and direct-pointer mode.
- Gamepad deadzone.
- Trigger threshold.
- Gamepad Y inversion.
- Mouse capture mode.
- FOV scale, VSync, anisotropy, texture filtering and MSAA through F10.
- Alt+Enter fullscreen shortcut.

## Popular ideas deliberately deferred

### Centered reticle / aim lock

Community interest is clear, but this changes the aiming model rather than merely exposing an existing PC option. It needs an isolated engine hook, weapon/zoom testing and Classic-mode parity before inclusion.

### High-refresh gameplay / 120+ FPS

Do not equate renderer FPS with safe simulation FPS. GoldenEye contains frame-counted systems. A high-refresh feature should wait for a verified fixed-tick/interpolation path so AI, firing cadence, timers and ammunition do not accelerate.

### True widescreen / ultrawide

Changing window aspect is not the same as true aspect-aware projection. Correct widescreen needs projection, HUD/watch and view-layout auditing. Keep current FOV scaling separate from that work.

### Co-op, horde, Lua/mod API

These are high-value future features but are not subtle changes. They belong in isolated milestones after the PC-control baseline is stable.

## Gate for future "small" features

A change can enter the safe pack only if all are true:

- no ROM or copyrighted asset is added;
- no PT-BR import path is changed;
- Classic behavior remains available;
- saves remain compatible;
- the change is reversible;
- expected anchors/state are validated before modification;
- Dam smoke test passes for movement, aim, fire, crouch, interaction, weapon cycling and F10;
- multiplayer/controller paths are not silently removed;
- original movement, aiming, objective and combat-feedback semantics remain unchanged unless the feature is explicitly opt-in.
