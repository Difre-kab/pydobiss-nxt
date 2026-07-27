"""Typed models for the DOBISS NXT API payloads.

Built with Pydantic v2 and validated against a real NXT firmware 4.30
discovery payload. Quirks handled (all observed in the wild):

* numbers arrive sometimes as strings ("8"), sometimes as ints (202);
* ``dimmable`` is ``null`` for non-dimmable outputs;
* ``settings`` is a dict — or an empty *list* when empty (PHP-ism);
* unknown ``type``/``icons_id`` values fall back to plain ``int``;
* unknown extra JSON keys are preserved (``extra="allow"``) for
  Home Assistant diagnostics.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator

from .const import IconId, ModuleType


class DobissSubject(BaseModel):
    """A single output/subject as returned by the discovery endpoint."""

    model_config = ConfigDict(extra="allow")

    name: str
    address: int
    channel: int
    dimmable: bool
    type: ModuleType | int
    icons_id: IconId | int
    tags: str | None = None
    device_info: dict[str, Any] | None = None
    settings: dict[str, Any] = {}

    @field_validator("dimmable", mode="before")
    @classmethod
    def _null_means_not_dimmable(cls, value: object) -> object:
        """NXT (seen on 4.30) sends ``null`` for non-dimmable outputs."""
        return False if value is None else value

    @field_validator("type", mode="before")
    @classmethod
    def _coerce_module_type(cls, value: object) -> object:
        """Prefer the enum: NXT sends "8" (str) or 202 (int) inconsistently."""
        try:
            return ModuleType(int(value))  # type: ignore[call-overload]
        except (ValueError, TypeError):
            return value

    @field_validator("icons_id", mode="before")
    @classmethod
    def _coerce_icon_id(cls, value: object) -> object:
        try:
            return IconId(int(value))  # type: ignore[call-overload]
        except (ValueError, TypeError):
            return value

    @field_validator("settings", mode="before")
    @classmethod
    def _empty_list_is_empty_dict(cls, value: object) -> object:
        """NXT serialises an empty settings dict as ``[]``."""
        return {} if value == [] else value

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


class IconInfo(BaseModel):
    """One entry of the icon catalog sent at the root of discovery."""

    model_config = ConfigDict(extra="allow")

    name: str
    type: str | None = None


class DiscoveryResponse(BaseModel):
    """Full payload of the discovery endpoint."""

    model_config = ConfigDict(extra="allow")

    groups: list[DobissGroup]
    temp_calendars: list[TempCalendar] = []
    icons: dict[str, IconInfo] = {}
    audio_sources: dict[str, Any] = {}
    ventilation_modes: list[Any] = []

    def all_subjects(self) -> list[DobissSubject]:
        """Flatten every output of every group into a single list."""
        return [s for g in self.groups for s in g.subjects]

    def unique_subjects(self) -> list[DobissSubject]:
        """Like :meth:`all_subjects` but deduplicated by :attr:`key`.

        DOBISS groups may overlap (one output listed in several rooms);
        entity creation must use this view.
        """
        seen: set[str] = set()
        out: list[DobissSubject] = []
        for s in self.all_subjects():
            if s.key not in seen:
                seen.add(s.key)
                out.append(s)
        return out
