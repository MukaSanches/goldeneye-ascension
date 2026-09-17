"""First-run generation of host-layout sidecars from the user's own ROM.

The conversion chain mirrors docs/building.md exactly:
  d43 (models) -> d69 (bg/stan) -> d88 --regen (21 Usetup files)
and then d125 verifies the emitted setup propDefs byte-for-byte.
"""
from __future__ import annotations

import contextlib
import csv
import hashlib
import io
import os
import runpy
import shutil
import sys

REGION = "ntsc-final"
EXPECTED_USETUP_COUNT = 21
MARKER_SCHEMA = "android-v1-sidecars-fingerprint-v2"
_MARKER = "data/.ascension_sidecars.version"


def _read_manifest_names(path: str) -> list[str]:
    try:
        with open(path, newline="", encoding="utf-8") as f:
            rows = csv.DictReader(f)
            if rows.fieldnames != ["name", "offset", "size"]:
                return []
            return [row.get("name", "") for row in rows if row.get("name")]
    except OSError:
        return []


def _artifact_valid(home: str, directory: str, bin_name: str) -> bool:
    out_dir = os.path.join(home, "data", directory)
    bin_path = os.path.join(out_dir, bin_name)
    manifest_path = os.path.join(out_dir, "manifest.csv")
    if not os.path.isfile(bin_path) or not os.path.isfile(manifest_path):
        return False

    bin_size = os.path.getsize(bin_path)
    if bin_size <= 0 or os.path.getsize(manifest_path) <= 0:
        return False

    try:
        with open(manifest_path, newline="", encoding="utf-8") as f:
            rows = csv.DictReader(f)
            if rows.fieldnames != ["name", "offset", "size"]:
                return False
            count = 0
            previous_end = 0
            for row in rows:
                name = row.get("name", "")
                offset = int(row.get("offset", "-1"), 10)
                size = int(row.get("size", "0"), 10)
                if not name or offset < previous_end or size <= 0:
                    return False
                end = offset + size
                if end > bin_size:
                    return False
                previous_end = end
                count += 1
            return count > 0
    except (OSError, ValueError, TypeError):
        return False


def _outputs_valid(home: str) -> bool:
    if not (
        _artifact_valid(home, "pcmodels-ntsc-final", "pcmodels.bin")
        and _artifact_valid(home, "pccg-ntsc-final", "pccg.bin")
    ):
        return False

    pccg_manifest = os.path.join(
        home, "data", "pccg-ntsc-final", "manifest.csv"
    )
    names = _read_manifest_names(pccg_manifest)
    setup_names = {
        name for name in names
        if name.startswith("Usetup") and name.endswith("Z")
    }
    return len(setup_names) == EXPECTED_USETUP_COUNT


def _generator_inputs(home: str) -> list[str]:
    fixed = [
        "tools_pc/d43_emit.py",
        "tools_pc/d69_emit.py",
        "tools_pc/d88_emit.py",
        "tools_pc/d88_propdefs.py",
        "tools_pc/d125_check.py",
        "scripts/filelist.u.csv",
        "assets/obseg/file_resource_table.inc.c",
    ]
    paths = [os.path.join(home, rel) for rel in fixed]

    assets_root = os.path.join(home, "assets")
    if os.path.isdir(assets_root):
        for root, _dirs, files in os.walk(assets_root):
            for name in files:
                if name.lower().endswith("modelfileheader.inc.c"):
                    paths.append(os.path.join(root, name))

    return sorted(
        paths,
        key=lambda p: os.path.relpath(p, home).replace(os.sep, "/"),
    )


def _generator_fingerprint(home: str) -> str:
    digest = hashlib.sha256()
    inputs = _generator_inputs(home)
    if len(inputs) < 8:
        raise RuntimeError("converter workspace is incomplete")

    for path in inputs:
        if not os.path.isfile(path):
            raise RuntimeError(
                "converter workspace file missing: "
                + os.path.relpath(path, home).replace(os.sep, "/")
            )
        rel = os.path.relpath(path, home).replace(os.sep, "/").encode("utf-8")
        digest.update(len(rel).to_bytes(4, "big"))
        digest.update(rel)
        with open(path, "rb") as f:
            while True:
                block = f.read(128 * 1024)
                if not block:
                    break
                digest.update(block)

    return MARKER_SCHEMA + ":" + digest.hexdigest()


