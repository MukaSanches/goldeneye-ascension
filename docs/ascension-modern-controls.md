# Ascension Modern Controls

Current release candidate: **Ascension 0.0.4**.

Ascension keeps GoldenEye's original gameplay/input machinery authoritative and adds narrowly scoped PC input layers around it. The guiding rule is preservation first: Classic remains the reference, and Modern behavior is explicit and reversible.

## Presets

`Input.ControlPreset`

- `0` — **Classic**: preserves the existing PC-port keyboard/gamepad behavior and disables Ascension-specific dedicated crouch translation.
- `1` — **Hybrid**: preserves legacy keyboard fire on Left Ctrl while enabling dedicated crouch on `C`.
- `2` — **Modern**: enables the complete Ascension PC control layer, including direct mouse look and the optional Modern controller-0 twin-stick path.

Classic remains the safe default for new configurations. Existing saved choices are preserved.

## Modern mouse

The accepted V3 mouse behavior remains unchanged in 0.0.4:

- direct sub-pixel gameplay camera look instead of routing mouse motion through N64 stick quantization;
- configurable direct-look sensitivity;
- independent ADS sensitivity scale;
- optional raw/precision response behavior;
- optional look auto-center suppression;
- signed FIFO mouse-wheel weapon cycling;
- menu-safe routing so gameplay camera deltas never leak into the frontend;
- native frontend pointer behavior remains separate from gameplay mouse-look.

Mouse direct-look still uses the narrow PORT bridge in `bondview2.c`; movement, collision, weapons, AI and mission logic remain in GoldenEye's native paths.

## Modern gamepad — V4

`Input.ModernGamepad=1` enables the Modern controller path only when the Modern preset is selected. It is scoped to controller 0/player 1; other controllers continue through the legacy mapping used by the port.

### Analog behavior

- left stick uses radial deadzone processing and feeds GoldenEye's native `analogStrafe` / `analogWalk` channels;
- right stick uses radial deadzone processing and feeds the same narrow PORT camera bridge used by direct mouse look;
- the deadzone is rescaled, so reaching full stick still reaches full output;
- `LINEAR` preserves the post-deadzone magnitude;
- `PRECISION` applies a mild precision curve while preserving stick direction;
- gamepad look sensitivity and ADS scale are independent;
- horizontal and vertical inversion are independent;
- Southpaw swaps movement and camera sticks;
- trigger swap exchanges LT/RT aim-fire roles without replacing analog trigger reads.

### Default Modern mapping

- Left stick: move/strafe
- Right stick: look
- RT: fire
- LT: aim
- A: action/use
- X: reload/cancel
- B: dedicated crouch through GoldenEye's native posture state machine
- Y: next weapon
- LB: previous weapon
- RB: native L/alternate action
- Start: start/pause
- D-pad: native D-pad

## Keyboard rebinding

Keyboard remapping still belongs to the existing `Input.Bind.*` configuration keys. Ascension 0.0.4 adds an in-game capture UI rather than introducing another binding database.

From `F10 -> Controls`, select a `Bind:` row, activate it, release the activation key and press the replacement key. The parsed scancode table is rebuilt immediately and the same `ge007.ini` value is persisted.

The currently exposed keyboard actions include movement, turn, fire, aim, action, reload/cancel, alternate action and start/pause.

## Modern gamepad rebinding

Modern gamepad digital actions are stored under `Input.ModernPadBind.*` and are editable from `F10 -> Controls`.

The exposed bindings are:

- action/use;
- reload/cancel;
- crouch;
- next weapon;
- previous weapon;
- alternate action;
- start/pause.

Activate a `Pad bind:` row, release any already-held controller button, then press the replacement button. Guide/Home is intentionally excluded because desktop operating systems or drivers may reserve it.

`Reset PC settings` restores both keyboard and Modern gamepad binding defaults.

## Important V4 configuration keys

- `Input.ModernGamepad`
- `Input.ModernPadDeadzone`
- `Input.ModernPadResponse`
- `Input.ModernPadLookSensitivity`
- `Input.ModernPadAdsScale`
- `Input.ModernPadInvertX`
- `Input.ModernPadInvertY`
- `Input.ModernPadSouthpaw`
- `Input.ModernPadSwapTriggers`
- `Input.ModernPadBind.Action`
- `Input.ModernPadBind.Cancel`
- `Input.ModernPadBind.Crouch`
- `Input.ModernPadBind.NextWeapon`
- `Input.ModernPadBind.PrevWeapon`
- `Input.ModernPadBind.AltAction`
- `Input.ModernPadBind.Start`

## Compatibility contract

- Classic behavior is the comparison baseline and must remain available.
- Hybrid keeps its existing dedicated-crouch compromise and legacy Ctrl-fire behavior.
- Modern features never change ROM data or the save format.
- Dedicated crouch is translated back through GoldenEye's native aim-plus-down posture gesture rather than bypassing weapon/crouch restrictions.
- Modern gamepad V4 is inactive in frontend menus and while the native Q Watch owns input.
- The Q Watch Escape/capture fix remains authoritative; closing the watch must immediately restore gameplay mouse response.
- Native frontend mouse-pointer routing remains authoritative outside gameplay.
- The F10 convenience return and stock Q Watch Abort Mission remain separate operations with different save/failure semantics.
- All Missions must remain reversible and must never counterfeit campaign progress.
- Local multiplayer controllers outside controller 0 remain on the legacy input path.

## Validation

The release candidate is exercised through:

```bash
python tools_pc/ascension.py prepare
python tools_pc/ascension.py test
python tools_pc/ascension.py assets
python tools_pc/ascension.py build
```

or the combined command:

```bash
python tools_pc/ascension.py all
```

The 0.0.4 code gate passes on Windows/MSYS2 and Linux GCC 13/14. Controller feel and transition behavior still require the manual Windows matrix in [`docs/dev/ascension-0.0.4.md`](dev/ascension-0.0.4.md) before the candidate is promoted to validated.
