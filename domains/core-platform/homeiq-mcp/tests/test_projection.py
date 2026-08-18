from datetime import UTC, datetime

import pytest
from src.errors import ToolError
from src.tools.projection import (
    expect_list,
    listing,
    present,
    require,
    rfc3339,
    state_string,
    window,
)


def test_expect_list_unwraps_envelope_and_rejects_bare_list():
    assert expect_list({"devices": [1, 2]}, tool="t", key="devices") == [1, 2]
    assert expect_list([1], tool="t") == [1]
    with pytest.raises(ToolError) as exc:
        expect_list([1], tool="t", key="devices")
    assert exc.value.code == "contract_violation" and "devices" in exc.value.message
    with pytest.raises(ToolError):
        expect_list({"devices": None}, tool="t", key="devices")


def test_require_and_present():
    row = {"a": 1, "b": "", "c": None, "d": [], "e": "x"}
    assert require(row, ("a",), tool="t") == {"a": 1}
    with pytest.raises(ToolError) as exc:
        require(row, ("a", "c"), tool="t")
    assert exc.value.code == "contract_violation" and "'c'" in exc.value.message
    assert present(row, ("a", "b", "c", "d", "e", "zz")) == {"a": 1, "e": "x"}


def test_state_string_projects_dicts_and_scalars():
    assert state_string({"state": "on", "attributes": {}}) == "on"
    assert state_string({"attributes": {}}) is None
    assert state_string(None) is None
    assert state_string(21.5) == "21.5"
    assert len(state_string("x" * 400)) == 255


def test_rfc3339_and_window():
    ts = datetime(2026, 8, 17, 10, 0, tzinfo=UTC)
    assert rfc3339(ts) == "2026-08-17T10:00:00+00:00"
    assert rfc3339("2026-08-17T10:00:00Z") == "2026-08-17T10:00:00Z"
    start, end = window(6)
    delta = datetime.fromisoformat(end) - datetime.fromisoformat(start)
    assert delta.total_seconds() == 6 * 3600


def test_listing_envelope_cap_hint_and_count_toggle():
    out = listing("rows", list(range(5)), 3, "limit")
    assert out == {"rows": [0, 1, 2], "truncated": True, "count": 3, "hint": "limit"}
    out = listing("rows", [1], 3, "limit", count=False, view="x")
    assert out == {"rows": [1], "truncated": False, "view": "x"}
