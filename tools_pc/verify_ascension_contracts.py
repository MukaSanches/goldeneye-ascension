#!/usr/bin/env python3
"""Static safety checks for GoldenEye Ascension.

This verifier intentionally does not need a ROM and does not launch the game.
It protects invariants that should remain true while Ascension evolves:

* Classic remains the default control preset.
* Dedicated crouch remains enabled by default but inert under Classic.
* ControlPreset remains constrained to Classic/Hybrid/Modern (0..2).
* DedicatedCrouch remains constrained to a boolean off/on value (0..1).
* Classic does not enable the Ascension dedicated-crouch bridge.
* Hybrid keeps dedicated crouch on C so Left Ctrl remains legacy fire.
* Modern keeps dedicated crouch available on Ctrl or C.
* Dedicated crouch safely handles an unavailable SDL keyboard state.
* Core PT-BR Ascension control/UI translations remain present.
* The Ascension controls guide keeps the preset/config fallback documented.
* The validated patcher manifest passes its non-mutating preflight.
* ROM images and reversible patcher backups are never tracked by Git.
* Generated Python bytecode/cache artifacts are never tracked by Git.

It is safe to run locally or in CI from any checkout of the repository.
"""
from __future__ import annotations

from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
CONTROLS = ROOT / "port" / "src" / "ascension_controls.c"
LOCALE = ROOT / "port" / "src" / "ascension_locale.c"
CONTROLS_DOC = ROOT / "docs" / "ASCENSION-CONTROLS.md"
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
    if not CONTROLS_DOC.is_file():
        return fail(f"missing {CONTROLS_DOC.relative_to(ROOT)}")
    if not PACK.is_file():
        return fail(f"missing {PACK.relative_to(ROOT)}")

    source = CONTROLS.read_text(encoding="utf-8")
    normalized_source = " ".join(source.split())

    required_controls = {
        "Classic default": "static int s_controlPreset = 0;",
        "dedicated crouch default": "static int s_dedicatedCrouch = 1;",
        "preset range": 'configRegisterInt("Input.ControlPreset", &s_controlPreset, 0, 2);',
        "dedicated crouch range": 'configRegisterInt("Input.DedicatedCrouch", &s_dedicatedCrouch, 0, 1);',
        "Classic dedicated-crouch guard": "if (!s_dedicatedCrouch || s_controlPreset == 0)",
        "dedicated-crouch SDL null guard": "if (!ks) return 0;",
        "Hybrid dedicated-crouch C-only mapping": "if (s_controlPreset == 1) return ks[SDL_SCANCODE_C] != 0;",
        "Modern dedicated-crouch Ctrl/C mapping": "return ks[SDL_SCANCODE_LCTRL] || ks[SDL_SCANCODE_RCTRL] || ks[SDL_SCANCODE_C];",
    }
    for label, needle in required_controls.items():
        if " ".join(needle.split()) not in normalized_source:
            return fail(f"control contract changed: {label}")

    locale = LOCALE.read_text(encoding="utf-8")
    normalized_locale = " ".join(locale.split())
    required_ptbr = {
        "language selector": '{ "PORTUGUESE (BRAZIL)", "PORTUGUES (BRASIL)" }',
        "control preset": '{ "Control preset", "Preset de controles" }',
        "dedicated crouch": '{ "Dedicated crouch", "Agachar dedicado" }',
        "Classic value": '{ "CLASSIC", "CLASSICO" }',
        "Hybrid value": '{ "HYBRID", "HIBRIDO" }',
        "Modern value": '{ "MODERN", "MODERNO" }',
    }
    for label, needle in required_ptbr.items():
        if " ".join(needle.split()) not in normalized_locale:
            return fail(f"PT-BR contract changed: {label}")

    controls_doc = CONTROLS_DOC.read_text(encoding="utf-8")
    normalized_controls_doc = " ".join(controls_doc.split())
    required_controls_doc = {
        "Classic default documentation": "`CLASSIC` is the default preset",
        "manual ControlPreset fallback": "ControlPreset = 0",
        "manual DedicatedCrouch fallback": "DedicatedCrouch = 1",
        "preset numeric values": "0 = CLASSIC`, `1 = HYBRID`, or `2 = MODERN",
        "safe INI editing": "Edit the file only while the game is closed",
        "static verifier command": "python3 tools_pc/verify_ascension_contracts.py",
        "patcher tests command": "python3 tools_pc/test_ascension_patchers.py",
    }
    for label, needle in required_controls_doc.items():
        if " ".join(needle.split()) not in normalized_controls_doc:
            return fail(f"control documentation contract changed: {label}")

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

    tracked_python_cache = [
        p for p in tracked
        if p.endswith((".pyc", ".pyo")) or "__pycache__/" in p
    ]
    if tracked_python_cache:
        return fail("tracked Python cache artifact(s): " + ", ".join(tracked_python_cache))

    try:
        branch = git_lines("rev-parse", "--abbrev-ref", "HEAD")[0]
        commit = git_lines("rev-parse", "--short=12", "HEAD")[0]
    except (RuntimeError, IndexError):
        branch, commit = "unknown", "unknown"

    print("PASS: Ascension static contracts verified")
    print(f"  branch: {branch}")
    print(f"  commit: {commit}")
    print("  controls: Classic default; dedicated crouch default; presets 0..2; mappings protected")
    print("  localization: core PT-BR control coverage present")
    print("  documentation: Ascension control presets and manual fallback protected")
    print("  patchers: preflight clean")
    print("  repository: no tracked ROM, Ascension backup, or Python cache artifacts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
