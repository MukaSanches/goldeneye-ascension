#!/usr/bin/env python3
"""Import graphics from the user's community-patched GoldenEye ROM safely.

The PC port must keep executing the verified US ROM. The community patch can
repack the image segment and change the compressed size table, so replacing the
whole ROM breaks the port's absolute ROM symbols.

This importer uses the verified US executable layout instead of heuristically
searching every RZ stream:

* the US c_data RZ stream starts at ROM 0x21990;
* the decompressed csegment starts at 0x80020D90;
* g_Textures starts at 0x80049300;
* on the original N64 layout, dataoffset is the low 24 bits of word 0.

Those facts are all present in the decomp/build files. The exact table position
is still validated against every size in assets/images.def before any output is
written. The translated ROM must then expose the same table layout and retain a
large structural match.

The result is a local sidecar with the original image-segment layout. Only
translated texture payloads that fit inside their original slot are copied.
Nothing ever overwrites the verified ROM.

Outputs (gitignored):
  data/ascension_ptbr_images.bin
  data/ascension_ptbr_graphics_report.txt
"""

from __future__ import annotations

import argparse
import collections
import csv
import re
import sys
import zlib
from dataclasses import dataclass
from pathlib import Path

from import_ptbr_patch import BASE_CRC32, crc32, find_rom

CART_BASE = 0x10000000
MAX_TEXTURE_SIZE = 0x100000
MAX_RZ_DECOMPRESSED = 8 * 1024 * 1024

# Verified NTSC-U layout (CRC32 B6330846).
# ge007.ld: code ends at 0x70020D90 -> csegment VADDR 0x80020D90.
# src/game/image.c: g_Textures is D:80049300.
# tools/data_compress.sh: c_data_array starts at ROM 0x21990.
US_CDATA_RZ_OFFSET = 0x21990
US_CSEGMENT_VADDR = 0x80020D90
US_G_TEXTURES_VADDR = 0x80049300
US_G_TEXTURES_STRUCT_OFFSET = US_G_TEXTURES_VADDR - US_CSEGMENT_VADDR
US_G_TEXTURES_DATA_POS_HINT = US_G_TEXTURES_STRUCT_OFFSET + 1

# Search only a few bytes around the source-derived field position to tolerate
# compiler bitfield placement differences while staying deterministic.
TABLE_POS_RADIUS = 8


@dataclass(frozen=True)
class TextureTable:
    rz_offset: int
    data_pos: int
    byteorder: str
    blob_size: int
    sizes: tuple[int, ...]
    equal_count: int

    @property
    def sentinel_pos(self) -> int:
        return self.data_pos + len(self.sizes) * 8


def parse_images_def(root: Path) -> tuple[list[str], list[int]]:
    text = (root / "assets" / "images.def").read_text(encoding="utf-8")
    names: list[str] = []
    sizes: list[int] = []
    rx = re.compile(
        r"^\s*IMAGE\(\s*([^,]+)\s*,\s*(0x[0-9A-Fa-f]+|[0-9]+)\s*,",
        re.M,
    )
    for m in rx.finditer(text):
        names.append(m.group(1).strip())
        sizes.append(int(m.group(2), 0))
    if len(names) < 100 or len(names) != len(sizes):
        raise RuntimeError("assets/images.def nao parece valido")
    return names, sizes


def parse_imagelist(root: Path, expected_sizes: list[int]) -> tuple[int, int]:
    rows: list[tuple[int, int]] = []
    with (root / "imagelist.u.csv").open("r", encoding="utf-8", newline="") as f:
        for row in csv.reader(f):
            if len(row) < 2:
                continue
            try:
                rows.append((int(row[0]), int(row[1])))
            except ValueError:
                continue

    if len(rows) != len(expected_sizes):
        raise RuntimeError(
            f"imagelist.u.csv tem {len(rows)} imagens; esperado {len(expected_sizes)}"
        )

    for i, ((off, size), expected) in enumerate(zip(rows, expected_sizes)):
        if size != expected:
            raise RuntimeError(
                f"imagelist.u.csv diverge de images.def no indice {i}: "
                f"{size:#x} != {expected:#x}"
            )
        if i and off != rows[i - 1][0] + rows[i - 1][1]:
            raise RuntimeError(
                f"imagelist.u.csv deixou de ser continuo no indice {i}"
            )

    start = rows[0][0]
    end = rows[-1][0] + rows[-1][1]
    if end <= start:
        raise RuntimeError("segmento de imagens invalido")
    return start, end


