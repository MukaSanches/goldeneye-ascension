#!/usr/bin/env bash
#
# Package a Windows GoldenEye 007 PC port build for distribution.
#
# Run from anywhere, inside the MSYS2 MINGW64 shell, AFTER ./build-pc.sh:
#
#     tools_pc/bundle-win.sh [VERSION]
#
# Produces, under dist/ :
#     goldeneye-pc-port-<VERSION>-win64/        the unpacked bundle
#     goldeneye-pc-port-<VERSION>-win64.zip     + .zip.sha256
#
# The bundle contains ONLY: the engine executable, its runtime DLLs, a README,
# and license texts. It contains NO ROM and NO game assets (textures, audio,
# models, levels, text) — the user supplies those at runtime from a ROM they
# own. The script hard-fails if a ROM image or oversized blob ends up inside.
#
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

VERSION="${1:-$(git describe --tags --always --dirty 2>/dev/null || echo 0.0.0-dev)}"
VERSION="${VERSION#v}"
NAME="goldeneye-pc-port-${VERSION}-win64"
OUT="dist/${NAME}"
MINGW="${MINGW_PREFIX:-/mingw64}"

EXE="$(ls build-pc/ge007*.exe 2>/dev/null | head -n1 || true)"
[ -n "$EXE" ] || { echo "error: no build-pc/ge007*.exe found — run ./build-pc.sh first" >&2; exit 1; }

echo "==> Bundling $EXE  ->  $NAME"
rm -rf "$OUT"
mkdir -p "$OUT/licenses"
cp "$EXE" "$OUT/"

# --- MinGW / SDL runtime DLLs --------------------------------------------
DLLS=(
  SDL2.dll
  zlib1.dll
  libwinpthread-1.dll
  libstdc++-6.dll
  libgcc_s_seh-1.dll
  libssp-0.dll
)
for d in "${DLLS[@]}"; do
  if [ -f "$MINGW/bin/$d" ]; then
    cp "$MINGW/bin/$d" "$OUT/"
    echo "    + $d"
  else
    echo "    . $d (not in $MINGW/bin — skipped)"
  fi
done

# --- Ascension Audio Remaster runtime ------------------------------------
# Steam Audio is dynamically loaded, so ldd on the game executable cannot
# discover it. The audio branch stages the pinned Valve runtime explicitly.
# This keeps the end-user experience zero-install: phonon.dll lives beside
# ge007.exe and the game activates HRTF automatically.
if [ -f port/src/ascension_audio_remaster.c ]; then
  if [ ! -f build-pc/phonon.dll ] || [ ! -f build-pc/STEAM-AUDIO-LICENSE.md ]; then
    python tools_pc/ensure_steam_audio.py stage
  fi
  [ -s build-pc/phonon.dll ] || { echo "error: Steam Audio phonon.dll missing" >&2; exit 1; }
  [ -s build-pc/STEAM-AUDIO-LICENSE.md ] || { echo "error: Steam Audio license missing" >&2; exit 1; }
  cp build-pc/phonon.dll "$OUT/phonon.dll"
  cp build-pc/STEAM-AUDIO-LICENSE.md "$OUT/licenses/LICENSE-Steam-Audio-Apache-2.0.md"
  echo "    + phonon.dll (Steam Audio 4.8.1)"

  if command -v ldd >/dev/null 2>&1; then
    if ldd build-pc/phonon.dll | tee /tmp/ascension-phonon-ldd.txt | grep -qi 'not found'; then
      echo "error: Steam Audio phonon.dll has unresolved runtime dependencies" >&2
      cat /tmp/ascension-phonon-ldd.txt >&2
      exit 1
    fi
  fi
fi

