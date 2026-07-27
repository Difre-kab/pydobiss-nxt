"""Tests for pydobiss_nxt.auth — token lifecycle and pairing."""

import jwt as pyjwt
import pytest

from pydobiss_nxt.auth import DobissAuth, fetch_secret
from pydobiss_nxt.exceptions import DobissAuthError, DobissConnectionError
from tests.conftest import FakeNxt

SECRET = "x" * 40


def test_urls_http_and_ws() -> None:
    auth = DobissAuth("nxt.local", SECRET)
    assert auth.base_url == "http://nxt.local/api/local/"
    assert auth.ws_url == "ws://nxt.local/sockets/api"


def test_urls_secure() -> None:
    auth = DobissAuth("nxt.local", SECRET, secure=True)
    assert auth.base_url == "https://nxt.local/api/local/"
    assert auth.ws_url == "wss://nxt.local/sockets/api"


def test_token_is_valid_hs256_and_cached() -> None:
    auth = DobissAuth("nxt.local", SECRET)
    t1 = auth.token
    assert t1 == auth.token  # cached between calls
    decoded = pyjwt.decode(t1, SECRET, algorithms=["HS256"])
    assert decoded == {"name": "pydobiss-nxt"}
    header = pyjwt.get_unverified_header(t1)
    assert header["expiresIn"] == "24h"  # NXT protocol quirk


def test_invalidate_forces_new_token() -> None:
    auth = DobissAuth("nxt.local", SECRET)
    t1 = auth.token
    auth.invalidate()
    assert auth.token  # a token is produced again
    assert auth.headers["Authorization"].startswith("Bearer ")
    assert t1 is not None


async def test_fetch_secret_pairing(fake_nxt: FakeNxt) -> None:
    secret = await fetch_secret(fake_nxt.session, fake_nxt.host)
    assert secret == "s3cret-from-pairing"


async def test_fetch_secret_unreachable() -> None:
    from aiohttp import ClientSession

    async with ClientSession() as session:
        with pytest.raises(DobissConnectionError):
            await fetch_secret(session, "127.0.0.1:9")


async def test_fetch_secret_refused(fake_nxt: FakeNxt) -> None:
    """A non-200 answer must raise DobissAuthError (pairing mode off)."""
    # /api/local/boom answers 500 — simulate by pointing at a wrong path
    # through a small monkeypatch of the URL builder is overkill; instead
    # reuse the boom route via a direct call on a purpose-built host.
    from aiohttp import web
    from aiohttp.test_utils import TestServer

    app = web.Application()

    async def refuse(request: web.Request) -> web.Response:
        return web.Response(status=403)

    app.router.add_get("/api/local/jwtsecret", refuse)
    server = TestServer(app)
    await server.start_server()
    try:
        with pytest.raises(DobissAuthError):
            await fetch_secret(fake_nxt.session, f"{server.host}:{server.port}")
    finally:
        await server.close()
