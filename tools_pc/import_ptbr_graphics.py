#!/usr/bin/env python3
"""Import graphics from the user's community-patched GoldenEye ROM safely.

The PC port cannot execute the patched ROM because the port's absolute ROM
symbols are tied to the verified US layout. This tool instead reconstructs an
image-segment shadow that has *the original slot layout*. A translated texture
is transplanted only when its patched compressed payload fits inside the
original slot. Oversize/ambiguous entries are never written over neighbouring
assets and are reported for the next engineering pass.

Output is local-only (data/ is gitignored):
  data/ascension_ptbr_images.bin
  data/ascension_ptbr_graphics_report.txt
"""

from __future__ import annotations

import argparse
import collections
import re
import sys
from pathlib import Path

from import_ptbr_patch import BASE_CRC32, crc32, find_rom

CART_BASE = 0x10000000
MAX_TEXTURE_SIZE = 0x100000


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


def locate_size_table(rom: bytes, expected: list[int]) -> tuple[int, int]:
    """Find g_Textures and the byte position of its 24-bit size field.

    The N64 table has 8-byte entries. We deliberately discover the bitfield
    byte position from the verified ROM rather than hardcoding compiler layout.
    """
    probe_count = min(96, len(expected))
    first = expected[0].to_bytes(3, "big")
    candidates: list[tuple[int, int, int]] = []
    pos = rom.find(first)
    while pos >= 0:
        for field in range(6):
            start = pos - field
            if start < 0 or start + probe_count * 8 > len(rom):
                continue
            score = 0
            for i in range(probe_count):
                p = start + i * 8 + field
                if rom[p : p + 3] == expected[i].to_bytes(3, "big"):
                    score += 1
            if score >= probe_count - 1:
                candidates.append((score, start, field))
        pos = rom.find(first, pos + 1)

    if not candidates:
        raise RuntimeError("nao foi possivel localizar g_Textures na ROM original")
    candidates.sort(reverse=True)
    best = candidates[0]
    tied = [x for x in candidates if x[0] == best[0] and (x[1], x[2]) != (best[1], best[2])]
    if tied:
        raise RuntimeError("g_Textures ficou ambiguo; importacao abortada por seguranca")

    _, start, field = best
    # Full-table verification against the source is our primary safety gate.
    for i, size in enumerate(expected):
        p = start + i * 8 + field
        got = int.from_bytes(rom[p : p + 3], "big")
        if got != size:
            raise RuntimeError(
                f"g_Textures diverge de assets/images.def no indice {i}: {got:#x} != {size:#x}"
            )
    return start, field


def read_patch_sizes(rom: bytes, table: int, field: int, count: int) -> list[int]:
    out: list[int] = []
    for i in range(count):
        p = table + i * 8 + field
        if p + 3 > len(rom):
            raise RuntimeError("tabela de imagens PT-BR truncada")
        size = int.from_bytes(rom[p : p + 3], "big")
        if not (0 < size <= MAX_TEXTURE_SIZE):
            raise RuntimeError(f"tamanho PT-BR impossivel no indice {i}: {size:#x}")
        out.append(size)
    return out


def cumulative(sizes: list[int]) -> list[int]:
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
    patch_sizes: list[int],
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
    # segment start from many independent anchors and let them vote.
    step = max(1, len(orig_sizes) // 180)
    search_lo = max(0, orig_start - 0x100000)
    search_hi = min(len(patched), orig_end + 0x100000)
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

    for start, _ in votes.most_common(12):
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

    try:
        table, field = locate_size_table(base, orig_sizes)
        patch_sizes = read_patch_sizes(patched, table, field, len(names))
        patch_start, exact_anchors, votes = candidate_patch_start(
            base, patched, orig_start, orig_end, orig_sizes, patch_sizes
        )
    except RuntimeError as exc:
        print(f"ERRO: {exc}")
        print("Nenhum sidecar grafico foi substituido.")
        return 3

    print(f"g_Textures: 0x{table:08X} campo24=+{field}")
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

        # Keep original tail bytes untouched. texLoad consumes the translated
        # self-contained stream and stops at its own end marker/header data.
        rel = ocum[i]
        shadow[rel : rel + psize] = pblock
        imported.append(name)

    report_lines = [
        "Ascension PT-BR community graphics import",
        f"base={base_path.name} crc32={crc32(base):08X}",
        f"patched={patch_path.name} crc32={crc32(patched):08X}",
        f"texture_table=0x{table:08X} field={field}",
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
