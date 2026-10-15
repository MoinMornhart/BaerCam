"""Verdrahtet die Dienste (Animaze, Hardware, Profile, Monitor, Player) mit dem RPC-Server."""

from __future__ import annotations

import asyncio
import time
from typing import Any

from . import hardware, profiles
from .animaze import detect
from .animaze.api import AnimazeClient, AnimazeError
from .animaze.tracker import TrackerSender
from .animaze.units import GROUPS, NAMES
from .animaze.vmc import VmcSender
from .clip import Clip, Player
from .monitor import Monitor
from .presets import TEST_CLIPS
from .server import App, RpcError
from .skeleton import BONES


class Services:
    def __init__(self, app: App) -> None:
        self.app = app
        cfg = app.settings.all()["animaze"]
        self.animaze = AnimazeClient(cfg["host"], cfg["apiPort"])
        self.vmc = VmcSender(cfg["host"], cfg["vmcPort"])
        self.tracker = TrackerSender(cfg["host"], cfg["trackerPort"])
        self.monitor = Monitor(app.emit)
        self.player = Player(self._apply_pose, self._release, self._emote)
        self._hw: hardware.HardwareInfo | None = None
        self._frames = 0
        self._fps_t = time.perf_counter()
        self.monitor.fps_source = self._fps
        self.animaze.on_status = lambda s: app.emit("animaze.status", s)
        self.animaze.on_event = lambda name, data: app.emit("animaze.event", {"name": name, "data": data})
        self._register()

    # ---------- Ausgänge ----------
    def _apply_pose(self, bones: dict, face: dict) -> None:
        self._frames += 1
        if bones:
            self.vmc.set_pose(bones, fade_s=0.2)
        if face:
            self.tracker.set_frame(face, fade_s=0.15)

    def _release(self) -> None:
        self.vmc.release()
        self.tracker.release()

    async def _emote(self, item: str) -> None:
        try:
            await self.animaze.trigger_emote(item)
        except AnimazeError:
            pass

    def _fps(self) -> dict:
        now = time.perf_counter()
        fps = self._frames / max(1e-6, now - self._fps_t)
        self._frames, self._fps_t = 0, now
        return {"animation": round(fps), "vmcPackets": self.vmc.packets, "trackerPackets": self.tracker.packets}

    async def startup(self) -> None:
        self.animaze.start()
        self.vmc.start()
        self.tracker.start()
        self.monitor.start()

    # ---------- RPC ----------
    def _register(self) -> None:
        m = self.app.methods
        az = self.animaze

        async def guarded(coro):
            try:
                return await coro
            except AnimazeError as e:
                raise RpcError("animaze", str(e)) from None

        m["animaze.status"] = lambda: {**az.status(), **detect.info()}

        def configure(host: str | None = None, apiPort: int | None = None, vmcPort: int | None = None, trackerPort: int | None = None):
            cfg = self.app.settings.update({"animaze": {k: v for k, v in
                                            {"host": host, "apiPort": apiPort, "vmcPort": vmcPort, "trackerPort": trackerPort}.items() if v is not None}})["animaze"]
            az.configure(cfg["host"], cfg["apiPort"])
            self.vmc.configure(cfg["host"], cfg["vmcPort"])
            self.tracker.configure(cfg["host"], cfg["trackerPort"])
            return cfg

        m["animaze.configure"] = configure

        async def avatars(withIcons: bool = False):
            items = await guarded(az.avatars())
            if withIcons:
                for it in items:
                    name = it.get("itemName") or it.get("name") if isinstance(it, dict) else it
                    try:
                        icon = await az.item_icon(name)
                    except AnimazeError:
                        icon = ""
                    if isinstance(it, dict):
                        it["icon"] = icon
            return items

        m["animaze.avatars"] = avatars
        m["animaze.icon"] = lambda name: guarded(az.item_icon(name))
        m["animaze.loadAvatar"] = lambda name: guarded(az.load_avatar(name))
        m["animaze.loadScene"] = lambda name: guarded(az.load_scene(name))

        lists = {"emotes": az.emotes, "specialActions": az.special_actions, "poses": az.poses, "idles": az.idles, "scenes": az.scenes}
        m["animaze.list"] = lambda kind: guarded(lists[kind]()) if kind in lists else _bad(kind)

        async def trigger(kind: str, value: Any):
            fn = {"emote": az.trigger_emote, "specialAction": az.trigger_special_action, "pose": az.trigger_pose, "idle": az.trigger_idle}.get(kind)
            if fn is None:
                _bad(kind)
            await guarded(fn(value))
            return True

        m["animaze.trigger"] = trigger
        m["animaze.broadcast"] = lambda on: guarded(az.broadcast(bool(on)))
        m["animaze.calibrate"] = lambda: guarded(az.calibrate())
        m["animaze.raw"] = lambda action, params=None: guarded(az.request(action, **(params or {})))

        # Bewegung
        m["motion.testClips"] = lambda: [{"id": k, "name": v["name"]} for k, v in TEST_CLIPS.items()]

        def play(id: str | None = None, clip: dict | None = None, speed: float = 1.0):
            data = clip if clip is not None else TEST_CLIPS.get(id or "")
            if data is None:
                raise RpcError("no_clip", "Kein Clip angegeben")
            self.player.play(Clip.from_dict(data), speed)
            return True

        m["motion.play"] = play
        m["motion.stop"] = lambda: self.player.stop() or True
        m["face.set"] = lambda frame, fade=0.15: self.tracker.set_frame(frame, fade) or True
        m["face.release"] = lambda: self.tracker.release() or True
        m["rig.describe"] = lambda: {"bones": list(BONES), "units": NAMES, "groups": GROUPS}

        # Hardware & Profile
        def hw_info(refresh: bool = False):
            if self._hw is None or refresh:
                self._hw = hardware.detect()
            return self._hw.to_dict()

        m["hardware.info"] = hw_info

        async def run_benchmark():
            hw_info()
            bench = await asyncio.to_thread(profiles.benchmark)
            rec, reasons = profiles.recommend(self._hw, bench)
            self.app.settings.update({"performance": {"benchmark": bench, "recommended": rec, "reasons": reasons}})
            return perf_state()

        m["performance.benchmark"] = run_benchmark

        def perf_state():
            p = self.app.settings.all()["performance"]
            chosen = p.get("profile", "auto")
            active = p.get("recommended") if chosen == "auto" else chosen
            return {
                "chosen": chosen,
                "active": active,
                "recommended": p.get("recommended"),
                "reasons": p.get("reasons", []),
                "benchmark": p.get("benchmark"),
                "profiles": [profiles.profile_dict(i) for i in profiles.ORDER],
                "hardware": hw_info(),
            }

        m["performance.state"] = perf_state

        def set_profile(id: str):
            if id != "auto" and id not in profiles.PROFILES:
                _bad(id)
            self.app.settings.update({"performance": {"profile": id}})
            state = perf_state()
            if state["active"]:
                fps = profiles.PROFILES[state["active"]].target_fps
                self.vmc.rate_hz = self.tracker.rate_hz = self.player.fps = float(fps)
            return state

        m["performance.setProfile"] = set_profile
        m["performance.sample"] = self.monitor.sample


def _bad(value: Any):
    raise RpcError("bad_params", f"Unbekannter Wert: {value}")


def attach(app: App) -> Services:
    services = Services(app)
    app.startup.append(services.startup)
    return services
