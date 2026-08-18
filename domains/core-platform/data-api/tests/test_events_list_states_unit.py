"""GET /events pivots state_value / previous_state so events carry their states.

Before this fix the raw-event query filtered to the single `context_id` field
and hard-coded `old_state=None, new_state=None`, so every consumer of
`/api/v1/events` (dashboard, MCP `get_entity_state` / `get_entity_history`)
saw null states forever.
"""

import sys
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent / ".."))

from src import events_endpoints as ee
from src.events_endpoints import EventFilter, EventsEndpoints


def _record(entity_id: str, state, previous, context_id="01CTX") -> MagicMock:
    rec = MagicMock()
    rec.values = {
        "entity_id": entity_id,
        "event_type": "state_changed",
        "domain": entity_id.split(".")[0],
        "device_class": "unknown",
        "context_id": context_id,
        "state_value": state,
        "previous_state": previous,
    }
    rec.get_time.return_value = datetime(2026, 8, 17, 10, 0, 0, tzinfo=UTC)
    return rec


def _stub(records):
    table = MagicMock()
    table.records = records
    query_api = MagicMock()
    query_api.query.return_value = [table]
    client = MagicMock()
    client.query_api.return_value = query_api
    return client, query_api


@pytest.mark.asyncio
async def test_raw_events_pivot_and_expose_states(monkeypatch):
    client, query_api = _stub([_record("light.office", "on", "off")])
    monkeypatch.setattr(ee, "_get_shared_influxdb_client", lambda: client)

    events = await EventsEndpoints()._get_events_from_influxdb(
        EventFilter(entity_id="light.office"), limit=10, offset=0
    )

    flux = query_api.query.call_args[0][0]
    assert 'r._field == "state_value"' in flux and 'r._field == "previous_state"' in flux
    assert 'r._field == "context_id"' in flux
    assert 'pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")' in flux
    assert flux.index("pivot(") < flux.index("group()")  # pivot within each series first
    assert len(events) == 1
    assert events[0].id == "01CTX"
    assert events[0].new_state == {"state": "on"}
    assert events[0].old_state == {"state": "off"}


@pytest.mark.asyncio
async def test_missing_previous_state_stays_null(monkeypatch):
    client, _ = _stub([_record("sensor.t", 21.5, None)])
    monkeypatch.setattr(ee, "_get_shared_influxdb_client", lambda: client)
    (event,) = await EventsEndpoints()._get_events_from_influxdb(EventFilter(), limit=1, offset=0)
    assert event.new_state == {"state": "21.5"} and event.old_state is None


@pytest.mark.asyncio
async def test_statistics_range_keeps_single_field_query(monkeypatch):
    client, query_api = _stub([])
    monkeypatch.setattr(ee, "_get_shared_influxdb_client", lambda: client)
    old = datetime(2026, 7, 1, tzinfo=UTC)
    await EventsEndpoints()._get_events_from_influxdb(
        EventFilter(start_time=old, end_time=datetime(2026, 7, 2, tzinfo=UTC)), limit=1, offset=0
    )
    flux = query_api.query.call_args[0][0]
    assert 'r._field == "mean"' in flux and "pivot(" not in flux


@pytest.mark.asyncio
async def test_legacy_state_object_repr_rows_yield_bare_state(monkeypatch):
    legacy = "{'entity_id': 'light.garage', 'state': 'off', 'attributes': {'brightness': None}}"
    client, _ = _stub([_record("light.garage", legacy, "{'state': 'on'}")])
    monkeypatch.setattr(ee, "_get_shared_influxdb_client", lambda: client)
    (event,) = await EventsEndpoints()._get_events_from_influxdb(EventFilter(), limit=1, offset=0)
    assert event.new_state == {"state": "off"} and event.old_state == {"state": "on"}


def test_state_dict_keeps_braces_that_are_not_state_objects():
    assert ee._state_dict("{not really}") == {"state": "{not really}"}
    assert ee._state_dict("{'state': None}") == {"state": "{'state': None}"}
