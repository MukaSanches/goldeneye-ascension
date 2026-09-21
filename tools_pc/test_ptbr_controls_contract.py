#!/usr/bin/env python3
"""ROM-free regression contract for Ascension's PT-BR control UI."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCALE = ROOT / "port" / "src" / "ascension_locale.c"

source = LOCALE.read_text(encoding="utf-8")

required = {
    "control preset": '{ "Control preset", "Preset de controles" }',
    "control preset description": '{ "Classic, Hybrid or Modern PC controls.", "Controles de PC Classico, Hibrido ou Moderno." }',
    "dedicated crouch": '{ "Dedicated crouch", "Agachar dedicado" }',
    "dedicated crouch description": '{ "Enable the Ascension crouch shortcut for Hybrid/Modern.", "Ativa o atalho de agachar do Ascension em Hibrido/Moderno." }',
    "mouse wheel weapons": '{ "Mouse wheel weapons", "Armas na roda do mouse" }',
    "mouse wheel weapons description": '{ "Use the mouse wheel to cycle weapons.", "Use a roda do mouse para alternar armas." }',
    "mouse aim speed": '{ "Mouse aim speed", "Velocidade ao mirar" }',
    "mouse aim speed description": '{ "Aim sensitivity. Range 1-100.", "Sensibilidade da mira. Faixa 1-100." }',
    "Classic value": '{ "CLASSIC", "CLASSICO" }',
    "Hybrid value": '{ "HYBRID", "HIBRIDO" }',
    "Modern value": '{ "MODERN", "MODERNO" }',
    "PT-BR selector": '{ "PORTUGUESE (BRAZIL)", "PORTUGUES (BRASIL)" }',
    "Ascension language scope": '{ "Ascension interface language.", "Idioma da interface do Ascension." }',
}

for label, needle in required.items():
    if needle not in source:
        raise SystemExit(f"FAIL: missing PT-BR control contract: {label}")

if 'configRegisterInt("Ascension.Language", &s_language, 0, 1);' not in source:
    raise SystemExit("FAIL: Ascension.Language registration changed")

print("PASS: PT-BR control UI contract is preserved")
