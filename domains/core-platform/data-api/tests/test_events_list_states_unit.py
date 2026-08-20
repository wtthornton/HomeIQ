"""GET /events pivots state_value / previous_state so events carry their states.

Before this fix the raw-event query filtered to the single `context_id` field
and hard-coded `old_state=None, new_state=None`, so every consumer of
`/api/v1/events` (dashboard, MCP `get_entity_state` / `get_entity_history`)
saw null states forever.
"""

import inspect
import sys
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

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
    # selective tag filters push down to storage BEFORE the pivot; pivot before the global group()
    assert (
        flux.index('r.entity_id == "light.office"') < flux.index("pivot(") < flux.index("group()")
    )
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
    # count, not mean: the downsampled tiers carry both, but mean exists only for
    # entities whose states parse as numbers. An events query reading mean would
    # drop every light, switch and binary_sensor from windows over 10 days.
    assert 'r._field == "count"' in flux and "pivot(" not in flux
    # start_time is more than 30 days back, so this is the hourly tier.
    assert 'r._measurement == "statistics"' in flux


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


@pytest.mark.asyncio
async def test_downsampled_rows_do_not_use_the_aggregate_as_an_id(monkeypatch):
    """A statistics row carries a count in _value, which is not a context id.

    Using it built EventData(id=1), which fails validation; the broad handler in
    _get_events_from_influxdb turned that into an empty 200, so every window over
    10 days looked like "no events occurred".
    """

    def _stat_row(entity_id: str) -> MagicMock:
        # What a downsampled row actually looks like: no context_id, no states,
        # the aggregate in _value.
        rec = MagicMock()
        rec.values = {
            "entity_id": entity_id,
            "event_type": "state_changed",
            "domain": entity_id.split(".")[0],
            "_value": 1,
        }
        rec.get_time.return_value = datetime(2026, 8, 17, 10, 0, 0, tzinfo=UTC)
        return rec

    rows = [_stat_row("sensor.a"), _stat_row("sensor.b")]
    client, _ = _stub(rows)
    monkeypatch.setattr(ee, "_get_shared_influxdb_client", lambda: client)
    old = datetime(2026, 7, 1, tzinfo=UTC)

    events = await EventsEndpoints()._get_events_from_influxdb(
        EventFilter(start_time=old), limit=10, offset=0
    )

    # Both survive: distinct synthesized ids, not one collapsed row keyed on "1".
    assert len(events) == 2
    assert {e.entity_id for e in events} == {"sensor.a", "sensor.b"}
    assert all(isinstance(e.id, str) for e in events)


@pytest.mark.asyncio
async def test_query_failure_raises_instead_of_returning_empty(monkeypatch):
    """A broken query must not look like a quiet window (TAP-6151).

    _get_events_from_influxdb used to catch everything and return [], so an
    unreachable InfluxDB, a rejected Flux query and an EventData validation
    error all arrived at the caller as a successful "no events occurred".
    """
    client, query_api = _stub([])
    query_api.query.side_effect = RuntimeError("unauthorized: token expired")
    monkeypatch.setattr(ee, "_get_shared_influxdb_client", lambda: client)

    with pytest.raises(RuntimeError, match="token expired"):
        await EventsEndpoints()._get_events_from_influxdb(EventFilter(), limit=10, offset=0)


@pytest.mark.asyncio
async def test_empty_window_still_returns_an_empty_list(monkeypatch):
    """The genuinely-empty case is unchanged, and distinguishable from failure."""
    client, _ = _stub([])
    monkeypatch.setattr(ee, "_get_shared_influxdb_client", lambda: client)

    events = await EventsEndpoints()._get_events_from_influxdb(EventFilter(), limit=10, offset=0)

    assert events == []


@pytest.mark.asyncio
async def test_get_all_events_maps_a_query_failure_to_503(monkeypatch):
    """The HTTP layer reports the failure rather than a 200 with no events."""
    client, query_api = _stub([])
    query_api.query.side_effect = RuntimeError("connection refused")
    monkeypatch.setattr(ee, "_get_shared_influxdb_client", lambda: client)

    with pytest.raises(HTTPException) as excinfo:
        await EventsEndpoints()._get_all_events(EventFilter(), limit=10, offset=0)

    assert excinfo.value.status_code == 503
    assert "connection refused" in excinfo.value.detail


