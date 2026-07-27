"""Tests for pydobiss_nxt.websocket — protocol, lifecycle, reconnect."""

import asyncio
import json
from typing import Any

from pydobiss_nxt.auth import DobissAuth
from pydobiss_nxt.websocket import DobissWebSocket, _normalize
from tests.conftest import FakeNxt

SECRET = "x" * 40


def test_normalize_shapes() -> None:
    assert _normalize({"1": [0, 1]}) == {"1": [0, 1]}
    assert _normalize([{"5": 1}]) == {"0": {"5": 1}}  # bare-list quirk
    assert _normalize([1, 2, 3]) is None
    assert _normalize("junk") is None


async def _collect(nxt: FakeNxt, duration: float) -> list[dict[str, Any]]:
    received: list[dict[str, Any]] = []
    ws = DobissWebSocket(DobissAuth(nxt.host, SECRET), nxt.session)
    ws.start(received.append)
    await asyncio.sleep(duration)
    assert ws.running
    await ws.stop()
    assert not ws.running
    return received


async def test_receives_and_normalizes(fake_nxt: FakeNxt) -> None:
    fake_nxt.ws_messages = [
        json.dumps({"2": [85, 0]}),
        json.dumps([{"5": {"status": 1}}]),  # bare-list quirk
        "not json at all",  # must be ignored, not fatal
        json.dumps({"202": {"1": "0"}}),
    ]
    received = await _collect(fake_nxt, 0.4)
    assert received == [
        {"2": [85, 0]},
        {"0": {"5": {"status": 1}}},
        {"202": {"1": "0"}},
    ]


async def test_start_is_idempotent(fake_nxt: FakeNxt) -> None:
    ws = DobissWebSocket(DobissAuth(fake_nxt.host, SECRET), fake_nxt.session)
    ws.start(lambda _u: None)
    task = ws._task
    ws.start(lambda _u: None)  # second start must not spawn a new task
    assert ws._task is task
    await ws.stop()


async def test_async_callback_is_awaited(fake_nxt: FakeNxt) -> None:
    fake_nxt.ws_messages = [json.dumps({"1": [1]})]
    received: list[dict[str, Any]] = []

    async def callback(update: dict[str, Any]) -> None:
        await asyncio.sleep(0)
        received.append(update)

    ws = DobissWebSocket(DobissAuth(fake_nxt.host, SECRET), fake_nxt.session)
    ws.start(callback)
    await asyncio.sleep(0.4)
    await ws.stop()
    assert received == [{"1": [1]}]


async def test_reconnects_after_server_close(fake_nxt: FakeNxt) -> None:
    """The fake server closes after sending; listener must come back."""
    fake_nxt.ws_messages = [json.dumps({"1": [1]})]
    fake_nxt.ws_close_after_send = True
    ws = DobissWebSocket(DobissAuth(fake_nxt.host, SECRET), fake_nxt.session)
    ws.start(lambda _u: None)
    # backoff starts at 1 s: after ~2.5 s we must have connected at least twice
    await asyncio.sleep(2.5)
    await ws.stop()
    assert fake_nxt.ws_connections >= 2
