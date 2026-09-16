#!/usr/bin/env python3
"""Create a community-patched PT-BR test ROM without replacing the runtime ROM.

The GoldenEye PC port must keep executing the verified original US ROM because
its absolute asset map is tied to that layout. This helper only creates
`data/ge007.ntsc-final.ptbr-test.z64`; tools_pc/import_ptbr_patch.py then imports
text from that file into a safe sidecar catalog.
"""

from __future__ import annotations

import binascii
import sys
from pathlib import Path

EXPECTED_BASE_CRC32 = 0xB6330846
OUTPUT_REL = Path("data") / "ge007.ntsc-final.ptbr-test.z64"


def crc32(data: bytes) -> int:
    return binascii.crc32(data) & 0xFFFFFFFF


def find_root() -> Path:
    here = Path(__file__).resolve()
    for p in (here.parent, *here.parents):
        if (p / "CMakeLists.txt").exists():
            return p
    return Path.cwd()


def find_base(root: Path) -> tuple[Path, bytes]:
    for rel in (
        Path("data/ge007.ntsc-final.original.z64"),
        Path("data/ge007.ntsc-final.z64"),
        Path("baserom.u.z64"),
        Path("data/baserom.u.z64"),
    ):
        p = root / rel
        if p.is_file():
            data = p.read_bytes()
            if crc32(data) == EXPECTED_BASE_CRC32:
                return p, data
    raise SystemExit(f"ERRO: ROM USA original CRC32 {EXPECTED_BASE_CRC32:08X} nao encontrada")


def find_ips(root: Path) -> Path:
    patches = [p for p in root.rglob("*.ips") if p.is_file()]
    if not patches:
        raise SystemExit("ERRO: nenhum patch .ips encontrado no projeto")
    named = [p for p in patches if "goldeneye" in p.name.lower()]
    return max(named or patches, key=lambda p: p.stat().st_size)


def apply_ips(source: bytes, patch: bytes) -> bytes:
    if not patch.startswith(b"PATCH"):
        raise ValueError("cabecalho IPS invalido")
    out = bytearray(source)
    pos = 5
    while True:
        if pos + 3 > len(patch):
            raise ValueError("IPS truncado")
        if patch[pos:pos + 3] == b"EOF":
            pos += 3
            break
        offset = int.from_bytes(patch[pos:pos + 3], "big")
        pos += 3
        if pos + 2 > len(patch):
            raise ValueError("IPS truncado no tamanho")
        size = int.from_bytes(patch[pos:pos + 2], "big")
        pos += 2
        if size == 0:
            if pos + 3 > len(patch):
                raise ValueError("IPS truncado em RLE")
            run = int.from_bytes(patch[pos:pos + 2], "big")
            value = patch[pos + 2]
            pos += 3
            end = offset + run
            if end > len(out):
                out.extend(b"\0" * (end - len(out)))
            out[offset:end] = bytes([value]) * run
        else:
            if pos + size > len(patch):
                raise ValueError("IPS truncado no payload")
            end = offset + size
            if end > len(out):
                out.extend(b"\0" * (end - len(out)))
            out[offset:end] = patch[pos:pos + size]
            pos += size
    if len(patch) - pos == 3:
        final_size = int.from_bytes(patch[pos:pos + 3], "big")
        out = out[:final_size] if final_size <= len(out) else out + b"\0" * (final_size - len(out))
    return bytes(out)


def main() -> int:
    root = find_root()
    base_path, base = find_base(root)
    ips_path = find_ips(root)
    print(f"ROM original OK: {base_path.relative_to(root)} CRC32={crc32(base):08X}")
    print(f"Patch: {ips_path.relative_to(root)}")
    try:
        translated = apply_ips(base, ips_path.read_bytes())
    except (OSError, ValueError) as exc:
        print(f"ERRO: {exc}")
        return 2
    out = root / OUTPUT_REL
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(translated)
    print(f"ROM PT-BR de referencia: {out.relative_to(root)} CRC32={crc32(translated):08X}")
    print("IMPORTANTE: esta ROM NAO e executada pelo PC port; use import_ptbr_patch.py.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
