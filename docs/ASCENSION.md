# Ascension

Ascension is an independent development line for a modern PC experience built from the GoldenEye 007 decompilation/port ecosystem.

## What independence means

Ascension owns its roadmap, release criteria, localization architecture, PC UX, controls, accessibility direction, tooling and compatibility policy. Other projects may be studied as references, but Ascension does not automatically mirror their main branches.

Independence does not erase history. Existing authorship, licenses and notices remain authoritative for inherited code. Any externally derived change must retain appropriate attribution and satisfy its license.

## Product pillars

1. **Classic preservation** — keep a path close to established/original behavior.
2. **Localization** — first-class language architecture, with Brazilian Portuguese as the first Ascension localization effort and English retained as a fallback/reference.
3. **Modern PC controls** — discoverable, configurable keyboard, mouse and controller behavior.
4. **PC-native settings** — configuration should be understandable in-game rather than requiring undocumented manual edits.
5. **Accessibility** — add tested player-facing options without changing mission design accidentally.
6. **Modern presentation** — resolution, HUD and presentation improvements should be optional and regression-tested.
7. **Modding and creator tooling** — long-term APIs/tools should expose stable semantic interfaces instead of requiring invasive game patches.
8. **Reversible engineering** — coherent commits, explicit rollback points and no untraceable feature dumps.

## Source and asset policy

Ascension does not distribute commercial ROMs or proprietary game assets. Users must provide legally obtained required source material where the build process requires it.

## External engineering intake

For each external implementation, classify it before adoption:

- **REUSE** — compatible, licensed, understood and suitable for direct integration.
- **ADAPT** — concept/implementation is useful but requires Ascension-specific changes.
- **LEARN** — valuable reference, but code should not be copied.
- **AVOID** — incompatible, risky, insufficiently verified or unsuitable.

Functional changes require build/test evidence appropriate to their subsystem. Rendering and input changes additionally require human playtesting when automated checks cannot validate visual correctness or control feel.

## Upstream relationship

The project retains the full Git history and credits of the work it was built from. That history is provenance, not product governance. Future external fixes are candidates for review rather than automatic synchronization.
