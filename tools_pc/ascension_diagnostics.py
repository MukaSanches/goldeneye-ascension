#!/usr/bin/env python3
"""Print a concise, non-destructive Ascension environment report.

The report is designed for bug triage. It never reads ROM contents and never
prints save/config contents. ROM candidates are counted only by extension.
"""
from __future__ import annotations

from pathlib import Path
import platform
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def command_output(args: list[str]) -> str:
    try:
        result = subprocess.run(
            args,
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return "unavailable"
    if result.returncode != 0:
        return "unavailable"
    line = result.stdout.strip().splitlines()
    return line[0] if line else "available"


def git_value(*args: str) -> str:
    return command_output(["git", *args]) if shutil.which("git") else "unavailable"


def main() -> int:
    print("GoldenEye Ascension diagnostics")
    print("===============================")
    print(f"OS: {platform.platform()}")
    print(f"Python: {platform.python_version()}")
    print(f"Git branch: {git_value('rev-parse', '--abbrev-ref', 'HEAD')}")
    print(f"Git commit: {git_value('rev-parse', '--short=12', 'HEAD')}")
    print(f"CMake: {command_output(['cmake', '--version']) if shutil.which('cmake') else 'unavailable'}")

    expected = [
        Path("build-pc.sh"),
        Path("port/src/ascension_controls.c"),
        Path("tools_pc/apply_ascension_safe_gameplay_pack.py"),
        Path("tools_pc/verify_ascension_contracts.py"),
    ]
    for rel in expected:
        print(f"{rel.as_posix()}: {'OK' if (ROOT / rel).is_file() else 'MISSING'}")

    rom_exts = {".z64", ".n64", ".v64"}
    rom_candidates = 0
    data_dir = ROOT / "data"
    if data_dir.is_dir():
        rom_candidates = sum(
            1 for p in data_dir.iterdir()
            if p.is_file() and p.suffix.lower() in rom_exts
        )
    print(f"ROM candidates in data/: {rom_candidates} (contents not inspected)")

    build_dir = ROOT / "build-pc"
    binary_names = (
        "ge007.x86_64.exe",
        "ge007.x86_64",
        "ge007.exe",
        "ge007",
    )
    built = next((name for name in binary_names if (build_dir / name).is_file()), None)
    print(f"Built executable: {built or 'not found'}")

    print("\nFor static verification run:")
    print("  python3 tools_pc/verify_ascension_contracts.py")
    print("For patcher safety run:")
    print("  python3 tools_pc/test_ascension_patchers.py")
    print("For full local build verification run:")
    print("  ASCENSION_NO_LAUNCH=1 ./tools_pc/run_ascension_safe_test.sh")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
