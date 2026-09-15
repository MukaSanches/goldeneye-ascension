#!/usr/bin/env python3
"""Static/regression contracts for Ascension UI Overhaul v1.

These tests target the failure modes that matter before gameplay testing:
menu pointer accidentally gated, click mapping lost, F10 mouse/drag lost,
category hitboxes disappearing, and UI code touching save/gameplay sources.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
INPUT = (ROOT / "port/src/input.c").read_text(encoding="utf-8")
OV = (ROOT / "port/src/optionsoverlay.c").read_text(encoding="utf-8")

def need(ok, msg):
    if not ok:
        print("FAIL:", msg)
        raise SystemExit(1)
    print("PASS:", msg)

need("if (mouseEnabled && !(menuMode && ascensionControlsIsModern()))" not in INPUT,
     "Modern menu pointer is not globally gated")
need("cursor_h_pos = (float)(loH + fx * (hiH - loH));" in INPUT,
     "absolute mouse X reaches native GoldenEye menu cursor")
need("cursor_v_pos = (float)(loV + fy * (hiV - loV));" in INPUT,
     "absolute mouse Y reaches native GoldenEye menu cursor")
need("SDL_BUTTON(SDL_BUTTON_LEFT))  button |= GE_CONT_A" in INPUT,
     "left click maps to native menu Select/A")
need("SDL_BUTTON(SDL_BUTTON_RIGHT)) button |= GE_CONT_B" in INPUT,
     "right click maps to native menu Back/B")
need("ascensionControlsQueueDirectLook(edx, dyLook, aimHeld)" in INPUT,
     "V3 direct look remains installed")
need("Ascension V3 menu guard: clear gameplay look residue only" in INPUT,
     "menu transition clears gameplay look residue without consuming pointer")

need("MI6 / Q BRANCH SYSTEMS" in OV, "F10 uses Q Branch art direction")
need("MI6 / CLASSIFIED ARCHIVES" in OV, "file select uses MI6 archive framing")
need("SDL_GetMouseState(&mx, &my)" in OV, "F10 reads absolute mouse")
need("sliderSetFromX" in OV and "dragRow" in OV, "F10 sliders support mouse drag")
need("Q Branch section tabs are real mouse targets" in OV, "F10 category tabs are clickable")
need("SDL_SCANCODE_W" in OV and "SDL_SCANCODE_S" in OV and "SDL_SCANCODE_A" in OV and "SDL_SCANCODE_D" in OV,
     "F10 retains WASD navigation fallback")
need("GE_MENU_FILE_SELECT" in OV, "archive chrome is scoped to file select")

# Scope contract: overhaul is a presentation/input patch only.
patcher = (ROOT / "tools_pc/apply_ui_overhaul_v1.py").read_text(encoding="utf-8")
need('port/src/optionsoverlay.c' in patcher, "overhaul patcher targets port-owned overlay")
for forbidden in ["src/game/front.c", "src/game/bondview2.c", "savefile", "mission state"]:
    need(forbidden not in patcher, f"overhaul patcher does not mutate {forbidden}")

print("\nAscension UI Overhaul v1 contracts: ALL PASS")
