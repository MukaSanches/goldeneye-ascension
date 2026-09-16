#!/usr/bin/env python3
"""Compatibility-safe PT-BR graphics importer launcher.

This module fixes two layout facts that the first importer treated too strictly:

* imagelist.u.csv contains 2698 real texture payload rows plus a trailing
  8-byte image2698 record which is not represented by g_Textures/images.def;
* the linker image segment extends to 0xC00000 and therefore includes padding
  after the real texture payloads.

The core importer is kept intact. We replace only the manifest/layout helpers
before calling its main(), so all existing CRC, csegment, table, anchor,
sidecar and fail-open validation remains active.
"""

from __future__ import annotations

import collections
import csv
import sys
from pathlib import Path

import import_ptbr_graphics as core


def parse_imagelist_safe(root: Path, expected_sizes: list[int]) -> tuple[int, int]:
    rows: list[tuple[int, int, str]] = []
    with (root / "imagelist.u.csv").open("r", encoding="utf-8", newline="") as f:
        for row in csv.reader(f):
            if len(row) < 2:
                continue
            try:
                off = int(row[0])
                size = int(row[1])
            except ValueError:
                continue
            path = row[2] if len(row) > 2 else ""
            rows.append((off, size, path))

    count = len(expected_sizes)
    if len(rows) < count:
        raise RuntimeError(
            f"imagelist.u.csv tem apenas {len(rows)} linhas; "
            f"g_Textures exige {count}"
        )

    real = rows[:count]
    for i, ((off, size, _path), expected) in enumerate(zip(real, expected_sizes)):
        if size != expected:
            raise RuntimeError(
                f"imagelist.u.csv diverge de images.def no indice {i}: "
                f"{size:#x} != {expected:#x}"
            )
        if i:
            prev_off, prev_size, _ = real[i - 1]
            if off != prev_off + prev_size:
                raise RuntimeError(
                    f"imagelist.u.csv deixou de ser continuo no indice {i}"
                )

    data_start = real[0][0]
    data_end = real[-1][0] + real[-1][1]
    sym_start, sym_end = core.image_segment_bounds_from_symbols(root)

    if data_start != sym_start:
        raise RuntimeError(
            "inicio das imagens no manifesto nao coincide com romassets_u.s "
            f"(0x{data_start:08X} != 0x{sym_start:08X})"
        )
    if data_end > sym_end:
        raise RuntimeError(
            "payloads de textura ultrapassam o segmento de imagens do linker"
        )

    # The historical extraction list may include records after g_Textures.
    # They are not texture slots and must not change the 2698-entry runtime
    # table. Validate that they are well formed and remain inside the linker
    # segment, then deliberately exclude them from texture indexing.
    trailing = rows[count:]
    cursor = data_end
    for off, size, path in trailing:
        if size < 0 or off != cursor:
            raise RuntimeError(
                "registro extra de imagelist.u.csv nao e um trailer continuo "
                f"({path or 'sem nome'})"
            )
        cursor = off + size
    if cursor > sym_end:
        raise RuntimeError("trailer de imagelist.u.csv ultrapassa o segmento de imagens")

    if trailing:
        print(
            f"INFO: {len(trailing)} registro(s) de trailer fora de g_Textures "
            f"ignorado(s) com seguranca; texturas reais={count}."
        )
    padding = sym_end - data_end
    print(
        f"INFO: segmento possui 0x{padding:X} bytes apos os {count} payloads; "
        "padding sera preservado da ROM original."
    )

    # core.main compares these values with the linker symbols and builds a
    # full-size sidecar. Returning linker bounds is therefore intentional.
    return sym_start, sym_end


def candidate_patch_start_safe(
    base: bytes,
    patched: bytes,
    orig_start: int,
    orig_end: int,
    orig_sizes: list[int],
    patch_sizes: list[int] | tuple[int, ...],
) -> tuple[int, int, int]:
    ocum = core.cumulative(orig_sizes)
    pcum = core.cumulative(patch_sizes)
    orig_total = sum(orig_sizes)
    patch_total = sum(patch_sizes)
    orig_data_end = orig_start + orig_total

    if orig_data_end > orig_end:
        raise RuntimeError(
            "payloads originais excedem o segmento reservado pelo linker"
        )
    if patch_total <= 0 or patch_total > len(patched):
        raise RuntimeError("tamanho total dos payloads PT-BR e invalido")

    # Setup Editor normally keeps the image segment base and repacks the
    # payloads from there. Keep that as the strongest deterministic candidate,
    # but independently derive candidates from unchanged textures as well.
    candidates: set[int] = {
        orig_start,
        orig_data_end - patch_total,
        orig_end - patch_total,
    }
    votes: collections.Counter[int] = collections.Counter()

    search_lo = max(0, orig_start - 0x400000)
    search_hi = min(len(patched), orig_end + 0x100000)
    step = max(1, len(orig_sizes) // 400)

    for i in range(0, len(orig_sizes), step):
        osize = orig_sizes[i]
        psize = patch_sizes[i]
        if osize != psize or osize < 64:
            continue

        needle = base[
            orig_start + ocum[i] : orig_start + ocum[i] + osize
        ]
        first = patched.find(needle, search_lo, search_hi)
        if first < 0:
            continue
        # Unique anchors only. Repeated tiny/common texture streams should not
        # vote on placement.
        if patched.find(needle, first + 1, search_hi) >= 0:
            continue
        votes[first - pcum[i]] += 1

    for start, _count in votes.most_common(48):
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
                orig_start + ocum[i] : orig_start + ocum[i] + osize
            ]
            b = patched[
                start + pcum[i] : start + pcum[i] + psize
            ]
            if a == b:
                exact += 1
        return exact, comparable

    ranked = sorted(
        ((score(s), votes[s], s) for s in candidates),
        key=lambda item: (
            item[0][0],
            item[1],
            item[2] == orig_start,
            -abs(item[2] - orig_start),
        ),
        reverse=True,
    )

    if not ranked:
        raise RuntimeError("nenhuma posicao candidata para as imagens PT-BR")

    (exact, comparable), vote_count, start = ranked[0]
    ratio = exact / comparable if comparable else 0.0

    # A valid translation changes only a subset of graphical assets. Requiring
    # many byte-identical payloads makes this placement check much stronger than
    # relying on ROM offsets alone while still allowing all text graphics to be
    # translated.
    if comparable < 100 or exact < 50 or ratio < 0.35:
        raise RuntimeError(
            "segmento PT-BR nao passou na verificacao cruzada de payloads "
            f"({exact}/{comparable}, {ratio:.1%})"
        )

    # A true tie is only unsafe if score, votes and distance are all identical.
    if len(ranked) > 1:
        second = ranked[1]
        if (
            second[0] == ranked[0][0]
            and second[1] == ranked[0][1]
            and abs(second[2] - orig_start) == abs(start - orig_start)
            and second[2] != start
        ):
            raise RuntimeError(
                "duas posicoes de imagens PT-BR passaram pelas mesmas validacoes"
            )

    return start, exact, vote_count


def main() -> int:
    core.parse_imagelist = parse_imagelist_safe
    core.candidate_patch_start = candidate_patch_start_safe
    return core.main()


if __name__ == "__main__":
    sys.exit(main())