def _marker_valid(home: str) -> bool:
    marker = os.path.join(home, _MARKER)
    try:
        expected = _generator_fingerprint(home)
        with open(marker, encoding="utf-8") as f:
            return f.read().strip() == expected
    except (OSError, RuntimeError):
        return False


def ready(home: str) -> bool:
    home = os.path.abspath(home)
    return _marker_valid(home) and _outputs_valid(home)


def _run_script(home: str, filename: str, args: list[str]) -> None:
    script = os.path.join(home, "tools_pc", filename)
    if not os.path.isfile(script):
        raise RuntimeError(f"converter script missing: {filename}")

    old_argv = sys.argv[:]
    old_path = sys.path[:]
    try:
        # d88_emit.py and d125_check.py import d88_propdefs by module name.
        sys.path.insert(0, os.path.dirname(script))
        sys.argv = [script, *args]
        try:
            runpy.run_path(script, run_name="__main__")
        except SystemExit as exc:
            if exc.code not in (None, 0):
                raise RuntimeError(
                    f"{filename} exited with status {exc.code}"
                ) from exc
    finally:
        sys.argv = old_argv
        sys.path[:] = old_path


def _verify_d125(home: str) -> None:
    capture = io.StringIO()
    with contextlib.redirect_stdout(capture):
        _run_script(home, "d125_check.py", [])
    report = capture.getvalue()

    result_lines = [
        line.strip() for line in report.splitlines()
        if line.startswith("MATCH") or line.startswith("MISMATCH")
    ]
    matches = [line for line in result_lines if line.startswith("MATCH")]
    mismatches = [line for line in result_lines if line.startswith("MISMATCH")]

    if mismatches or len(matches) != EXPECTED_USETUP_COUNT:
        detail = mismatches[0] if mismatches else (
            f"expected {EXPECTED_USETUP_COUNT} MATCH lines, got {len(matches)}"
        )
        raise RuntimeError("D125 setup sidecar validation failed: " + detail)


def _clear_generated(home: str) -> None:
    for directory in ("pcmodels-ntsc-final", "pccg-ntsc-final"):
        shutil.rmtree(os.path.join(home, "data", directory), ignore_errors=True)
    try:
        os.remove(os.path.join(home, _MARKER))
    except FileNotFoundError:
        pass


def _write_marker(home: str) -> None:
    marker = os.path.join(home, _MARKER)
    os.makedirs(os.path.dirname(marker), exist_ok=True)
    value = _generator_fingerprint(home)
    temp = marker + ".tmp"
    with open(temp, "w", encoding="utf-8") as f:
        f.write(value + "\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(temp, marker)


def generate(home: str) -> str:
    home = os.path.abspath(home)
    rom = os.path.join(home, "data", f"ge007.{REGION}.z64")
    if not os.path.isfile(rom) or os.path.getsize(rom) <= 0:
        raise RuntimeError("user ROM is missing from app-private storage")
    if ready(home):
        return "ready"

    _clear_generated(home)
    old_cwd = os.getcwd()
    try:
        os.chdir(home)
        _run_script(home, "d43_emit.py", [REGION])
        _run_script(home, "d69_emit.py", [REGION])
        _run_script(home, "d88_emit.py", [REGION, "--regen"])
        if not _outputs_valid(home):
            raise RuntimeError(
                "sidecar generation incomplete: expected 21 Usetup files"
            )
        _verify_d125(home)
    except Exception:
        _clear_generated(home)
        raise
    finally:
        os.chdir(old_cwd)

    if not _outputs_valid(home):
        _clear_generated(home)
        raise RuntimeError("sidecar generation incomplete or structurally invalid")

    _write_marker(home)
    if not ready(home):
        raise RuntimeError("sidecar generation fingerprint validation failed")
    return "generated"
