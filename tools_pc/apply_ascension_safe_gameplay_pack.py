#!/usr/bin/env python3
"""Apply Ascension's currently validated low-risk gameplay/input improvements.

Order:
  1. Modern Controls v1 input bridge
  2. In-game F10 control preset selector
  3. Existing-input tuning rows in F10
  4. Existing display/input compatibility rows in F10
  5. Conventional fullscreen shortcuts / small PC UX options
  6. Safe F10 video quality presets
  7. F12 screenshot organization
  8. Subtle F10/front-end visual polish
  9. Conservative PC-polish presets (FOV/mouse/gamepad)

Every child patcher is idempotent and anchor-validated. Before any patcher runs,
this wrapper also parses every child script so a syntax error cannot leave a
partially-applied local tree.

Use --preflight-only to validate the child patcher manifest without modifying
the source tree.
"""
from pathlib import Path
import argparse
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = [
    ROOT / "tools_pc" / "apply_modern_controls_test.py",
    ROOT / "tools_pc" / "apply_control_selector_test.py",
    ROOT / "tools_pc" / "apply_safe_input_f10_pack.py",
    ROOT / "tools_pc" / "apply_safe_display_f10_pack.py",
    ROOT / "tools_pc" / "apply_alt_enter_fullscreen.py",
    ROOT / "tools_pc" / "apply_quality_presets_f10.py",
    ROOT / "tools_pc" / "apply_screenshot_ux.py",
    ROOT / "tools_pc" / "apply_overlay_visual_polish.py",
    ROOT / "tools_pc" / "apply_pc_polish_presets.py",
]


def preflight() -> bool:
    """Verify the manifest is sane and every child patcher parses before changes."""
    if len(SCRIPTS) != len(set(SCRIPTS)):
        print("ERROR: duplicate patcher entry in Ascension manifest", file=sys.stderr)
        return False

    for script in SCRIPTS:
        if not script.is_file():
            print(f"ERROR: missing patcher file {script.relative_to(ROOT)}", file=sys.stderr)
            return False
        try:
            source = script.read_text(encoding="utf-8")
            compile(source, str(script), "exec")
        except (OSError, UnicodeError, SyntaxError) as exc:
            print(f"ERROR: preflight failed for {script.relative_to(ROOT)}: {exc}",
                  file=sys.stderr)
            return False
    return True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Apply the validated Ascension low-risk gameplay/input patch pack."
    )
    parser.add_argument(
        "--preflight-only",
        action="store_true",
        help="validate the child patcher manifest without modifying the source tree",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if not preflight():
        print("ERROR: no Ascension patchers were run.", file=sys.stderr)
        return 2

    print("==> Preflight OK: all Ascension patchers parse cleanly.")

    if args.preflight_only:
        print("SUCCESS: Ascension patcher manifest validated; no files were changed.")
        return 0

    for script in SCRIPTS:
        print(f"\n==> {script.name}")
        result = subprocess.run([sys.executable, str(script)], cwd=ROOT)
        if result.returncode != 0:
            print(f"ERROR: stopped at {script.name}", file=sys.stderr)
            return result.returncode

    print("\nSUCCESS: Ascension safe gameplay pack is applied.")
    print("Next: rm -rf build-pc && ./build-pc.sh ntsc-final")
    return 0


if __name__ == "__main__":
    sys.exit(main())
