#!/usr/bin/env python3
"""Canonical prepare/test/build/play entry point for Ascension 0.0.4."""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
REPORT = ROOT / "ascension-0.0.4-test-report.txt"

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
    [PY, "tools_pc/apply_universal_controller_layer.py"],
    [PY, "tools_pc/apply_audio_remaster.py"],
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
    [PY, "tools_pc/test_universal_controller_layer.py"],
    [PY, "tools_pc/test_audio_remaster.py"],
]


def cmd_text(cmd: list[str]) -> str:
    return " ".join(cmd)


def run(cmd: list[str], *, env: dict[str, str] | None = None) -> None:
    print("\n+", cmd_text(cmd), flush=True)
    subprocess.run(cmd, cwd=ROOT, env=env, check=True)


def run_code(cmd: list[str], *, env: dict[str, str] | None = None) -> int:
    print("\n+", cmd_text(cmd), flush=True)
    return subprocess.run(cmd, cwd=ROOT, env=env, check=False).returncode


def prepare() -> None:
    print("== Ascension 0.0.4: applying canonical stack ==")
    for cmd in PATCHERS:
        run(cmd)
    run([PY, "tools_pc/apply_modern_controls_v4.py", "--check"])
    run([PY, "tools_pc/apply_modern_controls_v4_padbinds.py", "--check"])
    run([PY, "tools_pc/apply_universal_controller_layer.py", "--check"])
    run([PY, "tools_pc/apply_audio_remaster.py", "--check"])


def test() -> None:
    print("== Ascension 0.0.4: regression contracts ==")
    results: list[tuple[str, int]] = []

    syntax_cmd = [PY, "-m", "compileall", "-q", "tools_pc"]
    results.append((cmd_text(syntax_cmd), run_code(syntax_cmd)))

    for cmd in TESTS:
        results.append((cmd_text(cmd), run_code(cmd)))

    git = shutil.which("git")
    if git:
        diff_cmd = [git, "diff", "--check"]
        results.append((cmd_text(diff_cmd), run_code(diff_cmd)))
    else:
        win_git = Path("/c/Program Files/Git/bin/git.exe")
        if win_git.exists():
            diff_cmd = [str(win_git), "diff", "--check"]
            results.append((cmd_text(diff_cmd), run_code(diff_cmd)))
        else:
            results.append(("git diff --check", 125))
            print("NOTE: git not in PATH; diff --check unavailable locally.")

    lines = ["Ascension 0.0.4 regression report", "=" * 36, ""]
    failed: list[str] = []
    for name, code in results:
        state = "PASS" if code == 0 else ("SKIP" if code == 125 else "FAIL")
        lines.append(f"{state:4}  {name}")
        if code not in (0, 125):
            failed.append(name)
    lines.append("")
    lines.append(f"Result: {'PASS' if not failed else 'FAIL'}")
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n" + REPORT.read_text(encoding="utf-8"), flush=True)

    if failed:
        raise SystemExit(
            "Ascension 0.0.4 regression gate failed: " + ", ".join(failed)
        )


def controllerdb(*, optional: bool) -> None:
    print("== Ascension 0.0.4: controller compatibility database ==")
    cmd = [PY, "tools_pc/update_controller_db.py"]
    if optional:
        cmd.append("--optional")
    run(cmd)


def steamaudio(*, stage: bool) -> None:
    action = "stage" if stage else "ensure"
    print(f"== Ascension Audio Remaster: Steam Audio 4.8.1 {action} ==")
    run([PY, "tools_pc/ensure_steam_audio.py", action])


def assets() -> None:
    print("== Ascension 0.0.4: ROM symbol generation ==")
    run([PY, "scripts/gen_romassets.py", "u"])


def build(target: str) -> None:
    print(f"== Ascension 0.0.4: build {target} ==")
    bash = shutil.which("bash")
    if bash:
        run([bash, "build-pc.sh", target], env=os.environ.copy())
    else:
        run(["./build-pc.sh", target], env=os.environ.copy())


def launch() -> None:
    candidates = [
        ROOT / "build-pc" / "ge007.x86_64.exe",
        ROOT / "build-pc" / "ge007.x86_64",
    ]
    executable = next((path for path in candidates if path.exists()), None)
    if executable is None:
        raise SystemExit(
            "Ascension executable not found under build-pc/. "
            "Run the build first or use: python tools_pc/ascension.py play"
        )

    print(f"== Ascension 0.0.4: launching {executable.name} ==")
    print("NOTE: runtime still requires your legally owned ROM-derived data/ assets.")
    run([str(executable)], env=os.environ.copy())


def full_pipeline(target: str) -> None:
    prepare()
    test()
    steamaudio(stage=False)
    assets()
    build(target)
    steamaudio(stage=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "command",
        choices=["prepare", "test", "controllerdb", "steamaudio", "assets", "build", "all", "run", "play"],
    )
    ap.add_argument("--target", default="ntsc-final")
    args = ap.parse_args()

    if args.command == "prepare":
        prepare()
    elif args.command == "test":
        test()
    elif args.command == "controllerdb":
        controllerdb(optional=False)
    elif args.command == "steamaudio":
        steamaudio(stage=False)
    elif args.command == "assets":
        assets()
    elif args.command == "build":
        build(args.target)
    elif args.command == "run":
        launch()
    elif args.command == "play":
        prepare()
        # Controller DB remains best-effort/offline-capable. Steam Audio is not:
        # this audio branch deliberately requires the pinned Valve runtime for
        # its full remaster path and stages it beside the executable.
        controllerdb(optional=True)
        test()
        steamaudio(stage=False)
        assets()
        build(args.target)
        steamaudio(stage=True)
        print("\nAscension 0.0.4 + Audio Remaster pipeline: PASS")
        launch()
        return 0
    else:
        full_pipeline(args.target)

    print("\nAscension 0.0.4 + Audio Remaster pipeline: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
