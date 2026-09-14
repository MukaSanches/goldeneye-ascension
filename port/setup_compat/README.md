# Ascension Setup Compatibility

Clean-room GoldenEye setup interoperability for Ascension.

This module does not embed GoldEditor/Setup Editor implementation code. It provides an Ascension-owned intermediate representation, a safe native setup ingress path, validation, interchange serialization and command-line tooling.

## Build

```sh
cmake -S port/setup_compat -B build-setup-compat
cmake --build build-setup-compat
ctest --test-dir build-setup-compat --output-on-failure
```

## CLI

```sh
# Validate an Ascension interchange file
build-setup-compat/asc-setup validate level.ascsetup

# Inspect sections and source offsets
build-setup-compat/asc-setup inspect level.ascsetup

# Normalize/repack an interchange file
build-setup-compat/asc-setup repack level.ascsetup normalized.ascsetup

# Import an extracted native GoldenEye setup blob safely
build-setup-compat/asc-setup import-native Usetup.bin level.ascsetup
```

On Windows/CMake multi-config generators, the executable may be under a configuration directory such as `Debug/` or `Release/`.

## Safety model

- Native setup roots are decoded as 32-bit big-endian relative offsets.
- Offsets are bounds checked before data is accessed.
- Serialized addresses are never cast directly to host pointers.
- The IR owns its payload copies and is independent from the source buffer lifetime.
- Native semantic decoding and runtime mutation are deliberately separate layers.
- Synthetic test fixtures are used in Git; ROM-derived assets stay local.

See `docs/setup-editor-compatibility.md` for the architecture and roadmap.
