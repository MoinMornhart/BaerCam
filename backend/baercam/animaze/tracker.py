"""Sender für den Animaze Programmable Tracker (UDP, 157 × float32).

Animaze nimmt die gesendeten Werte mit Vorrang vor der Webcam. Damit Live-Tracking und KI-Animation
sauber ineinander übergehen, hält der Sender pro Wert ein Gewicht (0 = neutral, 1 = KI-Wert) und
blendet weich. Ist nichts aktiv, wird nicht gesendet – dann gilt wieder Animazes eigenes Tracking.
"""

from __future__ import annotations

import asyncio
import socket
import struct
import time
from collections.abc import Mapping

from .units import COUNT, INDEX, NEUTRAL

_PACK = struct.Struct("<" + "f" * COUNT)


def encode(values: list[float]) -> bytes:
    if len(values) != COUNT:
        raise ValueError(f"Es werden genau {COUNT} Werte erwartet, nicht {len(values)}")
    return _PACK.pack(*values)


def resolve(frame: Mapping[str, float]) -> dict[int, float]:
    """Namen → Indizes. Unbekannte Namen werden ignoriert (nie ein Fehler)."""
    out: dict[int, float] = {}
    for name, value in frame.items():
        idx = INDEX.get(name)
        if idx is not None:
            out[idx] = min(1.0, max(0.0, float(value)))
    return out


class TrackerSender:
    def __init__(self, host: str = "127.0.0.1", port: int = 9003, rate_hz: float = 60.0) -> None:
        self.host = host
        self.port = port
        self.rate_hz = rate_hz
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.target: dict[int, float] = {}
        self.current = list(NEUTRAL)
        self.weight = 0.0  # 0 = Animaze-Tracking, 1 = BärCam-Werte
        self.weight_target = 0.0
        self.fade_s = 0.25
        self.packets = 0
        self._task: asyncio.Task | None = None

    def configure(self, host: str, port: int) -> None:
        self.host, self.port = host, port

    def set_frame(self, frame: Mapping[str, float], fade_s: float | None = None) -> None:
        self.target = resolve(frame)
        self.weight_target = 1.0 if self.target else 0.0
        if fade_s is not None:
            self.fade_s = max(0.0, fade_s)

    def release(self, fade_s: float = 0.3) -> None:
        """Zurück zum Live-Tracking (weiches Ausblenden)."""
        self.fade_s = fade_s
        self.weight_target = 0.0

    def _values(self) -> list[float]:
        w = self.weight
        vals = list(NEUTRAL)
        for idx, v in self.target.items():
            vals[idx] = NEUTRAL[idx] + (v - NEUTRAL[idx]) * w
        return vals

    def send_now(self, values: list[float]) -> None:
        self.sock.sendto(encode(values), (self.host, self.port))
        self.packets += 1

    async def run(self) -> None:
        dt = 1.0 / self.rate_hz
        last = time.perf_counter()
        while True:
            now = time.perf_counter()
            step = (now - last) / self.fade_s if self.fade_s > 0 else 1.0
            last = now
            if self.weight < self.weight_target:
                self.weight = min(self.weight_target, self.weight + step)
            elif self.weight > self.weight_target:
                self.weight = max(self.weight_target, self.weight - step)
            if self.weight > 0.0 or self.weight_target > 0.0:
                try:
                    self.send_now(self._values())
                except OSError:
                    pass
            elif not self.weight_target:
                self.target = {}
            await asyncio.sleep(dt)

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.get_running_loop().create_task(self.run())