def test_events_route_does_not_offer_an_entity_category_filter():
    """The tag was never written, so the filter could only return empty (TAP-6156)."""
    assert "entity_category" not in EventFilter.model_fields
    assert "exclude_category" not in EventFilter.model_fields

    params = {
        p.name
        for route in EventsEndpoints().router.routes
        if getattr(route, "path", None) == "/events"
        for p in inspect.signature(route.endpoint).parameters.values()
    }
    assert "entity_category" not in params and "exclude_category" not in params
    # event_category is the classification tag ingestion actually writes.
    assert "event_category" in params


@pytest.mark.asyncio
async def test_flux_never_filters_on_the_nonexistent_entity_category_tag(monkeypatch):
    client, query_api = _stub([])
    monkeypatch.setattr(ee, "_get_shared_influxdb_client", lambda: client)

    await EventsEndpoints()._get_events_from_influxdb(
        EventFilter(event_category="lighting"), limit=1, offset=0
    )

    flux = query_api.query.call_args[0][0]
    assert "entity_category" not in flux
    assert 'r.event_category == "lighting"' in flux


@pytest.mark.asyncio
async def test_service_scoped_events_fail_loudly_when_the_backend_is_dead():
    """The ?service= branch was the surviving twin of the TAP-6151 fix: an
    unreachable backend answered HTTP 200 + [], indistinguishable from an
    idle window. It must 503 like _get_all_events does."""
    endpoints = EventsEndpoints()
    endpoints.service_urls = {"websocket-ingestion": "http://127.0.0.1:1"}  # unroutable

    with pytest.raises(HTTPException) as excinfo:
        await endpoints._get_service_events(
            "websocket-ingestion", EventFilter(), limit=10, offset=0
        )

    assert excinfo.value.status_code == 503


@pytest.mark.asyncio
async def test_entities_aggregator_503s_when_every_backend_is_dead():
    """Partial aggregation may degrade; ALL backends failing must not read
    as 'no active entities' (TAP-6151 shape on /events/entities)."""
    endpoints = EventsEndpoints()
    endpoints.service_urls = {"websocket-ingestion": "http://127.0.0.1:1"}

    with pytest.raises(HTTPException) as excinfo:
        await endpoints._get_all_active_entities(limit=10)

    assert excinfo.value.status_code == 503


@pytest.mark.asyncio
async def test_event_types_aggregator_503s_when_every_backend_is_dead():
    endpoints = EventsEndpoints()
    endpoints.service_urls = {"websocket-ingestion": "http://127.0.0.1:1"}

    with pytest.raises(HTTPException) as excinfo:
        await endpoints._get_all_event_types(limit=10)

    assert excinfo.value.status_code == 503


def _route_client():
    """The full route stack against one unroutable backend (TAP-6151)."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    endpoints = EventsEndpoints()
    endpoints.service_urls = {"websocket-ingestion": "http://127.0.0.1:1"}
    app = FastAPI()
    app.include_router(endpoints.router, prefix="/api/v1")
    return TestClient(app, raise_server_exceptions=False)


def test_routes_answer_503_not_empty_200_when_every_backend_is_dead():
    """Pins the route-level `except HTTPException: raise` blocks: deleting
    them would relabel the helpers' 503 as a generic 500 (or worse, the old
    empty 200)."""
    client = _route_client()

    for path in (
        "/api/v1/events?service=websocket-ingestion",
        "/api/v1/events/entities",
        "/api/v1/events/types",
        "/api/v1/events/stats",
    ):
        response = client.get(path)
        assert response.status_code == 503, path
        assert "unavailable" in response.json()["detail"], path


def test_categories_route_503s_when_the_store_query_fails(monkeypatch):
    def _boom():
        raise RuntimeError("influx down")

    monkeypatch.setattr(ee, "_get_shared_influxdb_client", _boom)
    client = _route_client()

    response = client.get("/api/v1/events/categories")

    assert response.status_code == 503
    assert response.json()["detail"] == "Event categories query failed"


def test_trace_route_503s_when_the_store_query_fails(monkeypatch):
    def _boom():
        raise RuntimeError("influx down")

    monkeypatch.setattr(ee, "_get_shared_influxdb_client", _boom)
    client = _route_client()

    response = client.get("/api/v1/events/automation-trace/01CTX")

    assert response.status_code == 503
    assert response.json()["detail"] == "Automation trace query failed"
