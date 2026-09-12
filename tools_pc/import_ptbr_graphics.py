#!/usr/bin/env python3
"""Import graphics from the user's community-patched GoldenEye ROM safely.

The PC port cannot execute the patched ROM because the port's absolute ROM
symbols are tied to the verified US layout. This tool reconstructs an
image-segment shadow with the *original* slot layout and serves it only while
PT-BR is selected.

Important detail: g_Textures is not stored as a plain table in the retail ROM.
It lives in GoldenEye's compressed csegment. We therefore discover the table
inside decompressed RZ streams, validate it against assets/images.def, read the
patched texture sizes from the translated ROM's corresponding compressed game
data, then align the repacked image segment using many unchanged textures as
independent anchors.

A translated texture is transplanted only when its patched compressed payload
fits inside the original slot. Oversize/ambiguous entries are never written
over neighbouring assets and are reported for the next engineering pass.

Output is local-only (data/ is gitignored):
  data/ascension_ptbr_images.bin
  data/ascension_ptbr_graphics_report.txt
"""

from __future__ import annotations

import argparse
import collections
import re
import sys
import zlib
from dataclasses import dataclass
from pathlib import Path

from import_ptbr_patch import BASE_CRC32, crc32, find_rom

CART_BASE = 0x10000000
MAX_TEXTURE_SIZE = 0x100000
MAX_RZ_DECOMPRESSED = 8 * 1024 * 1024


@dataclass(frozen=True)
class TextureTable:
    rz_offset: int
    table_offset: int
    field: int
    byteorder: str
    blob_size: int
    sizes: tuple[int, ...]
    equal_count: int


def parse_images_def(root: Path) -> tuple[list[str], list[int]]:
    text = (root / "assets" / "images.def").read_text(encoding="utf-8")
    names: list[str] = []
    sizes: list[int] = []
    rx = re.compile(r"^\s*IMAGE\(\s*([^,]+)\s*,\s*(0x[0-9A-Fa-f]+|[0-9]+)\s*,", re.M)
    for m in rx.finditer(text):
        names.append(m.group(1).strip())
        sizes.append(int(m.group(2), 0))
    if len(names) < 100:
        raise RuntimeError("assets/images.def nao parece valido")
    return names, sizes


def image_segment_bounds(root: Path) -> tuple[int, int]:
    text = (root / "port" / "src" / "romassets_u.s").read_text(encoding="utf-8")

    def one(name: str) -> int:
        m = re.search(rf"{re.escape(name)}\s*,\s*0x([0-9A-Fa-f]+)", text)
        if not m:
            raise RuntimeError(f"simbolo {name} nao encontrado em romassets_u.s")
        value = int(m.group(1), 16)
        if value < CART_BASE:
            raise RuntimeError(f"endereco invalido para {name}")
        return value - CART_BASE

    start = one("_imagesSegmentRomStart")
    end = one("_imagesSegmentRomEnd")
    if end <= start:
        raise RuntimeError("segmento de imagens invalido")
    return start, end


def inflate_rz(rom: bytes, offset: int) -> bytes | None:
    """Inflate one GoldenEye 0x1172 raw-deflate stream with a generous cap."""
    if rom[offset : offset + 2] != b"\x11\x72":
        return None
    try:
        d = zlib.decompressobj(-15)
        out = d.decompress(rom[offset + 2 :], MAX_RZ_DECOMPRESSED + 1)
        if len(out) > MAX_RZ_DECOMPRESSED or not d.eof:
            return None
        return out
    except zlib.error:
        return None


def read24(blob: bytes, pos: int, byteorder: str) -> int:
    return int.from_bytes(blob[pos : pos + 3], byteorder)


def candidate_table_starts(blob: bytes, expected: list[int], field: int, byteorder: str) -> set[int]:
    """Generate plausible starts from several distinctive source sizes."""
    starts: set[int] = set()
    # Multiple anchors make discovery resilient even if the community patch
    # changes one of the first few images.
    anchor_indexes = (0, 1, 2, 3, 4, 9, 23, 40, 85, 120)
    for idx in anchor_indexes:
        if idx >= len(expected):
            continue
        needle = expected[idx].to_bytes(3, byteorder)
        pos = 0
        seen = 0
        while True:
            pos = blob.find(needle, pos)
            if pos < 0:
                break
            start = pos - field - idx * 8
            if start >= 0 and start + len(expected) * 8 + field + 3 <= len(blob):
                starts.add(start)
            pos += 1
            seen += 1
            # Avoid pathological tiny-pattern explosions. Other anchors still
            # contribute candidates, and real tables need agreement across all
            # 2698 entries to score highly.
            if seen >= 256:
                break
    return starts


