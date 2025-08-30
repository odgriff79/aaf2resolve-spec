from __future__ import annotations

from typing import Set

from src.validate_canonical import validate_event_ids


def _codes(data: dict) -> Set[str]:
    return {e.code for e in validate_event_ids(data)}


def test_invalid_event_id_alpha() -> None:
    data = {"timeline": {"events": [{"id": "event_1234"}]}}  # wrong prefix
    assert "CANON-REQ-020" in _codes(data)


def test_invalid_event_id_short() -> None:
    data = {"timeline": {"events": [{"id": "ev_99"}]}}  # not 4 digits
    assert "CANON-REQ-020" in _codes(data)


def test_valid_event_id() -> None:
    data = {"timeline": {"events": [{"id": "ev_0000"}]}}  # valid pattern
    assert "CANON-REQ-020" not in _codes(data)
