#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# Prefer an explicit override for unusual environments, then the conventional
# Python 3 command used by current Linux/macOS hosts, while retaining `python`
# compatibility for Windows/MSYS2 installations where that is the installed
# Python 3 executable. Validate the major version before running any patcher.
PYTHON_BIN="${ASCENSION_PYTHON:-}"
if [[ -z "$PYTHON_BIN" ]]; then
    if command -v python3 >/dev/null 2>&1; then
        PYTHON_BIN="python3"
    elif command -v python >/dev/null 2>&1; then
        PYTHON_BIN="python"
    else
        echo "ERROR: Python 3 is required to apply the Ascension patch pack." >&2
        exit 2
    fi
fi

if ! "$PYTHON_BIN" -c 'import sys; raise SystemExit(0 if sys.version_info.major == 3 else 1)' >/dev/null 2>&1; then
    echo "ERROR: '$PYTHON_BIN' is not a working Python 3 interpreter." >&2
    echo "       Set ASCENSION_PYTHON to the Python 3 executable to use." >&2
    exit 2
fi

# Fail before patching the source tree when the build tool is unavailable.
# build-pc.sh requires CMake, so discovering this prerequisite up front keeps
# a local checkout unchanged when it cannot be built or tested anyway.
if ! command -v cmake >/dev/null 2>&1; then
    echo "ERROR: CMake is required to build and test GoldenEye Ascension." >&2
    echo "       Install CMake for your platform, then rerun this command." >&2
    exit 2
fi

# The runner invokes build-pc.sh directly after patching. Verify the script is
# present and executable first so a damaged/incomplete checkout cannot be
# modified by the Ascension patch pack before an inevitable build failure.
if [[ ! -f ./build-pc.sh ]]; then
    echo "ERROR: build-pc.sh was not found at the repository root." >&2
    echo "       Restore the build script before running the Ascension test." >&2
    exit 2
fi
if [[ ! -x ./build-pc.sh ]]; then
    echo "ERROR: build-pc.sh is not executable." >&2
    echo "       Run 'chmod +x build-pc.sh' and retry." >&2
    exit 2
fi

echo "==> Applying validated Ascension low-risk pack with $PYTHON_BIN..."
"$PYTHON_BIN" tools_pc/apply_ascension_safe_gameplay_pack.py

echo "==> Building NTSC-final PC target..."
rm -rf build-pc
./build-pc.sh ntsc-final

# CMake emits an .exe on Windows and an extensionless executable on Unix-like
# hosts. Keep the test runner aligned with the port's documented Windows,
# Linux and macOS build support instead of assuming one host filename.
BIN=""
for candidate in \
    "build-pc/ge007.x86_64.exe" \
    "build-pc/ge007.x86_64" \
    "build-pc/ge007.exe" \
    "build-pc/ge007"; do
    # A successful build artifact must also be non-empty. This prevents a
    # truncated/zero-byte executable from being reported as a verified build.
    if [[ -s "$candidate" && ( -x "$candidate" || "$candidate" == *.exe ) ]]; then
        BIN="$candidate"
        break
    fi
done

if [[ -z "$BIN" ]]; then
    echo "ERROR: built GoldenEye executable not found in build-pc/ or is empty" >&2
    echo "       Expected non-empty ge007(.exe) or ge007.x86_64(.exe)." >&2
    exit 2
fi

echo "==> Build verified: $BIN"

# Keep the normal local workflow unchanged, while allowing CI/automation to
# validate the complete patch+build path without trying to open an SDL window.
if [[ "${ASCENSION_NO_LAUNCH:-0}" == "1" ]]; then
    echo "==> ASCENSION_NO_LAUNCH=1; skipping game launch."
    exit 0
fi

echo "==> Launching GoldenEye Ascension: $BIN"
exec "./$BIN"