def score_table(blob: bytes, start: int, field: int, byteorder: str, expected: list[int]) -> tuple[int, tuple[int, ...]]:
    sizes: list[int] = []
    equal = 0
    for i, want in enumerate(expected):
        p = start + i * 8 + field
        if p < 0 or p + 3 > len(blob):
            return -1, ()
        got = read24(blob, p, byteorder)
        if got <= 0 or got > MAX_TEXTURE_SIZE:
            return -1, ()
        sizes.append(got)
        if got == want:
            equal += 1
    return equal, tuple(sizes)


def scan_texture_tables(
    rom: bytes,
    expected: list[int],
    *,
    required_equal_ratio: float,
    fixed_layout: tuple[int, str] | None = None,
) -> list[TextureTable]:
    """Find g_Textures inside decompressed RZ game-data streams.

    The N64 compiler's bitfield byte placement is discovered instead of assumed.
    The table has an 8-byte entry stride (verified by the game code); the
    24-bit pre-boot dataoffset field contains each compressed image size until
    image_entries_load() converts sizes into cumulative offsets at runtime.
    """
    results: list[TextureTable] = []
    min_equal = int(len(expected) * required_equal_ratio)
    layouts = [fixed_layout] if fixed_layout else [
        (field, byteorder)
        for field in range(6)
        for byteorder in ("big", "little")
    ]

    pos = 0
    while True:
        pos = rom.find(b"\x11\x72", pos)
        if pos < 0:
            break
        blob = inflate_rz(rom, pos)
        if blob is None or len(blob) < len(expected) * 8:
            pos += 1
            continue

        for field, byteorder in layouts:
            for start in candidate_table_starts(blob, expected, field, byteorder):
                equal, sizes = score_table(blob, start, field, byteorder, expected)
                if equal < min_equal:
                    continue

                # The source table is followed by the 0xFFFF sentinel entry.
                # Treat it as a strong discriminator when present, but do not
                # make patch import depend on the exact neighbouring bitfields.
                sentinel_pos = start + len(expected) * 8 + field
                if sentinel_pos + 3 <= len(blob):
                    sentinel = read24(blob, sentinel_pos, byteorder)
                    if sentinel not in (0xFFFF, 0xFFFFFF):
                        # A near-perfect 2698-entry match is already decisive;
                        # keep it only when it is overwhelmingly strong.
                        if equal < len(expected) - 4:
                            continue

                results.append(
                    TextureTable(
                        rz_offset=pos,
                        table_offset=start,
                        field=field,
                        byteorder=byteorder,
                        blob_size=len(blob),
                        sizes=sizes,
                        equal_count=equal,
                    )
                )
        pos += 1

    # Remove duplicate discoveries of the same physical table, then rank by
    # exact source-size matches and compactness of the containing stream.
    unique: dict[tuple[int, int, int, str], TextureTable] = {}
    for item in results:
        key = (item.rz_offset, item.table_offset, item.field, item.byteorder)
        prev = unique.get(key)
        if prev is None or item.equal_count > prev.equal_count:
            unique[key] = item
    return sorted(unique.values(), key=lambda x: (x.equal_count, -x.blob_size), reverse=True)


def locate_original_table(rom: bytes, expected: list[int]) -> TextureTable:
    tables = scan_texture_tables(rom, expected, required_equal_ratio=1.0)
    if not tables:
        raise RuntimeError("nao foi possivel localizar g_Textures dentro do csegment RZ original")
    best = tables[0]
    equally_good = [t for t in tables if t.equal_count == best.equal_count]
    if len(equally_good) > 1:
        # If multiple byte-layout interpretations point at the exact same table,
        # prefer the one whose sentinel is the canonical 0xFFFF. Otherwise stop.
        locations = {(t.rz_offset, t.table_offset) for t in equally_good}
        if len(locations) > 1:
            raise RuntimeError("g_Textures original ficou ambiguo; importacao abortada por seguranca")
    return best


def locate_patch_table(rom: bytes, expected: list[int], original: TextureTable) -> TextureTable:
    tables = scan_texture_tables(
        rom,
        expected,
        required_equal_ratio=0.80,
        fixed_layout=(original.field, original.byteorder),
    )
    if not tables:
        raise RuntimeError("nao foi possivel localizar g_Textures dentro do csegment RZ PT-BR")

    # Most images are untouched by a translation patch, so the correct table
    # should dwarf false positives in exact-size agreement. Use decompressed
    # csegment size only as a tie-breaker; Setup Editor may recompress/relocate it.
    best = tables[0]
    if best.equal_count < int(len(expected) * 0.90):
        raise RuntimeError(
            f"g_Textures PT-BR teve pouca concordancia estrutural ({best.equal_count}/{len(expected)})"
        )
    if len(tables) > 1 and tables[1].equal_count == best.equal_count:
        a = abs(best.blob_size - original.blob_size)
        b = abs(tables[1].blob_size - original.blob_size)
        if b < a:
            best = tables[1]
        elif b == a and (tables[1].rz_offset, tables[1].table_offset) != (best.rz_offset, best.table_offset):
            raise RuntimeError("g_Textures PT-BR ficou ambiguo; importacao abortada por seguranca")
    return best


