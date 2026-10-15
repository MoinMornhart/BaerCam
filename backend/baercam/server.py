"""Lokaler JSON-RPC-Server über WebSocket für die Tauri-Oberfläche.

Protokoll:
  Anfrage  {"id": 1, "method": "system.ping", "params": {...}}
  Antwort  {"id": 1, "result": ...}  oder  {"id": 1, "error": {"code": ..., "message": ...}}
  Ereignis {"event": "animaze.status", "data": {...}}   (vom Server gepusht)

Der Server lauscht nur auf 127.0.0.1, auf einem freien Port, und verlangt ein Token,
das beim Start auf stdout ausgegeben wird (Zeile "BAERCAM_READY {...}").
"""

from __future__ import annotations

import asyncio
import inspect
import json
import logging
import secrets
from collections.abc import Awaitable, Callable
from typing import Any

from websockets.asyncio.server import ServerConnection, serve
from websockets.exceptions import ConnectionClosed

from . import __version__
from .settings import Settings

log = logging.getLogger("baercam.server")

Handler = Callable[..., Any | Awaitable[Any]]


class RpcError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class App:
    """Hält Methoden-Registry, verbundene Clients und gemeinsame Dienste."""

    def __init__(self, settings: Settings | None = None, token: str | None = None) -> None:
        self.settings = settings or Settings()
        self.token = token or secrets.token_urlsafe(24)
        self.methods: dict[str, Handler] = {}
        self.clients: set[ServerConnection] = set()
        self._register_core()

    def method(self, name: str) -> Callable[[Handler], Handler]:
        def deco(fn: Handler) -> Handler:
            self.methods[name] = fn
            return fn

        return deco

    def _register_core(self) -> None:
        self.methods["system.ping"] = lambda: {"pong": True, "version": __version__}
        self.methods["settings.get"] = self.settings.all
        self.methods["settings.update"] = lambda patch: self.settings.update(patch)

    async def emit(self, event: str, data: Any) -> None:
        if not self.clients:
            return
        msg = json.dumps({"event": event, "data": data}, ensure_ascii=False)
        for ws in list(self.clients):
            try:
                await ws.send(msg)
            except ConnectionClosed:
                self.clients.discard(ws)

    async def dispatch(self, raw: str) -> dict[str, Any]:
        try:
            req = json.loads(raw)
        except json.JSONDecodeError:
            return {"id": None, "error": {"code": "bad_json", "message": "Ungültiges JSON"}}
        rid = req.get("id")
        fn = self.methods.get(req.get("method", ""))
        if fn is None:
            return {"id": rid, "error": {"code": "no_method", "message": f"Unbekannte Methode: {req.get('method')}"}}
        params = req.get("params") or {}
        try:
            result = fn(**params) if isinstance(params, dict) else fn(*params)
            if inspect.isawaitable(result):
                result = await result
            return {"id": rid, "result": result}
        except RpcError as e:
            return {"id": rid, "error": {"code": e.code, "message": e.message}}
        except TypeError as e:
            return {"id": rid, "error": {"code": "bad_params", "message": str(e)}}
        except Exception as e:  # noqa: BLE001 – Fehler gehen als Antwort an die UI, nie als Absturz
            log.exception("Fehler in %s", req.get("method"))
            return {"id": rid, "error": {"code": "internal", "message": str(e)}}

    async def handle(self, ws: ServerConnection) -> None:
        if ws.request is None or f"token={self.token}" not in (ws.request.path or ""):
            await ws.close(4401, "Token fehlt oder falsch")
            return
        self.clients.add(ws)
        try:
            async for raw in ws:
                resp = await self.dispatch(raw if isinstance(raw, str) else raw.decode())
                await ws.send(json.dumps(resp, ensure_ascii=False))
        except ConnectionClosed:
            pass
        finally:
            self.clients.discard(ws)


async def run(app: App, port: int = 0) -> None:
    async with serve(app.handle, "127.0.0.1", port, max_size=32 * 1024 * 1024) as server:
        bound = server.sockets[0].getsockname()[1]
        print("BAERCAM_READY " + json.dumps({"port": bound, "token": app.token, "version": __version__}), flush=True)
        await asyncio.get_running_loop().create_future()
