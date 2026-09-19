#!/usr/bin/env python3
"""ROM-free regression contract for Ascension's PT-BR control UI."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCALE = ROOT / "port" / "src" / "ascension_locale.c"

source = LOCALE.read_text(encoding="utf-8")

required = {
    "control preset": '{ "Control preset", "Preset de controles" }',
    "dedicated crouch": '{ "Dedicated crouch", "Agachar dedicado" }',
    "mouse aim speed": '{ "Mouse aim speed", "Velocidade ao mirar" }',
    "Classic value": '{ "CLASSIC", "CLASSICO" }',
    "Hybrid value": '{ "HYBRID", "HIBRIDO" }',
    "Modern value": '{ "MODERN", "MODERNO" }',
    "PT-BR selector": '{ "PORTUGUESE (BRAZIL)", "PORTUGUES (BRASIL)" }',
}

for label, needle in required.items():
    if needle not in source:
        raise SystemExit(f"FAIL: missing PT-BR control contract: {label}")

if 'configRegisterInt("Ascension.Language", &s_language, 0, 1);' not in source:
    raise SystemExit("FAIL: Ascension.Language registration changed")

print("PASS: PT-BR control UI contract is preserved")
