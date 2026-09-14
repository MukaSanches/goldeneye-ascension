#!/usr/bin/env python3
"""Static safety checks for GoldenEye Ascension.

This verifier intentionally does not need a ROM and does not launch the game.
It protects invariants that should remain true while Ascension evolves:

* Classic remains the default control preset.
* ControlPreset remains constrained to Classic/Hybrid/Modern (0..2).
* Classic does not enable the Ascension dedicated-crouch bridge.
* Core PT-BR Ascension control/UI translations remain present.
* The validated patcher manifest passes its non-mutating preflight.
* ROM images and reversible patcher backups are never tracked by Git.

It is safe to run locally or in CI from any checkout of the repository.
"""
from __future__ import annotations

from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
CONTROLS = ROOT / "port" / "src" / "ascension_controls.c"
LOCALE = ROOT / "port" / "src" / "ascension_locale.c"
PACK = ROOT / "tools_pc" / "apply_ascension_safe_gameplay_pack.py"


def fail(message: str) -> int:
    print(f"FAIL: {message}", file=sys.stderr)
    return 1


def git_lines(*args: str) -> list[str]:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "git command failed")
    return [line for line in result.stdout.splitlines() if line]


def main() -> int:
    if not CONTROLS.is_file():
        return fail(f"missing {CONTROLS.relative_to(ROOT)}")
    if not LOCALE.is_file():
        return fail(f"missing {LOCALE.relative_to(ROOT)}")
    if not PACK.is_file():
        return fail(f"missing {PACK.relative_to(ROOT)}")

    source = CONTROLS.read_text(encoding="utf-8")

    required_controls = {
        "Classic default": "static int s_controlPreset = 0;",
        "preset range": 'configRegisterInt("Input.ControlPreset", &s_controlPreset, 0, 2);',
        "Classic dedicated-crouch guard": "if (!s_dedicatedCrouch || s_controlPreset == 0)",
    }
    for label, needle in required_controls.items():
        if needle not in source:
            return fail(f"control contract changed: {label}")

    locale = LOCALE.read_text(encoding="utf-8")
    required_ptbr = {
        "language selector": '{ "PORTUGUESE (BRAZIL)", "PORTUGUES (BRASIL)" }',
        "control preset": '{ "Control preset", "Preset de controles" }',
        "dedicated crouch": '{ "Dedicated crouch", "Agachar dedicado" }',
        "Classic value": '{ "CLASSIC", "CLASSICO" }',
        "Hybrid value": '{ "HYBRID", "HIBRIDO" }',
        "Modern value": '{ "MODERN", "MODERNO" }',
    }
    for label, needle in required_ptbr.items():
        if needle not in locale:
            return fail(f"PT-BR contract changed: {label}")

    preflight = subprocess.run(
        [sys.executable, str(PACK), "--preflight-only"],
        cwd=ROOT,
        check=False,
    )
    if preflight.returncode != 0:
        return fail("Ascension patcher manifest preflight failed")

    try:
        tracked = git_lines("ls-files")
    except RuntimeError as exc:
        return fail(str(exc))

    rom_exts = (".z64", ".n64", ".v64")
    tracked_roms = [p for p in tracked if p.lower().endswith(rom_exts)]
    if tracked_roms:
        return fail("tracked ROM image(s): " + ", ".join(tracked_roms))

    tracked_backups = [p for p in tracked if ".ascension-before-" in p]
    if tracked_backups:
        return fail("tracked patcher backup(s): " + ", ".join(tracked_backups))

    try:
        branch = git_lines("rev-parse", "--abbrev-ref", "HEAD")[0]
        commit = git_lines("rev-parse", "--short=12", "HEAD")[0]
    except (RuntimeError, IndexError):
        branch, commit = "unknown", "unknown"

    print("PASS: Ascension static contracts verified")
    print(f"  branch: {branch}")
    print(f"  commit: {commit}")
    print("  controls: Classic default; presets constrained to 0..2")
    print("  localization: core PT-BR control coverage present")
    print("  patchers: preflight clean")
    print("  repository: no tracked ROM images or Ascension backup artifacts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
