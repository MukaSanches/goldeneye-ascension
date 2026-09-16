# GoldenEye Ascension

<p align="center">
  <strong>A modern PC experience built on the native GoldenEye 007 decompilation port.</strong><br>
  Original gameplay. Modern controls. Universal controller support. PT-BR integration. A safer PC UX. World-aware 3D audio powered by Steam Audio.
</p>

<p align="center">
  <a href="https://github.com/MukaSanches/goldeneye-ascension/actions/workflows/ascension-0.0.4.yml"><img alt="Ascension 0.0.4 CI" src="https://github.com/MukaSanches/goldeneye-ascension/actions/workflows/ascension-0.0.4.yml/badge.svg"></a>
  <a href="https://github.com/MukaSanches/goldeneye-ascension/actions/workflows/ascension-audio-remaster.yml"><img alt="Audio Remaster CI" src="https://github.com/MukaSanches/goldeneye-ascension/actions/workflows/ascension-audio-remaster.yml/badge.svg"></a>
  <img alt="Version" src="https://img.shields.io/badge/Ascension-0.0.4-2f81f7">
  <img alt="Primary platform" src="https://img.shields.io/badge/primary-Windows%20x86__64-0078d4">
  <img alt="Steam Audio" src="https://img.shields.io/badge/Steam%20Audio-4.8.1-5c2d91">
  <img alt="License" src="https://img.shields.io/badge/license-MIT-green">
</p>

<p align="center">
  <img src="docs/img/attract-bunker1.png" width="32%" alt="GoldenEye Bunker attract camera running in the PC port">
  <img src="docs/media/goldeneye-demo.gif" width="32%" alt="GoldenEye PC port gameplay montage">
  <img src="docs/img/attract-dam.png" width="32%" alt="GoldenEye Dam attract camera running in the PC port">
</p>

> [!IMPORTANT]
> **GoldenEye Ascension does not include a GoldenEye 007 ROM.** You must provide a legally owned compatible ROM and generate the required local game data yourself. Do not distribute ROMs, extracted copyrighted assets, or proprietary game data with builds made from this repository.

---

## What is GoldenEye Ascension?

**GoldenEye Ascension** is an enhancement layer and development line built on the native PC port of the original **GoldenEye 007 (Nintendo 64, 1997)** reconstructed by the GoldenEye decompilation community.

It is not an emulation frontend and it is not based on the unreleased Xbox 360 remaster. The original game code is compiled for the host platform while the N64 hardware-facing systems are replaced or adapted by the PC port.

Ascension keeps that foundation and focuses on one goal:

> **Make the original GoldenEye feel natural on a modern PC without casually rewriting the game that makes GoldenEye, GoldenEye.**

That means improvements are concentrated in the PC-facing layers: input, controller normalization, presentation, accessibility, tooling, diagnostics and audio. Campaign logic, AI, collision, mission rules, save compatibility and the original gameplay model are treated as compatibility-sensitive systems.

The current source identity is **Ascension 0.0.4**. The main development line also contains the accepted world-space 3D audio integration described below.

---

## Highlights

### Modern PC controls without deleting Classic GoldenEye

Ascension provides three control philosophies:

| Preset | Purpose |
|---|---|
| **Classic** | Preserve the established GoldenEye PC-port behavior and serve as the compatibility baseline. |
| **Hybrid** | Keep familiar legacy behavior while adding selected PC conveniences. |
| **Modern** | Direct mouse look, modern twin-stick controller behavior, dedicated crouch, modern bindings and PC-oriented camera response. |

Modern controller support includes:

- twin-stick movement and camera control for player 1;
- radial analog deadzones with full-range rescaling;
- Linear and Precision response curves;
- independent look and ADS sensitivity;
- independent X/Y inversion;
- Southpaw layout;
- optional LT/RT aim-fire swap;
- live keyboard rebinding in the F10 Controls page;
- live Modern gamepad action rebinding;
- hot-plug, unplug and controller-remap handling;
- persistent configuration through `ge007.ini`.

The accepted Modern mouse path and the original Q Watch ownership model remain separate from the PC overlay so menu input does not accidentally become camera input.

See [`docs/dev/ascension-0.0.4.md`](docs/dev/ascension-0.0.4.md) for the full control contract.

### Universal Controller Layer

Ascension normalizes physical controllers before they reach gameplay:

```text
Physical controller
        |
        +-- SDL2 built-in / XInput / HID mapping
        +-- optional SDL_GameControllerDB mapping
        +-- conservative generic-controller fallback
        +-- explicit user override
        v
Normalized SDL_GameController
        v
Classic / Hybrid / Modern
        v
GoldenEye
```

