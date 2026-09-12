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

# Ascension PT-BR uses GNU ld's symbol wrapping so the original GoldenEye text
# renderer remains byte-for-byte intact while the PC build gains UTF-8-aware
# rendering/measurement/wrapping. MinGW and GNU/Linux ld support --wrap;
# macOS keeps the original path until an equivalent interpose layer is added.
EXTRA_LINK_FLAGS="${CMAKE_EXE_LINKER_FLAGS:-}"
case "$(uname -s 2>/dev/null || true)" in
  MINGW*|MSYS*|CYGWIN*|Linux*)
    EXTRA_LINK_FLAGS+=" -Wl,--wrap=textRender"
    EXTRA_LINK_FLAGS+=" -Wl,--wrap=textRenderOutlined"
    EXTRA_LINK_FLAGS+=" -Wl,--wrap=textMeasure"
    EXTRA_LINK_FLAGS+=" -Wl,--wrap=textWrap"
    ;;
esac

echo "==> Configuring PC port (ROMID=${ROMID})"
cmake -S . -B "${BUILD_DIR}" \
  -DROMID="${ROMID}" \
  -DCMAKE_EXE_LINKER_FLAGS="${EXTRA_LINK_FLAGS}"

echo "==> Building"
cmake --build "${BUILD_DIR}" -j

echo "==> Done."
echo "    Binary: ${BUILD_DIR}/ge007.*"
echo "    Put your ROM in ./data/ (see README) and run the binary."
