#!/usr/bin/env python3
"""Import GoldenEye PT-BR text from a user-supplied community-patched ROM.

The PC port must keep using the verified original US ROM because its absolute
asset symbols depend on the original layout. A traditional IPS ROM hack can
relocate compressed resources, so mapping the entire patched ROM (or copying
fixed byte ranges from it) is unsafe.

This tool scans the patched ROM for GoldenEye RZ streams, identifies translated
language banks by globally aligning their slot-table structure and ROM order,
and writes a compact runtime catalog to data/ascension_ptbr.bin. No ROM or
community patch is committed to this repository.
"""

from __future__ import annotations

import binascii
import csv
import math
import struct
import sys
import zlib
from dataclasses import dataclass
from pathlib import Path

BASE_CRC32 = 0xB6330846
MAGIC = b"ASPTBR1\0"
MAX_DECOMPRESSED = 2 * 1024 * 1024

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


def structural_score(src: Bank, dst: Bank) -> float:
    """Score a likely translation without requiring identical zero-slot layout.

    Setup Editor/community patchers may rebuild a bank and represent empty slots
    differently, so exact `(slot_count, zero_positions)` equality is too strict.
    Slot count, punctuation/newline structure, readable text, similar expanded
    size and ROM ordering are much more stable across translations.
    """
    ns = len(src.slots)
    nd = len(dst.slots)
    delta = abs(ns - nd)
    if delta > 2 or dst.ascii_ratio < 0.68:
        return -math.inf

    score = 32.0 if delta == 0 else (17.0 if delta == 1 else 8.0)
    score += dst.ascii_ratio * 8.0

    # Translation changes words but normally preserves line structure and most
    # punctuation. Only compare positions available in both banks.
    pairs = [(a, b) for a, b in zip(src.slots, dst.slots) if a is not None and b is not None]
    if pairs:
        structural = 0.0
        exact = 0
        changed = 0
        for a, b in pairs:
            if a == b:
                exact += 1
            else:
                changed += 1
            structural += 1.0 if a.count(b"\n") == b.count(b"\n") else 0.0
            structural += 0.5 if a.endswith(b"\n") == b.endswith(b"\n") else 0.0
            structural += 0.5 if a.count(b":") == b.count(b":") else 0.0
        score += (structural / (2.0 * len(pairs))) * 12.0
        # A real translation should change something. Do not reward a stale
        # byte-identical English copy, but allow proper names to remain equal.
        diff = changed / len(pairs)
        score += min(diff, 0.55) * 18.0
        if diff < 0.02:
            score -= 18.0

    # Expanded sizes stay in the same ballpark even when Portuguese is longer.
    size_ratio = len(dst.blob) / max(1, len(src.blob))
    if 0.55 <= size_ratio <= 1.85:
        score += 7.0 - abs(math.log(size_ratio)) * 3.0
    else:
        score -= 10.0

    return score


def choose_patch_banks(original: dict[str, Bank], candidates: list[Bank]) -> dict[str, Bank]:
    sources = sorted(original.items(), key=lambda kv: kv[1].offset)
    if not sources:
        return {}

    # GoldenEye's text resources live in one compact ROM area. Community patch
    # tools can move/repack that area, but not hundreds of kilobytes away. This
    # eliminates unrelated RZ assets that happen to parse like a string table.
    lo = min(b.offset for _, b in sources) - 0x60000
    hi = max(b.offset for _, b in sources) + 0x60000
    pool = sorted(
        [c for c in candidates if lo <= c.offset <= hi and c.ascii_ratio >= 0.68],
        key=lambda b: b.offset,
    )
    if not pool:
        return {}

    # Global monotonic alignment. The patch may rebuild every bank, so matching
    # each bank independently is ambiguous. Their order in the resource segment
    # is stable; dynamic programming uses that invariant and can skip J banks or
    # unrelated false-positive RZ streams between translated E banks.
    n = len(sources)
    m = len(pool)
    neg = -1.0e30
    dp = [[neg] * (m + 1) for _ in range(n + 1)]
    prev: list[list[tuple[int, int, bool] | None]] = [[None] * (m + 1) for _ in range(n + 1)]
    for j in range(m + 1):
        dp[0][j] = 0.0
        if j:
            prev[0][j] = (0, j - 1, False)

    for i in range(1, n + 1):
        src = sources[i - 1][1]
        for j in range(1, m + 1):
            # Skip candidate (J bank, duplicate, or false positive).
            if dp[i][j - 1] > dp[i][j]:
                dp[i][j] = dp[i][j - 1]
                prev[i][j] = (i, j - 1, False)

            s = structural_score(src, pool[j - 1])
            if s != -math.inf and dp[i - 1][j - 1] > neg / 2:
                v = dp[i - 1][j - 1] + s
                if v > dp[i][j]:
                    dp[i][j] = v
                    prev[i][j] = (i - 1, j - 1, True)

    # Backtrack best alignment. Missing sources are allowed here so diagnostics
    # can report them; REQUIRED validation below still refuses unsafe catalogs.
    best_j = max(range(m + 1), key=lambda j: dp[n][j])
    i, j = n, best_j
    matches: dict[int, Bank] = {}
    while i > 0 and j >= 0:
        p = prev[i][j]
        if p is None:
            break
        pi, pj, matched = p
        if matched:
            matches[i - 1] = pool[j - 1]
        i, j = pi, pj

    chosen: dict[str, Bank] = {}
    shifts: list[int] = []
    for idx, (name, src) in enumerate(sources):
        dst = matches.get(idx)
        if dst is None:
            continue
        score = structural_score(src, dst)
        diff = difference_ratio(src, dst)
        if score < 28.0:
            continue
        if name in REQUIRED and diff < 0.02:
            continue
        chosen[name] = dst
        shifts.append(dst.offset - src.offset)

    # Safety check: repacked text banks should move coherently. A single wildly
    # displaced match is almost certainly a false positive; drop it instead of
    # ever emitting a guessed translation.
    if len(shifts) >= 5:
        ordered = sorted(shifts)
        median = ordered[len(ordered) // 2]
        for name in list(chosen):
            src = original[name]
            dst = chosen[name]
            if abs((dst.offset - src.offset) - median) > 0x30000:
                del chosen[name]

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