This layer supports known controller families, unusual USB devices, hot-plugging and contiguous logical controller slots. Explicit user mappings always outrank generated fallbacks.

Mapping priority is:

1. `data/ascension-auto-mappings.txt`
2. root `gamecontrollerdb.txt`
3. `data/gamecontrollerdb.txt`
4. `data/ascension-controller-mappings.txt` — highest priority

The controller database helper is optional at runtime; Ascension remains offline-capable after the required local files have been prepared.

### World-aware 3D audio

Ascension extends the PC software mixer with a layered spatial-audio path based on **Steam Audio 4.8.1**.

For positional SFX where the game exposes real world coordinates, the pipeline is:

```text
GoldenEye positional SFX
        |
        +-- physical voice identity
        +-- source XYZ
        +-- listener XYZ / orientation
        +-- STAN room traversal
        +-- portals / closed transitions
        v
Ascension acoustic world model
        |
        +-- listener-space direction
        +-- physical distance model
        +-- propagation delay
        +-- air / barrier attenuation
        +-- obstruction / transmission
        +-- distance- and barrier-dependent low-pass
        +-- room-transition response
        +-- early-reflection field
        +-- bounded reverberant field
        v
Steam Audio per-source binaural HRTF
        v
GoldenEye software mixer
```

The system is intentionally **fail-safe rather than all-or-nothing**. The original GoldenEye contribution already exists in the mix before a replacement is attempted. A spatial replacement is committed only after a complete finite frame succeeds.

Fallback order is conceptually:

```text
World-aware XYZ path
        |
        | unavailable / invalid
        v
Existing per-source Steam Audio HRTF path
        |
        | unavailable
        v
Post-mix Steam Audio spatial path / conservative remaster
        |
        | unavailable or bypassed
        v
Original GoldenEye mix
```

The mixer-facing real-time path avoids file I/O, effect construction and allocation. Steam Audio effect objects are prepared outside per-source processing. The world-aware layer also exposes an A/B safety switch for diagnostics.

For best perception of front/back and elevation cues, use ordinary **stereo headphones** and avoid stacking an additional external virtual-surround processor while testing.

### PC UX and compatibility work

Ascension also includes a growing PC-specific quality layer:

- F10 systems/options overlay kept separate from the native Q Watch;
- modern display/input convenience controls;
- safe fullscreen shortcuts;
- screenshot workflow improvements;
- mission-selection convenience features;
- reversible All Missions availability override without writing fake campaign progression;
- PT-BR integration work in the PC-side localization path;
- safe configuration defaults and recovery paths;
- extensive patcher idempotence and regression checks.

---

## Design principles

Ascension development follows a few strict rules.

**Original gameplay is the compatibility baseline.** A PC feature should not silently rewrite mission logic, AI, collision, weapons, progression or save semantics.

**Classic must remain a recovery path.** New control systems are additive. When a Modern feature is disabled, the project should have a clear route back to known behavior.

**Audio must fail audible.** A failed HRTF, invalid metadata or unavailable spatial layer must not turn an existing sound into silence.

**Patchers fail closed.** Automated patch tools are designed to be idempotent and to stop when an expected source seam is no longer recognizable instead of blindly editing the wrong code.

**Compilation is necessary, not sufficient.** Automated contracts catch structural regressions; real controller feel, audio perception and end-to-end gameplay still require manual testing.

---

## Quick start for developers

Windows with **MSYS2 MINGW64** is the primary development and playtest environment.

### 1. Install the Windows toolchain

Open an **MSYS2 MINGW64** shell and install the core packages:

```bash
pacman -S --needed \
  mingw-w64-x86_64-toolchain \
  mingw-w64-x86_64-SDL2 \
  mingw-w64-x86_64-zlib \
  mingw-w64-x86_64-cmake \
  mingw-w64-x86_64-python \
  make \
  git
```

### 2. Clone Ascension

```bash
git clone https://github.com/MukaSanches/goldeneye-ascension.git
cd goldeneye-ascension
```

### 3. Supply your own compatible ROM

Place your legally owned ROM under `data/` using the expected filename.

| Region | Build target | Filename | SHA-1 |
|---|---|---|---|
| NTSC-U | `ntsc-final` | `ge007.ntsc-final.z64` | `abe01e4aeb033b6c0836819f549c791b26cfde83` |
| PAL | `pal-final` | `ge007.pal-final.z64` | `167c3c433dec1f1eb921736f7d53fac8cb45ee31` |
| NTSC-J | `jpn-final` | `ge007.jpn-final.z64` | `2a5dade32f7fad6c73c659d2026994632c1b3174` |

