"""Findet heraus, ob Animaze installiert ist und läuft (nur Windows; sonst immer 'nicht vorhanden')."""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import psutil


def _steam_libraries() -> list[Path]:
    roots = [Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "Steam"]
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam") as key:
            roots.insert(0, Path(winreg.QueryValueEx(key, "SteamPath")[0]))
    except OSError:
        pass
    libs: list[Path] = []
    for root in roots:
        vdf = root / "steamapps" / "libraryfolders.vdf"
        libs.append(root)
        if vdf.exists():
            libs += [Path(p.replace("\\\\", "\\")) for p in re.findall(r'"path"\s+"([^"]+)"', vdf.read_text(errors="ignore"))]
    return list(dict.fromkeys(libs))


def install_dir() -> str | None:
    if sys.platform != "win32":
        return None
    for lib in _steam_libraries():
        candidate = lib / "steamapps" / "common" / "Animaze"
        if candidate.exists():
            return str(candidate)
    return None


def is_running() -> bool:
    for p in psutil.process_iter(["name"]):
        name = (p.info.get("name") or "").lower()
        if name.startswith("animaze"):
            return True
    return False


def info() -> dict:
    path = install_dir()
    return {"installed": path is not None, "path": path, "running": is_running(), "platformSupported": sys.platform == "win32"}
