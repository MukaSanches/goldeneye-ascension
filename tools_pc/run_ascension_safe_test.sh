#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "==> Applying validated Ascension low-risk pack..."
python tools_pc/apply_ascension_safe_gameplay_pack.py

echo "==> Building NTSC-final PC target..."
rm -rf build-pc
./build-pc.sh ntsc-final

BIN="build-pc/ge007.x86_64.exe"
if [[ ! -f "$BIN" ]]; then
    echo "ERROR: expected binary not found: $BIN" >&2
    exit 2
fi

echo "==> Launching GoldenEye Ascension..."
exec "./$BIN"
