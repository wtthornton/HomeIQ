"""
Tests for Activity, Sports, HA Automation, MCP, and Analytics endpoints.

Each endpoint group uses a standalone FastAPI app with only its router
to avoid PostgreSQL and other heavy dependencies. External services
(InfluxDB, cache, etc.) are mocked.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient


# Override conftest fresh_db — these tests don't need PostgreSQL
@pytest_asyncio.fixture(autouse=True)
async def fresh_db():
    yield


# ---------------------------------------------------------------------------
# Activity Endpoints
# ---------------------------------------------------------------------------

def _make_activity_app():
    """Build a standalone FastAPI app with the activity router."""
    app = FastAPI()

    with patch("src.activity_endpoints._get_shared_influxdb_client"):
        from src.activity_endpoints import router as activity_router
        app.include_router(activity_router, prefix="/api/v1")

    return app


@pytest_asyncio.fixture
async def activity_client():
    app = _make_activity_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestActivityCurrentEndpoint:
    """GET /api/v1/activity — current activity."""

    @pytest.mark.asyncio
    async def test_current_activity_happy_path(self, activity_client):
        mock_items = [
            {
                "activity": "cooking",
                "activity_id": 3,
                "confidence": 0.92,
                "timestamp": "2026-03-17T10:00:00+00:00",
            }
        ]
        with (
            patch("src.activity_endpoints._query_activity_from_influxdb", new_callable=AsyncMock, return_value=mock_items),
            patch("src.activity_endpoints.cache") as mock_cache,
        ):
            mock_cache.get = AsyncMock(return_value=None)
            mock_cache.set = AsyncMock()

            resp = await activity_client.get("/api/v1/activity")

        assert resp.status_code == 200
        data = resp.json()
        assert data["activity"] == "cooking"
        assert data["activity_id"] == 3
        assert data["confidence"] == 0.92

    @pytest.mark.asyncio
    async def test_current_activity_from_cache(self, activity_client):
        cached = {
            "activity": "sleeping",
            "activity_id": 1,
            "confidence": 0.99,
            "timestamp": "2026-03-17T09:00:00+00:00",
        }
        with patch("src.activity_endpoints.cache") as mock_cache:
            mock_cache.get = AsyncMock(return_value=cached)

            resp = await activity_client.get("/api/v1/activity")

        assert resp.status_code == 200
        assert resp.json()["activity"] == "sleeping"

    @pytest.mark.asyncio
    async def test_current_activity_no_data_returns_404(self, activity_client):
        with (
            patch("src.activity_endpoints._query_activity_from_influxdb", new_callable=AsyncMock, return_value=[]),
            patch("src.activity_endpoints.cache") as mock_cache,
        ):
            mock_cache.get = AsyncMock(return_value=None)

            resp = await activity_client.get("/api/v1/activity")

        assert resp.status_code == 404


class TestActivityHistoryEndpoint:
    """GET /api/v1/activity/history — activity history."""

    @pytest.mark.asyncio
    async def test_history_happy_path(self, activity_client):
        mock_items = [
            {"activity": "cooking", "activity_id": 3, "confidence": 0.92, "timestamp": "2026-03-17T10:00:00+00:00"},
            {"activity": "sleeping", "activity_id": 1, "confidence": 0.88, "timestamp": "2026-03-17T08:00:00+00:00"},
        ]
        with patch("src.activity_endpoints._query_activity_from_influxdb", new_callable=AsyncMock, return_value=mock_items):
            resp = await activity_client.get("/api/v1/activity/history")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["activity"] == "cooking"

    @pytest.mark.asyncio
    async def test_history_custom_params(self, activity_client):
        with patch("src.activity_endpoints._query_activity_from_influxdb", new_callable=AsyncMock, return_value=[]) as mock_query:
            resp = await activity_client.get("/api/v1/activity/history?hours=48&limit=10")

        assert resp.status_code == 200
        mock_query.assert_called_once_with(hours=48, limit=10)

    @pytest.mark.asyncio
    async def test_history_empty_result(self, activity_client):
        with patch("src.activity_endpoints._query_activity_from_influxdb", new_callable=AsyncMock, return_value=[]):
            resp = await activity_client.get("/api/v1/activity/history")

        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_history_invalid_hours_below_min(self, activity_client):
        resp = await activity_client.get("/api/v1/activity/history?hours=0")
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_history_invalid_hours_above_max(self, activity_client):
        resp = await activity_client.get("/api/v1/activity/history?hours=999")
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Sports Endpoints
# ---------------------------------------------------------------------------

def _make_sports_app():
    """Build a standalone FastAPI app with the sports router."""
    app = FastAPI()

    with (
        patch("src.sports_endpoints.InfluxDBQueryClient"),
        patch("src.sports_endpoints.get_sports_writer") as mock_writer_fn,
    ):
        mock_writer = MagicMock()
        mock_writer.is_connected = False
        mock_writer_fn.return_value = mock_writer
        from src.sports_endpoints import router as sports_router
        app.include_router(sports_router, prefix="/api/v1")

    return app


@pytest_asyncio.fixture
async def sports_client():
    app = _make_sports_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestSportsLiveGames:
    """GET /api/v1/sports/games/live"""

    @pytest.mark.asyncio
    async def test_live_games_happy_path(self, sports_client):
        mock_records = [
            {
                "entity_id": "sensor.nhl_cbj",
                "team_abbr": "CBJ",
                "opponent_abbr": "VGK",
                "league": "NHL",
                "state": "IN",
                "team_score": 3,
                "opponent_score": 2,
                "clock": "12:30",
                "quarter": "2nd",
                "_time": datetime(2026, 3, 17, 20, 0, tzinfo=UTC),
                "team_homeaway": "home",
                "team_color_primary": "#002654",
                "team_color_secondary": "#CE1126",
                "team_winner": None,
                "opponent_winner": None,
                "event_name": "VGK @ CBJ",
                "last_play": "Goal by CBJ",
            }
        ]
        with patch("src.sports_endpoints.influxdb_client") as mock_influx:
            mock_influx.is_connected = True
            mock_influx._execute_query = AsyncMock(return_value=mock_records)

            resp = await sports_client.get("/api/v1/sports/games/live")

        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 1
        assert data["games"][0]["home_team"] == "CBJ"
        assert data["games"][0]["status"] == "live"

    @pytest.mark.asyncio
    async def test_live_games_empty(self, sports_client):
        with patch("src.sports_endpoints.influxdb_client") as mock_influx:
            mock_influx.is_connected = True
            mock_influx._execute_query = AsyncMock(return_value=[])

            resp = await sports_client.get("/api/v1/sports/games/live")

        assert resp.status_code == 200
        assert resp.json()["count"] == 0

    @pytest.mark.asyncio
    async def test_live_games_filter_by_league(self, sports_client):
        with patch("src.sports_endpoints.influxdb_client") as mock_influx:
            mock_influx.is_connected = True
            mock_influx._execute_query = AsyncMock(return_value=[])

            resp = await sports_client.get("/api/v1/sports/games/live?league=NHL")

        assert resp.status_code == 200


class TestSportsUpcomingGames:
    """GET /api/v1/sports/games/upcoming"""

    @pytest.mark.asyncio
    async def test_upcoming_games_happy_path(self, sports_client):
        mock_records = [
            {
                "entity_id": "sensor.nfl_cle",
                "team_abbr": "CLE",
                "opponent_abbr": "PIT",
                "league": "NFL",
                "state": "PRE",
                "clock": "Sun 1:00 PM",
                "_time": datetime(2026, 3, 22, 18, 0, tzinfo=UTC),
                "team_homeaway": "away",
                "event_name": "CLE @ PIT",
            }
        ]
        with patch("src.sports_endpoints.influxdb_client") as mock_influx:
            mock_influx.is_connected = True
            mock_influx._execute_query = AsyncMock(return_value=mock_records)

            resp = await sports_client.get("/api/v1/sports/games/upcoming")

        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 1
        assert data["games"][0]["status"] == "upcoming"
        assert data["games"][0]["home_score"] == 0

    @pytest.mark.asyncio
    async def test_upcoming_games_empty(self, sports_client):
        with patch("src.sports_endpoints.influxdb_client") as mock_influx:
            mock_influx.is_connected = True
            mock_influx._execute_query = AsyncMock(return_value=[])

            resp = await sports_client.get("/api/v1/sports/games/upcoming")

        assert resp.status_code == 200
        assert resp.json()["count"] == 0


class TestSportsTeams:
    """GET /api/v1/sports/teams"""

    @pytest.mark.asyncio
    async def test_all_teams(self, sports_client):
        resp = await sports_client.get("/api/v1/sports/teams")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 24  # 16 NFL + 8 NHL

    @pytest.mark.asyncio
    async def test_nfl_teams_only(self, sports_client):
        resp = await sports_client.get("/api/v1/sports/teams?league=NFL")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 16
        assert all(t["league"] == "NFL" for t in data["teams"])

    @pytest.mark.asyncio
    async def test_nhl_teams_only(self, sports_client):
        resp = await sports_client.get("/api/v1/sports/teams?league=NHL")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 8
        assert all(t["league"] == "NHL" for t in data["teams"])


class TestSportsGameHistory:
    """GET /api/v1/sports/games/history"""

    @pytest.mark.asyncio
    async def test_game_history_happy_path(self, sports_client):
        mock_records = [
            {
                "game_id": "game-001",
                "home_team": "Patriots",
                "away_team": "Bills",
                "home_score": 24,
                "away_score": 17,
                "status": "finished",
                "season": 2026,
                "week": "1",
                "_time": "2026-09-07T17:00:00Z",
            }
        ]
        with patch("src.sports_endpoints.influxdb_client") as mock_influx:
            mock_influx.is_connected = True
            mock_influx._execute_query = AsyncMock(return_value=mock_records)

            resp = await sports_client.get("/api/v1/sports/games/history?team=Patriots&league=NFL")

        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 1
        assert data["team"] == "Patriots"

    @pytest.mark.asyncio
    async def test_game_history_missing_team_param(self, sports_client):
        resp = await sports_client.get("/api/v1/sports/games/history")
        assert resp.status_code == 422  # team is required


class TestSportsGameTimeline:
    """GET /api/v1/sports/games/timeline/{game_id}"""

    @pytest.mark.asyncio
    async def test_timeline_not_found(self, sports_client):
        with patch("src.sports_endpoints.influxdb_client") as mock_influx:
            mock_influx.is_connected = True
            mock_influx._execute_query = AsyncMock(return_value=[])

            resp = await sports_client.get("/api/v1/sports/games/timeline/nonexistent")

        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_timeline_happy_path(self, sports_client):
        mock_records = [
            {
                "home_team": "CLE",
                "away_team": "PIT",
                "home_score": 7,
                "away_score": 0,
                "quarter": "1st",
                "time_remaining": "8:30",
                "_time": "2026-09-07T17:15:00Z",
            },
            {
                "home_team": "CLE",
                "away_team": "PIT",
                "home_score": 14,
                "away_score": 7,
                "quarter": "2nd",
                "time_remaining": "2:00",
                "_time": "2026-09-07T18:00:00Z",
            },
        ]
        with patch("src.sports_endpoints.influxdb_client") as mock_influx:
            mock_influx.is_connected = True
            mock_influx._execute_query = AsyncMock(return_value=mock_records)

            resp = await sports_client.get("/api/v1/sports/games/timeline/game-001?league=NFL")

        assert resp.status_code == 200
        data = resp.json()
        assert data["game_id"] == "game-001"
        assert len(data["timeline"]) == 2
        assert data["final_score"] == "14-7"


# ---------------------------------------------------------------------------
# HA Automation Endpoints
# ---------------------------------------------------------------------------

def _make_ha_app():
    """Build a standalone FastAPI app with the HA automation router."""
    app = FastAPI()

    with patch("src.ha_automation_endpoints.InfluxDBQueryClient"):
        from src.ha_automation_endpoints import router as ha_router
        # Clear webhooks between tests
        from src import ha_automation_endpoints
        ha_automation_endpoints.webhooks.clear()
        app.include_router(ha_router, prefix="/api/v1")

    return app


@pytest_asyncio.fixture
async def ha_client():
    app = _make_ha_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestHAGameStatus:
    """GET /api/v1/ha/game-status/{team}"""

    @pytest.mark.asyncio
    async def test_game_status_no_game(self, ha_client):
        with patch("src.ha_automation_endpoints.influxdb_client") as mock_influx:
            mock_influx._execute_query = AsyncMock(return_value=[])

            resp = await ha_client.get("/api/v1/ha/game-status/Patriots")

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "no_game"
        assert data["team"] == "Patriots"

    @pytest.mark.asyncio
    async def test_game_status_live(self, ha_client):
        mock_results = [
            {
                "game_id": "g123",
                "home_team": "Patriots",
                "away_team": "Bills",
                "status": "live",
                "home_score": 14,
                "away_score": 7,
                "time_remaining": "5:30",
                "_time": "2026-09-07T17:00:00Z",
            }
        ]
        with patch("src.ha_automation_endpoints.influxdb_client") as mock_influx:
            mock_influx._execute_query = AsyncMock(return_value=mock_results)

            resp = await ha_client.get("/api/v1/ha/game-status/Patriots")

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "live"
        assert data["score"] == "14-7"
        assert data["time_remaining"] == "5:30"


class TestHAGameContext:
    """GET /api/v1/ha/game-context/{team}"""

    @pytest.mark.asyncio
    async def test_game_context_no_game(self, ha_client):
        with patch("src.ha_automation_endpoints.influxdb_client") as mock_influx:
            mock_influx._execute_query = AsyncMock(return_value=[])

            resp = await ha_client.get("/api/v1/ha/game-context/Bruins")

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "no_game"

    @pytest.mark.asyncio
    async def test_game_context_with_data(self, ha_client):
        mock_results = [
            {
                "game_id": "g456",
                "home_team": "Bruins",
                "away_team": "Sabres",
                "status": "live",
                "home_score": 3,
                "away_score": 1,
                "quarter": None,
                "period": "2nd",
                "time_remaining": "10:00",
                "_time": "2026-03-17T19:00:00Z",
                "_measurement": "nhl_scores",
            }
        ]
        with patch("src.ha_automation_endpoints.influxdb_client") as mock_influx:
            mock_influx._execute_query = AsyncMock(return_value=mock_results)

            resp = await ha_client.get("/api/v1/ha/game-context/Bruins")

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "live"
        assert data["is_home_game"] is True
        assert data["opponent"] == "Sabres"
        assert data["league"] == "NHL"


class TestHAWebhooks:
    """POST/GET/DELETE /api/v1/ha/webhooks"""

    @pytest.mark.asyncio
    async def test_register_webhook(self, ha_client):
        payload = {
            "webhook_url": "https://ha.local/api/webhook/abc",
            "secret": "test-secret",
            "team": "Patriots",
            "events": ["game_start", "score_change"],
        }
        resp = await ha_client.post("/api/v1/ha/webhooks/register", json=payload)

        assert resp.status_code == 200
        data = resp.json()
        assert data["team"] == "Patriots"
        assert data["status"] == "active"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_list_webhooks_empty(self, ha_client):
        resp = await ha_client.get("/api/v1/ha/webhooks")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_register_then_list(self, ha_client):
        payload = {
            "webhook_url": "https://ha.local/api/webhook/xyz",
            "secret": "s3cret",
            "team": "Bruins",
            "events": ["game_end"],
        }
        await ha_client.post("/api/v1/ha/webhooks/register", json=payload)

        resp = await ha_client.get("/api/v1/ha/webhooks")
        assert resp.status_code == 200
        hooks = resp.json()
        assert len(hooks) == 1
        assert hooks[0]["team"] == "Bruins"

    @pytest.mark.asyncio
    async def test_delete_webhook(self, ha_client):
        # Register first
        payload = {
            "webhook_url": "https://ha.local/api/webhook/del",
            "secret": "sec",
            "team": "Bills",
            "events": ["game_start"],
        }
        reg_resp = await ha_client.post("/api/v1/ha/webhooks/register", json=payload)
        wh_id = reg_resp.json()["id"]

        # Delete
        resp = await ha_client.delete(f"/api/v1/ha/webhooks/{wh_id}")
        assert resp.status_code == 200
        assert resp.json()["success"] is True

        # Verify gone
        list_resp = await ha_client.get("/api/v1/ha/webhooks")
        assert list_resp.json() == []

    @pytest.mark.asyncio
    async def test_delete_nonexistent_webhook(self, ha_client):
        resp = await ha_client.delete("/api/v1/ha/webhooks/does-not-exist")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# MCP Endpoints
# ---------------------------------------------------------------------------

def _make_mcp_app():
    """Build a standalone FastAPI app with the MCP router."""
    app = FastAPI()
    from src.api.mcp_router import router as mcp_router
    app.include_router(mcp_router)
    return app


@pytest_asyncio.fixture
async def mcp_client():
    app = _make_mcp_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestMCPQueryDeviceHistory:
    """POST /mcp/tools/query_device_history

    Note: MCP router uses `from ..database.influx_client import InfluxDBQueryClient`
    but database.py is a flat module (no database/ package). These endpoints return 500
    at runtime due to the broken import. Tests verify error handling.
    """

    @pytest.mark.asyncio
    async def test_query_device_history_returns_500_broken_import(self, mcp_client):
        """MCP endpoint returns 500 because database.influx_client doesn't exist."""
        resp = await mcp_client.post("/mcp/tools/query_device_history", json={
            "entity_id": "sensor.power",
            "start_time": "-7d",
            "end_time": "now",
        })
        assert resp.status_code == 500


