import asyncio
import json
import socket
import struct

from pythonosc.osc_bundle import OscBundle
from websockets.asyncio.server import serve

from baercam.animaze.api import AnimazeClient, AnimazeError
from baercam.animaze.tracker import TrackerSender, encode, resolve
from baercam.animaze.units import COUNT, INDEX, NEUTRAL
from baercam.animaze.vmc import build_bundle


def test_units_match_holotech_doc():
    assert COUNT == 157
    assert INDEX["HeadPitch"] == 0 and INDEX["Viseme_AA"] == 85 and INDEX["Procedural_Breath"] == 156
    assert INDEX["HandR_Finger3"] == 73
    assert NEUTRAL[INDEX["HeadYaw"]] == 0.5 and NEUTRAL[INDEX["HandL_NaturalPose"]] == 1.0 and NEUTRAL[INDEX["JawDrop"]] == 0.0


def test_encode_is_157_float32_le():
    data = encode(list(NEUTRAL))
    assert len(data) == 157 * 4
    assert struct.unpack_from("<f", data, 4 * INDEX["HeadYaw"])[0] == 0.5


def test_resolve_ignores_unknown_and_clamps():
    out = resolve({"MouthOpen": 1.7, "GibtEsNicht": 0.3, "EyeLClosed": -1})
    assert out == {INDEX["MouthOpen"]: 1.0, INDEX["EyeLClosed"]: 0.0}


async def test_tracker_sends_and_blends_back():
    rx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    rx.bind(("127.0.0.1", 0))
    rx.setblocking(False)
    sender = TrackerSender("127.0.0.1", rx.getsockname()[1], rate_hz=200)
    sender.set_frame({"MouthOpen": 1.0}, fade_s=0.05)
    sender.start()
    await asyncio.sleep(0.15)
    packets = []
    try:
        while True:
            packets.append(rx.recv(4096))
    except BlockingIOError:
        pass
    assert packets, "keine UDP-Pakete angekommen"
    last = struct.unpack("<157f", packets[-1])
    assert abs(last[INDEX["MouthOpen"]] - 1.0) < 1e-6
    sender.release(fade_s=0.05)
    await asyncio.sleep(0.15)
    assert sender.weight == 0.0
    sender._task.cancel()


def test_vmc_bundle_contains_bones_and_ok():
    dgram = build_bundle({"Head": (10.0, 0.0, 0.0), "RightIndexProximal": (0.0, 0.0, 90.0)}, {"Joy": 1.0}, 1.0)
    bundle = OscBundle(dgram)
    addresses = [m.address for m in bundle]
    assert "/VMC/Ext/OK" in addresses and "/VMC/Ext/Blend/Apply" in addresses
    bones = {m.params[0]: m.params for m in bundle if m.address == "/VMC/Ext/Bone/Pos"}
    assert set(bones) == {"Head", "RightIndexProximal"}
    qx, qy, qz, qw = bones["Head"][4:8]
    assert abs(qx * qx + qy * qy + qz * qz + qw * qw - 1) < 1e-6


async def _fake_animaze(ws):
    async for raw in ws:
        req = json.loads(raw)
        action = req["action"]
        if action == "GetAvatars":
            await ws.send(json.dumps({"action": action, "id": req["id"], "avatars": [{"itemName": "Bear", "friendlyName": "Bär"}]}))
        elif action == "LoadAvatar" and req["name"] != "Bear":
            await ws.send(json.dumps({"action": action, "id": req["id"], "error": "Avatar not found"}))
        else:
            await ws.send(json.dumps({"action": action, "id": req["id"]}))


async def test_client_talks_to_fake_animaze():
    statuses = []
    async with serve(_fake_animaze, "127.0.0.1", 0) as server:
        port = server.sockets[0].getsockname()[1]
        client = AnimazeClient("127.0.0.1", port)

        async def on_status(s):
            statuses.append(s["connected"])

        client.on_status = on_status
        client.start()
        for _ in range(100):
            if client.connected:
                break
            await asyncio.sleep(0.02)
        assert client.connected
        assert (await client.avatars())[0]["itemName"] == "Bear"
        await client.load_avatar("Bear")
        try:
            await client.load_avatar("Wolf")
            raise AssertionError("Fehler erwartet")
        except AnimazeError as e:
            assert "not found" in str(e)
    for _ in range(100):
        if not client.connected:
            break
        await asyncio.sleep(0.02)
    assert statuses[0] is True and statuses[-1] is False
    client._task.cancel()


async def test_client_without_animaze_reports_disconnected():
    client = AnimazeClient("127.0.0.1", 1)  # dort lauscht nichts
    client.start()
    await asyncio.sleep(0.3)
    assert not client.connected
    try:
        await client.avatars()
        raise AssertionError("Fehler erwartet")
    except AnimazeError:
        pass
    client._task.cancel()
