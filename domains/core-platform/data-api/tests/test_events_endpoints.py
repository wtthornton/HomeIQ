"""
Tests for events_endpoints.py — Epic 80, Story 80.5

Covers 16 scenarios:
1.  EventsEndpoints initialization — creates router and service_urls
2.  EventData model validation — valid data
3.  EventData model — required fields enforced
4.  EventFilter model — default values
5.  EventFilter model — all filter fields populated
6.  EventSearch model — default limit and fields
7.  GET /events/categories — returns categories response
8.  GET /events/stats — returns stats response
9.  GET /events/stats?service=X — queries specific service
10. POST /events/search — returns search results
11. GET /events/stream — returns stream data
12. GET /events/entities — returns active entities
13. GET /events/types — returns event types
14. GET /events — returns events with default params
15. GET /events?entity_id=X — filters by entity
16. GET /events/{event_id} — 404 when event not found
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.events_endpoints import EventData, EventFilter, EventSearch, EventsEndpoints

# ---------------------------------------------------------------------------
# Override conftest fresh_db — events use InfluxDB, not PostgreSQL
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(autouse=True)
async def fresh_db():
    yield


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_app() -> FastAPI:
    """Build a minimal FastAPI app with events routes."""
    app = FastAPI()
    ep = EventsEndpoints()
    app.include_router(ep.router)
    return app


@pytest_asyncio.fixture
async def client():
    app = _make_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


# ===========================================================================
# Model Validation
# ===========================================================================


class TestEventDataModel:
    """EventData Pydantic model."""

    def test_valid_event(self):
        event = EventData(
            id="evt-001",
            timestamp=datetime.now(UTC),
            entity_id="light.living_room",
            event_type="state_changed",
        )
        assert event.id == "evt-001"
        assert event.entity_id == "light.living_room"
        assert event.attributes == {}
        assert event.tags == {}

    def test_event_with_states(self):
        event = EventData(
            id="evt-002",
            timestamp=datetime.now(UTC),
            entity_id="sensor.temp",
            event_type="state_changed",
            old_state={"state": "20.5"},
            new_state={"state": "21.0"},
            attributes={"unit": "°C"},
        )
        assert event.old_state["state"] == "20.5"
        assert event.new_state["state"] == "21.0"

    def test_required_fields_enforced(self):
        with pytest.raises(Exception):
            EventData()  # Missing required fields


class TestEventFilterModel:
    """EventFilter Pydantic model."""

    def test_defaults(self):
        f = EventFilter()
        assert f.entity_id is None
        assert f.event_type is None
        assert f.start_time is None
        assert f.end_time is None
        assert f.tags == {}
        assert f.device_id is None
        assert f.area_id is None

    def test_all_fields(self):
        now = datetime.now(UTC)
        f = EventFilter(
            entity_id="light.living_room",
            event_type="state_changed",
            start_time=now - timedelta(hours=1),
            end_time=now,
            device_id="dev-001",
            area_id="living_room",
            entity_category="config",
            exclude_category="diagnostic",
            event_category="lighting",
            home_type="house",
        )
        assert f.entity_id == "light.living_room"
        assert f.device_id == "dev-001"
        assert f.event_category == "lighting"


class TestEventSearchModel:
    """EventSearch Pydantic model."""

    def test_defaults(self):
        s = EventSearch(query="light")
        assert s.query == "light"
        assert s.limit == 100
        assert "entity_id" in s.fields

    def test_custom_fields(self):
        s = EventSearch(query="temp", fields=["entity_id"], limit=10)
        assert s.limit == 10
        assert s.fields == ["entity_id"]


# ===========================================================================
# Initialization
# ===========================================================================


class TestEventsEndpointsInit:
    """EventsEndpoints initialization."""

    def test_creates_router_and_service_urls(self):
        ep = EventsEndpoints()
        assert ep.router is not None
        assert "websocket-ingestion" in ep.service_urls


# ===========================================================================
# Endpoint Tests (with mocked InfluxDB / HTTP backends)
# ===========================================================================


class TestGetEventCategories:
    """GET /events/categories"""

    @pytest.mark.asyncio
    async def test_returns_categories(self, client):
        with patch.object(EventsEndpoints, "_get_event_categories", new_callable=AsyncMock) as mock:
            mock.return_value = {"categories": {"lighting": 10, "security": 5}, "total": 15}
            resp = await client.get("/events/categories")
            assert resp.status_code == 200
            data = resp.json()
            assert "categories" in data


class TestGetEventsStats:
    """GET /events/stats"""

    @pytest.mark.asyncio
    async def test_returns_stats(self, client):
        with patch.object(EventsEndpoints, "_get_all_events_stats", new_callable=AsyncMock) as mock:
            mock.return_value = {"total_events": 100, "events_per_minute": 5}
            resp = await client.get("/events/stats")
            assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_service_specific_stats(self, client):
        with patch.object(EventsEndpoints, "_get_service_events_stats", new_callable=AsyncMock) as mock:
            mock.return_value = {"total_events": 50}
            resp = await client.get("/events/stats?service=websocket-ingestion")
            assert resp.status_code == 200


class TestSearchEvents:
    """POST /events/search"""

    @pytest.mark.asyncio
    async def test_search_returns_results(self, client):
        mock_event = {
            "id": "evt-001",
            "timestamp": datetime.now(UTC).isoformat(),
            "entity_id": "light.living_room",
            "event_type": "state_changed",
            "attributes": {},
            "tags": {},
        }
        with patch.object(EventsEndpoints, "_search_events", new_callable=AsyncMock) as mock:
            mock.return_value = [EventData(**mock_event)]
            resp = await client.post("/events/search", json={"query": "light"})
            assert resp.status_code == 200
            data = resp.json()
            assert len(data) == 1


class TestGetEventsStream:
    """GET /events/stream"""

    @pytest.mark.asyncio
    async def test_returns_stream_data(self, client):
        with patch.object(EventsEndpoints, "_get_events_stream", new_callable=AsyncMock) as mock:
            mock.return_value = {"status": "streaming", "duration": 60, "events": []}
            resp = await client.get("/events/stream")
            assert resp.status_code == 200
            assert resp.json()["status"] == "streaming"


class TestGetActiveEntities:
    """GET /events/entities"""

    @pytest.mark.asyncio
    async def test_returns_entities(self, client):
        with patch.object(EventsEndpoints, "_get_all_active_entities", new_callable=AsyncMock) as mock:
            mock.return_value = [{"entity_id": "light.test", "last_event": "2026-03-16T00:00:00Z"}]
            resp = await client.get("/events/entities")
            assert resp.status_code == 200
            assert len(resp.json()) == 1


class TestGetEventTypes:
    """GET /events/types"""

    @pytest.mark.asyncio
    async def test_returns_types(self, client):
        with patch.object(EventsEndpoints, "_get_all_event_types", new_callable=AsyncMock) as mock:
            mock.return_value = [{"type": "state_changed", "count": 100}]
            resp = await client.get("/events/types")
            assert resp.status_code == 200


class TestGetRecentEvents:
    """GET /events"""

    @pytest.mark.asyncio
    async def test_returns_events(self, client):
        mock_event = EventData(
            id="evt-001",
            timestamp=datetime.now(UTC),
            entity_id="light.living_room",
            event_type="state_changed",
        )
        with patch.object(EventsEndpoints, "_get_all_events", new_callable=AsyncMock) as mock:
            mock.return_value = [mock_event]
            resp = await client.get("/events")
            assert resp.status_code == 200
            data = resp.json()
            assert len(data) == 1

    @pytest.mark.asyncio
    async def test_filter_by_entity_id(self, client):
        with patch.object(EventsEndpoints, "_get_all_events", new_callable=AsyncMock) as mock:
            mock.return_value = []
            resp = await client.get("/events?entity_id=light.test")
            assert resp.status_code == 200


class TestGetEventById:
    """GET /events/{event_id}"""

    @pytest.mark.asyncio
    async def test_404_when_not_found(self, client):
        with patch.object(EventsEndpoints, "_get_event_by_id", new_callable=AsyncMock) as mock:
            mock.return_value = None
            resp = await client.get("/events/nonexistent")
            assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_returns_event(self, client):
        mock_event = EventData(
            id="ctx-123",
            timestamp=datetime.now(UTC),
            entity_id="sensor.temp",
            event_type="state_changed",
        )
        with patch.object(EventsEndpoints, "_get_event_by_id", new_callable=AsyncMock) as mock:
            mock.return_value = mock_event
            resp = await client.get("/events/ctx-123")
            assert resp.status_code == 200
            assert resp.json()["id"] == "ctx-123"