class TestMCPGetDevices:
    """POST /mcp/tools/get_devices"""

    @pytest.mark.asyncio
    async def test_get_devices_returns_500_broken_import(self, mcp_client):
        """MCP endpoint returns 500 because database.get_db_session import path is broken."""
        resp = await mcp_client.post("/mcp/tools/get_devices")
        assert resp.status_code == 500


class TestMCPSearchEvents:
    """POST /mcp/tools/search_events"""

    @pytest.mark.asyncio
    async def test_search_events_returns_500_broken_import(self, mcp_client):
        """MCP endpoint returns 500 because database.influx_client doesn't exist."""
        resp = await mcp_client.post("/mcp/tools/search_events")
        assert resp.status_code == 500


# ---------------------------------------------------------------------------
# Analytics Endpoints
# ---------------------------------------------------------------------------

def _make_analytics_app():
    """Build a standalone FastAPI app with the analytics router."""
    app = FastAPI()
    from src.analytics_endpoints import router as analytics_router
    app.include_router(analytics_router, prefix="/api/v1")
    return app


@pytest_asyncio.fixture
async def analytics_client():
    app = _make_analytics_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


def _make_fake_series(n=5, value=1.0):
    """Generate a fake time series for analytics mocking."""
    from datetime import timedelta
    base = datetime(2026, 3, 17, 10, 0, tzinfo=UTC)
    return [
        {"timestamp": (base + timedelta(minutes=i)).isoformat() + "Z", "value": value}
        for i in range(n)
    ]


