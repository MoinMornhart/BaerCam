"""Einstellungen als JSON im Benutzer-Datenordner (nie im Repo).

API-Keys gehören NICHT hierher, sondern in den System-Schlüsselbund (siehe Etappe 2).
"""

from __future__ import annotations

import json
import os
import threading
from copy import deepcopy
from pathlib import Path
from typing import Any

from platformdirs import user_data_dir

DEFAULTS: dict[str, Any] = {
    "animaze": {"host": "127.0.0.1", "apiPort": 9000, "vmcPort": 39539, "trackerPort": 0},
    "performance": {"profile": "auto"},
    "ui": {"reducedEffects": False},
    "updates": {"checkOnStart": True},
}


def data_dir() -> Path:
    override = os.environ.get("BAERCAM_DATA_DIR")
    path = Path(override) if override else Path(user_data_dir("BaerCam", appauthor=False))
    path.mkdir(parents=True, exist_ok=True)
    return path


def _merge(base: dict[str, Any], extra: dict[str, Any]) -> dict[str, Any]:
    out = deepcopy(base)
    for key, value in extra.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _merge(out[key], value)
        else:
            out[key] = value
    return out


class Settings:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or data_dir() / "settings.json"
        self._lock = threading.Lock()
        self._data = self._load()

    def _load(self) -> dict[str, Any]:
        try:
            stored = json.loads(self.path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            stored = {}
        return _merge(DEFAULTS, stored if isinstance(stored, dict) else {})

    def all(self) -> dict[str, Any]:
        with self._lock:
            return deepcopy(self._data)

    def update(self, patch: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            self._data = _merge(self._data, patch)
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self._data, indent=2, ensure_ascii=False), encoding="utf-8")
            tmp.replace(self.path)
            return deepcopy(self._data)
