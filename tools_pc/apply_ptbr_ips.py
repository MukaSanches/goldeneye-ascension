#!/usr/bin/env python3
"""Apply the community Brazilian Portuguese IPS patch to a verified US GoldenEye ROM.

This tool does not ship a ROM or patch. It only uses files already present on
this machine. It searches the repository for a .ips file, verifies the known
GoldenEye 007 (USA) base ROM CRC32, applies the IPS, and writes the translated
ROM to data/ge007.ntsc-final.z64 so the PC port picks it up first.
"""

from __future__ import annotations

import binascii
import sys
from pathlib import Path

EXPECTED_BASE_CRC32 = 0xB6330846
OUTPUT_REL = Path("data") / "ge007.ntsc-final.z64"
BASE_CANDIDATES = (
    Path("baserom.u.z64"),
    Path("data") / "baserom.u.z64",
    Path("ge007.ntsc-final.z64"),
    Path("data") / "ge007.ntsc-final.z64",
)


def crc32(data: bytes) -> int:
    return binascii.crc32(data) & 0xFFFFFFFF


def find_repo_root() -> Path:
    here = Path(__file__).resolve()
    for p in (here.parent, *here.parents):
        if (p / ".git").exists() or (p / "CMakeLists.txt").exists():
            return p
    return Path.cwd()


def find_base_rom(root: Path) -> tuple[Path, bytes]:
    checked = []
    for rel in BASE_CANDIDATES:
        p = root / rel
        if not p.is_file():
            continue
        data = p.read_bytes()
        c = crc32(data)
        checked.append((p, c))
        if c == EXPECTED_BASE_CRC32:
            return p, data

    # Fallback: find any z64 in the repository with the correct CRC.
    for p in root.rglob("*.z64"):
        if p == root / OUTPUT_REL:
            continue
        try:
            data = p.read_bytes()
        except OSError:
            continue
        c = crc32(data)
        if c == EXPECTED_BASE_CRC32:
            return p, data
        checked.append((p, c))

    print("ERRO: ROM base correta nao encontrada.")
    print(f"Esperado CRC32: {EXPECTED_BASE_CRC32:08X}")
    if checked:
        print("ROMs encontradas:")
        for p, c in checked[:20]:
            print(f"  {p.relative_to(root)}  CRC32={c:08X}")
    raise SystemExit(2)


def find_ips(root: Path) -> Path:
    ips_files = [p for p in root.rglob("*.ips") if p.is_file()]
    if not ips_files:
        print("ERRO: nenhum arquivo .ips foi encontrado dentro do projeto.")
        raise SystemExit(3)

    # Prefer GoldenEye-named patches; otherwise pick the largest IPS file.
    named = [p for p in ips_files if "goldeneye" in p.name.lower()]
    candidates = named or ips_files
    candidates.sort(key=lambda p: p.stat().st_size, reverse=True)
    return candidates[0]


def apply_ips(source: bytes, patch: bytes) -> bytes:
    if not patch.startswith(b"PATCH"):
        raise ValueError("arquivo nao possui cabecalho IPS valido")

    out = bytearray(source)
    pos = 5

    while True:
        if pos + 3 > len(patch):
            raise ValueError("IPS truncado antes do marcador EOF")

        if patch[pos:pos + 3] == b"EOF":
            pos += 3
            break

        offset = int.from_bytes(patch[pos:pos + 3], "big")
        pos += 3

        if pos + 2 > len(patch):
            raise ValueError("IPS truncado no tamanho do registro")
        size = int.from_bytes(patch[pos:pos + 2], "big")
        pos += 2

        if size == 0:
            if pos + 3 > len(patch):
                raise ValueError("IPS truncado em registro RLE")
            run = int.from_bytes(patch[pos:pos + 2], "big")
            value = patch[pos + 2]
            pos += 3
            end = offset + run
            if end > len(out):
                out.extend(b"\x00" * (end - len(out)))
            out[offset:end] = bytes([value]) * run
        else:
            if pos + size > len(patch):
                raise ValueError("IPS truncado no payload do registro")
            end = offset + size
            if end > len(out):
                out.extend(b"\x00" * (end - len(out)))
            out[offset:end] = patch[pos:pos + size]
            pos += size

    # IPS may contain a 3-byte final size after EOF.
    remaining = len(patch) - pos
    if remaining == 3:
        final_size = int.from_bytes(patch[pos:pos + 3], "big")
        if final_size < len(out):
            del out[final_size:]
        elif final_size > len(out):
            out.extend(b"\x00" * (final_size - len(out)))
    elif remaining not in (0,):
        print(f"Aviso: IPS contem {remaining} byte(s) extras apos EOF.")

    return bytes(out)


def preserve_existing_output(out_path: Path, existing: bytes) -> None:
    """Never destroy an existing ROM silently."""
    if crc32(existing) == EXPECTED_BASE_CRC32:
        backup = out_path.with_name("ge007.ntsc-final.original.z64")
    else:
        backup = out_path.with_name("ge007.ntsc-final.previous.z64")

    if backup.exists():
        if backup.read_bytes() == existing:
            return
        i = 2
        while True:
            candidate = backup.with_name(f"{backup.stem}.{i}{backup.suffix}")
            if not candidate.exists():
                backup = candidate
                break
            i += 1

    backup.write_bytes(existing)
    print(f"Backup preservado: {backup.name}")


def main() -> int:
    root = find_repo_root()
    print(f"Projeto: {root}")

    base_path, base = find_base_rom(root)
    print(f"ROM base OK: {base_path.relative_to(root)}")
    print(f"CRC32 base: {crc32(base):08X}")

    ips_path = find_ips(root)
    print(f"Patch IPS: {ips_path.relative_to(root)}")

    try:
        translated = apply_ips(base, ips_path.read_bytes())
    except (OSError, ValueError) as exc:
        print(f"ERRO ao aplicar IPS: {exc}")
        return 4

    out_path = root / OUTPUT_REL
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if out_path.exists():
        existing = out_path.read_bytes()
        if existing == translated:
            print("ROM PT-BR ja esta pronta; nenhum arquivo foi alterado.")
            print(f"Saida: {out_path.relative_to(root)}")
            print(f"CRC32 PT-BR: {crc32(existing):08X}")
            return 0
        preserve_existing_output(out_path, existing)

    out_path.write_bytes(translated)
    print("\nSUCESSO: ROM PT-BR gerada sem perder a ROM anterior.")
    print(f"Saida: {out_path.relative_to(root)}")
    print(f"Tamanho: {len(translated)} bytes")
    print(f"CRC32 PT-BR: {crc32(translated):08X}")
    print("O PC port procura data/ge007.ntsc-final.z64 antes de baserom.u.z64.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