**NTSC-U is the recommended Ascension target and receives the most direct Windows playtesting.**

### 4. Use the canonical Ascension pipeline

The preferred entry point is `tools_pc/ascension.py`.

Prepare the Ascension patch stack:

```bash
python tools_pc/ascension.py prepare
```

Run ROM-free regression contracts:

```bash
python tools_pc/ascension.py test
```

Ensure the pinned Steam Audio 4.8.1 runtime is available:

```bash
python tools_pc/ascension.py steamaudio
```

Generate ROM symbols/assets required by the PC build:

```bash
python tools_pc/ascension.py assets
```

Build:

```bash
python tools_pc/ascension.py build --target ntsc-final
```

Or run the deterministic full pipeline:

```bash
python tools_pc/ascension.py all --target ntsc-final
```

For the developer playtest workflow — prepare, optional controller DB refresh, tests, Steam Audio, assets, build, runtime staging and launch:

```bash
python tools_pc/ascension.py play --target ntsc-final
```

### Direct build path

If the tree is already prepared, the compact build command remains:

```bash
./build-pc.sh ntsc-final
```

The Ascension build wrapper also runs the acoustic-world core test with warnings promoted to errors before the expensive native build.

Successful Windows output:

```text
build-pc/ge007.x86_64.exe
```

---

## Running

From the repository root:

```bash
./build-pc/ge007.x86_64.exe
```

Or:

```bash
python tools_pc/ascension.py run
```

The project writes its PC configuration to `ge007.ini`.

Do not edit `ge007.ini` while the game is running if you expect manual edits to persist: a normal shutdown writes the current runtime configuration back to disk.

---

## Modern controls overview

With the Modern gamepad path enabled, the intended default layout is:

| Action | Default Modern gamepad behavior |
|---|---|
| Move | Left stick |
| Look | Right stick |
| Fire | RT |
| Aim | LT |
| Action / use | A |
| Reload / cancel | X |
| Crouch | B |
| Next weapon | Y |
| Previous weapon | LB |
| Alternate/native L action | RB |
| Pause | Start |
| Native directional actions | D-pad |

Keyboard and mouse bindings can be changed live through **F10 → Controls**. Modern gamepad action bindings are exposed through the same PC-side controls interface.

Useful UI ownership rule:

- **Q** remains GoldenEye's native Watch path;
- **F10** opens Ascension's PC systems/options layer;
- menus must not inherit gameplay mouse-look behavior.

---

## 3D audio testing guide

A strong first test level is **Facility / Instala.** because it contains corridors, rooms, doors, walls and multiple guards at useful listening distances.

Use headphones and test these behaviors:

1. Keep a guard alive and rotate 360°. The sound should remain anchored to the guard's world position.
2. Compare a guard through a closed route versus an open doorway. The obstructed case should lose clarity/presence instead of simply muting.
3. Move toward and away from a source. Distance should affect more than raw volume.
4. Compare a corridor with a more open area and listen for differences in the reflection/reverb field.
5. Compare directly in front versus directly behind. Binaural front/back coloration should not collapse to ordinary left/right pan.
6. Stress several simultaneous guards, shots, doors and impacts. Audio must not disappear merely because the advanced path cannot claim a slot.
7. Open menus and the Q Watch after combat. World spatialization must not break menu ownership or freeze the game.

Bunker and Caverns are also useful follow-up environments for enclosed-space testing.

---

## Audio diagnostics and safety switches

These environment variables are intended for A/B testing and recovery.

| Variable | Effect |
|---|---|
| `GE_ASCENSION_WORLD3D=0` | Disable only the new real-world XYZ/room layer; keep the established per-source Steam Audio path available. |
| `GE_ASCENSION_SOURCE_HRTF=0` | Disable the per-source HRTF path for comparison. |
| `GE_ASCENSION_AUDIO_BYPASS=1` | Return the untouched GoldenEye mix from the remaster stage. |
| `GE_ASCENSION_AUDIO_DIAG=1` | Enable additional Steam Audio diagnostics. |
| `GE_MIXERTRACE=1` | Write low-level mixer tracing for debugging. |

Example in MSYS2:

```bash
GE_ASCENSION_WORLD3D=0 ./build-pc/ge007.x86_64.exe
```

These are diagnostics, not normal player requirements.

---

## Steam Audio integration

Ascension currently targets **Steam Audio 4.8.1**.

