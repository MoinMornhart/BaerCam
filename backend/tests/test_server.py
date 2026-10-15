import asyncio
import json

from websockets.asyncio.client import connect

from baercam.server import App, RpcError, run
from baercam.settings import Settings


def make_app(tmp_path) -> App:
    return App(settings=Settings(tmp_path / "settings.json"), token="testtoken")


async def test_dispatch_ping(tmp_path):
    app = make_app(tmp_path)
    resp = await app.dispatch(json.dumps({"id": 1, "method": "system.ping"}))
    assert resp["result"]["pong"] is True


async def test_unknown_method_is_error_not_crash(tmp_path):
    app = make_app(tmp_path)
    resp = await app.dispatch(json.dumps({"id": 2, "method": "gibts.nicht"}))
    assert resp["error"]["code"] == "no_method"


async def test_handler_exception_becomes_error(tmp_path):
    app = make_app(tmp_path)

    @app.method("test.boom")
    def boom():
        raise RpcError("kaputt", "absichtlich")

    resp = await app.dispatch(json.dumps({"id": 3, "method": "test.boom"}))
    assert resp["error"] == {"code": "kaputt", "message": "absichtlich"}


async def test_settings_roundtrip(tmp_path):
    app = make_app(tmp_path)
    await app.dispatch(json.dumps({"id": 1, "method": "settings.update", "params": {"patch": {"animaze": {"apiPort": 9100}}}}))
    again = Settings(tmp_path / "settings.json").all()
    assert again["animaze"]["apiPort"] == 9100
    assert again["animaze"]["vmcPort"] == 39539


async def test_websocket_requires_token(tmp_path, capsys):
    app = make_app(tmp_path)
    task = asyncio.create_task(run(app, 0))
    for _ in range(50):
        await asyncio.sleep(0.02)
        out = capsys.readouterr().out
        if "BAERCAM_READY" in out:
            break
    info = json.loads(out.split("BAERCAM_READY ", 1)[1].splitlines()[0])
    async with connect(f"ws://127.0.0.1:{info['port']}/?token=testtoken") as ws:
        await ws.send(json.dumps({"id": 9, "method": "system.ping"}))
        assert json.loads(await ws.recv())["result"]["pong"] is True
    async with connect(f"ws://127.0.0.1:{info['port']}/?token=falsch") as ws:
        await ws.wait_closed()
        assert ws.close_code == 4401
    task.cancel()
