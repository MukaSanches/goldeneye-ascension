#!/usr/bin/env python3
"""Import GoldenEye PT-BR text from a user-supplied community-patched ROM.

The PC port must keep using the verified original US ROM because its absolute
asset symbols depend on the original layout. A traditional IPS ROM hack can
relocate compressed resources, so mapping the entire patched ROM (or copying
fixed byte ranges from it) is unsafe.

This tool instead scans the patched ROM for GoldenEye RZ streams, identifies
translated language banks by their slot-table shape, and writes a compact
runtime catalog to data/ascension_ptbr.bin. No ROM or community patch is
committed to this repository.
"""

from __future__ import annotations

import binascii
import csv
import struct
import sys
import zlib
from dataclasses import dataclass
from pathlib import Path

BASE_CRC32 = 0xB6330846
MAGIC = b"ASPTBR1\0"
MAX_DECOMPRESSED = 2 * 1024 * 1024

# Exact bank order used by src/game/language.c. Bank 0 is unused.
BANK_IDS = {
    "LameE": 1, "LarchE": 2, "LarkE": 3, "LashE": 4, "LaztE": 5,
    "LcatE": 6, "LcaveE": 7, "LarecE": 8, "LcradE": 9, "LcrypE": 10,
    "LdamE": 11, "LdepoE": 12, "LdestE": 13, "LdishE": 14, "LearE": 15,
    "LeldE": 16, "LimpE": 17, "LjunE": 18, "LleeE": 19, "LlenE": 20,
    "LlipE": 21, "LlueE": 22, "LoatE": 23, "LpamE": 24, "LpeteE": 25,
    "LrefE": 26, "LritE": 27, "LrunE": 28, "LsevbE": 29, "LsevE": 30,
    "LsevxE": 31, "LsevxbE": 32, "LshoE": 33, "LsiloE": 34,
    "LstatE": 35, "LtraE": 36, "LwaxE": 37, "LgunE": 38,
    "LtitleE": 39, "LmpmenuE": 40, "LpropobjE": 41, "LmpweaponsE": 42,
    "LoptionsE": 43, "LmiscE": 44,
}

# Banks that must map before we accept the catalog. Unused/debug-only banks are
# deliberately not required.
REQUIRED = {
    "LarchE", "LarkE", "LaztE", "LcaveE", "LarecE", "LcradE", "LcrypE",
    "LdamE", "LdepoE", "LdestE", "LjunE", "LlenE", "LpeteE", "LrunE",
    "LsevbE", "LsevE", "LsevxE", "LsevxbE", "LsiloE", "LstatE", "LtraE",
    "LgunE", "LtitleE", "LmpmenuE", "LpropobjE", "LmpweaponsE",
    "LoptionsE", "LmiscE",
}


@dataclass
class Bank:
    offset: int
    blob: bytes
    slots: list[bytes | None]
    shape: tuple[int, tuple[int, ...]]
    ascii_ratio: float


def crc32(data: bytes) -> int:
    return binascii.crc32(data) & 0xFFFFFFFF


def inflate_rz(rom: bytes, offset: int) -> bytes | None:
    if rom[offset:offset + 2] != b"\x11\x72":
        return None
    try:
        d = zlib.decompressobj(-15)
        out = d.decompress(rom[offset + 2 :], MAX_DECOMPRESSED + 1)
        if len(out) > MAX_DECOMPRESSED or not d.eof:
            return None
        return out
    except zlib.error:
        return None