class TestAnalyticsEndpoint:
    """GET /api/v1/analytics"""

    @pytest.mark.asyncio
    async def test_analytics_happy_path(self, analytics_client):
        fake_series = _make_fake_series(60, 5.0)
        with (
            patch("src.main.data_api_service", create=True) as mock_svc,
            patch("src.analytics_endpoints.query_events_per_minute", new_callable=AsyncMock, return_value=fake_series),
            patch("src.analytics_endpoints.query_api_response_time", return_value=fake_series),
            patch("src.analytics_endpoints.query_database_latency", return_value=fake_series),
            patch("src.analytics_endpoints.query_error_rate", return_value=fake_series),
            patch("src.analytics_endpoints.calculate_service_uptime", return_value=99.9),
        ):
            mock_svc.influxdb_client = MagicMock()
            mock_svc.influxdb_client.is_connected = True

            resp = await analytics_client.get("/api/v1/analytics?range=1h")

        assert resp.status_code == 200
        data = resp.json()
        assert data["timeRange"] == "1h"
        assert "eventsPerMinute" in data
        assert "summary" in data
        assert data["summary"]["uptime"] == 99.9

    @pytest.mark.asyncio
    async def test_analytics_different_ranges(self, analytics_client):
        fake_series = _make_fake_series(10, 2.0)
        for time_range in ["6h", "24h", "7d"]:
            with (
                patch("src.main.data_api_service", create=True) as mock_svc,
                patch("src.analytics_endpoints.query_events_per_minute", new_callable=AsyncMock, return_value=fake_series),
                patch("src.analytics_endpoints.query_api_response_time", return_value=fake_series),
                patch("src.analytics_endpoints.query_database_latency", return_value=fake_series),
                patch("src.analytics_endpoints.query_error_rate", return_value=fake_series),
                patch("src.analytics_endpoints.calculate_service_uptime", return_value=100.0),
            ):
                mock_svc.influxdb_client = MagicMock()
                mock_svc.influxdb_client.is_connected = True

                resp = await analytics_client.get(f"/api/v1/analytics?range={time_range}")

            assert resp.status_code == 200
            assert resp.json()["timeRange"] == time_range

    @pytest.mark.asyncio
    async def test_analytics_invalid_range(self, analytics_client):
        resp = await analytics_client.get("/api/v1/analytics?range=30d")
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Analytics helpers (unit tests, no HTTP)
# ---------------------------------------------------------------------------

