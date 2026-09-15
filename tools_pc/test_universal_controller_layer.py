#!/usr/bin/env python3
"""Regression contract for Ascension 0.0.4 Universal Controller Layer."""
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "port/src/input.c"
VIDEO = ROOT / "port/src/video.c"
PATCHER = ROOT / "tools_pc/apply_universal_controller_layer.py"


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"FAIL: {label}: missing {needle!r}")


def forbid(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"FAIL: {label}: forbidden legacy pattern {needle!r}")


def main() -> int:
    input_text = INPUT.read_text(encoding="utf-8")
    video_text = VIDEO.read_text(encoding="utf-8")

    # Layering: standard SDL first, then DB/custom/fallback, without bypassing V4.
    for needle in (
        "ASCENSION UNIVERSAL CONTROLLER LAYER",
        "SDL_GameControllerAddMappingsFromFile",
        '"gamecontrollerdb.txt"',
        '"data/gamecontrollerdb.txt"',
        '"data/ascension-controller-mappings.txt"',
        '"data/ascension-auto-mappings.txt"',
        "SDL_GameControllerAddMapping(map)",
        "SDL_IsGameController(deviceIndex)",
        "SDL_JoystickGetGUIDString",
        "Input.ControllerDbEnabled",
        "Input.AutoMapUnknownGamepads",
    ):
        require(input_text, needle, "universal mapping stack")

    # Physical device indices must be normalized into contiguous GE pad slots.
    require(input_text, "int logical = 0;", "logical slot packing")
    require(input_text, "pads[logical] = pad;", "logical slot packing")
    require(input_text, "controller %d <- SDL device %d", "diagnostic identity")
    forbid(input_text, "pads[i] = SDL_GameControllerOpen(i);", "old sparse pad indexing")

    # Hot-plug must also see devices which are not controllers until fallback mapping.
    for needle in (
        "SDL_CONTROLLERDEVICEADDED",
        "SDL_CONTROLLERDEVICEREMOVED",
        "SDL_CONTROLLERDEVICEREMAPPED",
        "SDL_JOYDEVICEADDED",
        "SDL_JOYDEVICEREMOVED",
    ):
        require(video_text, needle, "hotplug/remap event coverage")

    # Existing accepted input owners remain present; universal mapping is only upstream.
    for needle in (
        "ascensionControlsQueueGamepadAxes",
        "ascensionControlsModernGamepadEnabled",
        "inputPadBindingCapturePressed",
        "inputBindingSetScancode",
        "SDL_GetRelativeMouseState",
        "optionsOverlayIsOpen",
    ):
        require(input_text, needle, "accepted V4/mouse/F10 path preservation")

    # Heuristic mapping must reject clearly non-gamepad devices rather than hijack wheels/HOTAS.
    require(input_text, "axes < 2 || buttons < 4", "safe generic-pad gate")
    require(input_text, "left raw (axes=%d buttons=%d hats=%d)", "safe generic-pad diagnostics")

    # User mappings must load after auto/community mappings so explicit corrections win.
    auto = input_text.index('loadControllerMappingFile("data/ascension-auto-mappings.txt"')
    community = input_text.index('loadControllerMappingFile("data/gamecontrollerdb.txt"')
    user = input_text.index('loadControllerMappingFile("data/ascension-controller-mappings.txt"')
    if not (auto < community < user):
        raise SystemExit("FAIL: mapping priority must be auto < community < user")

    # Patcher itself must be idempotent on the fully installed tree.
    spec = importlib.util.spec_from_file_location("asc_ucl", PATCHER)
    if spec is None or spec.loader is None:
        raise SystemExit("FAIL: could not load universal controller patcher")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if mod.patch_input(input_text) != input_text:
        raise SystemExit("FAIL: input patch is not idempotent")
    if mod.patch_video(video_text) != video_text:
        raise SystemExit("FAIL: video patch is not idempotent")

    print("Universal Controller Layer regression contract: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