def cumulative(sizes: list[int] | tuple[int, ...]) -> list[int]:
    out: list[int] = []
    n = 0
    for size in sizes:
        out.append(n)
        n += size
    return out


def candidate_patch_start(
    base: bytes,
    patched: bytes,
    orig_start: int,
    orig_end: int,
    orig_sizes: list[int],
    patch_sizes: list[int] | tuple[int, ...],
) -> tuple[int, int, int]:
    ocum = cumulative(orig_sizes)
    pcum = cumulative(patch_sizes)
    orig_total = sum(orig_sizes)
    patch_total = sum(patch_sizes)
    segment_len = orig_end - orig_start
    if orig_total > segment_len:
        raise RuntimeError("images.def excede o segmento original")
    tail_pad = segment_len - orig_total

    candidates: set[int] = {orig_start, orig_end - tail_pad - patch_total}
    votes: collections.Counter[int] = collections.Counter()

    # Exact unchanged textures are excellent anchors. Derive the translated
    # segment start from many independent anchors and let them vote. Searching
    # +/- 2 MiB is deliberately wider than typical Setup Editor relocations but
    # still avoids accidental matches elsewhere in the ROM.
    step = max(1, len(orig_sizes) // 220)
    search_lo = max(0, orig_start - 0x200000)
    search_hi = min(len(patched), orig_end + 0x200000)
    for i in range(0, len(orig_sizes), step):
        if orig_sizes[i] != patch_sizes[i] or orig_sizes[i] < 48:
            continue
        needle = base[orig_start + ocum[i] : orig_start + ocum[i] + orig_sizes[i]]
        pos = patched.find(needle, search_lo, search_hi)
        if pos < 0:
            continue
        if patched.find(needle, pos + 1, search_hi) >= 0:
            continue
        votes[pos - pcum[i]] += 1

    for start, _ in votes.most_common(20):
        candidates.add(start)

    def score(start: int) -> tuple[int, int]:
        if start < 0 or start + patch_total > len(patched):
            return (-1, -1)
        exact = 0
        comparable = 0
        for i, osize in enumerate(orig_sizes):
            if osize != patch_sizes[i] or osize < 16:
                continue
            comparable += 1
            a = base[orig_start + ocum[i] : orig_start + ocum[i] + osize]
            b = patched[start + pcum[i] : start + pcum[i] + osize]
            if a == b:
                exact += 1
        return exact, comparable

    ranked = sorted(((score(s), votes[s], s) for s in candidates), reverse=True)
    if not ranked or ranked[0][0][0] < 20:
        raise RuntimeError("nao houve ancoras suficientes para localizar o segmento de imagens PT-BR")

    (exact, comparable), vote_count, start = ranked[0]
    if comparable and exact / comparable < 0.35:
        raise RuntimeError(
            f"segmento PT-BR nao passou na validacao de identidade ({exact}/{comparable} ancoras)"
        )
    if len(ranked) > 1 and ranked[1][0] == ranked[0][0] and ranked[1][2] != start:
        raise RuntimeError("segmento de imagens PT-BR ficou ambiguo; importacao abortada por seguranca")
    return start, exact, vote_count


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--strict", action="store_true", help="falha se algum grafico alterado nao couber no slot original")
    args = ap.parse_args()

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
        names, orig_sizes = parse_images_def(root)
        orig_start, orig_end = image_segment_bounds(root)
    except (FileNotFoundError, RuntimeError) as exc:
        print(f"ERRO: {exc}")
        return 2

    base = base_path.read_bytes()
    patched = patch_path.read_bytes()
    if crc32(base) != BASE_CRC32:
        print("ERRO: ROM original nao e a USA verificada B6330846")
        return 2
    if orig_end > len(base):
        print("ERRO: segmento de imagens sai da ROM original")
        return 2

    print(f"ROM original: {base_path.relative_to(root)} CRC32={crc32(base):08X}")
    print(f"ROM do patch: {patch_path.relative_to(root)} CRC32={crc32(patched):08X}")
    print(f"Texturas conhecidas: {len(names)}")
    print("Localizando g_Textures dentro do csegment comprimido...")

    try:
        original_table = locate_original_table(base, orig_sizes)
        patch_table = locate_patch_table(patched, orig_sizes, original_table)
        patch_sizes = list(patch_table.sizes)
        patch_start, exact_anchors, votes = candidate_patch_start(
            base, patched, orig_start, orig_end, orig_sizes, patch_sizes
        )
    except RuntimeError as exc:
        print(f"ERRO: {exc}")
        print("Nenhum sidecar grafico foi substituido.")
        return 3

    print(
        "g_Textures original: "
        f"RZ@0x{original_table.rz_offset:08X} +0x{original_table.table_offset:X} "
        f"campo24=+{original_table.field} {original_table.byteorder}"
    )
    print(
        "g_Textures PT-BR:   "
        f"RZ@0x{patch_table.rz_offset:08X} +0x{patch_table.table_offset:X} "
        f"iguais={patch_table.equal_count}/{len(orig_sizes)}"
    )
    print(f"Images original: 0x{orig_start:08X}..0x{orig_end:08X}")
    print(f"Images PT-BR:   0x{patch_start:08X} (ancoras exatas={exact_anchors}, votos={votes})")

    ocum = cumulative(orig_sizes)
    pcum = cumulative(patch_sizes)
    shadow = bytearray(base[orig_start:orig_end])
    changed: list[str] = []
    imported: list[str] = []
    oversize: list[tuple[str, int, int]] = []

    for i, name in enumerate(names):
        osize = orig_sizes[i]
        psize = patch_sizes[i]
        ostart = orig_start + ocum[i]
        pstart = patch_start + pcum[i]
        if pstart < 0 or pstart + psize > len(patched):
            print(f"ERRO: textura PT-BR {name} aponta para fora da ROM")
            return 3

        oblock = base[ostart : ostart + osize]
        pblock = patched[pstart : pstart + psize]
        if osize == psize and oblock == pblock:
            continue

        changed.append(name)
        if psize > osize:
            oversize.append((name, osize, psize))
            continue

        # Preserve the original slot boundary. The translated compressed stream
        # is copied only into the bytes it owns; untouched tail bytes remain the
        # original ROM data. This prevents one replacement from ever corrupting
        # the next texture.
        rel = ocum[i]
        shadow[rel : rel + psize] = pblock
        imported.append(name)

    report_lines = [
        "Ascension PT-BR community graphics import",
        f"base={base_path.name} crc32={crc32(base):08X}",
        f"patched={patch_path.name} crc32={crc32(patched):08X}",
        (
            "original_texture_table="
            f"rz:0x{original_table.rz_offset:08X}+0x{original_table.table_offset:X} "
            f"field={original_table.field} endian={original_table.byteorder}"
        ),
        (
            "patched_texture_table="
            f"rz:0x{patch_table.rz_offset:08X}+0x{patch_table.table_offset:X} "
            f"equal={patch_table.equal_count}/{len(orig_sizes)}"
        ),
        f"original_segment=0x{orig_start:08X}-0x{orig_end:08X}",
        f"patched_segment=0x{patch_start:08X}",
        f"known={len(names)} changed={len(changed)} imported={len(imported)} oversize={len(oversize)}",
        "",
        "IMPORTED:",
        *imported,
        "",
        "OVERSIZE (not imported):",
        *[f"{n}: original={a} patch={b}" for n, a, b in oversize],
        "",
    ]
    report = root / "data" / "ascension_ptbr_graphics_report.txt"
    report.write_text("\n".join(report_lines), encoding="utf-8")

    print(f"Graficos alterados pelo patch: {len(changed)}")
    print(f"Graficos importados com seguranca: {len(imported)}")
    print(f"Graficos maiores que o slot original: {len(oversize)}")

    if not imported:
        print("ERRO: nenhum grafico alterado pôde ser importado com seguranca.")
        print(f"Relatorio: {report.relative_to(root)}")
        return 4

    if args.strict and oversize:
        print("ERRO: modo --strict recusou sidecar parcial.")
        for name, old, new in oversize[:30]:
            print(f"  {name}: {old} -> {new} bytes")
        print(f"Relatorio: {report.relative_to(root)}")
        print("O sidecar anterior, se existir, foi preservado.")
        return 5

    out = root / "data" / "ascension_ptbr_images.bin"
    tmp = out.with_suffix(".bin.tmp")
    tmp.write_bytes(shadow)
    tmp.replace(out)

    print(f"Sidecar: {out.relative_to(root)} ({len(shadow)} bytes)")
    print(f"Relatorio: {report.relative_to(root)}")
    if oversize:
        print("AVISO: existem graficos ainda nao importados; o jogo usara o original nesses slots.")
    else:
        print("OK: todos os graficos alterados detectados couberam no layout original.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