def image_segment_bounds_from_symbols(root: Path) -> tuple[int, int]:
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
        raise RuntimeError("segmento de imagens invalido em romassets_u.s")
    return start, end


def inflate_rz(rom: bytes, offset: int) -> bytes:
    if rom[offset : offset + 2] != b"\x11\x72":
        raise RuntimeError(
            f"csegment RZ nao comeca com 0x1172 em 0x{offset:08X}"
        )
    try:
        d = zlib.decompressobj(-15)
        out = d.decompress(rom[offset + 2 :], MAX_RZ_DECOMPRESSED + 1)
        if len(out) > MAX_RZ_DECOMPRESSED or not d.eof:
            raise RuntimeError("csegment RZ truncado ou maior que o limite")
        return out
    except zlib.error as exc:
        raise RuntimeError(f"falha ao descompactar csegment RZ: {exc}") from exc


def read24(blob: bytes, pos: int, byteorder: str) -> int:
    return int.from_bytes(blob[pos : pos + 3], byteorder)


def read_size_table(
    blob: bytes,
    data_pos: int,
    byteorder: str,
    count: int,
) -> tuple[int, ...] | None:
    end = data_pos + count * 8 + 3
    if data_pos < 0 or end > len(blob):
        return None

    out: list[int] = []
    for i in range(count):
        value = read24(blob, data_pos + i * 8, byteorder)
        if not (0 < value <= MAX_TEXTURE_SIZE):
            return None
        out.append(value)
    return tuple(out)


def locate_original_table(blob: bytes, expected: list[int]) -> TextureTable:
    candidates: list[TextureTable] = []

    lo = max(0, US_G_TEXTURES_DATA_POS_HINT - TABLE_POS_RADIUS)
    hi = US_G_TEXTURES_DATA_POS_HINT + TABLE_POS_RADIUS

    for data_pos in range(lo, hi + 1):
        for byteorder in ("big", "little"):
            sizes = read_size_table(blob, data_pos, byteorder, len(expected))
            if sizes is None:
                continue
            equal = sum(a == b for a, b in zip(sizes, expected))
            sentinel = read24(
                blob, data_pos + len(expected) * 8, byteorder
            )
            if equal == len(expected) and sentinel == 0xFFFF:
                candidates.append(
                    TextureTable(
                        rz_offset=US_CDATA_RZ_OFFSET,
                        data_pos=data_pos,
                        byteorder=byteorder,
                        blob_size=len(blob),
                        sizes=sizes,
                        equal_count=equal,
                    )
                )

    if not candidates:
        # Diagnostic fallback: search the decompressed csegment for the first
        # size and only accept a complete 2698-entry + sentinel match.
        for byteorder in ("big", "little"):
            needle = expected[0].to_bytes(3, byteorder)
            pos = 0
            while True:
                pos = blob.find(needle, pos)
                if pos < 0:
                    break
                sizes = read_size_table(blob, pos, byteorder, len(expected))
                if sizes is not None and sizes == tuple(expected):
                    sentinel = read24(
                        blob, pos + len(expected) * 8, byteorder
                    )
                    if sentinel == 0xFFFF:
                        candidates.append(
                            TextureTable(
                                rz_offset=US_CDATA_RZ_OFFSET,
                                data_pos=pos,
                                byteorder=byteorder,
                                blob_size=len(blob),
                                sizes=sizes,
                                equal_count=len(expected),
                            )
                        )
                pos += 1

    # Deduplicate by the bytes that actually hold the 24-bit field. The old
    # importer treated equivalent bitfield interpretations as different table
    # starts and falsely reported "ambiguous".
    unique: dict[tuple[int, str], TextureTable] = {}
    for item in candidates:
        unique[(item.data_pos, item.byteorder)] = item

    if not unique:
        raise RuntimeError(
            "g_Textures original nao passou na validacao exata de 2698 entradas"
        )

    ranked = sorted(
        unique.values(),
        key=lambda t: (
            abs(t.data_pos - US_G_TEXTURES_DATA_POS_HINT),
            t.byteorder != "big",
        ),
    )
    best = ranked[0]

    # The verified source-derived location wins deterministically. If discovery
    # also found duplicate copies elsewhere, they are irrelevant: the csegment
    # runtime table is the one nearest the known g_Textures VADDR.
    if abs(best.data_pos - US_G_TEXTURES_DATA_POS_HINT) > TABLE_POS_RADIUS:
        raise RuntimeError(
            "g_Textures foi encontrado fora da janela esperada do csegment"
        )
    return best


