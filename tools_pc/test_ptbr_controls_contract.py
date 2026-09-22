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
    "mouse turn speed": '{ "Mouse turn speed", "Velocidade ao virar" }',
    "mouse turn speed description": '{ "Turn sensitivity. Range 1-100.", "Sensibilidade ao virar. Faixa 1-100." }',
    "mouse invert Y": '{ "Mouse invert Y", "Inverter Y do mouse" }',
    "mouse invert Y description": '{ "Reverse vertical mouse look.", "Inverte o eixo vertical do mouse." }',
    "mouse capture": '{ "Mouse capture", "Captura do mouse" }',
    "mouse capture description": '{ "Choose how mouse lock activates.", "Escolhe como o mouse fica preso ao jogo." }',
    "mouse input": '{ "Mouse input", "Entrada do mouse" }',
    "mouse input description": '{ "Enable or disable mouse input without changing keyboard/gamepad.", "Ativa ou desativa o mouse sem alterar teclado ou controle." }',
    "raw mouse input": '{ "Raw mouse input", "Entrada bruta do mouse" }',
    "raw mouse input description": '{ "Bypass OS pointer acceleration for aiming.", "Ignora a aceleracao do ponteiro do sistema ao mirar." }',
    "mouse smoothing": '{ "Mouse smoothing %", "Suavizacao do mouse %" }',
    "mouse smoothing description": '{ "Low-pass mouse smoothing. 0 keeps raw motion.", "Suavizacao do movimento do mouse. 0 mantem movimento bruto." }',
    "mouse Y scale": '{ "Mouse Y scale %", "Escala Y do mouse %" }',
    "mouse Y scale description": '{ "Vertical mouse sensitivity relative to horizontal.", "Sensibilidade vertical do mouse em relacao a horizontal." }',
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
