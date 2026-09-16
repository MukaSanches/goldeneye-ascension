# GoldenEye Ascension compatibility contract

Ascension extends the PC port without turning the project into a different game by default. These invariants are part of the project contract and should be treated as release blockers when a change unintentionally violates them.

## 1. ROM ownership and distribution

- Ascension never bundles a GoldenEye 007 ROM.
- The player must supply a legally owned compatible ROM exactly as required by the underlying PC port.
- Nintendo/Rare assets extracted from a ROM are not committed or distributed by Ascension.
- Build, CI and release automation must remain useful without embedding ROM data.

## 2. Save compatibility

- Existing saves must remain readable unless a future migration is explicitly designed, documented and tested.
- Changes to EEPROM/save serialization require a pre-change save compatibility test before merge.
- Ascension options should prefer the PC configuration layer instead of consuming original save fields.

## 3. Original behavior remains available

- `Classic` is the default Ascension control preset for a new configuration.
- Classic must preserve original GoldenEye behavior unless a narrowly scoped bug fix is demonstrably required by the PC port itself.
- Hybrid and Modern may intentionally reinterpret PC input, but only when the player selects those presets/options.
- New gameplay-affecting behavior must be opt-in unless it is behavior-neutral infrastructure, diagnostics or a compatibility fix.

## 4. PT-BR preservation

- Existing PT-BR work must not be deleted, overwritten or silently replaced by English-only text.
- Changes to user-facing strings must be reviewed for localization impact.
- Refactors should preserve translation identifiers and data layout whenever practical.

## 5. Reversible tooling

- Ascension patchers must remain anchor-validated and idempotent.
- Patchers must fail before mutation when their expected source context is missing.
- Local backup artifacts created for reversibility must never be tracked by Git or included in release bundles.
- Large speculative source rewrites are out of scope for the low-risk Ascension patch pack.

## 6. Repository hygiene

- No ROM images (`.z64`, `.n64`, `.v64`) belong in Git history or release artifacts.
- Generated local build output, patcher backups and temporary test files should remain ignored.
- Public documentation must describe the current project state rather than an upstream or obsolete phase.

## 7. Verification levels

A change should be validated at the lowest level that can actually prove it safe:

1. **Static:** syntax, manifest, repository hygiene and compatibility contracts.
2. **Build:** configure/compile/link on supported CI toolchains.
3. **Runtime:** ROM-backed smoke test for input, UI, level loading or gameplay behavior.
4. **Compatibility:** existing saves, Classic behavior and PT-BR preservation when relevant.

`python3 tools_pc/verify_ascension_contracts.py` covers the non-ROM static layer. `docs/ascension-smoke-test.md` covers the runtime layer that still needs a real game session.

## Review rule

If a change cannot be validated at the level required by its risk, do not merge it as a gameplay change. Prefer research, documentation, a test harness or a smaller reversible step first.
