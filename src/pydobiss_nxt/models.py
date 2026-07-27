"""Typed models for the DOBISS NXT API payloads.

Built with Pydantic v2. Field names mirror the raw JSON keys of the NXT
API so payloads can be parsed without alias gymnastics; snake_case
properties expose cleaner accessors where the raw name is awkward.

The models are deliberately *tolerant*:

* unknown ``type`` / ``icons_id`` values fall back to plain ``int``
  instead of failing validation (new DOBISS firmware must not break us);
* unknown extra JSON keys are preserved (``extra="allow"``) so they can
  be surfaced verbatim in Home Assistant diagnostics later.
"""

from pydantic import BaseModel, ConfigDict, field_validator

from .const import IconId, ModuleType


class DobissSubject(BaseModel):
    """A single output/subject as returned by the discovery endpoint.

    "Subject" is DOBISS wording: one controllable channel of a module —
    a light, a socket, one direction of a cover, a scenario slot, ...
    """

    model_config = ConfigDict(extra="allow")

    name: str
    address: int
    channel: int
    dimmable: bool
    type: ModuleType | int
    icons_id: IconId | int

    @field_validator("dimmable", mode="before")
    @classmethod
    def _null_means_not_dimmable(cls, value: object) -> object:
        """NXT firmware (seen on 4.30) sends ``null`` for non-dimmable outputs."""
        return False if value is None else value

    @property
    def key(self) -> str:
        """Stable unique identifier of this output: ``address_channel``."""
        return f"{self.address}_{self.channel}"

    @property
    def is_virtual(self) -> bool:
        """True for NXT-hosted outputs (scenarios, logic, thermostat...)."""
        return self.address > 200


class DobissGroupInfo(BaseModel):
    """Metadata of a group (a room or zone defined in the DOBISS config)."""

    model_config = ConfigDict(extra="allow")

    id: int
    name: str | None = None


class DobissGroup(BaseModel):
    """A group with its outputs."""

    model_config = ConfigDict(extra="allow")

    group: DobissGroupInfo
    subjects: list[DobissSubject]


class TempCalendar(BaseModel):
    """A thermostat calendar/preset defined on the NXT."""

    model_config = ConfigDict(extra="allow")

    id: int
    name: str


class DiscoveryResponse(BaseModel):
    """Full payload of the discovery endpoint."""

    model_config = ConfigDict(extra="allow")

    groups: list[DobissGroup]
    temp_calendars: list[TempCalendar] = []

    def all_subjects(self) -> list[DobissSubject]:
        """Flatten every output of every group into a single list."""
        return [s for g in self.groups for s in g.subjects]
