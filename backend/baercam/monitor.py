"""Live-Auslastung (CPU, RAM, GPU) und Ruckel-Erkennung mit Profil-Vorschlag."""

from __future__ import annotations

import asyncio
from collections import deque
from collections.abc import Awaitable, Callable

import psutil

try:  # NVIDIA-Auslastung, falls Treiber vorhanden
    import pynvml

    pynvml.nvmlInit()
    _NV = pynvml.nvmlDeviceGetHandleByIndex(0)
except Exception:  # noqa: BLE001 – keine NVIDIA-GPU oder kein Treiber
    _NV = None


def gpu_stats() -> dict | None:
    if _NV is None:
        return None
    try:
        util = pynvml.nvmlDeviceGetUtilizationRates(_NV)
        mem = pynvml.nvmlDeviceGetMemoryInfo(_NV)
        return {"util": util.gpu, "vramUsedGb": round(mem.used / 1024**3, 2), "vramTotalGb": round(mem.total / 1024**3, 1)}
    except Exception:  # noqa: BLE001
        return None


class Monitor:
    """Misst jede Sekunde. Liegt die Last 10 s am Anschlag, wird ein niedrigeres Profil vorgeschlagen."""

    def __init__(self, emit: Callable[[str, dict], Awaitable[None]]) -> None:
        self.emit = emit
        self.history: deque[dict] = deque(maxlen=60)
        self.fps_source: Callable[[], dict] | None = None
        self._task: asyncio.Task | None = None
        self._suggested = False
        psutil.cpu_percent(None)

    def sample(self) -> dict:
        vm = psutil.virtual_memory()
        s = {"cpu": psutil.cpu_percent(None), "ram": vm.percent, "ramFreeGb": round(vm.available / 1024**3, 1), "gpu": gpu_stats()}
        if self.fps_source:
            s["fps"] = self.fps_source()
        return s

    def overloaded(self) -> bool:
        recent = list(self.history)[-10:]
        if len(recent) < 10:
            return False
        hot = [r for r in recent if r["cpu"] > 92 or r["ram"] > 93 or (r.get("gpu") or {}).get("util", 0) > 97]
        return len(hot) >= 9

    async def run(self) -> None:
        while True:
            s = self.sample()
            self.history.append(s)
            await self.emit("perf.sample", s)
            if self.overloaded() and not self._suggested:
                self._suggested = True
                await self.emit("perf.suggestLower", {"reason": "Dein PC ist seit 10 Sekunden voll ausgelastet."})
            elif not self.overloaded():
                self._suggested = False
            await asyncio.sleep(1.0)

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.get_running_loop().create_task(self.run())
