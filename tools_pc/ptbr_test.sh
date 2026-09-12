#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

clean=0
if [[ "${1:-}" == "--clean" ]]; then
    clean=1
    shift
fi

echo "[1/6] Restaurando a ROM original verificada para o PC port..."
cp -f data/ge007.ntsc-final.original.z64 data/ge007.ntsc-final.z64

echo "[2/6] Importando todos os bancos de texto da traducao comunitaria..."
python tools_pc/import_ptbr_patch.py

echo "[3/6] Auditando cobertura estrutural dos textos..."
python tools_pc/ptbr_audit.py --strict

echo "[4/6] Importando graficos traduzidos com manifesto/padding validados..."
python tools_pc/import_ptbr_graphics_safe.py

echo "[5/6] Compilando Ascension..."
if [[ $clean -eq 1 ]]; then
    rm -rf build-pc
fi
./build-pc.sh ntsc-final

echo "[6/6] Iniciando GoldenEye 007 Ascension..."
echo "      F10 -> JOGO -> IDIOMA -> PORTUGUES (BRASIL)"
exec ./build-pc/ge007.x86_64.exe "$@"
