#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "==> Applying validated Ascension low-risk pack..."
python tools_pc/apply_ascension_safe_gameplay_pack.py

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
    if [[ -f "$candidate" && ( -x "$candidate" || "$candidate" == *.exe ) ]]; then
        BIN="$candidate"
        break
    fi
done

if [[ -z "$BIN" ]]; then
    echo "ERROR: built GoldenEye executable not found in build-pc/" >&2
    echo "       Expected ge007(.exe) or ge007.x86_64(.exe)." >&2
    exit 2
fi

echo "==> Launching GoldenEye Ascension: $BIN"
exec "./$BIN"
