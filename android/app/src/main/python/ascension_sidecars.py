"""First-run generation of host-layout sidecars from the user's own ROM.

The heavy conversion algorithms remain the repository's d43_emit.py and
 d69_emit.py. Android extracts their read-only metadata workspace into HOME,
then this module executes them exactly as the desktop tooling does.
"""
from __future__ import annotations

import os
import runpy
import sys

REGION = "ntsc-final"
_REQUIRED = (
    "data/pcmodels-ntsc-final/pcmodels.bin",
    "data/pcmodels-ntsc-final/manifest.csv",
    "data/pccg-ntsc-final/pccg.bin",
    "data/pccg-ntsc-final/manifest.csv",
)


def _required_ready(home: str) -> bool:
    for rel in _REQUIRED:
        path = os.path.join(home, rel)
        if not os.path.isfile(path) or os.path.getsize(path) <= 0:
            return False
    return True


def ready(home: str) -> bool:
    return _required_ready(os.path.abspath(home))


def _run_tool(home: str, filename: str) -> None:
    script = os.path.join(home, "tools_pc", filename)
    if not os.path.isfile(script):
        raise RuntimeError(f"converter script missing: {filename}")

    old_argv = sys.argv[:]
    try:
        sys.argv = [script, REGION]
        try:
            runpy.run_path(script, run_name="__main__")
        except SystemExit as exc:
            if exc.code not in (None, 0):
                raise RuntimeError(f"{filename} exited with status {exc.code}") from exc
    finally:
        sys.argv = old_argv


def generate(home: str) -> str:
    home = os.path.abspath(home)
    rom = os.path.join(home, "data", f"ge007.{REGION}.z64")
    if not os.path.isfile(rom) or os.path.getsize(rom) <= 0:
        raise RuntimeError("user ROM is missing from app-private storage")
    if _required_ready(home):
        return "ready"

    old_cwd = os.getcwd()
    try:
        os.chdir(home)
        _run_tool(home, "d43_emit.py")
        _run_tool(home, "d69_emit.py")
    finally:
        os.chdir(old_cwd)

    if not _required_ready(home):
        missing = [rel for rel in _REQUIRED
                   if not os.path.isfile(os.path.join(home, rel))
                   or os.path.getsize(os.path.join(home, rel)) <= 0]
        raise RuntimeError("sidecar generation incomplete: " + ", ".join(missing))
    return "generated"
