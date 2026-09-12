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

## Provenance / third-party work

<!-- Keep this explicit whenever the change was inspired by another port,
     mod, patch, tool, forum post, issue, or codebase. -->

- [ ] External implementations or research used by this PR are linked below,
      including the exact project / commit / issue when practical.
- [ ] Any reused or adapted code is license-compatible with this repository
      and attribution / NOTICE requirements are satisfied.
- [ ] No ROM, extracted game assets, proprietary SDK files, or other
      redistributable game content are included.
- [ ] If no third-party implementation or material was used, write `None`
      below rather than leaving provenance ambiguous.

Sources / provenance: <!-- URLs + short note, or None -->

## Verification

<!-- What you actually ran. Delete lines that don't apply. -->

- [ ] `./build-pc.sh ntsc-final` — clean configure + link
- [ ] Crash-free run of at least one level (`-level_09`)
- [ ] Single-frame `GE_PCDUMP` diff against the committed golden — no
      unexpected change
- [ ] pal-final / jpn-final also configured

Platform tested: <!-- e.g. Windows 10 / MSYS2 MINGW64 -->

## Notes for the reviewer

<!-- Anything uncertain, follow-ups, or areas that need a closer look. -->
