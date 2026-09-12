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

Every child patcher is idempotent and anchor-validated. This wrapper aborts on
the first failure, making local test setup reproducible and easy to audit.
"""
from pathlib import Path
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
]


def main() -> int:
    for script in SCRIPTS:
        if not script.exists():
            print(f"ERROR: missing {script.relative_to(ROOT)}", file=sys.stderr)
            return 2
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
