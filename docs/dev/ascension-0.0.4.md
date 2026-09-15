# Ascension 0.0.4 — Modern Experience

Status: **test candidate**. This branch starts from the manually accepted `checkpoint/2026-09-15-watch-fixed` state. The checkpoint remains the recovery baseline and is not rewritten by this release work.

## Release intent

0.0.4 turns the already-proven Modern mouse/Q Watch work into a coherent PC-controls release without disturbing the parts that were accepted in manual play.

The release adds:

- Modern controller-0 twin-stick mode;
- radial left/right stick deadzone;
- Linear and Precision right-stick response;
- independent gamepad look sensitivity and ADS scale;
- independent gamepad X/Y inversion;
- analog left-stick movement through GoldenEye's existing `analogStrafe` and `analogWalk` channels;
- frame-scaled right-stick camera look through the existing V3 PORT camera bridge;
- a familiar Modern face-button layout while Classic/Hybrid keep their legacy path;
- live keyboard rebinding inside `F10 -> Controls` using the existing `Input.Bind.*` config keys;
- one canonical prepare/test/build entry point: `tools_pc/ascension.py`;
- Windows and Linux GCC 13/14 CI for the complete stack.

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

## Radial shaping

`Input.ModernPadDeadzone` is a radial percentage rather than separate X/Y gates. Input inside the circle is zero. Input outside it is rescaled back to the full 0..1 range so the deadzone does not reduce maximum speed.

`PRECISION` applies a mild power curve after the deadzone; `LINEAR` leaves the rescaled magnitude linear. Direction is preserved in both modes.

## Keyboard rebinding

Open `F10 -> Controls`, select a `Bind:` row, activate it with Enter/right/LMB, release that activation key, then press the new key. Escape or F10 cancels capture.

The implementation edits the same lifetime buffers registered under `Input.Bind.*`, immediately rebuilds the parsed scancode table and saves `ge007.ini`. No parallel binding database is introduced.

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

## Required manual smoke test

Before promotion, test at minimum:

1. Frontend mouse pointer reaches all menu edges; LMB selects and RMB backs out.
2. Start Dam with Modern mouse, verify the mouse feel is unchanged from the accepted checkpoint.
3. Open/close Q Watch twice and verify mouse look resumes immediately.
4. Open/close F10 twice and verify mouse look resumes immediately.
5. Connect an Xbox-compatible controller and enable Modern + Modern twin-stick.
6. Walk/strafe diagonally slowly, then at full stick; verify no square deadzone or sudden digital strafe step.
7. Rotate with the right stick slowly around center and then full deflection; verify Precision feels controllable and maximum turn remains available.
8. Hold LT and verify ADS right-stick speed is lower than hip-fire at the default 65%.
9. Test A/X/B/Y/LB/RB/RT/LT and Start.
10. Rebind Forward to another key in F10, close F10, verify it works immediately, relaunch, and verify it persisted.
11. Reset PC settings and verify binding defaults return.
12. Switch to Classic and verify the old gamepad mapping still behaves as before.
13. Switch to Hybrid and verify its behavior still matches the checkpoint.
14. Return to the mission selector through F10 and verify the selected save/profile remains intact.
15. Toggle All Missions off/on and verify no campaign progress is written.
16. Alt-Tab out/in during gameplay and verify there is no camera snap.

## Promotion rule

A green CI run proves source integration and deterministic contracts. It does not prove controller feel. 0.0.4 should move from test candidate to validated only after the manual matrix above is played on Windows with a real controller and the existing mouse/Q Watch checkpoint behavior remains intact.
