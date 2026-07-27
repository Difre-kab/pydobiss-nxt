"""pydobiss-nxt: async Python client for the DOBISS NXT home automation server."""

from .auth import DobissAuth, fetch_secret
from .client import DobissClient
from .const import Action, IconId, ModuleType
from .exceptions import (
    DobissApiError,
    DobissAuthError,
    DobissConnectionError,
    DobissError,
)
from .models import DiscoveryResponse, DobissGroup, DobissSubject, TempCalendar
from .status import StateTracker, parse_status_update
from .websocket import DobissWebSocket

__version__ = "0.1.0"

__all__ = [
    "Action",
    "DiscoveryResponse",
    "DobissApiError",
    "DobissAuth",
    "DobissAuthError",
    "DobissClient",
    "DobissConnectionError",
    "DobissError",
    "DobissGroup",
    "DobissSubject",
    "DobissWebSocket",
    "IconId",
    "ModuleType",
    "StateTracker",
    "TempCalendar",
    "fetch_secret",
    "parse_status_update",
]
