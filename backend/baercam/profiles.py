"""Leistungsprofile und Benchmark.

Jedes Profil sagt nur, WIE etwas läuft (Modellgröße, Quantisierung, FPS, lokal/online, welcher Avatar) –
nie OB. Auch „Toaster“ kann alles, nur langsamer oder über Online-Dienste.
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass

import numpy as np

from .hardware import HardwareInfo


@dataclass(frozen=True)
class Profile:
    id: str
    label: str
    description: str
    model_size: str  # large | medium | small | tiny
    quantization: str  # fp16 | int8 | int4
    target_fps: int
    prefer_online: bool
    avatar: str  # animaze | fallback3d | fallback2d
    render: str  # realtime | background
    ui_effects: bool


PROFILES: dict[str, Profile] = {
    p.id: p
    for p in [
        Profile("ultra", "Ultra", "Volle Qualität, alles lokal in Echtzeit.", "large", "fp16", 60, False, "animaze", "realtime", True),
        Profile("normal", "Normal", "Etwas kleinere Modelle, weiterhin lokal.", "medium", "int8", 60, False, "animaze", "realtime", True),
        Profile("sparsam", "Sparsam", "Kleinste, quantisierte Modelle, weniger FPS.", "small", "int4", 30, False, "animaze", "realtime", False),
        Profile("toaster", "Toaster", "KI auf CPU oder online, leichter 2D-Bär, Videos im Hintergrund.", "tiny", "int4", 15, True, "fallback2d", "background", False),
    ]
}
ORDER = ["ultra", "normal", "sparsam", "toaster"]


def benchmark(seconds: float = 1.5) -> dict:
    """Kurzer CPU-Test: Matrixmultiplikation (float32) → GFLOPS. Dauert ca. `seconds` Sekunden."""
    n = 384
    a = np.random.rand(n, n).astype(np.float32)
    b = np.random.rand(n, n).astype(np.float32)
    a @ b  # Aufwärmen
    ops = 0
    start = time.perf_counter()
    while time.perf_counter() - start < seconds:
        a @ b
        ops += 2 * n**3
    elapsed = time.perf_counter() - start
    return {"cpuGflops": round(ops / elapsed / 1e9, 1), "seconds": round(elapsed, 2)}


def recommend(hw: HardwareInfo, bench: dict | None = None) -> tuple[str, list[str]]:
    """Wählt ein Profil und begründet die Wahl (Gründe auf Deutsch für die Oberfläche)."""
    gflops = (bench or {}).get("cpuGflops", 0.0)
    gpu = hw.best_gpu
    vram = (gpu.vram_gb or 0) if gpu else 0
    dedicated = gpu is not None and not gpu.integrated
    reasons: list[str] = []

    if gpu and gpu.vendor == "apple":
        dedicated, vram = True, gpu.vram_gb or 0

    if dedicated and vram >= 8 and hw.ram_gb >= 16 and ("cuda" in hw.accelerators or gpu.vendor == "apple"):
        choice = "ultra"
        reasons.append(f"Starke Grafikkarte ({gpu.name}, {vram:g} GB) und {hw.ram_gb:g} GB RAM.")
    elif dedicated and vram >= 4 and hw.ram_gb >= 12:
        choice = "normal"
        reasons.append(f"Eigene Grafikkarte mit {vram:g} GB, {hw.ram_gb:g} GB RAM.")
    elif hw.ram_gb >= 8 and (dedicated or gflops >= 40):
        choice = "sparsam"
        reasons.append("Ausreichend RAM, aber keine starke Grafikkarte.")
    else:
        choice = "toaster"
        reasons.append("Wenig RAM bzw. keine Grafikkarte – KI läuft über CPU oder online.")

    if gflops and gflops < 15 and ORDER.index(choice) < ORDER.index("sparsam"):
        choice = "sparsam"
        reasons.append(f"Die CPU ist eher langsam ({gflops:g} GFLOPS).")
    if hw.ram_gb < 6:
        choice = "toaster"
        reasons.append(f"Nur {hw.ram_gb:g} GB RAM.")
    return choice, reasons


def profile_dict(pid: str) -> dict:
    return asdict(PROFILES[pid])


def lower(pid: str) -> str | None:
    i = ORDER.index(pid)
    return ORDER[i + 1] if i + 1 < len(ORDER) else None
