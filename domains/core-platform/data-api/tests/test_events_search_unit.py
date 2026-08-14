"""Event search queries the store, not phantom federation (TAP-5997).

The old `_search_events` POSTed to collector services that never
implemented `/events/search`, swallowed every 404, and returned [] —
structurally, forever. These tests pin the store-backed behavior with a
stubbed query_api so the facade cannot regress to always-empty.
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent / ".."))

from src import events_endpoints as ee
from src.events_endpoints import EventSearch, EventsEndpoints


def _record(entity_id: str, event_type: str = "state_changed") -> MagicMock:
    # Pivoted shape: context_id is a real column, not in _value.
    rec = MagicMock()
    rec.values = {
        "entity_id": entity_id,
        "event_type": event_type,
        "domain": entity_id.split(".")[0],
        "context_id": "01REALCTXID",
    }
    rec.get_time.return_value = __import__("datetime").datetime(2026, 8, 13, 10, 0, 0)
    return rec


def _stub_query_api(records: list) -> MagicMock:
    table = MagicMock()
    table.records = records
    query_api = MagicMock()
    query_api.query.return_value = [table]
    client = MagicMock()
    client.query_api.return_value = query_api
    return client, query_api


@pytest.mark.asyncio
async def test_search_queries_the_store_and_returns_matches(monkeypatch):
    client, query_api = _stub_query_api([_record("light.office")])
    monkeypatch.setattr(ee, "_get_shared_influxdb_client", lambda: client)

    results = await EventsEndpoints()._search_events(EventSearch(query="office"))

    flux = query_api.query.call_args[0][0]
    assert "strings.containsStr" in flux
    assert '_measurement == "home_assistant_events"' in flux
    assert "pivot(" in flux and "group()" in flux  # global limit + real ids
    assert "strings.toLower" in flux  # case-insensitive
    assert 'substr: "office"' in flux
    assert len(results) == 1
    assert results[0].entity_id == "light.office"
    # Real context_id survives (drill-down keeps working), not a synthetic id.
    assert results[0].id == "01REALCTXID"


@pytest.mark.asyncio
async def test_search_needle_goes_through_the_shared_sanitizer(monkeypatch):
    """A Flux ${...} interpolation payload must be stripped, not escaped —
    the verifier broke the hand-rolled escape with ${r.entity_id}."""
    client, query_api = _stub_query_api([])
    monkeypatch.setattr(ee, "_get_shared_influxdb_client", lambda: client)

    await EventsEndpoints()._search_events(EventSearch(query="${r.entity_id}"))

    flux = query_api.query.call_args[0][0]
    assert "${" not in flux  # sanitize_flux_value drops $ { }
    assert "r.entity_id}" not in flux.split("substr:")[-1].split("\n")[0].replace(
        "r.entity_id), substr", ""
    )


@pytest.mark.asyncio
async def test_search_clamps_limit_and_window(monkeypatch):
    client, query_api = _stub_query_api([])
    monkeypatch.setattr(ee, "_get_shared_influxdb_client", lambda: client)

    # Pydantic rejects out-of-range at the model boundary.
    with pytest.raises(Exception):
        EventSearch(query="x", limit=-1)
    with pytest.raises(Exception):
        EventSearch(query="x", limit=99999)

    await EventsEndpoints()._search_events(EventSearch(query="x", limit=5, hours=48))
    flux = query_api.query.call_args[0][0]
    assert "limit(n: 5)" in flux
    assert "range(start: -48h)" in flux


@pytest.mark.asyncio
async def test_search_never_federates_to_services(monkeypatch):
    """The phantom fan-out is gone: no HTTP client is touched."""
    client, _ = _stub_query_api([])
    monkeypatch.setattr(ee, "_get_shared_influxdb_client", lambda: client)
    import inspect

    src = inspect.getsource(EventsEndpoints._search_events)
    assert "service_urls" not in src
    assert "aiohttp" not in src
    assert "session.post" not in src
    assert await EventsEndpoints()._search_events(EventSearch(query="x")) == []


@pytest.mark.asyncio
async def test_search_quote_breakout_is_neutralized(monkeypatch):
    client, query_api = _stub_query_api([])
    monkeypatch.setattr(ee, "_get_shared_influxdb_client", lambda: client)

    await EventsEndpoints()._search_events(EventSearch(query='x") or true or (r._value == "'))

    flux = query_api.query.call_args[0][0]
    # The sanitizer strips ) " ( = so no token can close the substr literal
    # or open a new Flux expression — the payload survives only as inert
    # text inside the quoted substring.
    assert '"' not in flux.split('substr: "')[1].split('")')[0]
    assert ") or true" not in flux
    assert "== " not in flux.split("containsStr")[1]


@pytest.mark.asyncio
async def test_empty_query_returns_no_matches_not_everything(monkeypatch):
    """An empty query must not degrade into "return every event" (bug-hunt
    c4, BUG-HomeIQ-4-4). sanitize_flux_value("") == "", and
    strings.containsStr(substr: "") matches every string, so building the
    query anyway would silently dump the whole store."""
    client, query_api = _stub_query_api([_record("light.office")])
    monkeypatch.setattr(ee, "_get_shared_influxdb_client", lambda: client)

    results = await EventsEndpoints()._search_events(EventSearch(query=""))

    assert results == []
    query_api.query.assert_not_called()


@pytest.mark.asyncio
async def test_symbols_only_query_returns_no_matches_not_everything(monkeypatch):
    """Symbols-only input (e.g. "!!!") also sanitizes to "" and must be
    treated the same as an empty query."""
    client, query_api = _stub_query_api([_record("light.office")])
    monkeypatch.setattr(ee, "_get_shared_influxdb_client", lambda: client)

    results = await EventsEndpoints()._search_events(EventSearch(query="!!!"))

    assert results == []
    query_api.query.assert_not_called()


@pytest.mark.asyncio
async def test_store_failure_surfaces_as_502_not_silent_empty():
    from httpx import ASGITransport, AsyncClient

    from src.main import app  # noqa: F401 — ensure app imports

    endpoints = EventsEndpoints()
    with patch.object(
        EventsEndpoints, "_search_events", new_callable=AsyncMock
    ) as mock:
        mock.side_effect = Exception("store down")
        from fastapi import FastAPI

        test_app = FastAPI()
        test_app.include_router(endpoints.router)
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://t"
        ) as client:
            resp = await client.post("/events/search", json={"query": "light"})
    assert resp.status_code == 502
