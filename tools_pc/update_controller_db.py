#!/usr/bin/env python3
"""Fetch the pinned SDL_GameControllerDB snapshot used by Ascension.

The game never downloads controller data at runtime.  This helper is invoked by
`ascension.py play` as a best-effort developer convenience and can also be run
explicitly.  Failure is non-fatal when --optional is supplied because SDL2's
built-in/XInput database plus Ascension's generic fallback remain available.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PINNED_COMMIT = "5a12daa568d19344f9b6e9286ef5929833b25c7c"
SOURCE = (
    "https://raw.githubusercontent.com/mdqinc/SDL_GameControllerDB/"
    f"{PINNED_COMMIT}/gamecontrollerdb.txt"
)
DEST = ROOT / "data/gamecontrollerdb.txt"
META = ROOT / "data/gamecontrollerdb.meta.txt"


def validate(data: bytes) -> None:
    if len(data) < 100_000:
        raise ValueError(f"controller DB unexpectedly small ({len(data)} bytes)")
    text = data.decode("utf-8")
    required = (
        "# Game Controller DB for SDL",
        "platform:Windows,",
        "platform:Linux,",
        "xinput,XInput Controller",
    )
    for needle in required:
        if needle not in text:
            raise ValueError(f"controller DB missing expected marker {needle!r}")


def download(timeout: int) -> bytes:
    req = urllib.request.Request(
        SOURCE,
        headers={"User-Agent": "GoldenEye-Ascension-controllerdb/0.0.4"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read()


def write_atomic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--optional", action="store_true")
    ap.add_argument("--timeout", type=int, default=15)
    args = ap.parse_args()

    try:
        data = download(args.timeout)
        validate(data)
        digest = hashlib.sha256(data).hexdigest()
        write_atomic(DEST, data)
        meta = (
            "Ascension controller mapping database\n"
            f"source={SOURCE}\n"
            f"commit={PINNED_COMMIT}\n"
            f"sha256={digest}\n"
            "license=zlib (SDL_GameControllerDB)\n"
            "priority=community; explicit data/ascension-controller-mappings.txt overrides this file\n"
        ).encode("utf-8")
        write_atomic(META, meta)
        print(f"Controller DB: PASS ({len(data)} bytes, sha256={digest})")
        print(f"Saved: {DEST.relative_to(ROOT)}")
        return 0
    except (OSError, UnicodeError, ValueError, urllib.error.URLError) as exc:
        message = f"Controller DB update unavailable: {exc}"
        if args.optional:
            print("NOTE:", message)
            print("Using SDL built-in/XInput mappings + Ascension generic fallback.")
            return 0
        print("ERROR:", message, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
