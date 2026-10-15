"""Humanoides Skelett (Unity-Humanoid-/VMC-Knochennamen) mit Gelenkgrenzen.

Diese Beschreibung bekommt später auch das LLM, damit es Keyframes für jeden Knochen erzeugen kann.
Rotationen sind Euler-Winkel in Grad (X = Nicken, Y = Drehen, Z = Kippen) relativ zur T-Pose.
Grenzen sind bewusst großzügig: Sie verhindern „kaputte“ Posen, nicht ausdrucksstarke.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Bone:
    name: str
    parent: str | None
    limits: tuple[tuple[float, float], tuple[float, float], tuple[float, float]]  # (x, y, z) in Grad


def _b(name: str, parent: str | None, x=(-180, 180), y=(-180, 180), z=(-180, 180)) -> Bone:
    return Bone(name, parent, (x, y, z))


_BONES: list[Bone] = [
    _b("Hips", None),
    _b("Spine", "Hips", (-40, 40), (-40, 40), (-30, 30)),
    _b("Chest", "Spine", (-30, 30), (-30, 30), (-25, 25)),
    _b("UpperChest", "Chest", (-20, 20), (-20, 20), (-15, 15)),
    _b("Neck", "UpperChest", (-40, 40), (-50, 50), (-30, 30)),
    _b("Head", "Neck", (-50, 50), (-70, 70), (-40, 40)),
    _b("LeftEye", "Head", (-25, 25), (-35, 35), (0, 0)),
    _b("RightEye", "Head", (-25, 25), (-35, 35), (0, 0)),
    _b("Jaw", "Head", (0, 30), (-10, 10), (-5, 5)),
]
for side, sgn in (("Left", 1), ("Right", -1)):
    _BONES += [
        _b(f"{side}Shoulder", "UpperChest", (-20, 20), (-30, 30), (-30, 30)),
        _b(f"{side}UpperArm", f"{side}Shoulder", (-120, 120), (-100, 100), (-90, 160) if sgn > 0 else (-160, 90)),
        _b(f"{side}LowerArm", f"{side}UpperArm", (-90, 90), (-150, 150), (-10, 10)),
        _b(f"{side}Hand", f"{side}LowerArm", (-80, 80), (-40, 40), (-80, 80)),
        _b(f"{side}UpperLeg", "Hips", (-120, 60), (-60, 60), (-60, 60)),
        _b(f"{side}LowerLeg", f"{side}UpperLeg", (0, 160), (-10, 10), (-10, 10)),
        _b(f"{side}Foot", f"{side}LowerLeg", (-50, 50), (-30, 30), (-30, 30)),
        _b(f"{side}Toes", f"{side}Foot", (-40, 60), (0, 0), (0, 0)),
    ]
    for finger in ("Thumb", "Index", "Middle", "Ring", "Little"):
        for seg in ("Proximal", "Intermediate", "Distal"):
            parent = f"{side}Hand" if seg == "Proximal" else f"{side}{finger}{'Proximal' if seg == 'Intermediate' else 'Intermediate'}"
            # Fingerbeugung um Z (Unity-Konvention, Beugen = Richtung Handfläche); Spreizen um Y nur am Grundgelenk
            spread = (-25, 25) if seg == "Proximal" else (0, 0)
            bend = (-10, 100) if finger != "Thumb" else (-30, 60)
            _BONES.append(_b(f"{side}{finger}{seg}", parent, (-20, 20) if finger == "Thumb" else (0, 0), spread, bend))

BONES: dict[str, Bone] = {b.name: b for b in _BONES}


def clamp_euler(name: str, euler: tuple[float, float, float]) -> tuple[float, float, float]:
    """Begrenzt eine Rotation auf die Gelenkgrenzen. Unbekannte Knochen bleiben unverändert."""
    bone = BONES.get(name)
    if bone is None:
        return euler
    return tuple(min(hi, max(lo, v)) for v, (lo, hi) in zip(euler, bone.limits))  # type: ignore[return-value]


def euler_to_quat(x: float, y: float, z: float) -> tuple[float, float, float, float]:
    """Euler (Grad, Unity-Reihenfolge Z-X-Y) → Quaternion (x, y, z, w)."""
    hx, hy, hz = (math.radians(a) / 2 for a in (x, y, z))
    cx, sx, cy, sy, cz, sz = math.cos(hx), math.sin(hx), math.cos(hy), math.sin(hy), math.cos(hz), math.sin(hz)
    # q = qy * qx * qz  (Unity wendet Z, dann X, dann Y an)
    qw = cy * cx * cz + sy * sx * sz
    qx = cy * sx * cz + sy * cx * sz
    qy = sy * cx * cz - cy * sx * sz
    qz = cy * cx * sz - sy * sx * cz
    return (qx, qy, qz, qw)


def describe_for_llm() -> str:
    """Kompakte Skelettbeschreibung für den System-Prompt."""
    lines = ["Knochen (Name, Eltern, Grenzen X/Y/Z in Grad):"]
    for b in _BONES:
        (x0, x1), (y0, y1), (z0, z1) = b.limits
        lines.append(f"{b.name} <- {b.parent or '-'} | X {x0}..{x1} Y {y0}..{y1} Z {z0}..{z1}")
    return "\n".join(lines)
