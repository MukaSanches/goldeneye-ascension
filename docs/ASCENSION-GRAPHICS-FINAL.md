# Ascension Graphics Final

This document describes the graphics stack shipped by the `feature/ascension-graphics-final` validation branch and the engineering decisions behind it.

The goal of this release is not to replace one set of rendering problems with a newer set. The goal is to make the strongest production-quality graphical improvement that can be validated in the existing GoldenEye Ascension source-port architecture and in the Windows/MSYS2 toolchain used by the project.

## Shipping graphics stack

The final presentation path is:

```text
GoldenEye display lists
        |
        v
GoldenEye-aware Fast3D
  - F3DGOLDEN / G_TRI4 handling
  - texture pitch correction
  - palette-content cache identity
  - mip-chain contamination protection
  - GoldenEye PORT sky/water path
        |
        v
OpenGL render target
  - 4x MSAA default
  - N64 3-point texture filtering default
  - trilinear minification where mipmaps are available
  - 16x anisotropic filtering default
        |
        v
Ascension adaptive final presentation pass
  - local-contrast-aware sharpening
  - anti-ringing neighbourhood clamp
  - fail-open GPU integration
        |
        v
SDL presentation
```

The original game frame remains the authoritative source. Post-processing does not modify gameplay, display lists, RDP state, depth data, world geometry, input, or timing.

## What changes for users

Fresh installs and existing installs that have not yet received Graphics Quality Revision 1 are migrated once to:

- 4x MSAA;
- N64-style 3-point texture filtering;
- linear mip filtering;
- 16x anisotropic filtering;
- existing mip-texture correctness fix enabled;
- adaptive final sharpening enabled at a conservative 35% strength.

The migration records `Ascension.GraphicsQualityRevision=1`. After that point the game never overwrites the player's graphics choices again.

The F10 Display page exposes:

- MSAA;
- texture filtering;
- anisotropic filtering;
- Adaptive sharpen on/off;
- Sharpness from 0 to 100;
- FOV, resolution, fullscreen, VSync and frame-cap controls already provided by Ascension.

`Reset PC settings` now restores the final graphics defaults rather than the earlier low-cost baseline.

## Adaptive presentation pass

`port/src/ascension_postfx.cpp` adds a final full-frame GPU pass immediately before the SDL swap and before screenshot capture.

The filter is an original edge-adaptive sharpening implementation influenced by the general design goals of modern contrast-adaptive sharpening filters:

1. sample a compact 3x3 neighbourhood;
2. estimate local contrast;
3. recover high-frequency detail from a stable low-pass estimate;
4. reduce gain on hard transitions where overshoot would be most visible;
5. clamp the result to the local colour neighbourhood with a small tolerance to suppress ringing and halos.

The pass is deliberately conservative. Ascension does not apply forced saturation, contrast curves, fake HDR, bloom, chromatic aberration, film grain or other art-direction changes by default.

### Safety properties

The pass:

- initializes lazily only after the OpenGL context exists;
- performs no steady-state heap allocation;
- reallocates its capture texture only when the drawable size changes;
- preserves the GL state categories it touches;
- logs initialization failure and leaves the original frame unchanged;
- can be disabled without rebuilding.

Environment overrides:

```text
GE_POSTFX=0        disable the final presentation pass
GE_POSTFX=1        force-enable the final presentation pass
GE_SHARPEN=0       disable sharpening while leaving the feature configured
GE_SHARPEN=35      default production strength
GE_SHARPEN=100     maximum strength for comparison/testing
```

## Existing GoldenEye-specific renderer work preserved

This release intentionally preserves the accumulated renderer fixes in Ascension instead of starting again from a generic renderer.

Important examples include:

- C-array texture byte-order normalization;
- palette-content hashing for CI texture-cache correctness;
- source row-pitch de-striding for sub-rectangle texture loads;
- base-level clipping for GoldenEye mip-chain loads;
- GoldenEye-specific `G_TRI4` support;
- the PORT sky/water path that avoids the unresolved upstream LLE-sky limitation described below.

These fixes are correctness work, not post-processing. The new final pass sits after them and does not hide their failures.

## Renderer technology research

The following projects were reviewed before choosing the shipping architecture.

### RT64

Repository: <https://github.com/rt64/rt64>

RT64 is the most important long-term renderer candidate for Ascension. It provides modern D3D12/Vulkan/Metal rendering, ubershaders, deferred RSP/RDP processing, GPU TMEM decoding, framebuffer tracking, high-resolution rendering, widescreen support, texture replacement and high-frame-rate rendering features.

RT64 now contains explicit GoldenEye microcode support under `F3DGOLDEN`, including GoldenEye's `G_TRIX`/`0xB1` command.

It is not made the default renderer in this release for two production reasons:

1. RT64 upstream issue #194 remains open: GoldenEye's LLE sky requires splitting/reconstructing low-level RDP triangles.
   <https://github.com/rt64/rt64/issues/194>
2. Existing GoldenEye RT64 recompilation projects still document black/incorrect sky and water cases caused by those custom commands.

Replacing a working Ascension sky/water implementation with a known upstream regression would not meet the definition of a final product.

RT64 remains the preferred future secondary backend once the GoldenEye LLE sky path and the project's exact Windows toolchain are validated end-to-end.

### GoldenEye64Recomp and GoldenRecomp

Repositories:

- <https://github.com/cblock85/GoldenEye64Recomp>
- <https://github.com/kholdfuzion/GoldenRecomp>

These projects prove that GoldenEye can run on RT64 and provide valuable integration references. They also independently document the current sky/water limitation, which is why this release does not blindly replace Ascension Fast3D with RT64.

