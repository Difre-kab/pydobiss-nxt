"""JWT authentication for the DOBISS NXT local API.

The NXT auth model is unusual: there is no login endpoint. Instead the
NXT exposes a shared *secret* (Global settings → API). The client signs
its **own** JWT with that secret (HS256); the server validates the
signature. Tokens are declared valid for 24 h, so we regenerate them
well before expiry.

The secret can be obtained in two ways:

* read manually by the user in the NXT web UI, or
* fetched over the network via ``GET /api/local/jwtsecret`` — only
  while the API pairing mode is enabled in the NXT UI (blue button).
"""

from __future__ import annotations

from datetime import datetime, timedelta

import jwt
from aiohttp import ClientError, ClientSession

from .exceptions import DobissAuthError, DobissConnectionError

#: Lifetime requested for each generated token.
TOKEN_VALIDITY = timedelta(hours=24)

#: Regenerate the token this long before its declared expiry.
TOKEN_REFRESH_MARGIN = timedelta(hours=4)


class DobissAuth:
    """Builds the NXT base URLs and produces fresh bearer tokens."""

    def __init__(self, host: str, secret: str, *, secure: bool = False) -> None:
        """:param host: hostname or IP of the NXT server.
        :param secret: the JWT secret from Global settings → API.
        :param secure: use HTTPS/WSS instead of HTTP/WS.
        """
        self._secret = secret
        scheme = "https" if secure else "http"
        ws_scheme = "wss" if secure else "ws"
        self.base_url = f"{scheme}://{host}/api/local/"
        self.ws_url = f"{ws_scheme}://{host}/sockets/api"
        self._token = ""
        self._expires_at = datetime.min

    @property
    def token(self) -> str:
        """A valid bearer token, regenerated automatically near expiry."""
        if datetime.now() + TOKEN_REFRESH_MARGIN >= self._expires_at:
            self._token = jwt.encode(
                {"name": "pydobiss-nxt"},
                self._secret,
                algorithm="HS256",
                headers={"expiresIn": "24h"},
            )
            self._expires_at = datetime.now() + TOKEN_VALIDITY
        return self._token

    @property
    def headers(self) -> dict[str, str]:
        """Ready-to-use HTTP headers with the bearer token."""
        return {"Authorization": f"Bearer {self.token}"}

    def invalidate(self) -> None:
        """Force regeneration of the token on next access."""
        self._token = ""
        self._expires_at = datetime.min


async def fetch_secret(
    session: ClientSession, host: str, *, secure: bool = False
) -> str:
    """Fetch the JWT secret from the NXT (API pairing mode must be ON).

    :raises DobissAuthError: the NXT refused (pairing mode disabled).
    :raises DobissConnectionError: the NXT could not be reached.
    """
    scheme = "https" if secure else "http"
    url = f"{scheme}://{host}/api/local/jwtsecret"
    try:
        async with session.get(url) as response:
            if response.status != 200:
                raise DobissAuthError(
                    f"NXT refused to hand out the secret (HTTP {response.status})."
                    " Enable API pairing mode in Global settings → API."
                )
            data: dict[str, str] = await response.json()
    except ClientError as err:
        raise DobissConnectionError(f"Cannot reach NXT at {host}: {err}") from err
    try:
        return data["jwt_secret"]
    except KeyError as err:
        raise DobissAuthError("Unexpected /jwtsecret payload") from err
