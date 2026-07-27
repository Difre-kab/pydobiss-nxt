"""Shared fixtures for the pydobiss-nxt test suite.

The sample payload reproduces every real-world quirk observed on NXT
firmware 4.30 (see models.py docstring): string/int numbers, null
dimmable, settings as empty list, overlapping groups.
"""

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

import pytest
from aiohttp import ClientSession, WSMsgType, web
from aiohttp.test_utils import TestServer


@pytest.fixture()
def discovery_payload() -> dict[str, Any]:
    """A miniature but faithful NXT 4.30 discovery payload."""
    return {
        "groups": [
            {
                "group": {"id": 0, "name": "No group"},
                "subjects": [
                    {
                        "name": "NXT Input 1",
                        "address": "0",
                        "channel": "0",
                        "type": "0",
                        "tags": "0.1",
                        "icons_id": "101",
                        "dimmable": None,
                        "device_info": None,
                        "settings": {"locks": [None, None], "readonly": None},
                    },
                ],
            },
            {
                "group": {"id": 1, "name": "Rez"},
                "subjects": [
                    {
                        "name": "Lampe Salon plafond",
                        "address": "2",
                        "channel": "0",
                        "type": "24",
                        "tags": "2.1",
                        "icons_id": "0",
                        "dimmable": True,
                        "device_info": None,
                        "settings": [],
                    },
                    {
                        "name": "Lampe ATELIER",
                        "address": "1",
                        "channel": "3",
                        "type": "8",
                        "tags": "1.4",
                        "icons_id": "0",
                        "dimmable": None,
                        "device_info": None,
                        "settings": [],
                    },
                ],
            },
            {
                "group": {"id": 2, "name": "Exterieur"},
                "subjects": [
                    # duplicate of Lampe ATELIER: groups overlap
                    {
                        "name": "Lampe ATELIER",
                        "address": "1",
                        "channel": "3",
                        "type": "8",
                        "tags": "1.4",
                        "icons_id": "0",
                        "dimmable": None,
                        "device_info": None,
                        "settings": [],
                    },
                ],
            },
            {
                "group": {"id": 3, "name": "Automations"},
                "subjects": [
                    # virtual: ints not strings, settings dict
                    {
                        "name": "Simulation de présence",
                        "address": 202,
                        "channel": "3",
                        "type": 202,
                        "tags": "202.3",
                        "icons_id": 202,
                        "dimmable": False,
                        "device_info": None,
                        "settings": {"readonly": "0", "pincode": ""},
                    },
                ],
            },
        ],
        "icons": {"0": {"name": "light", "type": "output", "allow": None}},
        "temp_calendars": [],
        "audio_sources": {"1": None},
        "ventilation_modes": [],
        "unknown_future_field": {"x": 1},
    }


# ---------------------------------------------------------------------------
# Fake NXT server (REST + WebSocket) for network tests
# ---------------------------------------------------------------------------


@dataclass
class FakeNxt:
    """Handle on the fake NXT: address, spies, and websocket controls."""

    host: str
    session: ClientSession
    discovery: dict[str, Any]
    actions: list[dict[str, Any]] = field(default_factory=list)
    status_bodies: list[dict[str, Any]] = field(default_factory=list)
    ws_messages: list[str] = field(default_factory=list)
    ws_connections: int = 0
    reject_auth: bool = False
    ws_close_after_send: bool = False


@pytest.fixture()
async def fake_nxt(discovery_payload: dict[str, Any]) -> AsyncIterator[FakeNxt]:
    """Spin up a fake NXT; yields host, a client session, and spies."""
    nxt = FakeNxt(host="", session=None, discovery=discovery_payload)  # type: ignore[arg-type]

    def _check_auth(request: web.Request) -> web.Response | None:
        auth = request.headers.get("Authorization", "")
        if nxt.reject_auth or not auth.startswith("Bearer ey"):
            return web.Response(status=401)
        return None

    async def h_jwtsecret(request: web.Request) -> web.Response:
        return web.json_response({"jwt_secret": "s3cret-from-pairing"})

    async def h_discover(request: web.Request) -> web.Response:
        return _check_auth(request) or web.json_response(nxt.discovery)

    async def h_status(request: web.Request) -> web.Response:
        nxt.status_bodies.append(await request.json())
        return _check_auth(request) or web.json_response({"status": {"1": [0, 1]}})

    async def h_action(request: web.Request) -> web.Response:
        nxt.actions.append(await request.json())
        return _check_auth(request) or web.json_response({})

    async def h_boom(request: web.Request) -> web.Response:
        return web.Response(status=500)

    async def h_ws(request: web.Request) -> web.WebSocketResponse:
        ws = web.WebSocketResponse(protocols=("wamp",))
        await ws.prepare(request)
        nxt.ws_connections += 1
        for message in nxt.ws_messages:
            await ws.send_str(message)
        if nxt.ws_close_after_send:
            await ws.close()
            return ws
        # stay open until the client disconnects
        async for msg in ws:
            if msg.type == WSMsgType.CLOSE:
                break
        return ws

    app = web.Application()
    app.router.add_get("/api/local/jwtsecret", h_jwtsecret)
    app.router.add_get("/api/local/discover", h_discover)
    app.router.add_get("/api/local/status", h_status)
    app.router.add_post("/api/local/action", h_action)
    app.router.add_get("/api/local/boom", h_boom)
    app.router.add_get("/sockets/api", h_ws)

    server = TestServer(app)
    await server.start_server()
    async with ClientSession() as session:
        nxt.host = f"{server.host}:{server.port}"
        nxt.session = session
        yield nxt
    await server.close()