GoldenEye's software audio path renders at 22.05 kHz. Steam Audio's built-in HRTF set does not provide a native 22.05 kHz dataset, so the Ascension source-HRTF path uses the nearest built-in 24 kHz HRTF filter set while preserving GoldenEye's source sample clock and pitch. The original mix remains the safety baseline.

The runtime loader checks the staged Steam Audio library next to the executable and the repository's pinned third-party runtime location. On Windows the expected runtime is `phonon.dll`.

The helper:

```bash
python tools_pc/ensure_steam_audio.py ensure
```

verifies/prepares the pinned runtime, while:

```bash
python tools_pc/ensure_steam_audio.py stage
```

stages it for the built executable. The canonical `ascension.py play` workflow handles both stages automatically.

---

## Validation

Ascension uses several layers of validation rather than one monolithic test.

### Static and patcher contracts

The repository contains regression tests for:

- Modern Controls V2/V3/V4;
- Modern gamepad rebinding;
- universal controller normalization;
- UI overhaul behavior;
- persistent F10 UX;
- All Missions save isolation;
- Q Watch runtime ownership;
- audio remaster integration;
- patcher idempotence;
- repository hygiene.

Run the canonical contract suite with:

```bash
python tools_pc/ascension.py test
```

A report is written to:

```text
ascension-0.0.4-test-report.txt
```

### Acoustic-world test

The build wrapper compiles the acoustic-world core with strict warnings and executes its regression binary before building the full game.

The standalone Windows/MSYS2 equivalent is:

```bash
gcc \
  -std=gnu11 \
  -Wall \
  -Wextra \
  -Werror \
  -DASC_AUDIO_WORLD_TEST_SYNC=1 \
  -Iport/include \
  port/src/ascension_audio_world.c \
  port/tests/test_ascension_audio_world.c \
  -pthread \
  -lm \
  -o test_ascension_audio_world.exe

./test_ascension_audio_world.exe
```

Expected result:

```text
ascension_audio_world: all tests passed
```

### Manual validation still matters

Automated success proves integration properties; it cannot prove controller feel, every unusual HID mapping, binaural perception on every headphone, or every campaign edge case.

A change should not be described as fully validated merely because it compiled.

---

## Architecture

At a high level:

```text
GoldenEye reconstructed game source
                |
                v
       host-compiled game code
                |
      +---------+---------+
      |                   |
      v                   v
 software RSP/audio     game logic
      |                   |
      v                   |
 Ascension PC layers <----+
      |
      +-- input / controller normalization
      +-- F10 PC systems UI
      +-- localization integration
      +-- Steam Audio spatial pipeline
      +-- SDL2 / OpenGL / filesystem / configuration
      v
          Windows / Linux host
```

Important directories:

| Path | Purpose |
|---|---|
| `src/` | GoldenEye reconstructed game source and game-facing glue inherited from the decompilation/port. |
| `port/` | Host platform implementation: video, audio, input, configuration, software RSP and Ascension runtime modules. |
| `port/src/ascension_*` | Ascension-owned runtime systems. |
| `port/include/ascension_*` | Ascension public/internal interfaces. |
| `port/tests/` | Low-level C regression tests for host-side systems. |
| `tools_pc/` | Patchers, validators, build helpers, controller tooling and Ascension's canonical developer CLI. |
| `scripts/` | Repository/build integration helpers. |
| `docs/` | Architecture notes, compatibility contracts, smoke tests, recovery procedures and development documentation. |
| `.github/workflows/` | CI and release qualification workflows. |

---

## Important documentation

Start here when changing the project:

- [`CHANGELOG-ASCENSION.md`](CHANGELOG-ASCENSION.md) — Ascension-specific history.
- [`docs/dev/ascension-0.0.4.md`](docs/dev/ascension-0.0.4.md) — 0.0.4 control architecture and qualification contract.
- [`docs/ascension-compatibility-contract.md`](docs/ascension-compatibility-contract.md) — compatibility boundaries.
- [`docs/ascension-patch-stack.md`](docs/ascension-patch-stack.md) — patch-stack structure.
- [`docs/ascension-recovery-playbook.md`](docs/ascension-recovery-playbook.md) — recovery and troubleshooting procedures.
- [`docs/ascension-smoke-test.md`](docs/ascension-smoke-test.md) — manual smoke-test guidance.
- [`docs/ascension-modern-controls.md`](docs/ascension-modern-controls.md) — Modern control design.
- [`docs/ascension-ui-overhaul-v2.md`](docs/ascension-ui-overhaul-v2.md) — PC UI layer.
- [`docs/ascension-ui-art-bible.md`](docs/ascension-ui-art-bible.md) — visual direction.
- [`docs/checkpoints/2026-09-15-watch-fixed.md`](docs/checkpoints/2026-09-15-watch-fixed.md) — accepted Q Watch recovery checkpoint.
- [`docs/building.md`](docs/building.md) — underlying PC-port build details.

