#!/usr/bin/env python3
"""Fetch and stage the pinned Steam Audio runtime used by Ascension Audio Remaster.

The SDK binary is intentionally not committed. This helper downloads Valve's
official Steam Audio 4.8.1 release once, verifies GitHub's published SHA-256,
extracts only the platform runtime library, and stages it beside the executable.
The Apache-2.0 license text is tracked in tools_pc/dist so packaging does not
rely on the binary SDK archive containing documentation files.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import platform
import shutil
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "4.8.1"
SDK_URL = "https://github.com/ValveSoftware/steam-audio/releases/download/v4.8.1/steamaudio_4.8.1.zip"
SDK_SHA256 = "4a0aa5ec1176f38f0b0993a37c2259d9e86f27e22d5e24f83ec4c3cb9a1d5449"
CACHE_DIR = ROOT / "third_party" / "steam-audio" / ".cache"
SDK_DIR = ROOT / "third_party" / "steam-audio" / VERSION
LICENSE_NAME = "STEAM-AUDIO-LICENSE.md"
LICENSE_SOURCE = ROOT / "tools_pc" / "dist" / "LICENSE-Steam-Audio-Apache-2.0.md"


def target() -> tuple[str, str, str]:
    system = platform.system().lower()
    if os.name == "nt" or sys.platform.startswith("win") or "mingw" in system:
        return "windows-x64", "phonon.dll", "lib/windows-x64/phonon.dll"
    if system == "linux":
        return "linux-x64", "libphonon.so", "lib/linux-x64/libphonon.so"
    if system == "darwin":
        return "osx", "libphonon.dylib", "lib/osx/libphonon.dylib"
    raise SystemExit(f"Steam Audio bootstrap: unsupported host platform: {platform.system()}")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def download_zip(dest: Path) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    if dest.exists() and sha256(dest) == SDK_SHA256:
        print(f"Steam Audio {VERSION}: verified cached SDK archive")
        return
    if dest.exists():
        dest.unlink()

    print(f"Steam Audio {VERSION}: downloading official Valve SDK (~181 MB)")
    req = urllib.request.Request(SDK_URL, headers={"User-Agent": "GoldenEye-Ascension/0.0.4"})
    with urllib.request.urlopen(req, timeout=120) as response:
        total = int(response.headers.get("Content-Length") or 0)
        with tempfile.NamedTemporaryFile(delete=False, dir=str(CACHE_DIR), suffix=".part") as tmp:
            tmp_path = Path(tmp.name)
            done = 0
            next_report = 16 * 1024 * 1024
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                tmp.write(chunk)
                done += len(chunk)
                if done >= next_report:
                    if total:
                        print(f"  {done // (1024*1024)} / {total // (1024*1024)} MB")
                    else:
                        print(f"  {done // (1024*1024)} MB")
                    next_report += 16 * 1024 * 1024
    got = sha256(tmp_path)
    if got != SDK_SHA256:
        tmp_path.unlink(missing_ok=True)
        raise SystemExit(
            "Steam Audio SDK integrity check failed. "
            f"Expected {SDK_SHA256}, got {got}."
        )
    tmp_path.replace(dest)
    print("Steam Audio SDK archive SHA-256: PASS")


def _extract_member(zf: zipfile.ZipFile, member: str, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    with zf.open(member) as src, out.open("wb") as dst:
        shutil.copyfileobj(src, dst)
    if out.stat().st_size == 0:
        out.unlink(missing_ok=True)
        raise SystemExit(f"Steam Audio SDK extracted an empty file: {member}")


def ensure() -> Path:
    platform_dir, lib_name, suffix = target()
    out_dir = SDK_DIR / platform_dir
    out = out_dir / lib_name
    if out.exists() and out.stat().st_size > 0:
        print(f"Steam Audio {VERSION}: runtime already present: {out.relative_to(ROOT)}")
        return out

    archive = CACHE_DIR / f"steamaudio_{VERSION}.zip"
    download_zip(archive)
    out_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(archive, "r") as zf:
        normalized = [(name, name.replace("\\", "/")) for name in zf.namelist()]
        candidates = [name for name, norm in normalized if norm.endswith(suffix)]
        if not candidates:
            raise SystemExit(f"Steam Audio SDK archive does not contain {suffix}")
        candidates.sort(key=len)
        _extract_member(zf, candidates[0], out)

    print(f"Steam Audio {VERSION}: extracted {out.relative_to(ROOT)}")
    return out


def stage() -> Path:
    lib = ensure()
    if not LICENSE_SOURCE.exists() or LICENSE_SOURCE.stat().st_size < 1000:
        raise SystemExit(f"Steam Audio tracked license missing or invalid: {LICENSE_SOURCE.relative_to(ROOT)}")

    build_dir = ROOT / "build-pc"
    build_dir.mkdir(parents=True, exist_ok=True)
    dest = build_dir / lib.name
    shutil.copy2(lib, dest)
    shutil.copy2(LICENSE_SOURCE, build_dir / LICENSE_NAME)
    print(f"Steam Audio {VERSION}: staged {dest.relative_to(ROOT)}")
    print(f"Steam Audio {VERSION}: staged build-pc/{LICENSE_NAME}")
    return dest


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("command", nargs="?", choices=["ensure", "stage", "path"], default="ensure")
    args = ap.parse_args()
    if args.command == "ensure":
        ensure()
    elif args.command == "stage":
        stage()
    else:
        print(ensure())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
