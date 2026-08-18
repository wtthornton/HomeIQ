"""Group 1 tools against real data-api payload shapes (`EventData`, trace items)."""

from __future__ import annotations

import httpx
import pytest
import respx
from src.auth import READ_SCOPES
from src.errors import ToolError
from src.tools import history

DATA_API = "http://data-api.test:8006"


def _event(i: int, entity="light.office", **extra):
    return {
        "id": f"e{i}",
        "timestamp": f"2026-08-17T10:{i % 60:02d}:00+00:00",
        "entity_id": entity,
        "event_type": "state_changed",
        "old_state": {"state": "off", "attributes": {}},
        "new_state": {"state": "on" if i % 2 else "off", "attributes": {"brightness": i}},
        "attributes": {},
        "tags": {},
        **extra,
    }


@pytest.fixture
def reg(registry, backings):
    history.register(registry, backings)
    return registry


def _validate(catalogue, name, payload):
    catalogue.tools[name].output_validator.validate(payload)


def test_registers_group(reg):
    assert reg.names() == [
        "get_entity_history",
        "get_entity_state",
        "get_recent_events",
        "search_events",
        "trace_automation",
    ]


@respx.mock
async def test_entity_history_derives_window_and_projects_state(reg, catalogue):
    route = respx.get(f"{DATA_API}/api/v1/events").mock(
        return_value=httpx.Response(200, json=[_event(1), _event(2)])
    )
    out = await reg.call(
        "get_entity_history", {"entity_id": "light.office", "hours": 6}, scopes=READ_SCOPES
    )
    _validate(catalogue, "get_entity_history", out)
    assert out["points"] == [
        {"t": "2026-08-17T10:01:00+00:00", "state": "on"},
        {"t": "2026-08-17T10:02:00+00:00", "state": "off"},
    ]
    assert out["count"] == 2 and out["truncated"] is False
    params = route.calls.last.request.url.params
    assert params["entity_id"] == "light.office" and params["limit"] == "500"
    assert "start_time" in params and "end_time" in params and "hours" not in params


@respx.mock
async def test_entity_history_explicit_range_and_downsample(reg, catalogue):
    events = [_event(i) for i in range(6)]  # one per minute
    respx.get(f"{DATA_API}/api/v1/events").mock(return_value=httpx.Response(200, json=events))
    out = await reg.call(
        "get_entity_history",
        {
            "entity_id": "light.office",
            "start_time": "2026-08-17T00:00:00Z",
            "end_time": "2026-08-17T12:00:00Z",
            "downsample_minutes": 5,
        },
        scopes=READ_SCOPES,
    )
    _validate(catalogue, "get_entity_history", out)
    assert [p["t"] for p in out["points"]] == [
        "2026-08-17T10:00:00+00:00",
        "2026-08-17T10:05:00+00:00",
    ]


@respx.mock
async def test_entity_history_row_cap(reg, catalogue):
    respx.get(f"{DATA_API}/api/v1/events").mock(
        return_value=httpx.Response(200, json=[_event(i) for i in range(520)])
    )
    out = await reg.call("get_entity_history", {"entity_id": "light.office"}, scopes=READ_SCOPES)
    _validate(catalogue, "get_entity_history", out)
    assert (
        out["truncated"] is True
        and out["hint"] == "hours"
        and out["count"] == len(out["points"]) <= 500
    )


@respx.mock
async def test_entity_history_missing_timestamp_is_contract_violation(reg):
    respx.get(f"{DATA_API}/api/v1/events").mock(
        return_value=httpx.Response(
            200, json=[{"entity_id": "light.office", "new_state": {"state": "on"}}]
        )
    )
    with pytest.raises(ToolError) as exc:
        await reg.call("get_entity_history", {"entity_id": "light.office"}, scopes=READ_SCOPES)
    assert exc.value.code == "contract_violation"


@respx.mock
async def test_search_events_posts_body_and_projects(reg, catalogue):
    route = respx.post(f"{DATA_API}/api/v1/events/search").mock(
        return_value=httpx.Response(200, json=[_event(3, entity="switch.fan")])
    )
    out = await reg.call(
        "search_events", {"query": "fan", "hours": 48, "limit": 10}, scopes=READ_SCOPES
    )
    _validate(catalogue, "search_events", out)
    assert out["events"][0] == {
        "t": "2026-08-17T10:03:00+00:00",
        "entity_id": "switch.fan",
        "event_type": "state_changed",
        "old_state": "off",
        "new_state": "on",
    }
    import json

    assert json.loads(route.calls.last.request.content) == {
        "query": "fan",
        "hours": 48,
        "limit": 10,
    }


@respx.mock
async def test_recent_events_filters_offset_and_cap(reg, catalogue):
    route = respx.get(f"{DATA_API}/api/v1/events").mock(
        return_value=httpx.Response(200, json=[_event(i) for i in range(250)])
    )
    out = await reg.call(
        "get_recent_events", {"area_id": "office", "offset": 5, "limit": 200}, scopes=READ_SCOPES
    )
    _validate(catalogue, "get_recent_events", out)
    assert out["offset"] == 5 and out["truncated"] is True and len(out["events"]) == 200
    params = route.calls.last.request.url.params
    assert params["area_id"] == "office" and params["offset"] == "5" and "entity_id" not in params


