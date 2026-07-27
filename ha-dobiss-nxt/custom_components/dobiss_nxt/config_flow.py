"""Config flow for the DOBISS NXT integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from pydobiss_nxt import (
    DobissAuth,
    DobissAuthError,
    DobissClient,
    DobissConnectionError,
)

from .const import CONF_SECRET, DOMAIN

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_SECRET): str,
    }
)


class DobissNxtConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the initial configuration of a DOBISS NXT server."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """First (and for now only) step: host + API secret."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            secret = user_input[CONF_SECRET].strip()

            await self.async_set_unique_id(host)
            self._abort_if_unique_id_configured()

            session = async_get_clientsession(self.hass)
            client = DobissClient(DobissAuth(host, secret), session)
            try:
                discovery = await client.discover()
            except DobissAuthError:
                errors["base"] = "invalid_auth"
            except DobissConnectionError:
                errors["base"] = "cannot_connect"
            else:
                count = len(discovery.unique_subjects())
                return self.async_create_entry(
                    title=f"DOBISS NXT ({host})",
                    data={CONF_HOST: host, CONF_SECRET: secret},
                    description_placeholders={"count": str(count)},
                )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_SCHEMA, errors=errors
        )
