"""First-run generation of host-layout sidecars from the user's own ROM.

The heavy conversion algorithms remain the repository's d43_emit.py and
d69_emit.py. Android extracts their read-only metadata workspace into HOME,
then this module executes them exactly as the desktop tooling does.
"""
from __future__ import annotations

import csv
import hashlib
import os
import runpy
import shutil
import sys

REGION = "ntsc-final"
MARKER_SCHEMA = "android-v1-sidecars-fingerprint-v1"
_MARKER = "data/.ascension_sidecars.version"


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
    return (
        _artifact_valid(home, "pcmodels-ntsc-final", "pcmodels.bin")
        and _artifact_valid(home, "pccg-ntsc-final", "pccg.bin")
    )


def _generator_inputs(home: str) -> list[str]:
    fixed = [
        "tools_pc/d43_emit.py",
        "tools_pc/d69_emit.py",
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

    return sorted(paths, key=lambda p: os.path.relpath(p, home).replace(os.sep, "/"))


def _generator_fingerprint(home: str) -> str:
    digest = hashlib.sha256()
    inputs = _generator_inputs(home)
    if len(inputs) < 5:
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


def _run_tool(home: str, filename: str) -> None:
    script = os.path.join(home, "tools_pc", filename)
    if not os.path.isfile(script):
        raise RuntimeError(f"converter script missing: {filename}")

    old_argv = sys.argv[:]
    try:
        sys.argv = [script, REGION]
        try:
            runpy.run_path(script, run_name="__main__")
        except SystemExit as exc:
            if exc.code not in (None, 0):
                raise RuntimeError(f"{filename} exited with status {exc.code}") from exc
    finally:
        sys.argv = old_argv


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
        _run_tool(home, "d43_emit.py")
        _run_tool(home, "d69_emit.py")
    finally:
        os.chdir(old_cwd)

    if not _outputs_valid(home):
        _clear_generated(home)
        raise RuntimeError("sidecar generation incomplete or structurally invalid")

    _write_marker(home)
    if not ready(home):
        raise RuntimeError("sidecar generation fingerprint validation failed")
    return "generated"
