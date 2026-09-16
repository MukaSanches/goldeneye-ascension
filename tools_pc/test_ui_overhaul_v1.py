#!/usr/bin/env python3
"""Static/regression contracts for Ascension UI Overhaul v1.

The V1 suite is also run after V2 in the release stack. It therefore validates
V1's durable interaction/scope guarantees while allowing the newer V2 visual
language to supersede V1 chrome. This prevents a stale aesthetic assertion from
blocking a deliberately evolved interface.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUT = (ROOT / "port/src/input.c").read_text(encoding="utf-8")
OV = (ROOT / "port/src/optionsoverlay.c").read_text(encoding="utf-8")
PATCHER = (ROOT / "tools_pc/apply_ui_overhaul_v1.py").read_text(encoding="utf-8")


def need(ok, msg):
    if not ok:
        print("FAIL:", msg)
        raise SystemExit(1)
    print("PASS:", msg)


# Menu/gameplay isolation.
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
     "menu transition clears gameplay-look residue without consuming pointer")

# Visual hierarchy. V2 intentionally replaces V1's dossier/sidebar chrome with
# a denser GoldenEye/Q-Watch configuration language. Accept whichever generation
# is actually installed, while requiring an authored (non-generic) identity.
v2 = "Ascension UI Overhaul V2 - Q Watch compact settings" in OV
if v2:
    need("Q WATCH / SYSTEM CONFIGURATION" in OV,
         "F10 uses the current Q Watch systems identity")
    need("MI6 CLASSIFIED ARCHIVES" not in OV,
         "superseded V1 archive chrome does not leak into V2")
    need("tabCategoryAt" in OV and "categoryBounds" in OV,
         "V2 category tabs keep page-scoped navigation")
    need("ptrFontZurichBold" in OV and "drawGothic" in OV,
         "V2 retains GoldenEye-native typography hierarchy")
else:
    need("Q BRANCH SYSTEMS" in OV, "F10 uses Q Branch systems identity")
    need("MI6 CLASSIFIED ARCHIVES" in OV, "file select uses classified-archive identity")
    need("ASC_UI_PAPER" in OV and "ASC_UI_INK" in OV and "ASC_UI_RED" in OV,
         "dossier palette contains paper, ink and classification red")
    need("categoryBounds" in OV and "rows[row].category == rows[s_sel].category" in OV,
         "scrolling and hit testing stay inside the active department")
    need("Active rows only" in OV, "renderer draws only the selected department rows")
    need("overlayHasInfoPanel" in OV and "FIELD NOTE" in OV,
         "wide layouts get the contextual intelligence-note panel")
    need("ACTIVE DOSSIER / FILE %02d" in OV and "selected_folder_num" in OV,
         "file-select archive header reflects the actual selected native save slot")

need("CAT_SYSTEM" in OV, "settings retain deliberate system categorization")

# Mouse/keyboard interaction survives both visual generations.
need("SDL_GetMouseState(&mx, &my)" in OV, "F10 reads absolute mouse")
need("sliderSetFromX" in OV and "dragRow" in OV, "F10 sliders support mouse drag")
if v2:
    need("tabCategoryAt" in OV, "Q Watch category rail has real mouse hit targets")
else:
    need("sidebarCategoryAt" in OV and "hoverCat" in OV,
         "Q Branch department rail has real mouse hit targets")
    need("Entire selector row is a target" in OV,
         "toggles/enums use generous professional click targets")
need("SDL_SCANCODE_W" in OV and "SDL_SCANCODE_S" in OV and
     "SDL_SCANCODE_A" in OV and "SDL_SCANCODE_D" in OV,
     "F10 retains WASD navigation fallback")
need(("LMB SELECT  |  RMB BACK" in OV) or ("LMB SELECT/DRAG   RMB BACK" in OV),
     "mouse affordances are visible in UI")

# Scope contract: V1 itself is presentation/input only; GoldenEye stays authoritative.
need('port/src/optionsoverlay.c' in PATCHER, "overhaul patcher targets port-owned overlay")
for forbidden in ["src/game/front.c", "src/game/bondview2.c", "savefile", "mission state"]:
    need(forbidden not in PATCHER, f"overhaul patcher does not mutate {forbidden}")

print("\nAscension UI Overhaul v1 durable contracts: ALL PASS")
