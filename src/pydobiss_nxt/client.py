"""Async REST client for the DOBISS NXT local API.

Design notes:

* The :class:`aiohttp.ClientSession` is **injected, never owned**: in
  Home Assistant the session is shared across integrations, so this
  library must not create or close it.
* Every network/HTTP failure is translated into the library's exception
  hierarchy — callers never see raw ``aiohttp`` errors.
* Endpoint quirk: ``GET /status`` takes a JSON *body* (non-standard but
  that is what the NXT expects).
"""

from __future__ import annotations

from typing import Any

from aiohttp import ClientError, ClientSession

from .auth import DobissAuth
from .const import DELAY_MAX, Action
from .exceptions import DobissApiError, DobissAuthError, DobissConnectionError
from .models import DiscoveryResponse


def _encode_delay(seconds: int) -> dict[str, int | str]:
    """Encode a delay in the NXT wire format.

    Up to 120 s it is sent in seconds; above, converted to minutes and
    capped at 120 min (the maximum the NXT accepts).
    """
    if seconds <= DELAY_MAX:
        return {"value": seconds, "unit": "s"}
    return {"value": min(round(seconds / 60), DELAY_MAX), "unit": "min"}


class DobissClient:
    """Client for the NXT REST endpoints (``discover``/``status``/``action``)."""

    def __init__(self, auth: DobissAuth, session: ClientSession) -> None:
        self._auth = auth
        self._session = session

    async def _request(
        self, method: str, endpoint: str, json: dict[str, Any] | None = None
    ) -> Any:
        """Perform one authenticated request and translate failures."""
        url = self._auth.base_url + endpoint
        try:
            async with self._session.request(
                method, url, headers=self._auth.headers, json=json
            ) as response:
                if response.status in (401, 403):
                    raise DobissAuthError(
                        f"NXT rejected our token (HTTP {response.status})"
                    )
                if response.status >= 400:
                    raise DobissApiError(
                        f"NXT error on {endpoint}", status=response.status
                    )
                if response.content_type == "application/json":
                    return await response.json()
                return await response.text()
        except ClientError as err:
            raise DobissConnectionError(f"Cannot reach NXT: {err}") from err

    async def discover(self) -> DiscoveryResponse:
        """Fetch and parse the full installation topology."""
        raw = await self._request("GET", "discover")
        return DiscoveryResponse.model_validate(raw)

    async def get_status(
        self, address: int | None = None, channel: int | None = None
    ) -> Any:
        """Fetch live status — of everything, one module, or one output."""
        payload: dict[str, Any] = {}
        if address is not None:
            payload["address"] = address
        if channel is not None:
            payload["channel"] = channel
        return await self._request("GET", "status", json=payload)

    async def action(
        self,
        address: int,
        channel: int,
        action: Action | int,
        *,
        option1: int | None = None,
        option2: int | None = None,
        delayon: int | None = None,
        delayoff: int | None = None,
    ) -> None:
        """Send one action to an output (see :class:`~.const.Action`)."""
        payload: dict[str, Any] = {
            "address": address,
            "channel": channel,
            "action": int(action),
        }
        if option1 is not None:
            payload["option1"] = option1
        if option2 is not None:
            payload["option2"] = option2
        if delayon is not None:
            payload["delayon"] = _encode_delay(delayon)
        if delayoff is not None:
            payload["delayoff"] = _encode_delay(delayoff)
        await self._request("POST", "action", json=payload)

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    async def turn_on(
        self, address: int, channel: int, *, brightness: int | None = None
    ) -> None:
        """Turn an output on, optionally dimmed (0-100)."""
        await self.action(address, channel, Action.ON, option1=brightness)

    async def turn_off(self, address: int, channel: int) -> None:
        """Turn an output off."""
        await self.action(address, channel, Action.OFF)

    async def toggle(self, address: int, channel: int) -> None:
        """Toggle an output."""
        await self.action(address, channel, Action.TOGGLE)
