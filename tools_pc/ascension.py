#!/usr/bin/env python3
"""Canonical prepare/test/build entry point for Ascension 0.0.4."""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable

PATCHERS = [
    [PY, "tools_pc/apply_modern_controls_v2.py", "--no-backup"],
    [PY, "tools_pc/apply_modern_controls_v3.py", "--no-backup"],
    [PY, "tools_pc/apply_modern_menu_guard.py"],
    [PY, "tools_pc/apply_ui_overhaul_v1.py"],
    [PY, "tools_pc/fix_ui_overhaul_text_state.py"],
    [PY, "tools_pc/install_ui_overhaul_v2.py", "--no-backup"],
    [PY, "tools_pc/apply_persistent_f10_hint.py", "--no-backup"],
    [PY, "tools_pc/apply_unlock_all_missions.py", "--no-backup"],
    [PY, "tools_pc/apply_watch_ui_final_safe.py", "--no-backup"],
    [PY, "tools_pc/apply_watch_runtime_fix.py", "--no-backup"],
    [PY, "tools_pc/apply_modern_controls_v4.py", "--no-backup"],
    [PY, "tools_pc/apply_modern_controls_v4_padbinds.py"],
]

TESTS = [
    [PY, "tools_pc/test_modern_controls_v2.py"],
    [PY, "tools_pc/test_modern_controls_v3.py"],
    [PY, "tools_pc/test_ui_overhaul_v1.py"],
    [PY, "tools_pc/test_ui_overhaul_v2.py"],
    [PY, "tools_pc/test_persistent_f10_hint.py"],
    [PY, "tools_pc/test_unlock_all_missions.py"],
    [PY, "tools_pc/test_watch_ui_final.py"],
    [PY, "tools_pc/test_watch_runtime_fix.py"],
    [PY, "tools_pc/test_modern_controls_v4.py"],
    [PY, "tools_pc/test_modern_controls_v4_padbinds.py"],
]


def run(cmd: list[str], *, env: dict[str, str] | None = None) -> None:
    print("\n+", " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=ROOT, env=env, check=True)


def prepare() -> None:
    print("== Ascension 0.0.4: applying canonical stack ==")
    for cmd in PATCHERS:
        run(cmd)
    run([PY, "tools_pc/apply_modern_controls_v4.py", "--check"])
    run([PY, "tools_pc/apply_modern_controls_v4_padbinds.py", "--check"])


def test() -> None:
    print("== Ascension 0.0.4: regression contracts ==")
    run([PY, "-m", "compileall", "-q", "tools_pc"])
    for cmd in TESTS:
        run(cmd)

    git = shutil.which("git")
    if git:
        run([git, "diff", "--check"])
    else:
        win_git = Path("/c/Program Files/Git/bin/git.exe")
        if win_git.exists():
            run([str(win_git), "diff", "--check"])
        else:
            print("NOTE: git not in PATH; diff --check skipped locally.")


def assets() -> None:
    print("== Ascension 0.0.4: ROM symbol generation ==")
    run([PY, "scripts/gen_romassets.py", "u"])


def build(target: str) -> None:
    print(f"== Ascension 0.0.4: build {target} ==")
    run(["./build-pc.sh", target], env=os.environ.copy())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["prepare", "test", "assets", "build", "all"])
    ap.add_argument("--target", default="ntsc-final")
    args = ap.parse_args()

    if args.command == "prepare": prepare()
    elif args.command == "test": test()
    elif args.command == "assets": assets()
    elif args.command == "build": build(args.target)
    else:
        prepare(); test(); assets(); build(args.target)

    print("\nAscension 0.0.4 pipeline: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
