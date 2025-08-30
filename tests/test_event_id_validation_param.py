from __future__ import annotations

from typing import Any

import pytest

from src.validate_canonical import validate_event_ids


def _codes(data: dict[str, Any]) -> set[str]:
    return {e.code for e in validate_event_ids(data)}


@pytest.mark.parametrize("ev_id", ["ev_0000", "ev_0123", "ev_9999"])
def test_valid_ids_pass(ev_id: str) -> None:
    data = {"timeline": {"events": [{"id": ev_id}]}}
    assert "CANON-REQ-020" not in _codes(data)


@pytest.mark.parametrize(
    "ev_id",
    [
        "event_1234",  # wrong prefix
        "ev_99",  # too short
        "ev_123",  # too short
        "ev_12345",  # too long
        "ev_12a4",  # non-digit
        "ev-",  # missing digits
        "ev_",  # missing digits
        "ev 1234",  # space
    ],
)
def test_invalid_strings_fail(ev_id: str) -> None:
    data = {"timeline": {"events": [{"id": ev_id}]}}
    assert "CANON-REQ-020" in _codes(data)


@pytest.mark.parametrize("bad_id", [None, 1234, {}, []])
def test_non_string_id_fails(bad_id: Any) -> None:
    data = {"timeline": {"events": [{"id": bad_id}]}}
    assert "CANON-REQ-020" in _codes(data)


def test_missing_id_field_fails() -> None:
    data: dict[str, Any] = {"timeline": {"events": [{}]}}
    assert "CANON-REQ-020" in _codes(data)
