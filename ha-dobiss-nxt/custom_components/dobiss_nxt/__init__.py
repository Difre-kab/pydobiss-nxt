"""The DOBISS NXT integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from pydobiss_nxt import (
    DobissAuth,
    DobissAuthError,
    DobissClient,
    DobissConnectionError,
)

from .const import CONF_SECRET

# Entity platforms will be added here step by step (light first).
PLATFORMS: list[Platform] = []

type DobissConfigEntry = ConfigEntry[DobissClient]


async def async_setup_entry(hass: HomeAssistant, entry: DobissConfigEntry) -> bool:
    """Set up DOBISS NXT from a config entry."""
    auth = DobissAuth(entry.data[CONF_HOST], entry.data[CONF_SECRET])
    client = DobissClient(auth, async_get_clientsession(hass))

    try:
        await client.discover()
    except DobissAuthError as err:
        raise ConfigEntryAuthFailed("NXT rejected the API secret") from err
    except DobissConnectionError as err:
        raise ConfigEntryNotReady(f"Cannot reach the NXT server: {err}") from err

    entry.runtime_data = client
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: DobissConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
