from baercam import hardware, profiles
from baercam.clip import Clip
from baercam.hardware import Gpu, HardwareInfo
from baercam.presets import TEST_CLIPS
from baercam.skeleton import BONES, clamp_euler


def hw(ram, gpus=(), accel=("cpu",)):
    return HardwareInfo(os="Test", arch="x86_64", cpu="Test-CPU", cores=4, threads=8, ram_gb=ram, gpus=list(gpus), accelerators=list(accel))


def test_gaming_pc_is_ultra():
    pc = hw(32, [Gpu("NVIDIA GeForce RTX 5060 Ti", "nvidia", 16.0)], ["cuda", "directml", "cpu"])
    assert profiles.recommend(pc, {"cpuGflops": 300})[0] == "ultra"


def test_midrange_is_normal():
    pc = hw(16, [Gpu("AMD Radeon RX 6500", "amd", 4.0)], ["directml", "vulkan", "cpu"])
    assert profiles.recommend(pc, {"cpuGflops": 120})[0] == "normal"


def test_old_laptop_is_toaster():
    pc = hw(4, [Gpu("Intel HD Graphics 4000", "intel", None, integrated=True)])
    choice, reasons = profiles.recommend(pc, {"cpuGflops": 8})
    assert choice == "toaster" and reasons


def test_every_profile_can_do_everything():
    # "Toaster" heißt langsamer/online – nicht "geht nicht"
    for p in profiles.PROFILES.values():
        assert p.model_size and p.target_fps > 0 and p.avatar


def test_hardware_detect_never_crashes():
    info = hardware.detect()
    assert info.ram_gb > 0 and info.threads >= 1 and info.accelerators[-1] == "cpu"


def test_benchmark_is_quick():
    r = profiles.benchmark(seconds=0.2)
    assert r["cpuGflops"] > 0 and r["seconds"] < 2


def test_skeleton_has_every_finger_bone():
    for side in ("Left", "Right"):
        for f in ("Thumb", "Index", "Middle", "Ring", "Little"):
            for seg in ("Proximal", "Intermediate", "Distal"):
                assert f"{side}{f}{seg}" in BONES
    assert clamp_euler("LeftIndexProximal", (0, 0, 500)) == (0, 0, 100)
    assert clamp_euler("Schwanz", (1, 2, 3)) == (1, 2, 3)  # unbekannt = durchreichen, kein Fehler


def test_clip_interpolates_and_tolerates_garbage():
    clip = Clip.from_dict({"bones": {"Head": [[0, 0, 0, 0], [1, 10, 0, 0]], "Kaputt": "x"}, "face": {"JawDrop": [[0, 0], [1, 1], [2]]}})
    bones, face = clip.pose_at(0.5)
    assert 4 < bones["Head"][0] < 6 and 0.4 < face["JawDrop"] < 0.6
    assert "Kaputt" not in clip.bones and clip.duration == 1.0


def test_presets_are_valid_clips():
    for data in TEST_CLIPS.values():
        c = Clip.from_dict(data)
        assert c.duration > 0 and (c.bones or c.face)