### GLideN64

Repository: <https://github.com/gonetz/GLideN64>

GLideN64 has mature explicit `F3DGOLDEN` support and handles the `G_RDPHALF_1`, `G_RDPHALF_2` and `G_RDPHALF_CONT` family used by GoldenEye's low-level triangle path.

Its implementation is valuable as behavioural research and a compatibility oracle. GLideN64 is GPLv2, so Ascension does not copy its implementation into permissively licensed renderer code. Behaviour is studied and independently implemented/tested where needed.

### paraLLEl-RDP

Repository: <https://github.com/Themaister/parallel-rdp>

paraLLEl-RDP is a Vulkan-compute RDP implementation with strong conformance tooling. It is especially valuable for future renderer validation, RDP dump replay and pixel/command-level comparisons against a high-accuracy reference.

It is lower-level than the current source-port render interface, so it is treated as a validation/reference technology rather than a drop-in final backend in this release.

### Angrylion RDP Plus

Repository: <https://github.com/ata4/angrylion-rdp-plus>

Angrylion remains an important accuracy reference for N64 RDP behaviour. It is useful for validating difficult edge cases where a visually plausible result is not enough.

### libultraship Fast3D

Repository: <https://github.com/Kenix3/libultraship>

libultraship provides a modern, maintained Fast3D renderer and modern port infrastructure. It is an excellent architectural reference, but migrating the entire current renderer would still require GoldenEye-specific compatibility work already present in Ascension. Therefore a wholesale migration is not justified for this release.

### FidelityFX CAS research

Repository: <https://github.com/GPUOpen-Effects/FidelityFX-CAS>

AMD FidelityFX Contrast Adaptive Sharpening was reviewed as a reference for low-cost adaptive detail recovery. Ascension's final shader is an original implementation rather than a verbatim CAS port; it follows the same broad product principle of adapting sharpening to local contrast while adding a local anti-ringing guard suitable for the N64 UI and texture style.

### SMAA research

SMAA was reviewed as an additional post-process anti-aliasing option. Ascension already has multisample anti-aliasing integrated before presentation, so adding a multi-pass SMAA pipeline would increase complexity and GPU cost while duplicating a problem already addressed by 4x/8x MSAA. It is therefore not stacked on top of MSAA by default.

## Why 4x MSAA is the default instead of 8x

The F10 menu still offers 8x MSAA.

4x is the product default because it provides a substantial edge-quality improvement while remaining much safer across integrated GPUs, high-resolution displays and older OpenGL drivers. A final product should not make the highest theoretical setting mandatory when the visual return from 4x to 8x is small compared with the performance/memory increase.

Users with headroom can select 8x immediately.

## Why 16x anisotropic filtering is the default

Anisotropic filtering has a particularly good cost/benefit ratio for this game because many GoldenEye surfaces are viewed at steep angles: floors, corridors, runway surfaces, rooftops and long walls.

The rendering backend clamps the requested value to the driver's reported maximum, so `16` is a quality request rather than an unsafe assumption.

## Why N64 3-point filtering is the default

The existing renderer implements a three-point texture filtering path that better matches the characteristic N64 texture reconstruction than ordinary PC bilinear magnification. For minification, mip filtering remains enabled to reduce distant shimmer.

This combination gives a sharper and more period-appropriate image than simply forcing generic bilinear filtering everywhere.

## Validation matrix

A candidate is not considered complete because it compiles. Visual verification should cover distinct renderer stress cases:

| Area | What to inspect |
|---|---|
| File select / Watch / F10 | text clarity, UI edges, no post-FX halos |
| Facility | doors, corridors, close textures, weapon models |
| Dam | long-distance geometry, towers, sky transition |
| Surface I/II | sky, tree/cliff textures, distant anisotropic surfaces |
| Statue | PORT sky path and horizon continuity |
| Frigate | water/sky path, transparency, deck textures |
| Depot | mipmapped roof/floor texture stability |
| Control | glass, alpha, portal/culling boundaries |
| Death/restart | texture-cache correctness after level reload |
| Resize/fullscreen | post-FX texture resize and viewport correctness |
| Screenshot F12 | captured image must include final presentation pass |

For each scene compare PostFX on/off and, where useful, 1x versus 4x/8x MSAA. A graphical feature is not accepted if it fixes one scene by degrading another.

## Build validation

Every normal `build-pc.sh` run now applies and verifies the graphics integration before CMake configuration:

```text
==> Wiring Ascension final graphics pipeline
ascension_graphics_final: integration contracts passed
```

The integration script is idempotent and refuses to guess if a source seam changes.

GitHub Actions additionally builds the complete branch on:

- Windows / MSYS2 MINGW64 — the same environment used for manual user testing;
- Ubuntu / GCC 14 — catches host/compiler assumptions outside MinGW.

## Toolchain note

MSYS2 has moved new development toward UCRT64/CLANG64, while this project currently has a proven MINGW64 user workflow. This release keeps MINGW64 working rather than combining a renderer release with a toolchain migration. A later toolchain migration should be isolated and validated separately.

## Future renderer path

The recommended long-term architecture is still dual-backend rather than a destructive renderer rewrite:

```text
GoldenEye / Ascension
        |
        +--> GoldenEye-aware Fast3D  (compatibility/fallback)
        |
        +--> RT64                    (future modern primary backend)
```

RT64 should become selectable only after it reaches visual parity for GoldenEye's sky/water/custom LLE path and passes the same scene matrix above. At that point Fast3D remains a compatibility/reference backend rather than being deleted.

That migration policy prevents a renderer technology upgrade from silently becoming a gameplay preservation regression.
