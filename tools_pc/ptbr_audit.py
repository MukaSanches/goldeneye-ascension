#!/usr/bin/env python3
"""Deterministic coverage audit for Ascension's community PT-BR catalog."""

from __future__ import annotations

import argparse
import csv
import struct
import sys
from pathlib import Path

from import_ptbr_patch import BASE_CRC32, BANK_IDS, REQUIRED, crc32, find_rom, original_banks

MAGIC = b"ASPTBR1\0"


def read_catalog(path: Path) -> dict[int, bytes]:
    data = path.read_bytes()
    if len(data) < 12 or data[:8] != MAGIC:
        raise RuntimeError("catalogo PT-BR invalido")
    count = struct.unpack_from("<I", data, 8)[0]
    if count == 0 or 12 + count * 8 > len(data):
        raise RuntimeError("indice do catalogo PT-BR invalido")
    result: dict[int, bytes] = {}
    previous = -1
    for i in range(count):
        slot_id, off = struct.unpack_from("<II", data, 12 + i * 8)
        if slot_id <= previous:
            raise RuntimeError("catalogo PT-BR nao esta ordenado/unico")
        previous = slot_id
        if off >= len(data):
            raise RuntimeError(f"offset invalido para slot 0x{slot_id:04X}")
        end = data.find(b"\0", off)
        if end < 0:
            raise RuntimeError(f"string sem terminador para slot 0x{slot_id:04X}")
        result[slot_id] = data[off:end]
    return result


def clean(value: bytes | None) -> str:
    if value is None:
        return ""
    return value.decode("latin-1", errors="replace").replace("\r", "\\r").replace("\n", "\\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--strict", action="store_true", help="retorna erro se algum slot usado nao estiver no catalogo")
    args = ap.parse_args()

    root = Path(__file__).resolve().parents[1]
    try:
        base_path = find_rom(
            root,
            ("data/ge007.ntsc-final.original.z64", "data/ge007.ntsc-final.z64", "baserom.u.z64"),
            BASE_CRC32,
        )
        catalog_path = root / "data" / "ascension_ptbr.bin"
        catalog = read_catalog(catalog_path)
    except (FileNotFoundError, RuntimeError) as exc:
        print(f"ERRO: {exc}")
        return 2

    base = base_path.read_bytes()
    if crc32(base) != BASE_CRC32:
        print("ERRO: ROM original nao e a USA verificada B6330846")
        return 2

    banks = original_banks(root, base)
    missing_banks = sorted(REQUIRED - banks.keys())
    if missing_banks:
        print("ERRO: bancos originais nao reconhecidos: " + ", ".join(missing_banks))
        return 3

    rows: list[tuple[str, int, int, str, str, str, str]] = []
    total = 0
    present = 0
    changed = 0
    same = 0
    missing = 0
    newline_mismatch = 0

    for name in sorted(REQUIRED, key=lambda n: BANK_IDS[n]):
        bank = banks[name]
        for slot, en in enumerate(bank.slots):
            if en is None:
                continue
            total += 1
            slot_id = (BANK_IDS[name] << 10) | slot
            pt = catalog.get(slot_id)
            if pt is None:
                status = "MISSING"
                note = "sem entrada no catalogo"
                missing += 1
            else:
                present += 1
                if pt == en:
                    status = "SAME"
                    note = "igual ao original; revisar se nome/acronimo ou texto nao traduzido"
                    same += 1
                else:
                    status = "TRANSLATED"
                    note = ""
                    changed += 1
                if en.count(b"\n") != pt.count(b"\n"):
                    newline_mismatch += 1
                    note = (note + "; " if note else "") + "quantidade de quebras de linha mudou"
            rows.append((name, slot, slot_id, status, clean(en), clean(pt), note))

    coverage = (present * 100.0 / total) if total else 0.0
    translated_ratio = (changed * 100.0 / total) if total else 0.0

    csv_path = root / "data" / "ascension_ptbr_audit.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["bank", "slot", "slot_id", "status", "english", "pt_br", "note"])
        w.writerows(rows)

    same_rows = [r for r in rows if r[3] == "SAME"]
    missing_rows = [r for r in rows if r[3] == "MISSING"]
    report = root / "data" / "ascension_ptbr_audit.txt"
    lines = [
        "Ascension PT-BR text coverage audit",
        f"base={base_path.name} crc32={crc32(base):08X}",
        f"catalog={catalog_path.name} entries={len(catalog)}",
        f"required_banks={len(REQUIRED)}",
        f"used_original_slots={total}",
        f"catalog_present={present}",
        f"translated_different={changed}",
        f"present_but_same={same}",
        f"missing={missing}",
        f"coverage={coverage:.2f}%",
        f"different_from_english={translated_ratio:.2f}%",
        f"newline_mismatch={newline_mismatch}",
        "",
        "MISSING:",
        *[f"{r[0]}[{r[1]}] 0x{r[2]:04X}: {r[4]}" for r in missing_rows],
        "",
        "PRESENT BUT IDENTICAL TO ENGLISH (editorial review; many are legitimate names/acronyms):",
        *[f"{r[0]}[{r[1]}] 0x{r[2]:04X}: {r[4]}" for r in same_rows],
        "",
    ]
    report.write_text("\n".join(lines), encoding="utf-8")

    print("========================================")
    print("AUDITORIA PT-BR")
    print("========================================")
    print(f"Bancos obrigatorios:       {len(REQUIRED)}")
    print(f"Slots usados no original:  {total}")
    print(f"Presentes no catalogo:     {present}")
    print(f"Traduzidos/diferentes:     {changed}")
    print(f"Iguais ao ingles:          {same}")
    print(f"Ausentes:                  {missing}")
    print(f"Cobertura estrutural:      {coverage:.2f}%")
    print(f"CSV: {csv_path.relative_to(root)}")
    print(f"Relatorio: {report.relative_to(root)}")

    if args.strict and missing:
        print("ERRO: cobertura estrutural incompleta; jogo nao sera iniciado pelo teste completo.")
        return 4

    if not missing:
        print("OK: nenhum slot de texto usado nos bancos obrigatorios ficou sem entrada PT-BR.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
