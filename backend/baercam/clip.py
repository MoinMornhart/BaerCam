"""Animations-Clip: Keyframes für Knochen (Euler, Grad) und Gesichts-/Hand-Units (0..1).

Format (JSON):
{
  "name": "Winken",
  "duration": 2.0,
  "bones": {"RightUpperArm": [[0.0, 0, 0, -70], [0.4, 0, 0, 60]], ...},   # [t, x, y, z]
  "face":  {"MouthSmileL": [[0.0, 0], [0.3, 1]], ...},                      # [t, wert]
  "emotes": [[0.5, "itemName"]]                                             # optionale Animaze-Emotes
}
Unbekannte Knochen-/Unit-Namen sind erlaubt und werden durchgereicht bzw. ignoriert – nie ein Fehler.
"""

from __future__ import annotations

import asyncio
import bisect
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any


def _sample(keys: list[list[float]], t: float, width: int) -> list[float]:
    if not keys:
        return [0.0] * width
    times = [k[0] for k in keys]
    i = bisect.bisect_right(times, t)
    if i == 0:
        return list(keys[0][1:])
    if i >= len(keys):
        return list(keys[-1][1:])
    a, b = keys[i - 1], keys[i]
    span = b[0] - a[0] or 1e-6
    u = (t - a[0]) / span
    u = u * u * (3 - 2 * u)  # weich (smoothstep)
    return [x + (y - x) * u for x, y in zip(a[1:], b[1:])]


@dataclass
class Clip:
    name: str = "Animation"
    duration: float = 1.0
    bones: dict[str, list[list[float]]] = field(default_factory=dict)
    face: dict[str, list[list[float]]] = field(default_factory=dict)
    emotes: list[list[Any]] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Clip:
        def norm(tracks: Any, width: int) -> dict[str, list[list[float]]]:
            out: dict[str, list[list[float]]] = {}
            if not isinstance(tracks, dict):
                return out
            for name, keys in tracks.items():
                good = [[float(v) for v in k[: width + 1]] for k in (keys or []) if isinstance(k, (list, tuple)) and len(k) >= width + 1]
                if good:
                    out[str(name)] = sorted(good, key=lambda k: k[0])
            return out

        bones, face = norm(d.get("bones"), 3), norm(d.get("face"), 1)
        last = max([k[-1][0] for k in [*bones.values(), *face.values()]] or [0.0])
        return cls(
            name=str(d.get("name") or "Animation"),
            duration=max(float(d.get("duration") or 0), last, 0.1),
            bones=bones,
            face=face,
            emotes=[e for e in d.get("emotes") or [] if isinstance(e, (list, tuple)) and len(e) == 2],
        )

    def pose_at(self, t: float) -> tuple[dict[str, tuple[float, float, float]], dict[str, float]]:
        bones = {n: tuple(_sample(k, t, 3)) for n, k in self.bones.items()}
        face = {n: _sample(k, t, 1)[0] for n, k in self.face.items()}
        return bones, face  # type: ignore[return-value]


class Player:
    """Spielt Clips ab und schiebt die Posen pro Frame zu den Ausgängen (Animaze oder Ersatz-Avatar)."""

    def __init__(self, on_pose: Callable[[dict, dict], None], on_release: Callable[[], None],
                 on_emote: Callable[[str], Awaitable[None]] | None = None, fps: float = 60.0) -> None:
        self.on_pose, self.on_release, self.on_emote = on_pose, on_release, on_emote
        self.fps = fps
        self._task: asyncio.Task | None = None
        self.current: str | None = None

    def play(self, clip: Clip, speed: float = 1.0) -> None:
        self.stop(release=False)
        self._task = asyncio.get_running_loop().create_task(self._run(clip, max(0.05, speed)))

    def stop(self, release: bool = True) -> None:
        if self._task and not self._task.done():
            self._task.cancel()
        self.current = None
        if release:
            self.on_release()

    async def _run(self, clip: Clip, speed: float) -> None:
        self.current = clip.name
        start = time.perf_counter()
        pending_emotes = sorted(clip.emotes, key=lambda e: e[0])
        try:
            while True:
                t = (time.perf_counter() - start) * speed
                while pending_emotes and pending_emotes[0][0] <= t and self.on_emote:
                    await self.on_emote(str(pending_emotes.pop(0)[1]))
                self.on_pose(*clip.pose_at(min(t, clip.duration)))
                if t >= clip.duration:
                    break
                await asyncio.sleep(1.0 / self.fps)
        finally:
            self.current = None
            self.on_release()
