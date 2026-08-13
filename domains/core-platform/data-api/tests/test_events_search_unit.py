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
    rec = MagicMock()
    rec.values = {
        "entity_id": entity_id,
        "event_type": event_type,
        "domain": entity_id.split(".")[0],
        "_time": "2026-08-13T10:00:00Z",
        "_value": "ctx-1",
    }
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
    assert 'strings.containsStr' in flux
    assert '_measurement == "home_assistant_events"' in flux
    assert 'substr: "office"' in flux
    assert len(results) == 1
    assert results[0].entity_id == "light.office"


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
async def test_search_escapes_flux_string_context(monkeypatch):
    client, query_api = _stub_query_api([])
    monkeypatch.setattr(ee, "_get_shared_influxdb_client", lambda: client)

    await EventsEndpoints()._search_events(EventSearch(query='x") or true or (r._value == "'))

    flux = query_api.query.call_args[0][0]
    assert '\\"' in flux  # quotes escaped — the needle cannot break out
    assert '") or true or' not in flux.replace('\\"', "")


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
