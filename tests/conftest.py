"""Shared fixtures for the pydobiss-nxt test suite.

The sample payload reproduces every real-world quirk observed on NXT
firmware 4.30 (see models.py docstring): string/int numbers, null
dimmable, settings as empty list, overlapping groups.
"""

from typing import Any

import pytest


@pytest.fixture()
def discovery_payload() -> dict[str, Any]:
    """A miniature but faithful NXT 4.30 discovery payload."""
    return {
        "groups": [
            {
                "group": {"id": 0, "name": "No group"},
                "subjects": [
                    {
                        "name": "NXT Input 1",
                        "address": "0",
                        "channel": "0",
                        "type": "0",
                        "tags": "0.1",
                        "icons_id": "101",
                        "dimmable": None,
                        "device_info": None,
                        "settings": {"locks": [None, None], "readonly": None},
                    },
                ],
            },
            {
                "group": {"id": 1, "name": "Rez"},
                "subjects": [
                    {
                        "name": "Lampe Salon plafond",
                        "address": "2",
                        "channel": "0",
                        "type": "24",
                        "tags": "2.1",
                        "icons_id": "0",
                        "dimmable": True,
                        "device_info": None,
                        "settings": [],
                    },
                    {
                        "name": "Lampe ATELIER",
                        "address": "1",
                        "channel": "3",
                        "type": "8",
                        "tags": "1.4",
                        "icons_id": "0",
                        "dimmable": None,
                        "device_info": None,
                        "settings": [],
                    },
                ],
            },
            {
                "group": {"id": 2, "name": "Exterieur"},
                "subjects": [
                    # duplicate of Lampe ATELIER: groups overlap
                    {
                        "name": "Lampe ATELIER",
                        "address": "1",
                        "channel": "3",
                        "type": "8",
                        "tags": "1.4",
                        "icons_id": "0",
                        "dimmable": None,
                        "device_info": None,
                        "settings": [],
                    },
                ],
            },
            {
                "group": {"id": 3, "name": "Automations"},
                "subjects": [
                    # virtual: ints not strings, settings dict
                    {
                        "name": "Simulation de présence",
                        "address": 202,
                        "channel": "3",
                        "type": 202,
                        "tags": "202.3",
                        "icons_id": 202,
                        "dimmable": False,
                        "device_info": None,
                        "settings": {"readonly": "0", "pincode": ""},
                    },
                ],
            },
        ],
        "icons": {"0": {"name": "light", "type": "output", "allow": None}},
        "temp_calendars": [],
        "audio_sources": {"1": None},
        "ventilation_modes": [],
        "unknown_future_field": {"x": 1},
    }
