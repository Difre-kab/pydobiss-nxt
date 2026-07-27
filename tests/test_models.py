"""Tests for pydobiss_nxt.models — each 4.30 quirk pinned by a test."""

from typing import Any

from pydobiss_nxt.const import IconId, ModuleType
from pydobiss_nxt.models import DiscoveryResponse, DobissSubject


def test_full_payload_parses(discovery_payload: dict[str, Any]) -> None:
    d = DiscoveryResponse.model_validate(discovery_payload)
    assert len(d.groups) == 4
    assert len(d.all_subjects()) == 5


def test_string_numbers_are_coerced(discovery_payload: dict[str, Any]) -> None:
    d = DiscoveryResponse.model_validate(discovery_payload)
    salon = next(s for s in d.all_subjects() if s.name == "Lampe Salon plafond")
    assert salon.address == 2
    assert salon.channel == 0
    assert salon.key == "2_0"


def test_null_dimmable_means_false(discovery_payload: dict[str, Any]) -> None:
    d = DiscoveryResponse.model_validate(discovery_payload)
    atelier = next(s for s in d.all_subjects() if s.name == "Lampe ATELIER")
    assert atelier.dimmable is False
    salon = next(s for s in d.all_subjects() if s.name == "Lampe Salon plafond")
    assert salon.dimmable is True


def test_types_resolve_to_enums_for_str_and_int(
    discovery_payload: dict[str, Any],
) -> None:
    """NXT sends "8" (str) for physical, 202 (int) for virtual outputs."""
    d = DiscoveryResponse.model_validate(discovery_payload)
    salon = next(s for s in d.all_subjects() if s.name == "Lampe Salon plafond")
    assert salon.type is ModuleType.ANALOG
    assert salon.icons_id is IconId.LIGHT
    auto = next(s for s in d.all_subjects() if s.address == 202)
    assert auto.type is ModuleType.AUTOMATION
    assert auto.icons_id is IconId.AUTOMATION


def test_unknown_type_falls_back_to_int() -> None:
    """A future firmware type must not break discovery."""
    s = DobissSubject.model_validate(
        {
            "name": "Future",
            "address": "9",
            "channel": "0",
            "type": "99",
            "icons_id": "77",
            "dimmable": None,
        }
    )
    assert s.type == 99
    assert s.icons_id == 77


def test_settings_empty_list_becomes_dict(discovery_payload: dict[str, Any]) -> None:
    d = DiscoveryResponse.model_validate(discovery_payload)
    salon = next(s for s in d.all_subjects() if s.name == "Lampe Salon plafond")
    assert salon.settings == {}
    auto = next(s for s in d.all_subjects() if s.address == 202)
    assert auto.settings["readonly"] == "0"


def test_unique_subjects_deduplicates_overlapping_groups(
    discovery_payload: dict[str, Any],
) -> None:
    d = DiscoveryResponse.model_validate(discovery_payload)
    assert len(d.all_subjects()) == 5
    uniq = d.unique_subjects()
    assert len(uniq) == 4
    assert len({s.key for s in uniq}) == 4


def test_is_virtual(discovery_payload: dict[str, Any]) -> None:
    d = DiscoveryResponse.model_validate(discovery_payload)
    auto = next(s for s in d.all_subjects() if s.address == 202)
    salon = next(s for s in d.all_subjects() if s.address == 2)
    assert auto.is_virtual is True
    assert salon.is_virtual is False


def test_extra_fields_are_preserved(discovery_payload: dict[str, Any]) -> None:
    """Unknown keys must survive for HA diagnostics."""
    d = DiscoveryResponse.model_validate(discovery_payload)
    assert d.model_extra is not None
    assert d.model_extra["unknown_future_field"] == {"x": 1}
    inp = next(s for s in d.all_subjects() if s.name == "NXT Input 1")
    assert inp.tags == "0.1"
