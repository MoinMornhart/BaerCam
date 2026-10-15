"""Hardware-Erkennung: CPU, RAM, GPU(s) mit VRAM, verfügbare Beschleunigung.

Jede Erkennung ist „best effort“: Schlägt etwas fehl, gibt es weniger Infos – nie einen Absturz.
"""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass, field

import psutil

GB = 1024**3
_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0


@dataclass
class Gpu:
    name: str
    vendor: str  # nvidia | amd | intel | apple | other
    vram_gb: float | None = None
    integrated: bool = False


@dataclass
class HardwareInfo:
    os: str
    arch: str
    cpu: str
    cores: int
    threads: int
    ram_gb: float
    gpus: list[Gpu] = field(default_factory=list)
    accelerators: list[str] = field(default_factory=list)  # Reihenfolge = Bevorzugung

    def to_dict(self) -> dict:
        return asdict(self)

    @property
    def best_gpu(self) -> Gpu | None:
        ranked = sorted(self.gpus, key=lambda g: (not g.integrated, g.vram_gb or 0), reverse=True)
        return ranked[0] if ranked else None


def _run(cmd: list[str], timeout: float = 5.0) -> str:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, creationflags=_NO_WINDOW).stdout
    except (OSError, subprocess.SubprocessError):
        return ""


def _vendor(name: str) -> str:
    n = name.lower()
    for key, vendor in (("nvidia", "nvidia"), ("geforce", "nvidia"), ("quadro", "nvidia"), ("radeon", "amd"),
                        ("amd", "amd"), ("intel", "intel"), ("apple", "apple")):
        if key in n:
            return vendor
    return "other"


def _is_integrated(name: str, vendor: str, vram: float | None) -> bool:
    n = name.lower()
    if vendor == "intel" and "arc" not in n:
        return True
    if vendor == "amd" and ("graphics" in n and "rx" not in n):
        return True
    return vram is not None and vram < 1.0


def _cpu_name() -> str:
    if sys.platform == "win32":
        try:
            import winreg

            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0") as k:
                return str(winreg.QueryValueEx(k, "ProcessorNameString")[0]).strip()
        except OSError:
            pass
    if sys.platform == "darwin":
        out = _run(["sysctl", "-n", "machdep.cpu.brand_string"]).strip()
        if out:
            return out
    if os.path.exists("/proc/cpuinfo"):
        for line in open("/proc/cpuinfo", encoding="utf-8", errors="ignore"):
            if line.startswith("model name"):
                return line.split(":", 1)[1].strip()
    return platform.processor() or "Unbekannte CPU"


def _nvidia_gpus() -> list[Gpu]:
    if not shutil.which("nvidia-smi"):
        return []
    out = _run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"])
    gpus = []
    for line in out.strip().splitlines():
        try:
            name, mem = [p.strip() for p in line.split(",")]
            gpus.append(Gpu(name=name, vendor="nvidia", vram_gb=round(float(mem) / 1024, 1)))
        except ValueError:
            continue
    return gpus


def _windows_gpus() -> list[Gpu]:
    """Liest Grafikkarten aus der Registry (dort steht der echte VRAM, WMI deckelt bei 4 GB)."""
    gpus: list[Gpu] = []
    try:
        import winreg

        base = r"SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}"
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, base) as root:
            for i in range(64):
                try:
                    sub = winreg.EnumKey(root, i)
                except OSError:
                    break
                if not sub.isdigit():
                    continue
                try:
                    with winreg.OpenKey(root, sub) as k:
                        name = str(winreg.QueryValueEx(k, "DriverDesc")[0])
                        vram = None
                        for val in ("HardwareInformation.qwMemorySize", "HardwareInformation.MemorySize"):
                            try:
                                raw = winreg.QueryValueEx(k, val)[0]
                                vram = (int.from_bytes(raw, "little") if isinstance(raw, bytes) else int(raw)) / GB
                                break
                            except OSError:
                                continue
                except OSError:
                    continue
                if any(skip in name.lower() for skip in ("virtual", "basic display", "remote", "parsec", "meta ")):
                    continue
                v = _vendor(name)
                vr = round(vram, 1) if vram else None
                gpus.append(Gpu(name=name, vendor=v, vram_gb=vr, integrated=_is_integrated(name, v, vr)))
    except OSError:
        pass
    return gpus


def _mac_gpus(ram_gb: float) -> list[Gpu]:
    if platform.machine() == "arm64":
        return [Gpu(name=f"Apple Silicon ({_cpu_name()})", vendor="apple", vram_gb=round(ram_gb * 0.66, 1), integrated=True)]
    out = _run(["system_profiler", "SPDisplaysDataType", "-json"], timeout=10)
    try:
        items = json.loads(out).get("SPDisplaysDataType", [])
    except json.JSONDecodeError:
        items = []
    return [Gpu(name=i.get("sppci_model", "GPU"), vendor=_vendor(i.get("sppci_model", ""))) for i in items]


def _linux_gpus() -> list[Gpu]:
    gpus: list[Gpu] = []
    for line in _run(["lspci"]).splitlines():
        if "VGA" in line or "3D controller" in line:
            name = line.split(":", 2)[-1].strip()
            v = _vendor(name)
            if v != "nvidia":
                gpus.append(Gpu(name=name, vendor=v, integrated=_is_integrated(name, v, None)))
    return gpus


def detect() -> HardwareInfo:
    ram_gb = round(psutil.virtual_memory().total / GB, 1)
    gpus = _nvidia_gpus()
    if sys.platform == "win32":
        gpus += [g for g in _windows_gpus() if g.vendor != "nvidia" or not gpus]
    elif sys.platform == "darwin":
        gpus += _mac_gpus(ram_gb)
    else:
        gpus += _linux_gpus()

    accel: list[str] = []
    if any(g.vendor == "nvidia" for g in gpus):
        accel.append("cuda")
    if sys.platform == "win32" and gpus:
        accel.append("directml")
    if sys.platform != "darwin" and any(g.vendor in ("amd", "intel") for g in gpus):
        accel.append("vulkan")
    if any(g.vendor == "apple" for g in gpus):
        accel += ["coreml", "metal"]
    accel.append("cpu")

    os_name = f"{platform.system()} {platform.release()}"
    if sys.platform == "win32" and sys.getwindowsversion().build >= 22000:
        os_name = "Windows 11"
    return HardwareInfo(
        os=os_name,
        arch=platform.machine(),
        cpu=_cpu_name(),
        cores=psutil.cpu_count(logical=False) or 1,
        threads=psutil.cpu_count(logical=True) or 1,
        ram_gb=ram_gb,
        gpus=gpus,
        accelerators=accel,
    )
