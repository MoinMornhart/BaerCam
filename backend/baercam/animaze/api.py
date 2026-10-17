"""Client für die Animaze-WebSocket-API (Standard ws://localhost:9000).

Eigene, schlanke Umsetzung (AnimazePy ist GPL-3 und nicht gepflegt). Hält die Verbindung automatisch
aufrecht, ordnet Antworten über "id" (Fallback: "action") zu und meldet Status-Änderungen.
"""

from __future__ import annotations

import asyncio
import itertools
import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from websockets.asyncio.client import ClientConnection, connect
from websockets.exceptions import ConnectionClosed, InvalidHandshake, InvalidURI

log = logging.getLogger("baercam.animaze")

StatusCallback = Callable[[dict[str, Any]], Awaitable[None]]
EventCallback = Callable[[str, dict[str, Any]], Awaitable[None]]


class AnimazeError(Exception):
    pass


class AnimazeClient:
    def __init__(self, host: str = "127.0.0.1", port: int = 9000, timeout: float = 8.0) -> None:
        self.host, self.port, self.timeout = host, port, timeout
        self.ws: ClientConnection | None = None
        self.connected = False
        self.last_error = ""
        self._ids = itertools.count(1)
        self._pending: dict[str, asyncio.Future] = {}
        self._task: asyncio.Task | None = None
        self.on_status: StatusCallback | None = None
        self.on_event: EventCallback | None = None

    @property
    def url(self) -> str:
        return f"ws://{self.host}:{self.port}"

    def status(self) -> dict[str, Any]:
        return {"connected": self.connected, "url": self.url, "error": self.last_error}

    async def _set_status(self, connected: bool, error: str = "") -> None:
        changed = connected != self.connected or error != self.last_error
        self.connected, self.last_error = connected, error
        if changed and self.on_status:
            await self.on_status(self.status())

    def configure(self, host: str, port: int) -> None:
        if (host, port) != (self.host, self.port):
            self.host, self.port = host, port
            if self.ws:
                asyncio.get_running_loop().create_task(self.ws.close())

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.get_running_loop().create_task(self._run())

    async def _run(self) -> None:
        delay = 1.0
        while True:
            try:
                async with connect(self.url, open_timeout=3, max_size=64 * 1024 * 1024, ping_interval=10) as ws:
                    self.ws = ws
                    delay = 1.0
                    await self._set_status(True)
                    async for raw in ws:
                        self._on_message(raw)
                # Sauber geschlossen (z. B. Animaze beendet): sofort melden, nicht erst beim nächsten Versuch
                await self._set_status(False, "closed")
            except (OSError, ConnectionClosed, InvalidHandshake, InvalidURI, asyncio.TimeoutError, TimeoutError) as e:
                refused = isinstance(e, OSError) and not isinstance(e, TimeoutError)
                await self._set_status(False, "refused" if refused else type(e).__name__)
            finally:
                self.ws = None
                for fut in self._pending.values():
                    if not fut.done():
                        fut.set_exception(AnimazeError("Verbindung zu Animaze getrennt"))
                self._pending.clear()
            await asyncio.sleep(delay)
            delay = min(delay * 1.5, 5.0)

    def _on_message(self, raw: str | bytes) -> None:
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            return
        key = str(msg.get("id", "")) or None
        fut = self._pending.pop(key, None) if key else None
        if fut is None:
            # Antworten ohne id: dem ältesten offenen Aufruf mit derselben action zuordnen
            action = msg.get("action")
            for k, f in list(self._pending.items()):
                if getattr(f, "action", None) == action:
                    fut = self._pending.pop(k)
                    break
        if fut is not None and not fut.done():
            fut.set_result(msg)
        elif self.on_event:
            asyncio.get_running_loop().create_task(self.on_event(str(msg.get("action", "event")), msg))

    async def request(self, action: str, **params: Any) -> dict[str, Any]:
        if not self.ws:
            raise AnimazeError("Nicht mit Animaze verbunden")
        rid = f"bc{next(self._ids)}"
        fut = asyncio.get_running_loop().create_future()
        fut.action = action  # type: ignore[attr-defined]
        self._pending[rid] = fut
        await self.ws.send(json.dumps({"action": action, "id": rid, **params}))
        try:
            msg = await asyncio.wait_for(fut, self.timeout)
        except asyncio.TimeoutError:
            self._pending.pop(rid, None)
            raise AnimazeError(f"Animaze hat auf {action} nicht geantwortet") from None
        if msg.get("error"):
            raise AnimazeError(str(msg["error"]))
        return msg

    # --- Bequeme Aufrufe (Namen wie in der Holotech-Doku) ---------------------------------
    async def avatars(self) -> list[Any]:
        r = await self.request("GetAvatars")
        return r.get("avatars") or r.get("avatarList") or r.get("items") or []

    async def item_icon(self, name: str) -> str:
        r = await self.request("GetItemIcon", name=name)
        return r.get("image", "")

    async def load_avatar(self, name: str) -> None:
        await self.request("LoadAvatar", name=name)

    async def scenes(self) -> list[Any]:
        r = await self.request("GetScenes")
        return r.get("scenes") or r.get("sceneList") or r.get("items") or []

    async def load_scene(self, name: str) -> None:
        await self.request("LoadScene", name=name)

    async def emotes(self) -> list[Any]:
        r = await self.request("GetEmotes")
        return r.get("emotes") or r.get("emoteList") or r.get("items") or []

    async def trigger_emote(self, item_name: str) -> None:
        await self.request("TriggerEmote", itemName=item_name)

    async def special_actions(self) -> list[Any]:
        r = await self.request("GetSpecialActions")
        return r.get("specialActions") or r.get("specialActionList") or r.get("items") or []

    async def trigger_special_action(self, index: int) -> None:
        await self.request("TriggerSpecialAction", index=index)

    async def poses(self) -> list[Any]:
        r = await self.request("GetPoses")
        return r.get("poseList") or r.get("poses") or []

    async def trigger_pose(self, index: int) -> None:
        await self.request("TriggerPose", index=index)

    async def idles(self) -> list[Any]:
        r = await self.request("GetIdleAnims")
        return r.get("idleList") or r.get("idles") or []

    async def trigger_idle(self, index: int) -> None:
        await self.request("TriggerIdle", index=index)

    async def broadcast(self, on: bool) -> None:
        await self.request("Broadcast", toggle=on)

    async def calibrate(self) -> None:
        await self.request("CalibrateTracker")

    async def set_override(self, behavior: str, value: bool) -> None:
        await self.request("SetOverride", behavior=behavior, value=value)

    async def set_avatar_transform(self, position: list[float], rotation: list[float], scale: list[float]) -> None:
        await self.request("SetAvatarTransform", position=position, rotation=rotation, scale=scale)