@respx.mock
async def test_recent_events_missing_entity_is_contract_violation(reg):
    respx.get(f"{DATA_API}/api/v1/events").mock(
        return_value=httpx.Response(
            200, json=[{"timestamp": "2026-08-17T10:00:00+00:00", "event_type": "x"}]
        )
    )
    with pytest.raises(ToolError) as exc:
        await reg.call("get_recent_events", {}, scopes=READ_SCOPES)
    assert exc.value.code == "contract_violation"


@respx.mock
async def test_trace_automation_projects_chain_items(reg, catalogue):
    items = [
        {
            "depth": d,
            "context_id": f"ctx{d}",
            "context_parent_id": f"ctx{d - 1}",
            "timestamp": f"2026-08-17T10:0{d}:00+00:00",
            "entity_id": "automation.morning",
            "event_type": "automation_triggered",
            "state": "on" if d else None,
            "old_state": None,
        }
        for d in range(4)
    ]
    respx.get(f"{DATA_API}/api/v1/events/automation-trace/ctx0").mock(
        return_value=httpx.Response(200, json=items)
    )
    out = await reg.call(
        "trace_automation", {"context_id": "ctx0", "max_depth": 2}, scopes=READ_SCOPES
    )
    _validate(catalogue, "trace_automation", out)
    # max_depth bounds chain LEVELS, not rows: depths 0..2 kept (3 rows), depth 3 dropped, no row cap.
    assert out["count"] == 3 and out["truncated"] is False and "hint" not in out
    assert [c["depth"] for c in out["chain"]] == [0, 1, 2]
    assert "state" not in out["chain"][0] and out["chain"][1]["state"] == "on"
    assert out["chain"][1]["t"] == "2026-08-17T10:01:00+00:00"


@respx.mock
async def test_trace_automation_missing_context_id_is_contract_violation(reg):
    respx.get(f"{DATA_API}/api/v1/events/automation-trace/ctx0").mock(
        return_value=httpx.Response(
            200, json=[{"depth": 0, "timestamp": "2026-08-17T10:00:00+00:00"}]
        )
    )
    with pytest.raises(ToolError) as exc:
        await reg.call("trace_automation", {"context_id": "ctx0"}, scopes=READ_SCOPES)
    assert exc.value.code == "contract_violation"


@respx.mock
async def test_entity_state_newest_event(reg, catalogue):
    route = respx.get(f"{DATA_API}/api/v1/events").mock(
        return_value=httpx.Response(200, json=[_event(7)])
    )
    out = await reg.call("get_entity_state", {"entity_id": "light.office"}, scopes=READ_SCOPES)
    _validate(catalogue, "get_entity_state", out)
    assert out == {
        "entity_id": "light.office",
        "state": "on",
        "t": "2026-08-17T10:07:00+00:00",
        "source": "last_observed_event",
    }
    assert route.calls.last.request.url.params["limit"] == "1"


@respx.mock
async def test_entity_state_without_events_is_null(reg, catalogue):
    respx.get(f"{DATA_API}/api/v1/events").mock(return_value=httpx.Response(200, json=[]))
    out = await reg.call("get_entity_state", {"entity_id": "light.office"}, scopes=READ_SCOPES)
    _validate(catalogue, "get_entity_state", out)
    assert out["state"] is None and out["t"] is None


@respx.mock
async def test_backing_404_maps_to_not_found(reg):
    respx.get(f"{DATA_API}/api/v1/events/automation-trace/nope").mock(
        return_value=httpx.Response(404)
    )
    with pytest.raises(ToolError) as exc:
        await reg.call("trace_automation", {"context_id": "nope"}, scopes=READ_SCOPES)
    assert exc.value.code == "not_found"


@respx.mock
async def test_history_skips_state_changed_rows_without_new_state_and_filters_event_type(
    reg, catalogue
):
    route = respx.get(f"{DATA_API}/api/v1/events").mock(
        return_value=httpx.Response(
            200, json=[_event(1), {**_event(2), "new_state": None}, _event(3)]
        )
    )
    out = await reg.call("get_entity_history", {"entity_id": "light.office"}, scopes=READ_SCOPES)
    _validate(catalogue, "get_entity_history", out)
    assert [p["t"] for p in out["points"]] == [
        "2026-08-17T10:01:00+00:00",
        "2026-08-17T10:03:00+00:00",
    ]
    assert route.calls.last.request.url.params["event_type"] == "state_changed"


@pytest.mark.parametrize(
    "bad", ["../v1/energy/statistics", "a/b", "x?y=1", "ctx#frag", "with space", "", "z" * 300]
)
async def test_path_traversal_in_context_id_is_rejected_before_any_request(reg, bad):
    with pytest.raises(ToolError) as exc:
        await reg.call("trace_automation", {"context_id": bad}, scopes=READ_SCOPES)
    assert exc.value.code == "invalid_input"
