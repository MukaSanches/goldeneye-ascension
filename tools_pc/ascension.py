#!/usr/bin/env python3
"""Canonical prepare/test/build entry point for Ascension 0.0.4.

The stack is validated in ownership order. Older patchers are tested before a
newer layer deliberately extends their generated blocks; final 0.0.4 tests then
verify the composed state without asking old generators to rewrite newer code.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable

V2_PATCHERS = [
    [PY, "tools_pc/apply_modern_controls_v2.py", "--no-backup"],
]
V3_PATCHERS = [
    [PY, "tools_pc/apply_modern_controls_v3.py", "--no-backup"],
    [PY, "tools_pc/apply_modern_menu_guard.py"],
]
CHECKPOINT_PATCHERS = [
    [PY, "tools_pc/apply_ui_overhaul_v1.py"],
    [PY, "tools_pc/fix_ui_overhaul_text_state.py"],
    [PY, "tools_pc/install_ui_overhaul_v2.py", "--no-backup"],
    [PY, "tools_pc/apply_persistent_f10_hint.py", "--no-backup"],
    [PY, "tools_pc/apply_unlock_all_missions.py", "--no-backup"],
    [PY, "tools_pc/apply_watch_ui_final_safe.py", "--no-backup"],
    [PY, "tools_pc/apply_watch_runtime_fix.py", "--no-backup"],
]
V4_PATCHERS = [
    [PY, "tools_pc/apply_modern_controls_v4.py", "--no-backup"],
    [PY, "tools_pc/apply_modern_controls_v4_padbinds.py"],
]

CHECKPOINT_TESTS = [
    [PY, "tools_pc/test_ui_overhaul_v1.py"],
    [PY, "tools_pc/test_ui_overhaul_v2.py"],
    [PY, "tools_pc/test_persistent_f10_hint.py"],
    [PY, "tools_pc/test_unlock_all_missions.py"],
    [PY, "tools_pc/test_watch_ui_final.py"],
    [PY, "tools_pc/test_watch_runtime_fix.py"],
]
FINAL_TESTS = [
    [PY, "tools_pc/test_modern_controls_v4.py"],
    [PY, "tools_pc/test_modern_controls_v4_padbinds.py"],
    [PY, "tools_pc/test_ascension_004_preservation.py"],
]


def run(cmd: list[str], *, env: dict[str, str] | None = None) -> None:
    print("\n+", " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=ROOT, env=env, check=True)


def run_many(commands: list[list[str]]) -> None:
    for cmd in commands:
        run(cmd)


def final_stack_present() -> bool:
    probes = {
        ROOT / "port/src/input.c": "inputPadBindingCapturePressed",
        ROOT / "src/game/bondview2.c": "ascensionControlsConsumeGamepadLook",
        ROOT / "port/src/optionsoverlay.c": "Input.ModernPadBind.Action",
    }
    return all(path.exists() and marker in path.read_text(encoding="utf-8")
               for path, marker in probes.items())


def prepare() -> None:
    print("== Ascension 0.0.4: applying canonical stack ==")
    run([PY, "-m", "compileall", "-q", "tools_pc"])

    if final_stack_present():
        print("Final 0.0.4 generated state already present; destructive re-application skipped.")
        run([PY, "tools_pc/apply_modern_controls_v4.py", "--check"])
        run([PY, "tools_pc/apply_modern_controls_v4_padbinds.py", "--check"])
        return

    print("\n== Phase 1: Modern Controls V2 baseline ==")
    run_many(V2_PATCHERS)
    run([PY, "tools_pc/test_modern_controls_v2.py"])

    print("\n== Phase 2: Modern Controls V3 + menu isolation ==")
    run_many(V3_PATCHERS)
    run([PY, "tools_pc/test_modern_controls_v2.py"])
    run([PY, "tools_pc/test_modern_controls_v3.py"])

    print("\n== Phase 3: accepted UI / Q Watch checkpoint ==")
    run_many(CHECKPOINT_PATCHERS)
    run_many(CHECKPOINT_TESTS)

    print("\n== Phase 4: Ascension 0.0.4 Modern Experience ==")
    run_many(V4_PATCHERS)
    run([PY, "tools_pc/apply_modern_controls_v4.py", "--check"])
    run([PY, "tools_pc/apply_modern_controls_v4_padbinds.py", "--check"])


def test() -> None:
    print("== Ascension 0.0.4: final composed-state contracts ==")
    run([PY, "-m", "compileall", "-q", "tools_pc"])
    run_many(FINAL_TESTS)

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
    run(["bash", "build-pc.sh", target], env=os.environ.copy())


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
