<!--
Read CONTRIBUTING.md first. This is a faithfulness-focused port; the ground
rules there are non-negotiable.
-->

## What this changes

<!-- One or two sentences. Link the issue it closes: "Closes #123". -->

## Why

<!-- The reasoning, not just the diff. What was wrong / missing? -->

## Scope check

- [ ] No changes under `src/` or `include/` — **or** the only changes are the
      narrow `#ifdef PORT` ABI exception (CONTRIBUTING.md rule 2), and each is
      documented in `docs/porting-notes.md` / `docs/dev/findings.md`.
- [ ] `Makefile`, `tools/`, `rsp/`, `ld/` untouched (N64 build).
- [ ] If `CMakeLists.txt` `REGION_DEFS` changed, it still matches the N64
      `Makefile` per-region macro set exactly.

### Ascension compatibility

<!-- Preserve these invariants unless the PR explicitly documents why a
     narrowly-scoped Ascension option intentionally changes one of them. -->

- [ ] The user must still supply a legally owned GoldenEye 007 ROM; no ROM,
      extracted Nintendo assets, or copyrighted game data is added.
- [ ] Existing save files remain compatible, or this PR does not touch save
      serialization / EEPROM behavior.
- [ ] Existing PT-BR work remains intact; changed user-facing strings were
      checked for localization impact.
- [ ] Original GoldenEye behavior remains the default. Any intentional
      gameplay/control behavior change is explicitly enabled by an Ascension
      option or preset.

## Verification

<!-- What you actually ran. Delete lines that don't apply. -->

- [ ] `./build-pc.sh ntsc-final` — clean configure + link
- [ ] Crash-free run of at least one level (`-level_09`)
- [ ] Single-frame `GE_PCDUMP` diff against the committed golden — no
      unexpected change
- [ ] pal-final / jpn-final also configured
- [ ] If Ascension patchers, controls, F10 options, or PC UX changed:
      `ASCENSION_NO_LAUNCH=1 ./tools_pc/run_ascension_safe_test.sh`
- [ ] If controls or input behavior changed: completed the **Ascension controls**
      section of `docs/ascension-smoke-test.md`, including CLASSIC / HYBRID /
      MODERN coverage and saved-preset persistence.

Platform tested: <!-- e.g. Windows 10 / MSYS2 MINGW64 -->

## Notes for the reviewer

<!-- Anything uncertain, follow-ups, or areas that need a closer look. -->
