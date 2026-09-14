# Ascension Setup Editor Compatibility Layer

## Purpose

GoldenEye Ascension needs first-class map/mission tooling without coupling the PC runtime to one editor implementation. This layer defines an Ascension-owned boundary for setup data so converters, inspectors, future GUI tools and the runtime can communicate through one stable model.

It is **not** a copy of GoldEditor/GoldenEye Setup Editor source code. The public GoldEditor repository currently advertises CC BY-NC-ND 4.0; modified/adapted redistribution is therefore not an acceptable foundation for Ascension. Compatibility is implemented independently from public format knowledge, observable behaviour and GoldenEye's decompiled engine structures.

## Ground truth

The GoldenEye engine's `stagesetup` model is the runtime truth. Its canonical roots are:

1. path table
2. path links
3. intro
4. object list
5. paths
6. AI lists
7. pads
8. 3D pads
9. pad names
10. 3D pad names

The decompilation/reference tooling shows these roots serialized as 32-bit big-endian offsets relative to the beginning of the loaded setup file. Ascension therefore keeps native references as fixed-width integer offsets until an explicit decoder validates and relocates them.

Ascension must preserve game behaviour. Native setup decoding belongs in a port/tooling adapter; game logic under `src/game/` remains untouched.

## Architecture

```text
External editor / converter / future Ascension GUI
                    |
                    v
        +---------------------------+
        | AscSetupDocument (IR)     |
        | versioned + validated     |
        | stable ids + raw payloads |
        +---------------------------+
             |               |
             v               v
      Native GE codec    ASCSETUP codec
             |               |
             v               v
      runtime bridge     tooling / CLI / tests
             |
             v
      GoldenEye StageSetup
```

The intermediate representation (IR) is intentionally pointer-free and editor-neutral. Runtime pointers are never serialized.

## Current implementation

### Core IR

The compatibility core currently provides:

- a versioned `AscSetupDocument` IR;
- canonical setup section kinds corresponding to the StageSetup roots;
- stable IDs for editor-side references;
- original source offsets for diagnostics and future relocation work;
- unknown/raw section preservation at the IR level;
- structural validation and diagnostics;
- hard safety limits against malformed or hostile files;
- a runtime-neutral root view;
- no dependency on editor GUI code or ROM-derived assets.

### ASCSETUP container

`ASCSETUP` is an Ascension-owned interchange format for tooling and tests. It is **not** the original ROM setup format and is not intended to replace the native setup files.

Header, little-endian:

| Offset | Size | Meaning |
|---:|---:|---|
| 0x00 | 8 | ASCII `ASCSETUP` |
| 0x08 | 4 | format version |
| 0x0c | 4 | section count |

Each directory entry is 20 bytes:

| Field | Size |
|---|---:|
| section kind | 4 |
| stable id | 4 |
| flags | 4 |
| payload offset | 4 |
| payload size | 4 |

Payloads follow the directory. The codec performs bounds, overflow, count and size checks before exposing data.

### Native GoldenEye reader

`asc_setup_native_read_roots()` reads the ten serialized StageSetup roots as big-endian 32-bit offsets. Every non-zero offset must point inside the supplied blob and beyond the root table before it can be used.

`asc_setup_native_import()` performs a lossless coarse import:

1. validates the full root table;
2. keeps offsets as integers;
3. finds each root's raw byte interval by locating the next greater root offset;
4. copies that interval into the corresponding pointer-free IR section;
5. retains the original source offset;
6. validates the resulting document.

This is intentionally below the semantic decoder layer. It provides a safe native-file ingress path before object, AI, intro and path record interpretation is added.

### Command-line tooling

The standalone `asc-setup` utility currently supports:

```text
asc-setup validate      <file.ascsetup>
asc-setup inspect       <file.ascsetup>
asc-setup repack        <input.ascsetup> <output.ascsetup>
asc-setup import-native <native-setup.bin> <output.ascsetup>
```

The CLI has an independent file-size ceiling, reports structural diagnostics and never mutates live game state.

### Build

The module can be compiled independently:

```sh
cmake -S port/setup_compat -B build-setup-compat
cmake --build build-setup-compat
ctest --test-dir build-setup-compat --output-on-failure
```