# --- verify executable dependency closure --------------------------------
missing=0
if command -v ldd >/dev/null 2>&1; then
  while read -r name _ path _; do
    case "$path" in
      "$MINGW"/*|*/mingw64/*)
        [ -f "$OUT/$name" ] || { echo "    MISSING: $name  ($path)" >&2; missing=1; } ;;
    esac
  done < <(ldd "$EXE")
else
  echo "    (ldd unavailable — skipping closure check)"
fi
[ "$missing" -eq 0 ] || { echo "error: exe needs MinGW DLLs that were not bundled (see above)" >&2; exit 1; }

# --- docs + licenses ------------------------------------------------------
EXE_NAME="$(basename "$EXE")"
sed -e "s|@VERSION@|${VERSION}|g" \
    -e "s|@PLATFORM@|Windows x86-64|g" \
    -e "s|@EXE@|${EXE_NAME}|g" \
    -e "s|@DEPS@||g" \
    -e "s|@LICENSE_EXTRA@|, the MinGW runtime, and Steam Audio 4.8.1|g" \
    tools_pc/dist/README.md.in > "$OUT/README.md"
cp NOTICE  "$OUT/licenses/NOTICE"
cp LICENSE "$OUT/licenses/LICENSE-port-MIT.txt"
[ -f port/fast3d/LICENSE.txt ] && cp port/fast3d/LICENSE.txt "$OUT/licenses/LICENSE-fast3d.txt"
for l in SDL2 zlib gcc-libs libwinpthread mingw-w64; do
  [ -d "$MINGW/share/licenses/$l" ] && cp -r "$MINGW/share/licenses/$l" "$OUT/licenses/$l"
done

# --- asset-prep tool ------------------------------------------------------
PREP="$OUT/prepare-assets"
mkdir -p "$PREP/vendor/scripts" "$PREP/vendor/assets/obseg"
cp tools_pc/dist/prepare-assets/prepare-assets.py "$PREP/"
cp tools_pc/d43_emit.py tools_pc/d69_emit.py       "$PREP/"
cp tools_pc/d88_emit.py tools_pc/d88_propdefs.py   "$PREP/"
cp scripts/filelist.u.csv                          "$PREP/vendor/scripts/"
cp assets/obseg/file_resource_table.inc.c          "$PREP/vendor/assets/obseg/"
( cd . && find assets -iname 'modelfileheader.inc.c' -print0 \
    | xargs -0 -I{} cp --parents {} "$PREP/vendor/" )
nmh="$(find "$PREP/vendor/assets" -iname 'modelfileheader.inc.c' | wc -l)"
echo "    + prepare-assets/ (emit scripts + $nmh model headers)"
[ "$nmh" -gt 400 ] || { echo "error: prepare-assets vendored only $nmh model headers — expected ~512" >&2; exit 1; }

# --- guard: no ROM / game data snuck in ---------------------------------
if find "$OUT" -type f \( -iname '*.z64' -o -iname '*.n64' -o -iname '*.v64' \) | grep -q .; then
  echo "error: bundle contains a ROM image — aborting" >&2
  exit 1
fi
BYTES="$(du -sb "$OUT" | cut -f1)"
LIMIT=$((60 * 1024 * 1024))
if [ "$BYTES" -gt "$LIMIT" ]; then
  echo "error: bundle is $BYTES bytes (> 60 MB) — likely contains game data, aborting" >&2
  exit 1
fi

# --- zip + checksum -------------------------------------------------------
zip_dir() {
  if command -v zip >/dev/null 2>&1; then
    ( cd dist && zip -qr "$1" "$2" )
  elif command -v 7z >/dev/null 2>&1; then
    ( cd dist && 7z a -tzip -bso0 -bsp0 "$1" "$2" >/dev/null )
  elif [ -x "/c/Program Files/7-Zip/7z.exe" ]; then
    ( cd dist && "/c/Program Files/7-Zip/7z.exe" a -tzip -bso0 -bsp0 "$1" "$2" >/dev/null )
  elif command -v powershell >/dev/null 2>&1; then
    ( cd dist && powershell -NoProfile -Command \
        "Compress-Archive -Force -Path '$2' -DestinationPath '$1'" )
  else
    echo "error: need one of: zip, 7z, or powershell to package the bundle" >&2
    exit 1
  fi
}
( cd dist && rm -f "${NAME}.zip" "${NAME}.zip.sha256" )
zip_dir "${NAME}.zip" "$NAME"
( cd dist && sha256sum "${NAME}.zip" > "${NAME}.zip.sha256" )

echo "==> dist/${NAME}.zip  ($(du -h "dist/${NAME}.zip" | cut -f1))"
cat "dist/${NAME}.zip.sha256"
( cd dist && unzip -l "${NAME}.zip" ) 2>/dev/null \
  || find "$OUT" -type f | sed "s#^dist/##" | sort
