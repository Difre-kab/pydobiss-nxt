"""Unified status parsing for the DOBISS NXT.

The NXT reports state in three different shapes, all observed on real
firmware 4.30 websocket captures:

* **relay/dimmer modules** — a list, index = channel::

      "1": [0, 0, 1, ...]          # on/off
      "2": [85, 100, 0, ...]       # dim levels 0-100

* **the NXT module itself (and address 251)** — a dict of dicts::

      "0": {"13": {"status": 1}, ...}

* **virtual outputs (202, 206, 208...)** — a dict of *strings*::

      "202": {"1": "0", ...}

This module flattens them all into ``{"address_channel": int}`` — the
same keys as :attr:`~.models.DobissSubject.key`.
"""

from __future__ import annotations

import logging
from typing import Any

_LOGGER = logging.getLogger(__name__)


def _coerce_value(value: Any) -> int | None:
    """Extract an int state from any of the observed value shapes."""
    if isinstance(value, dict):  # {"status": 0}
        value = value.get("status")
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return round(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None


def parse_status_update(update: dict[str, Any]) -> dict[str, int]:
    """Flatten one status payload into ``{"address_channel": value}``.

    Unknown shapes are skipped with a debug log rather than raising:
    a stray field must never take the whole update down.
    """
    flat: dict[str, int] = {}
    for address, channels in update.items():
        if isinstance(channels, list):
            for channel, value in enumerate(channels):
                coerced = _coerce_value(value)
                if coerced is not None:
                    flat[f"{address}_{channel}"] = coerced
        elif isinstance(channels, dict):
            for channel, value in channels.items():
                coerced = _coerce_value(value)
                if coerced is not None:
                    flat[f"{address}_{channel}"] = coerced
        else:
            _LOGGER.debug("Unknown status shape for address %s: %r", address, channels)
    return flat


class StateTracker:
    """Cumulative state of the installation, fed by status updates.

    The NXT always pushes the *full* state of a module (never a delta),
    so applying an update is a plain merge — and the returned set of
    changed keys is what an update coordinator needs to know.
    """

    def __init__(self) -> None:
        self._state: dict[str, int] = {}

    @property
    def state(self) -> dict[str, int]:
        """Read-only view of the current known state."""
        return dict(self._state)

    def get(self, key: str) -> int | None:
        """Current value of one output (``"address_channel"``), if known."""
        return self._state.get(key)

    def apply(self, update: dict[str, Any]) -> set[str]:
        """Merge one raw status payload; return the keys that changed."""
        changed: set[str] = set()
        for key, value in parse_status_update(update).items():
            if self._state.get(key) != value:
                self._state[key] = value
                changed.add(key)
        return changed
