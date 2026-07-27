"""Constants for the DOBISS NXT API.

Values transcribed from the official DOBISS NXT local API documentation
(Dutch: "lijst van acties" / module type table) and cross-checked against
real-world payloads.
"""

from enum import IntEnum

# ---------------------------------------------------------------------------
# Module / output types  →  field ``type`` in the discovery payload
# ---------------------------------------------------------------------------


class ModuleType(IntEnum):
    """Hardware or virtual module type of an output.

    Values 0-24 are physical CAN modules; values >= 200 are virtual
    outputs handled by the NXT server itself (scenarios, logic, ...).
    """

    NXT = 0  # The NXT server itself
    INPUT = 1  # Push-button / input module
    DALI = 4  # DALI lighting module
    RELAY = 8  # Relay module (on/off outputs)
    DIMMER = 16  # Dimmer module
    ANALOG = 24  # 0-10 V analog output module

    # Virtual NXT outputs (address > 200)
    SCENARIO = 201
    AUTOMATION = 202
    CONDITION = 203  # Logical condition
    TEMPERATURE = 204  # Thermostat zone
    AUDIO = 205
    FLAG = 206  # Internal boolean flag


# ---------------------------------------------------------------------------
# Icon IDs  →  field ``icons_id`` in the discovery payload
# ---------------------------------------------------------------------------


class IconId(IntEnum):
    """Icon chosen in the DOBISS configuration.

    The icon is more than cosmetic: it is the only reliable way to tell
    what an output really controls (a relay channel can be a light, a
    socket, half of a cover pair, ...).
    """

    LIGHT = 0
    PLUG = 1
    VENTILATION = 2
    UP = 3  # Cover: up direction (paired with DOWN "buddy")
    DOWN = 4  # Cover: down direction (paired with UP "buddy")
    HEATING = 5
    TABLE_LIGHT = 6
    DOOR = 7
    GARAGE = 8
    GATE = 9
    RED = 10
    GREEN = 11
    BLUE = 12
    WHITE = 13
    INPUT_STATUS = 100
    LIGHT_SENSOR = 101
    SCENARIO = 201
    AUTOMATION = 202
    CONDITION = 203
    TEMPERATURE = 204
    AUDIO = 205
    FLAG = 206


# ---------------------------------------------------------------------------
# Actions  →  field ``action`` of POST /action
# ---------------------------------------------------------------------------


class Action(IntEnum):
    """Action IDs accepted by the ``POST /action`` endpoint."""

    OFF = 0
    ON = 1
    TOGGLE = 2
    SET_CALENDAR = 110  # Thermostat: activate a temperature calendar/preset


# ---------------------------------------------------------------------------
# Special protocol values
# ---------------------------------------------------------------------------

#: ``option1`` value that marks an ON request as triggered by a PIR sensor.
BRIGHTNESS_FROM_PIR: int = 9

#: Thermostat ``option2``: hold the setpoint indefinitely.
TEMP_TIME_FOREVER: int = 0xFE

#: Thermostat time unit: periods are expressed in quarters of an hour.
TEMP_TIME_QUARTER_MINUTES: int = 15

#: Maximum value (seconds or minutes) accepted by ``delayon``/``delayoff``.
DELAY_MAX: int = 120
