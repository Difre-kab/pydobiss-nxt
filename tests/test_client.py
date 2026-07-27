"""Tests for pydobiss_nxt.client — wire payloads and error translation."""

import pytest

from pydobiss_nxt.auth import DobissAuth
from pydobiss_nxt.client import DobissClient, _encode_delay
from pydobiss_nxt.const import Action, ModuleType
from pydobiss_nxt.exceptions import (
    DobissApiError,
    DobissAuthError,
    DobissConnectionError,
)
from tests.conftest import FakeNxt

SECRET = "x" * 40


def _client(nxt: FakeNxt) -> DobissClient:
    return DobissClient(DobissAuth(nxt.host, SECRET), nxt.session)


def test_encode_delay() -> None:
    assert _encode_delay(45) == {"value": 45, "unit": "s"}
    assert _encode_delay(120) == {"value": 120, "unit": "s"}
    assert _encode_delay(300) == {"value": 5, "unit": "min"}
    assert _encode_delay(999_999) == {"value": 120, "unit": "min"}  # capped


async def test_discover_parses_models(fake_nxt: FakeNxt) -> None:
    d = await _client(fake_nxt).discover()
    salon = next(s for s in d.all_subjects() if s.key == "2_0")
    assert salon.type is ModuleType.ANALOG
    assert salon.dimmable is True


async def test_action_wire_payload(fake_nxt: FakeNxt) -> None:
    client = _client(fake_nxt)
    await client.turn_on(1, 0, brightness=60)
    assert fake_nxt.actions[-1] == {
        "address": 1,
        "channel": 0,
        "action": 1,
        "option1": 60,
    }
    await client.toggle(2, 3)
    assert fake_nxt.actions[-1] == {"address": 2, "channel": 3, "action": 2}
    await client.action(1, 0, Action.OFF, delayoff=300)
    assert fake_nxt.actions[-1]["delayoff"] == {"value": 5, "unit": "min"}


async def test_status_sends_json_body_on_get(fake_nxt: FakeNxt) -> None:
    """NXT quirk: GET /status takes a JSON body."""
    await _client(fake_nxt).get_status(address=1, channel=0)
    assert fake_nxt.status_bodies[-1] == {"address": 1, "channel": 0}


async def test_401_raises_auth_error(fake_nxt: FakeNxt) -> None:
    fake_nxt.reject_auth = True
    with pytest.raises(DobissAuthError):
        await _client(fake_nxt).discover()


async def test_500_raises_api_error_with_status(fake_nxt: FakeNxt) -> None:
    client = _client(fake_nxt)
    with pytest.raises(DobissApiError) as excinfo:
        await client._request("GET", "boom")
    assert excinfo.value.status == 500


async def test_unreachable_raises_connection_error(fake_nxt: FakeNxt) -> None:
    client = DobissClient(DobissAuth("127.0.0.1:9", SECRET), fake_nxt.session)
    with pytest.raises(DobissConnectionError):
        await client.discover()