Its CMake file is also structured so the directory can later be embedded with `add_subdirectory()` by the main PC build without declaring a nested project.

## Important boundary rule

`asc_setup_runtime_roots_from_document()` exposes pointers to IR section payloads only. Those pointers are **not automatically native GoldenEye structs**. A native-format adapter must decode pointer-width, endian and record-layout details before the runtime can consume a section as `stagesetup` data. This is deliberate: the codec layer must never make a 32-bit N64 serialized pointer look like a valid 64-bit host pointer.

## Compatibility roadmap

### Phase A — foundation — implemented

- IR and validation;
- deterministic ASCSETUP codec;
- clean-room boundary documentation;
- synthetic corruption and round-trip tests;
- standalone/embeddable CMake target.

### Phase B1 — native root reader — implemented

- ten-root big-endian reader;
- bounds checks before relocation;
- raw root-region import into the IR;
- CLI import path;
- synthetic native-root tests.

### Phase B2 — semantic native setup reader

Implement typed decoding above the raw root regions:

- object-list command stream by opcode/record length;
- intro records;
- AI-list directory and script bodies while retaining unknown opcodes byte-for-byte;
- pads and 3D pads;
- path table, path links and path sets;
- names/string tables;
- original source offsets on every typed node.

No native record is allowed to be read by casting an untrusted byte buffer to a host struct.

### Phase C — semantic object model

Add typed records for the Setup Editor concepts used by the community:

- doors and door scales;
- standard props, keys, alarms, cameras and autoguns;
- ammo, weapons, armour and hats;
- guards and guard attributes;
- monitors and linked monitors;
- objectives and objective conditions;
- tags, links and presets;
- paths, waypoints and guard patrols;
- intro/spawn records;
- AI action blocks and script references.

Every typed node retains a stable ID and its original raw form where necessary so unsupported records survive load/save.

### Phase D — native writer + round-trip proof

- encode a semantic document back to the extracted native setup representation;
- byte-diff fixtures where exact preservation is expected;
- semantic-diff fixtures where relocation changes are expected;
- reject unresolved references instead of emitting corrupt data;
- deterministic output for reproducible builds.

### Phase E — runtime integration

- port-layer adapter constructs runtime-ready StageSetup data;
- developer-only level reload hook;
- safe teardown/reload lifecycle for props, AI and path data;
- runtime diagnostics shown in the developer console;
- no changes to original game control flow.

### Phase F — Ascension level tooling

The same IR becomes the data source for:

- Level Inspector;
- object/pad/path browser;
- room/portal/STAN overlays;
- AI-list disassembler/editor;
- objective editor;
- validation panel;
- import/export bridge for community workflows.

## Engineering invariants

1. `src/game/` behaviour remains the ground truth and is not altered for editor support.
2. The N64 build is untouched.
3. All file parsing is bounds checked before dereference.
4. Serialized addresses are fixed-width integers until explicitly relocated.
5. Unknown records should be preserved whenever their length can be determined safely.
6. Parsing and validation never mutate live game state.
7. Native write support is gated behind round-trip tests.
8. No ROM-derived assets are committed to the repository.
9. No GoldEditor/Setup Editor implementation code is copied into Ascension.
10. Compatibility claims are backed by fixtures/tests, not assumptions.

## Testing strategy

Synthetic fixtures are the default and contain no copyrighted game content. Later local tests may operate on assets extracted from a user's own ROM, but those fixtures must remain outside Git.

The current tests cover:

- ASCSETUP encode/decode round-trip;
- invalid magic;
- duplicate stable IDs;
- truncated directory;
- native big-endian root decoding;
- native raw-region import;
- out-of-range native roots.

Minimum gates for each future native record family:

- valid minimum record;
- valid maximum/edge values;
- truncated record;
- invalid reference;
- integer-overflow attempt;
- unknown opcode/record preservation;
- decode -> encode -> decode semantic equivalence.

## Why this design

A direct editor-to-runtime dependency would make map tooling fragile and would mix GUI concerns, binary parsing and live game state. The IR boundary lets Ascension support the existing community workflow and a native Ascension editor without rewriting the game integration each time.
