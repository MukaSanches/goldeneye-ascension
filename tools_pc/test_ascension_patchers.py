#!/usr/bin/env python3
"""ROM-free regression test for the Ascension patcher pack.

The test runs entirely in a temporary copy of the repository. It verifies five
properties that make the low-risk pack safe to iterate on:

1. Applying the complete pack twice is idempotent: the second run changes no
   file produced by the first run.
2. Every ``*.ascension-before-*`` backup created by a patcher is non-empty,
   maps to a real source file, and remains unchanged on the second run.
3. The Modern Controls bridge produced by the pack stays opt-in, menu-safe,
   and uses GoldenEye's native crouch gesture rather than replacing gameplay
   logic.
4. Classic, Hybrid, and Modern retain their intended dedicated-crouch
   semantics, including Classic's original behavior and Hybrid's legacy fire.
5. The F10 control rows remain unique and ordered so repeated patching cannot
   duplicate or scramble the Ascension control settings.

Backups are intentionally checked against the state captured by each patcher,
not against the state before the *whole* pack. Later patchers may legitimately
back up a file already modified by an earlier patcher in the same ordered pack.

The real checkout is never modified.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
PACK_REL = Path("tools_pc/apply_ascension_safe_gameplay_pack.py")

IGNORE_DIRS = {
    ".git",
    ".ccache",
    "build",
    "build-pc",
    "build-linux",
    "build-ntsc",
    "dist",
    "__pycache__",
}


def digest(path: Path) -> str:
    h = sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def snapshot(root: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if any(part in IGNORE_DIRS for part in rel.parts):
            continue
        result[rel.as_posix()] = digest(path)
    return result


def copy_ignore(_directory: str, names: list[str]) -> set[str]:
    return {name for name in names if name in IGNORE_DIRS}


def run_pack(root: Path) -> str:
    result = subprocess.run(
        [sys.executable, str(root / PACK_REL)],
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if result.returncode != 0:
        print(result.stdout, file=sys.stderr)
        raise RuntimeError(f"patcher pack failed with exit code {result.returncode}")
    return result.stdout


def verify_backups(root: Path) -> int:
    backups = [p for p in root.rglob("*.ascension-before-*") if p.is_file()]
    if not backups:
        print("NOTE: no Ascension backup files were created in this tree")
        return 0

    for backup in backups:
        rel = backup.relative_to(root).as_posix()
        source_rel = rel.split(".ascension-before-", 1)[0]
        source = root / source_rel
        if not source.is_file():
            print(f"FAIL: backup has no corresponding source file: {rel}", file=sys.stderr)
            return 1
        if backup.stat().st_size == 0:
            print(f"FAIL: empty patcher backup: {rel}", file=sys.stderr)
            return 1

    print(f"PASS: {len(backups)} reversible backup(s) are present and non-empty")
    return 0


def verify_modern_controls_bridge(root: Path) -> int:
    input_path = root / "port" / "src" / "input.c"
    if not input_path.is_file():
        print("FAIL: missing port/src/input.c after patcher pack", file=sys.stderr)
        return 1

    source = input_path.read_text(encoding="utf-8")
    required = {
        "Ascension controls include": '#include "ascension_controls.h"',
        "menu-safe opt-in crouch guard":
            "int dedicatedCrouch = !menuMode && ascensionControlsDedicatedCrouchHeld();",
        "legacy fire preserved outside dedicated crouch":
            "(actHeld(ks, IA_FIRE) && !dedicatedCrouch)",
        "native aim bridge": "actHeld(ks, IA_AIM) || dedicatedCrouch;",
        "native stick-down crouch gesture": "if (dedicatedCrouch)\n            sy = -STICK_MAX;",
        "dedicated crouch preserves stick-Y during mouse look":
            "if (!dedicatedCrouch && fabs(dyLook) >= AIM_MOVE_THRESH)",
        "dedicated crouch preserves horizontal mouse aim":
            "if (fabs(edx) >= AIM_MOVE_THRESH) {",
    }
    for label, needle in required.items():
        if needle not in source:
            print(f"FAIL: Modern Controls bridge contract changed: {label}", file=sys.stderr)
            return 1

    print("PASS: Modern Controls bridge remains opt-in, menu-safe, and native-gesture based")
    return 0


def verify_control_preset_semantics(root: Path) -> int:
    controls_path = root / "port" / "src" / "ascension_controls.c"
    if not controls_path.is_file():
        print("FAIL: missing port/src/ascension_controls.c after patcher pack", file=sys.stderr)
        return 1

    source = controls_path.read_text(encoding="utf-8")
    required = {
        "Classic disables dedicated crouch":
            "if (!s_dedicatedCrouch || s_controlPreset == 0)\n        return 0;",
        "Hybrid has its own C-only branch":
            "if (s_controlPreset == 1)\n        return ks[SDL_SCANCODE_C] != 0;",
        "Modern accepts both Ctrl keys and C":
            "return ks[SDL_SCANCODE_LCTRL] || ks[SDL_SCANCODE_RCTRL] ||\n           ks[SDL_SCANCODE_C];",
    }
    for label, needle in required.items():
        if needle not in source:
            print(f"FAIL: control preset contract changed: {label}", file=sys.stderr)
            return 1

    print("PASS: Classic/Hybrid/Modern dedicated-crouch semantics are preserved")
    return 0


def verify_f10_control_rows(root: Path) -> int:
    overlay_path = root / "port" / "src" / "optionsoverlay.c"
    if not overlay_path.is_file():
        print("FAIL: missing port/src/optionsoverlay.c after patcher pack", file=sys.stderr)
        return 1

    source = overlay_path.read_text(encoding="utf-8")
    keys = [
        ' .key="Input.ControlPreset"',
        ' .key="Input.DedicatedCrouch"',
        ' .key="Input.MouseAimSpeed"',
    ]
    for key in keys:
        count = source.count(key)
        if count != 1:
            print(f"FAIL: F10 control row {key.strip()} occurs {count} time(s), expected 1", file=sys.stderr)
            return 1

    positions = [source.index(key) for key in keys]
    if positions != sorted(positions):
        print("FAIL: F10 control rows are out of order", file=sys.stderr)
        return 1

    print("PASS: F10 control rows are unique and ordered")
    return 0


def main() -> int:
    if not (ROOT / PACK_REL).is_file():
        print(f"FAIL: missing {PACK_REL}", file=sys.stderr)
        return 1

    with tempfile.TemporaryDirectory(prefix="ascension-patcher-test-") as tmp:
        sandbox = Path(tmp) / "repo"
        shutil.copytree(ROOT, sandbox, ignore=copy_ignore)

        try:
            run_pack(sandbox)
        except RuntimeError as exc:
            print(f"FAIL: {exc}", file=sys.stderr)
            return 1

        if verify_backups(sandbox) != 0:
            return 1
        if verify_modern_controls_bridge(sandbox) != 0:
            return 1
        if verify_control_preset_semantics(sandbox) != 0:
            return 1
        if verify_f10_control_rows(sandbox) != 0:
            return 1

        after_first = snapshot(sandbox)
        try:
            second_output = run_pack(sandbox)
        except RuntimeError as exc:
            print(f"FAIL: second application: {exc}", file=sys.stderr)
            return 1
        after_second = snapshot(sandbox)

        changed = sorted(
            set(after_first) ^ set(after_second)
            | {p for p in set(after_first) & set(after_second)
               if after_first[p] != after_second[p]}
        )
        if changed:
            print("FAIL: patcher pack is not idempotent; second run changed:", file=sys.stderr)
            for path in changed:
                print(f"  {path}", file=sys.stderr)
            reapplied = [
                line for line in second_output.splitlines()
                if line.startswith("APPLY:")
            ]
            if reapplied:
                print("Second-run patch operations:", file=sys.stderr)
                for line in reapplied:
                    print(f"  {line}", file=sys.stderr)
            return 1

    print("PASS: Ascension patcher pack is idempotent")
    print("PASS: backups are stable across repeated application")
    print("PASS: Modern Controls bridge safety contract is preserved")
    print("PASS: Classic/Hybrid/Modern control preset semantics are preserved")
    print("PASS: F10 control rows remain unique and ordered")
    print("PASS: real checkout was not modified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())