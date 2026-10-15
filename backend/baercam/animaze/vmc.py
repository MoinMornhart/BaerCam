"""VMC-Sender (OSC über UDP) für Körperbewegungen an Animaze ("VMC Body Tracker", Port 39539).

Pro Frame wird ein OSC-Bundle geschickt: Root, alle gesetzten Knochen (lokale Rotation), Zeit, OK.
Laut Animaze-Doku werden nur Körperdaten übernommen; Finger und Blendshapes schicken wir trotzdem mit
(kostet nichts) – falls Animaze sie ignoriert, übernimmt der Programmable Tracker die Finger.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Mapping

from pythonosc.osc_bundle_builder import IMMEDIATELY, OscBundleBuilder
from pythonosc.osc_message_builder import OscMessageBuilder
from pythonosc.udp_client import UDPClient

from ..skeleton import BONES, clamp_euler, euler_to_quat

# Ruhepose (Arme locker unten) statt T-Pose – dahin wird beim Loslassen geblendet.
REST_POSE: dict[str, tuple[float, float, float]] = {
    "LeftUpperArm": (0.0, 0.0, 70.0),
    "RightUpperArm": (0.0, 0.0, -70.0),
    "LeftLowerArm": (0.0, -10.0, 0.0),
    "RightLowerArm": (0.0, 10.0, 0.0),
}


def _msg(address: str, *args) -> OscMessageBuilder:
    m = OscMessageBuilder(address=address)
    for a in args:
        m.add_arg(a)
    return m


def build_bundle(bones: Mapping[str, tuple[float, float, float]], blend: Mapping[str, float], t: float) -> bytes:
    b = OscBundleBuilder(IMMEDIATELY)
    b.add_content(_msg("/VMC/Ext/OK", 1).build())
    b.add_content(_msg("/VMC/Ext/T", float(t)).build())
    b.add_content(_msg("/VMC/Ext/Root/Pos", "root", 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0).build())
    for name, euler in bones.items():
        qx, qy, qz, qw = euler_to_quat(*clamp_euler(name, euler))
        b.add_content(_msg("/VMC/Ext/Bone/Pos", name, 0.0, 0.0, 0.0, qx, qy, qz, qw).build())
    for key, val in blend.items():
        b.add_content(_msg("/VMC/Ext/Blend/Val", key, float(val)).build())
    if blend:
        b.add_content(_msg("/VMC/Ext/Blend/Apply").build())
    return b.build().dgram


class VmcSender:
    def __init__(self, host: str = "127.0.0.1", port: int = 39539, rate_hz: float = 60.0) -> None:
        self.client = UDPClient(host, port)
        self.host, self.port = host, port
        self.rate_hz = rate_hz
        self.target: dict[str, tuple[float, float, float]] = {}
        self.blend: dict[str, float] = {}
        self.weight = 0.0
        self.weight_target = 0.0
        self.fade_s = 0.3
        self.hold_rest_s = 1.0  # nach dem Ausblenden noch kurz Ruhepose senden, dann Ruhe
        self.packets = 0
        self._idle_since: float | None = None
        self._task: asyncio.Task | None = None
        self._t0 = time.perf_counter()

    def configure(self, host: str, port: int) -> None:
        self.host, self.port = host, port
        self.client = UDPClient(host, port)

    def set_pose(self, bones: Mapping[str, tuple[float, float, float]], blend: Mapping[str, float] | None = None,
                 fade_s: float | None = None) -> None:
        # Unbekannte Knochennamen werden einfach mitgeschickt – Animaze ignoriert, was es nicht kennt.
        self.target = {k: tuple(map(float, v)) for k, v in bones.items()}  # type: ignore[misc]
        self.blend = dict(blend or {})
        self.weight_target = 1.0
        self._idle_since = None
        if fade_s is not None:
            self.fade_s = max(0.0, fade_s)

    def release(self, fade_s: float = 0.4) -> None:
        self.fade_s = fade_s
        self.weight_target = 0.0

    def current_pose(self) -> dict[str, tuple[float, float, float]]:
        w = self.weight
        names = set(self.target) | set(REST_POSE)
        out = {}
        for n in names:
            rest = REST_POSE.get(n, (0.0, 0.0, 0.0))
            tgt = self.target.get(n, rest)
            out[n] = tuple(r + (t - r) * w for r, t in zip(rest, tgt))
        return out  # type: ignore[return-value]

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
            active = self.weight > 0 or self.weight_target > 0
            if not active:
                self._idle_since = self._idle_since or now
            if active or (self._idle_since and now - self._idle_since < self.hold_rest_s):
                try:
                    blend = {k: v * self.weight for k, v in self.blend.items()}
                    self.client.send(_Raw(build_bundle(self.current_pose(), blend, now - self._t0)))
                    self.packets += 1
                except OSError:
                    pass
            await asyncio.sleep(dt)

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.get_running_loop().create_task(self.run())


class _Raw:
    """Adapter, damit UDPClient.send() fertige Bytes verschickt."""

    def __init__(self, dgram: bytes) -> None:
        self.dgram = dgram


__all__ = ["VmcSender", "build_bundle", "REST_POSE", "BONES"]
