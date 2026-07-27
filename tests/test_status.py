"""Tests for pydobiss_nxt.status — the three wire formats, pinned.

The payloads below are lifted from real websocket captures on NXT 4.30.
"""

from typing import Any

from pydobiss_nxt.status import StateTracker, parse_status_update

REAL_INITIAL: dict[str, Any] = {
    "1": [0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0],
    "2": [0, 0, 0, 100, 0, 0, 0, 0],
    "0": {"13": {"status": 1}, "16": {"status": 1}, "17": {"status": 0}},
    "202": {"1": "0", "2": "0"},
    "206": {"1": "0"},
    "251": {"1": {"status": 0}},
}


def test_list_format_relay_and_dimmer() -> None:
    flat = parse_status_update({"1": [0, 1], "2": [85, 0]})
    assert flat == {"1_0": 0, "1_1": 1, "2_0": 85, "2_1": 0}


def test_dict_of_status_format() -> None:
    flat = parse_status_update({"0": {"13": {"status": 1}, "17": {"status": 0}}})
    assert flat == {"0_13": 1, "0_17": 0}


def test_dict_of_strings_format() -> None:
    flat = parse_status_update({"202": {"1": "0", "3": "1"}})
    assert flat == {"202_1": 0, "202_3": 1}


def test_mixed_real_payload() -> None:
    flat = parse_status_update(REAL_INITIAL)
    assert flat["1_7"] == 1  # LeDs escalier on
    assert flat["2_3"] == 100  # applique RDC at 100%
    assert flat["0_13"] == 1  # boiler plug on
    assert flat["202_1"] == 0
    assert flat["251_1"] == 0


def test_unknown_shapes_are_skipped_not_fatal() -> None:
    flat = parse_status_update({"1": [0, 1], "weird": "???", "x": 3.7})
    assert flat == {"1_0": 0, "1_1": 1}


def test_tracker_reports_only_changes() -> None:
    t = StateTracker()
    first = t.apply(REAL_INITIAL)
    assert "1_7" in first and "2_3" in first  # everything is new

    # detector switches staircase LEDs off: full module state re-sent
    changed = t.apply({"1": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]})
    assert changed == {"1_7"}
    assert t.get("1_7") == 0

    # periodic automation refresh with no actual change
    assert t.apply({"202": {"1": "0", "2": "0"}}) == set()


def test_tracker_state_is_a_copy() -> None:
    t = StateTracker()
    t.apply({"1": [1]})
    snapshot = t.state
    snapshot["1_0"] = 99
    assert t.get("1_0") == 1