---

## Troubleshooting

### The build fails at the final link step

Always read the **first linker error**, not only the final `collect2.exe` line. The project uses a mixed C/C++ native link, so duplicate symbols or a missing runtime function can surface only at the last step.

Re-run:

```bash
./build-pc.sh ntsc-final
```

and capture from the first `undefined reference`, `multiple definition`, or `error:` line.

### Steam Audio does not initialize

Run:

```bash
python tools_pc/ascension.py steamaudio
python tools_pc/ensure_steam_audio.py stage
```

Then launch again. For diagnostics:

```bash
GE_ASCENSION_AUDIO_DIAG=1 ./build-pc/ge007.x86_64.exe
```

### I need to isolate the new world-audio layer

```bash
GE_ASCENSION_WORLD3D=0 ./build-pc/ge007.x86_64.exe
```

If the game works normally in that mode, the issue is isolated to the world-aware metadata/acoustic path rather than the established source-HRTF path.

### A generic controller is mapped incorrectly

Put a correct SDL controller mapping in:

```text
data/ascension-controller-mappings.txt
```

Explicit user mappings have the highest priority.

### Configuration feels corrupted

Close the game before manually editing `ge007.ini`. Use Classic as the baseline when determining whether a behavior belongs to original/legacy input or an Ascension Modern feature.

---

## Compatibility and non-goals

Ascension is deliberately conservative around game-state compatibility.

The project does not treat the following as casual PC polish targets:

- campaign progression semantics;
- mission scripting;
- AI behavior;
- weapon balance;
- collision rules;
- original save meaning;
- original GoldenEye level logic.

Features such as **All Missions** are implemented as reversible frontend availability overrides rather than fake progression writes.

The purpose of Ascension is not to turn GoldenEye into a different shooter. It is to make the original game more comfortable, understandable and immersive on PC while retaining a path back to the original behavior.

---

## Contributing

Before opening a pull request that touches Ascension-owned systems:

```bash
python tools_pc/ascension.py prepare
python tools_pc/ascension.py test
```

For native changes, also complete a full build:

```bash
./build-pc.sh ntsc-final
```

For controls, audio or Watch/UI changes, include a manual runtime test description in the pull request. A compiler-only result is not enough for behavior that depends on perception or physical input hardware.

Please keep changes scoped and preserve the compatibility contracts described in `docs/`.

---

## Credits and technical heritage

GoldenEye Ascension exists because of several major bodies of work.

### GoldenEye 007 decompilation

The reconstructed source foundation comes from the **GoldenEye 007 decompilation project**:

- <https://github.com/n64decomp/007>

### Native GoldenEye PC port

Ascension is built on the native GoldenEye PC-port architecture and extensive low-level porting work from:

- <https://github.com/jkdansereau/goldeneye-pc-port>

The PC port established the host build, software-RSP path, platform shims, asset workflow and much of the foundational runtime architecture Ascension extends.

### Perfect Dark PC port

The broader architecture also benefits from the earlier Perfect Dark source-port work from the same Rare engine family:

- <https://github.com/fgsfdsfgs/perfect_dark>

### Steam Audio

World-aware binaural rendering uses **Valve Steam Audio 4.8.1** through a dynamically loaded runtime:

- <https://valvesoftware.github.io/steam-audio/>

### Controller ecosystem

Controller normalization relies on SDL2's GameController model and can optionally consume SDL_GameControllerDB-format mappings.

Ascension-specific engineering, integration, controls, PC UX, tooling, localization work and audio experimentation live in this repository's commit history and changelog.

---

## Legal

GoldenEye 007, Nintendo 64, Nintendo, Rare and related names, characters, imagery and trademarks belong to their respective rights holders.

This project is an independent technical/community project and is not affiliated with, endorsed by, sponsored by or approved by Nintendo, Microsoft, Rare or MGM/Amazon.

No GoldenEye ROM is included. Users are responsible for complying with the laws applicable to their own copies and local jurisdiction.

Do not open issues asking for ROM downloads, copyrighted asset packs or links to unauthorized game data.

---

## License

Repository-authored code is provided under the license terms present in [`LICENSE`](LICENSE), subject to the provenance and licensing of upstream components and third-party dependencies used by the project.

---

<p align="center">
  <strong>GoldenEye Ascension</strong><br>
  Preserve the game. Modernize the interface between the game and the player.
</p>
