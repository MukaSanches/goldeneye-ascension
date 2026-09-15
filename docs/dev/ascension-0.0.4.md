# Ascension 0.0.4 — Modern Experience

Status: **test candidate — CI-qualified**. This branch starts from the manually accepted `checkpoint/2026-09-15-watch-fixed` state. The checkpoint remains the recovery baseline and is not rewritten by this release work.

The source-integration gate is green on Windows/MSYS2 and Linux with GCC 13 and GCC 14. Manual Windows playtesting with a real controller is still required before calling 0.0.4 validated.

## Release intent

0.0.4 turns the already-proven Modern mouse/Q Watch work into a coherent PC-controls release without disturbing the parts that were accepted in manual play.

The release adds:

- Modern controller-0 twin-stick mode;
- radial left/right stick deadzone;
- Linear and Precision right-stick response;
- independent gamepad look sensitivity and ADS scale;
- independent gamepad X/Y inversion;
- Southpaw stick layout;
- optional LT/RT fire/aim swap;
- analog left-stick movement through GoldenEye's existing `analogStrafe` and `analogWalk` channels;
- frame-scaled right-stick camera look through the existing V3 PORT camera bridge;
- a familiar Modern face-button layout while Classic/Hybrid keep their legacy path;
- live keyboard rebinding inside `F10 -> Controls` using the existing `Input.Bind.*` config keys;
- live Modern gamepad button rebinding inside `F10 -> Controls` using `Input.ModernPadBind.*`;
- one canonical prepare/test/build entry point: `tools_pc/ascension.py`;
- Windows and Linux GCC 13/14 CI for the complete stack, including retained regression/build logs.

## Deliberate non-changes

0.0.4 does **not** redesign or replace:

- the accepted Modern mouse direct-look math;
- native frontend mouse pointer behavior;
- Q Watch ownership or stock Abort Mission semantics;
- F10 quick-return semantics;
- mission availability/save isolation;
- collision, AI, weapons or mission logic;
- ROM text/assets;
- Classic or Hybrid gamepad behavior.

If one of those changes while testing 0.0.4, treat it as a regression.

## Modern gamepad contract

With `Input.ControlPreset=2` and `Input.ModernGamepad=1`:

- left stick: analog strafe + walk;
- right stick: direct camera look;
- RT: fire;
- LT: aim;
- A: action/use;
- X: reload/cancel;
- B: dedicated crouch through GoldenEye's native aim+down posture gesture;
- Y: next weapon using the native inventory edge;
- LB: previous weapon using GoldenEye's A+Z reverse inventory chord;
- RB: native L/alternate action;
- Start and D-pad retain their native mapping.

The V4 path is scoped to controller 0 because the PC mouse/keyboard Modern experience is also player-1 oriented. Local multiplayer controllers continue through the legacy N64 mapping.

`Input.ModernPadSouthpaw=1` swaps the movement and camera sticks without changing game logic. `Input.ModernPadSwapTriggers=1` swaps the LT/RT aim-fire roles without changing their analog trigger behavior.

## Radial shaping

`Input.ModernPadDeadzone` is a radial percentage rather than separate X/Y gates. Input inside the circle is zero. Input outside it is rescaled back to the full 0..1 range so the deadzone does not reduce maximum speed.

`PRECISION` applies a mild power curve after the deadzone; `LINEAR` leaves the rescaled magnitude linear. Direction is preserved in both modes.

## Keyboard rebinding

Open `F10 -> Controls`, select a `Bind:` row, activate it with Enter/right/LMB, release that activation key, then press the new key. Escape or F10 cancels capture.

The implementation edits the same lifetime buffers registered under `Input.Bind.*`, immediately rebuilds the parsed scancode table and saves `ge007.ini`. No parallel binding database is introduced.

## Modern gamepad rebinding

Open `F10 -> Controls` and select one of the `Pad bind:` rows. Activate it, release any controller button that was already held, then press the new button.

The configurable Modern actions are:

- action/use;
- reload/cancel;
- crouch;
- next weapon;
- previous weapon;
- alternate action;
- start/pause.

The capture layer ignores the Guide/Home button because operating systems and controller drivers may reserve it before the game receives the event. Bindings persist in `ge007.ini` under `Input.ModernPadBind.*`. Resetting PC settings restores both keyboard and Modern gamepad binding defaults.

## Canonical commands

From MSYS2 MINGW64:

```bash
python tools_pc/ascension.py prepare
python tools_pc/ascension.py test
python tools_pc/ascension.py assets
python tools_pc/ascension.py build
```

Or run everything:

```bash
python tools_pc/ascension.py all
```

The regression command runs every contract and writes `ascension-0.0.4-test-report.txt`. CI also retains build logs so compiler failures can be diagnosed without weakening a release gate.

## Automated qualification

The 0.0.4 test candidate currently passes the complete pipeline on:

- Windows latest with MSYS2 MINGW64;
- Linux with GCC 13;
- Linux with GCC 14.

That gate includes stack preparation, Python syntax checks, the V2/V3/V4 controls contracts, UI contracts, Q Watch/runtime contracts, mission/save-isolation checks, `git diff --check`, ROM symbol generation, a complete native build and executable existence verification.

Automated success is necessary but not sufficient for input feel. The release remains a test candidate until the manual matrix below is completed on the target Windows machine.

## Required manual smoke test

Before promotion, test at minimum:

1. Frontend mouse pointer reaches all menu edges; LMB selects and RMB backs out.
2. Start Dam with Modern mouse and verify the mouse feel is unchanged from the accepted checkpoint.
3. Open/close Q Watch twice and verify mouse look resumes immediately.
4. Open/close F10 twice and verify mouse look resumes immediately.
5. Connect an Xbox-compatible controller and enable Modern + Modern twin-stick.
6. Walk/strafe diagonally slowly, then at full stick; verify no square deadzone or sudden digital strafe step.
7. Rotate with the right stick slowly around center and then full deflection; verify Precision feels controllable and maximum turn remains available.
8. Hold LT and verify ADS right-stick speed is lower than hip-fire at the default 65%.
9. Test the default A/X/B/Y/LB/RB/RT/LT, Start and D-pad mappings.
10. Enable Southpaw and verify the movement/camera sticks exchange roles cleanly; disable it and verify the default layout returns.
11. Enable trigger swap and verify LT/RT exchange aim/fire roles; disable it and verify the default trigger layout returns.
12. Rebind at least Action and Crouch from F10, close F10 and verify the new gamepad buttons work immediately.
13. Relaunch and verify the gamepad mappings from the previous step persisted.
14. Rebind Forward to another keyboard key in F10, close F10 and verify it works immediately; relaunch and verify persistence.
15. Reset PC settings and verify keyboard and Modern gamepad bindings return to their defaults.
16. Switch to Classic and verify the old gamepad mapping still behaves as before.
17. Switch to Hybrid and verify its behavior still matches the checkpoint.
18. Open and close the native Q Watch while using the controller, then immediately resume mouse input; ownership must remain clean in both directions.
19. Return to the mission selector through F10 and verify the selected save/profile remains intact.
20. Toggle All Missions off/on and verify no campaign progress is written.
21. Alt-Tab out/in during gameplay and verify there is no camera snap or stale controller look.

## Promotion rule

A green CI run proves source integration and deterministic contracts. It does not prove controller feel. 0.0.4 should move from test candidate to validated only after the manual matrix above is played on Windows with a real controller and the existing mouse/Q Watch checkpoint behavior remains intact.