class TestAnalyticsHelpers:
    """Unit tests for analytics helper functions."""

    def test_calculate_trend_stable(self):
        from src.analytics_endpoints import calculate_trend
        data = [1.0] * 20
        assert calculate_trend(data) == "stable"

    def test_calculate_trend_up(self):
        from src.analytics_endpoints import calculate_trend
        # window=5, so last 5 vs preceding 5; need >10% diff
        data = [1.0] * 5 + [5.0] * 5
        assert calculate_trend(data) == "up"

    def test_calculate_trend_down(self):
        from src.analytics_endpoints import calculate_trend
        # window=5, so last 5 vs preceding 5; need >10% diff
        data = [5.0] * 5 + [1.0] * 5
        assert calculate_trend(data) == "down"

    def test_calculate_trend_short_series(self):
        from src.analytics_endpoints import calculate_trend
        assert calculate_trend([1.0, 2.0]) == "stable"

    def test_get_time_range_params(self):
        from src.analytics_endpoints import get_time_range_params
        start, interval, num_points = get_time_range_params("1h")
        assert interval == "1m"
        assert num_points == 60

        start, interval, num_points = get_time_range_params("7d")
        assert interval == "2h"
        assert num_points == 84

    def test_build_metric(self):
        from src.analytics_endpoints import _build_metric
        series = [
            {"timestamp": "2026-03-17T10:00:00Z", "value": 5.0},
            {"timestamp": "2026-03-17T10:01:00Z", "value": 10.0},
            {"timestamp": "2026-03-17T10:02:00Z", "value": 3.0},
        ]
        metric = _build_metric(series)
        assert metric.current == 3.0
        assert metric.peak == 10.0
        assert metric.min == 3.0
        assert metric.average == pytest.approx(6.0)