def locate_patch_table(
    blob: bytes,
    expected: list[int],
    original: TextureTable,
) -> TextureTable:
    # A translation patch changes values in g_Textures, not the executable data
    # layout. Read the same field position first; this is the primary path.
    positions = [original.data_pos]
    positions.extend(
        p
        for p in range(
            max(0, original.data_pos - TABLE_POS_RADIUS),
            original.data_pos + TABLE_POS_RADIUS + 1,
        )
        if p != original.data_pos
    )

    candidates: list[TextureTable] = []
    for data_pos in positions:
        sizes = read_size_table(
            blob, data_pos, original.byteorder, len(expected)
        )
        if sizes is None:
            continue
        sentinel = read24(
            blob, data_pos + len(expected) * 8, original.byteorder
        )
        if sentinel != 0xFFFF:
            continue
        equal = sum(a == b for a, b in zip(sizes, expected))
        candidates.append(
            TextureTable(
                rz_offset=US_CDATA_RZ_OFFSET,
                data_pos=data_pos,
                byteorder=original.byteorder,
                blob_size=len(blob),
                sizes=sizes,
                equal_count=equal,
            )
        )

    if not candidates:
        raise RuntimeError(
            "g_Textures PT-BR nao foi encontrado na posicao validada do csegment"
        )

    candidates.sort(
        key=lambda t: (
            t.equal_count,
            -abs(t.data_pos - original.data_pos),
        ),
        reverse=True,
    )
    best = candidates[0]

    # Graphics patches normally touch only a small subset of 2698 images. This
    # gate rejects unrelated/corrupt tables without caring how many text banks
    # were changed elsewhere in the ROM.
    minimum = int(len(expected) * 0.80)
    if best.equal_count < minimum:
        raise RuntimeError(
            "g_Textures PT-BR teve pouca concordancia estrutural "
            f"({best.equal_count}/{len(expected)})"
        )
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

    if orig_total != segment_len:
        raise RuntimeError(
            "manifesto de imagens nao ocupa exatamente o segmento original "
            f"({orig_total} != {segment_len})"
        )
    if patch_total <= 0 or patch_total > len(patched):
        raise RuntimeError("tamanho total do segmento PT-BR e invalido")

    candidates: set[int] = {
        orig_start,
        len(patched) - patch_total,
        orig_end - patch_total,
    }
    votes: collections.Counter[int] = collections.Counter()

    # Use many unchanged textures as independent anchors. The correct translated
    # segment start should receive a large cluster of identical votes.
    step = max(1, len(orig_sizes) // 320)
    search_lo = max(0, orig_start - 0x300000)
    search_hi = min(len(patched), orig_end + 0x300000)

    for i in range(0, len(orig_sizes), step):
        if orig_sizes[i] != patch_sizes[i] or orig_sizes[i] < 64:
            continue

        needle = base[
            orig_start + ocum[i] :
            orig_start + ocum[i] + orig_sizes[i]
        ]
        first = patched.find(needle, search_lo, search_hi)
        if first < 0:
            continue
        second = patched.find(needle, first + 1, search_hi)
        if second >= 0:
            continue
        votes[first - pcum[i]] += 1

    for start, _ in votes.most_common(32):
        candidates.add(start)

    def score(start: int) -> tuple[int, int]:
        if start < 0 or start + patch_total > len(patched):
            return (-1, -1)
        exact = 0
        comparable = 0
        for i, osize in enumerate(orig_sizes):
            psize = patch_sizes[i]
            if osize != psize or osize < 16:
                continue
            comparable += 1
            a = base[
                orig_start + ocum[i] :
                orig_start + ocum[i] + osize
            ]
            b = patched[
                start + pcum[i] :
                start + pcum[i] + psize
            ]
            if a == b:
                exact += 1
        return exact, comparable

    ranked = sorted(
        ((score(s), votes[s], s) for s in candidates),
        key=lambda item: (item[0][0], item[1], -abs(item[2] - orig_start)),
        reverse=True,
    )
    if not ranked or ranked[0][0][0] < 20:
        raise RuntimeError(
            "nao houve ancoras suficientes para localizar o segmento de imagens PT-BR"
        )

    (exact, comparable), vote_count, start = ranked[0]
    ratio = exact / comparable if comparable else 0.0
    if comparable < 50 or ratio < 0.35:
        raise RuntimeError(
            "segmento PT-BR nao passou na validacao de identidade "
            f"({exact}/{comparable} ancoras)"
        )

    # Do not reject a numeric tie blindly. Prefer the candidate with direct
    # anchor votes, then the one closest to the known original segment. Only a
    # true tie after both deterministic rules is unsafe.
    if len(ranked) > 1:
        a = ranked[0]
        b = ranked[1]
        if (
            a[0] == b[0]
            and a[1] == b[1]
            and abs(a[2] - orig_start) == abs(b[2] - orig_start)
            and a[2] != b[2]
        ):
            raise RuntimeError(
                "segmento de imagens PT-BR continuou realmente ambiguo"
            )

    return start, exact, vote_count


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--strict",
        action="store_true",
        help="falha se algum grafico alterado nao couber no slot original",
    )
    args = ap.parse_args()

    root = Path(__file__).resolve().parents[1]

    try:
        base_path = find_rom(
            root,
            (
                "data/ge007.ntsc-final.original.z64",
                "data/ge007.ntsc-final.z64",
                "baserom.u.z64",
            ),
            BASE_CRC32,
        )
        patch_path = find_rom(
            root,
            (
                "data/ge007.ntsc-final.ptbr-test.z64",
                "data/ge007.ntsc-final.community-ptbr.z64",
            ),
        )
        names, orig_sizes = parse_images_def(root)
        list_start, list_end = parse_imagelist(root, orig_sizes)
        sym_start, sym_end = image_segment_bounds_from_symbols(root)
        if (list_start, list_end) != (sym_start, sym_end):
            raise RuntimeError(
                "imagelist.u.csv e romassets_u.s discordam sobre o segmento de imagens"
            )
        orig_start, orig_end = list_start, list_end
    except (FileNotFoundError, RuntimeError) as exc:
        print(f"ERRO: {exc}")
        return 2

    base = base_path.read_bytes()
    patched = patch_path.read_bytes()

    if crc32(base) != BASE_CRC32:
        print("ERRO: ROM original nao e a USA verificada B6330846")
        return 2
    if len(patched) != len(base):
        print(
            "ERRO: ROM PT-BR tem tamanho diferente da ROM original; "
            "nenhum sidecar foi substituido."
        )
        return 2
    if orig_end > len(base):
        print("ERRO: segmento de imagens sai da ROM original")
        return 2

    print(
        f"ROM original: {base_path.relative_to(root)} "
        f"CRC32={crc32(base):08X}"
    )
    print(
        f"ROM do patch: {patch_path.relative_to(root)} "
        f"CRC32={crc32(patched):08X}"
    )
    print(f"Texturas conhecidas: {len(names)}")
    print(
        "Validando g_Textures no csegment conhecido "
        f"(RZ@0x{US_CDATA_RZ_OFFSET:08X})..."
    )

    try:
        base_cseg = inflate_rz(base, US_CDATA_RZ_OFFSET)
        patch_cseg = inflate_rz(patched, US_CDATA_RZ_OFFSET)
        original_table = locate_original_table(base_cseg, orig_sizes)
        patch_table = locate_patch_table(
            patch_cseg, orig_sizes, original_table
        )
        patch_start, exact_anchors, votes = candidate_patch_start(
            base,
            patched,
            orig_start,
            orig_end,
            orig_sizes,
            patch_table.sizes,
        )
    except RuntimeError as exc:
        print(f"ERRO: {exc}")
        print("Nenhum sidecar grafico foi substituido.")
        return 3

    print(
        "g_Textures original: "
        f"data+0x{original_table.data_pos:05X} "
        f"{original_table.byteorder} "
        f"({original_table.equal_count}/{len(orig_sizes)})"
    )
    print(
        "g_Textures PT-BR:   "
        f"data+0x{patch_table.data_pos:05X} "
        f"iguais={patch_table.equal_count}/{len(orig_sizes)}"
    )
    print(
        f"Images original: 0x{orig_start:08X}..0x{orig_end:08X}"
    )
    print(
        f"Images PT-BR:   0x{patch_start:08X} "
        f"(ancoras exatas={exact_anchors}, votos={votes})"
    )

    ocum = cumulative(orig_sizes)
    pcum = cumulative(patch_table.sizes)
    shadow = bytearray(base[orig_start:orig_end])

    changed: list[str] = []
    imported: list[str] = []
    oversize: list[tuple[str, int, int]] = []

    for i, name in enumerate(names):
        osize = orig_sizes[i]
        psize = patch_table.sizes[i]
        ostart = orig_start + ocum[i]
        pstart = patch_start + pcum[i]

        if pstart < 0 or pstart + psize > len(patched):
            print(f"ERRO: textura PT-BR {name} aponta para fora da ROM")
            print("O sidecar anterior, se existir, foi preservado.")
            return 3

        oblock = base[ostart : ostart + osize]
        pblock = patched[pstart : pstart + psize]

        if osize == psize and oblock == pblock:
            continue

        changed.append(name)

        if psize > osize:
            oversize.append((name, osize, psize))
            continue

        rel = ocum[i]
        shadow[rel : rel + psize] = pblock
        imported.append(name)

    report_lines = [
        "Ascension PT-BR community graphics import",
        f"base={base_path.name} crc32={crc32(base):08X}",
        f"patched={patch_path.name} crc32={crc32(patched):08X}",
        f"cdata_rz=0x{US_CDATA_RZ_OFFSET:08X}",
        (
            f"texture_table_data_pos=0x{original_table.data_pos:X} "
            f"byteorder={original_table.byteorder}"
        ),
        (
            f"patch_table_equal="
            f"{patch_table.equal_count}/{len(orig_sizes)}"
        ),
        f"original_segment=0x{orig_start:08X}-0x{orig_end:08X}",
        f"patched_segment=0x{patch_start:08X}",
        (
            f"known={len(names)} changed={len(changed)} "
            f"imported={len(imported)} oversize={len(oversize)}"
        ),
        "",
        "IMPORTED:",
        *imported,
        "",
        "OVERSIZE (not imported):",
        *[
            f"{name}: original={old} patch={new}"
            for name, old, new in oversize
        ],
        "",
    ]

    report = root / "data" / "ascension_ptbr_graphics_report.txt"
    report.write_text("\n".join(report_lines), encoding="utf-8")

    print(f"Graficos alterados pelo patch: {len(changed)}")
    print(f"Graficos importados com seguranca: {len(imported)}")
    print(f"Graficos maiores que o slot original: {len(oversize)}")

    if not imported:
        print(
            "ERRO: nenhum grafico alterado pode ser importado com seguranca."
        )
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
        print(
            "AVISO: existem graficos maiores que o slot original; "
            "eles continuam usando o grafico original por seguranca."
        )
    else:
        print(
            "OK: todos os graficos alterados detectados couberam "
            "no layout original."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