def parse_language_bank(blob: bytes, offset: int) -> Bank | None:
    if len(blob) < 8:
        return None

    max_words = min(len(blob) // 4, 1024)
    words = [struct.unpack_from(">I", blob, i * 4)[0] for i in range(max_words)]
    positives = [v for v in words if 0 < v < len(blob)]
    if not positives:
        return None

    table_end = min(positives)
    if table_end % 4:
        return None
    nslots = table_end // 4
    if nslots < 2 or nslots > max_words:
        return None

    offsets = words[:nslots]
    if any(v != 0 and not (table_end <= v < len(blob)) for v in offsets):
        return None

    slots: list[bytes | None] = []
    total = 0
    printable = 0
    nonzero = 0

    for v in offsets:
        if v == 0:
            slots.append(None)
            continue
        end = blob.find(b"\0", v)
        if end < 0:
            return None
        s = blob[v:end]
        # Language strings can contain newlines/tabs. Japanese banks may use
        # high bytes; keeping them valid here helps shape matching while the
        # ASCII score later selects the translated E/PT-BR bank.
        total += len(s)
        printable += sum(c in (9, 10, 13) or 32 <= c <= 126 for c in s)
        nonzero += 1
        slots.append(s)

    if nonzero < 2:
        return None

    zeroes = tuple(i for i, v in enumerate(offsets) if v == 0)
    ratio = printable / total if total else 0.0
    return Bank(offset, blob, slots, (nslots, zeroes), ratio)


def scan_rz_language_banks(rom: bytes) -> list[Bank]:
    result: list[Bank] = []
    pos = 0
    while True:
        pos = rom.find(b"\x11\x72", pos)
        if pos < 0:
            break
        blob = inflate_rz(rom, pos)
        if blob is not None:
            bank = parse_language_bank(blob, pos)
            if bank is not None:
                result.append(bank)
        pos += 1
    return result


def find_rom(root: Path, names: tuple[str, ...], expected_crc: int | None = None) -> Path:
    for name in names:
        p = root / name
        if p.is_file():
            if expected_crc is None or crc32(p.read_bytes()) == expected_crc:
                return p
    if expected_crc is not None:
        for p in (root / "data").glob("*.z64"):
            try:
                if crc32(p.read_bytes()) == expected_crc:
                    return p
            except OSError:
                pass
    raise FileNotFoundError(names[0])


def original_banks(root: Path, rom: bytes) -> dict[str, Bank]:
    result: dict[str, Bank] = {}
    filelist = root / "scripts" / "filelist.u.csv"
    with filelist.open("r", encoding="utf-8", newline="") as f:
        for row in csv.reader(f):
            if len(row) < 3:
                continue
            try:
                off = int(row[0])
            except ValueError:
                continue
            name = Path(row[2].replace("\\", "/")).name
            if name not in BANK_IDS:
                continue
            blob = inflate_rz(rom, off)
            if blob is None:
                continue
            bank = parse_language_bank(blob, off)
            if bank is not None:
                result[name] = bank
    return result


def difference_ratio(a: Bank, b: Bank) -> float:
    pairs = [(x, y) for x, y in zip(a.slots, b.slots) if x is not None and y is not None]
    if not pairs:
        return 0.0
    return sum(x != y for x, y in pairs) / len(pairs)


def choose_patch_banks(original: dict[str, Bank], candidates: list[Bank]) -> dict[str, Bank]:
    by_shape: dict[tuple[int, tuple[int, ...]], list[Bank]] = {}
    for c in candidates:
        by_shape.setdefault(c.shape, []).append(c)

    used: set[int] = set()
    chosen: dict[str, Bank] = {}

    # Process in original ROM order. Shape + high printable ratio + actual
    # content difference reliably separates PT-BR E banks from their J twins
    # and from stale/orphaned English copies left by old patching tools.
    for name, src in sorted(original.items(), key=lambda kv: kv[1].offset):
        pool = [c for c in by_shape.get(src.shape, []) if c.offset not in used]
        if not pool:
            continue

        def score(c: Bank) -> tuple[float, float, float]:
            diff = difference_ratio(src, c)
            # Prefer a translated, ASCII-readable candidate. Distance is only
            # a tie-breaker because Setup Editor is allowed to relocate files.
            distance = abs(c.offset - src.offset)
            return (diff, c.ascii_ratio, -distance)

        best = max(pool, key=score)
        diff = difference_ratio(src, best)

        # E/PT-BR should be overwhelmingly readable ASCII (the 2012 patch does
        # not use accented glyphs). Reject likely J/binary false positives.
        if best.ascii_ratio < 0.70:
            continue

        # For an unused/untranslated bank, an exact original match is fine;
        # for real game banks we expect the community patch to differ.
        if name in REQUIRED and diff < 0.02:
            continue

        chosen[name] = best
        used.add(best.offset)

    return chosen


def build_catalog(chosen: dict[str, Bank]) -> tuple[bytes, int]:
    entries: list[tuple[int, bytes]] = []
    for name, bank in chosen.items():
        bank_id = BANK_IDS[name]
        for slot, text in enumerate(bank.slots):
            if text is not None:
                entries.append(((bank_id << 10) | slot, text))

    entries.sort(key=lambda x: x[0])
    header_size = 12 + len(entries) * 8
    strings = bytearray()
    records = bytearray()

    for slot_id, text in entries:
        off = header_size + len(strings)
        records += struct.pack("<II", slot_id, off)
        strings += text + b"\0"

    out = bytearray(MAGIC)
    out += struct.pack("<I", len(entries))
    out += records
    out += strings
    return bytes(out), len(entries)


def main() -> int:
    root = Path(__file__).resolve().parents[1]

    try:
        base_path = find_rom(
            root,
            ("data/ge007.ntsc-final.original.z64", "data/ge007.ntsc-final.z64", "baserom.u.z64"),
            BASE_CRC32,
        )
        patch_path = find_rom(
            root,
            ("data/ge007.ntsc-final.ptbr-test.z64", "data/ge007.ntsc-final.community-ptbr.z64"),
        )
    except FileNotFoundError as exc:
        print(f"ERRO: ROM necessaria nao encontrada: {exc}")
        return 2

    base = base_path.read_bytes()
    patched = patch_path.read_bytes()

    print(f"ROM original: {base_path.relative_to(root)}  CRC32={crc32(base):08X}")
    print(f"ROM do patch: {patch_path.relative_to(root)}  CRC32={crc32(patched):08X}")
    print("Analisando bancos RZ da traducao comunitaria...")

    originals = original_banks(root, base)
    candidates = scan_rz_language_banks(patched)
    chosen = choose_patch_banks(originals, candidates)

    missing = sorted(REQUIRED - chosen.keys())
    print(f"Bancos originais reconhecidos: {len(originals)}")
    print(f"Candidatos na ROM PT-BR:       {len(candidates)}")
    print(f"Bancos PT-BR mapeados:         {len(chosen)}")

    for name in sorted(chosen, key=lambda n: BANK_IDS[n]):
        src = originals[name]
        dst = chosen[name]
        print(
            f"  {name:<12} bank={BANK_IDS[name]:2d} "
            f"0x{src.offset:08X} -> 0x{dst.offset:08X} "
            f"slots={len(dst.slots):3d} diff={difference_ratio(src, dst)*100:5.1f}%"
        )

    if missing:
        print("\nERRO: nao foi seguro identificar todos os bancos obrigatorios:")
        print("  " + ", ".join(missing))
        print("Nenhum catalogo foi substituido.")
        return 3

    catalog, count = build_catalog(chosen)
    out = root / "data" / "ascension_ptbr.bin"
    tmp = out.with_suffix(".bin.tmp")
    tmp.write_bytes(catalog)
    tmp.replace(out)

    report = root / "data" / "ascension_ptbr_report.txt"
    report.write_text(
        "Ascension PT-BR community patch import\n"
        f"base={base_path.name} crc32={crc32(base):08X}\n"
        f"patched={patch_path.name} crc32={crc32(patched):08X}\n"
        f"mapped_banks={len(chosen)} strings={count}\n",
        encoding="utf-8",
    )

    print(f"\nSUCESSO: {count} strings importadas exclusivamente do patch comunitario.")
    print(f"Catalogo: {out.relative_to(root)}")
    print("A ROM original continua sendo a ROM executada pelo PC port.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
