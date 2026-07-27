"""Real-time status updates over the NXT WebSocket.

The NXT pushes status updates on ``ws(s)://<host>/sockets/api`` using
the ``wamp`` subprotocol, authenticated with the same bearer token as
the REST API. Each message is a JSON object mapping module addresses to
per-channel values — the same shape as ``GET /status``.

Design notes:

* the ``aiohttp.ClientSession`` is injected, never owned (HA pattern);
* the listener reconnects forever with exponential backoff (1 s → 60 s),
  resetting after a successful connection;
* one known firmware quirk is normalised here: a bare one-element list
  instead of a dict (module 0 status, seen on NXT 3.20).
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from aiohttp import ClientError, ClientSession, WSMsgType

from .auth import DobissAuth
from .exceptions import DobissConnectionError

_LOGGER = logging.getLogger(__name__)

#: Callback invoked for every status update pushed by the NXT.
UpdateCallback = Callable[[dict[str, Any]], Awaitable[None] | None]

_BACKOFF_INITIAL = 1.0
_BACKOFF_MAX = 60.0


def _normalize(payload: Any) -> dict[str, Any] | None:
    """Turn a raw WS message into an address-keyed dict, or None to skip."""
    if isinstance(payload, dict):
        return payload
    if isinstance(payload, list) and len(payload) == 1:
        # NXT quirk: module-0 status arrives as a bare one-element list.
        return {"0": payload[0]}
    return None


class DobissWebSocket:
    """Listens to NXT push updates and forwards them to a callback."""

    def __init__(self, auth: DobissAuth, session: ClientSession) -> None:
        self._auth = auth
        self._session = session
        self._task: asyncio.Task[None] | None = None

    @property
    def running(self) -> bool:
        """True while the background listener task is active."""
        return self._task is not None and not self._task.done()

    def start(self, callback: UpdateCallback) -> None:
        """Start listening in a background task (idempotent)."""
        if self.running:
            return
        self._task = asyncio.get_running_loop().create_task(
            self._listen_forever(callback), name="pydobiss-nxt-ws"
        )

    async def stop(self) -> None:
        """Stop the background listener and wait for it to finish."""
        if self._task is None:
            return
        self._task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await self._task
        self._task = None

    async def _listen_forever(self, callback: UpdateCallback) -> None:
        backoff = _BACKOFF_INITIAL
        while True:
            try:
                await self._listen_once(callback)
                backoff = _BACKOFF_INITIAL  # clean close: retry quickly
            except asyncio.CancelledError:
                raise
            except (ClientError, DobissConnectionError, OSError) as err:
                _LOGGER.warning(
                    "NXT websocket lost (%s), reconnecting in %.0f s", err, backoff
                )
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, _BACKOFF_MAX)

    async def _listen_once(self, callback: UpdateCallback) -> None:
        """One connection lifecycle: connect, then consume until closed."""
        async with self._session.ws_connect(
            self._auth.ws_url, protocols=("wamp",), headers=self._auth.headers
        ) as ws:
            _LOGGER.debug("NXT websocket connected")
            async for msg in ws:
                if msg.type != WSMsgType.TEXT:
                    continue
                try:
                    update = _normalize(msg.json())
                except ValueError:
                    _LOGGER.debug("Ignoring non-JSON WS message: %r", msg.data)
                    continue
                if update is None:
                    continue
                result = callback(update)
                if asyncio.iscoroutine(result):
                    await result
