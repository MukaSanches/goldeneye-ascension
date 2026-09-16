#!/usr/bin/env bash
#
# Build the GoldenEye 007 PC port.
#
# Usage:
#   ./build-pc.sh [ntsc-final|pal-final|jpn-final]
#
# Dependencies (see docs/building.md):
#   - CMake >= 3.16
#   - SDL2 dev
#   - zlib dev
#   - OpenGL dev (opengl32 on Windows, GL on Linux, OpenGL.framework on macOS)
#
# Example (Linux):
#   sudo apt install cmake libsdl2-dev zlib1g-dev libgl1-mesa-dev
# Example (macOS):
#   brew install cmake sdl2 zlib
# Example (Windows/MSYS2):
#   pacman -S mingw-w64-x86_64-toolchain mingw-w64-x86_64-SDL2 \
#             mingw-w64-x86_64-zlib mingw-w64-x86_64-cmake
#
set -euo pipefail

ROMID="${1:-ntsc-final}"
BUILD_DIR="${BUILD_DIR:-build-pc}"

# Real-world positional audio is deliberately wired at build time instead of
# carrying a giant generated propobj.c diff. The patcher is idempotent and
# fails closed if the decomp seam ever changes.
PYTHON_BIN="${PYTHON:-python3}"
if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
  PYTHON_BIN="python"
fi

echo "==> Wiring Ascension real-world 3D audio"
"${PYTHON_BIN}" scripts/apply_audio_world_integration.py

# Keep the acoustic math warning-clean on the exact compiler doing the game
# build. This catches the same class of MinGW issue before the expensive link.
mkdir -p "${BUILD_DIR}"
AUDIO_WORLD_TEST="${BUILD_DIR}/test_ascension_audio_world"
if [[ "${OS:-}" == "Windows_NT" || "$(uname -s 2>/dev/null || true)" == MINGW* || "$(uname -s 2>/dev/null || true)" == MSYS* ]]; then
  AUDIO_WORLD_TEST="${AUDIO_WORLD_TEST}.exe"
fi

echo "==> Verifying Ascension acoustic-world core (-Werror)"
gcc \
  -std=gnu11 \
  -Wall \
  -Wextra \
  -Werror \
  -DASC_AUDIO_WORLD_TEST_SYNC=1 \
  -Iport/include \
  port/src/ascension_audio_world.c \
  port/tests/test_ascension_audio_world.c \
  -pthread \
  -lm \
  -o "${AUDIO_WORLD_TEST}"
"${AUDIO_WORLD_TEST}"

echo "==> Configuring PC port (ROMID=${ROMID})"
cmake -S . -B "${BUILD_DIR}" -DROMID="${ROMID}"

echo "==> Building"
cmake --build "${BUILD_DIR}" -j

echo "==> Done."
echo "    Binary: ${BUILD_DIR}/ge007.*"
echo "    Put your ROM in ./data/ (see README) and run the binary."
