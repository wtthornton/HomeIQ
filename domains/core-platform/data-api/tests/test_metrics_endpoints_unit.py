"""Unit tests for MetricsEndpoints — metrics_endpoints.py

Tests metrics collection, aggregation, and reset endpoints
with mocked MetricsCollector and aiohttp sessions.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.metrics_endpoints import MetricsEndpoints, create_metrics_router, ServiceMetrics


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_collector(**overrides):
    """Create a mock MetricsCollector with sensible defaults."""
    collector = MagicMock()
    collector.get_all_metrics.return_value = overrides.get("all_metrics", {
        "service": "admin-api",
        "timestamp": "2026-03-18T10:00:00Z",
        "uptime_seconds": 3600.0,
        "counters": {"request_count": 100},
        "gauges": {"active_connections": 5.0},
        "timers": {"request_latency": {"avg_ms": 12.5, "p95_ms": 45.0}},
        "system": {
            "cpu": {"percent": 22.5},
            "memory": {"rss_mb": 128.0},
        },
    })
    collector.get_system_metrics.return_value = overrides.get("system_metrics", {
        "cpu": {"percent": 22.5, "count": 4},
        "memory": {"rss_mb": 128.0, "vms_mb": 512.0},
        "disk": {"usage_percent": 55.0},
    })
    collector.reset_metrics.return_value = None
    return collector


def _make_endpoints(collector=None):
    """Build MetricsEndpoints with a mock collector."""
    return MetricsEndpoints(metrics_collector=collector or _make_collector())


def _mock_aiohttp_response(status=200, json_data=None):
    """Create a mock aiohttp response context manager."""
    resp = AsyncMock()
    resp.status = status
    resp.json = AsyncMock(return_value=json_data or {})
    return resp


# ---------------------------------------------------------------------------
# ServiceMetrics pydantic model
# ---------------------------------------------------------------------------

class TestServiceMetricsModel:

    @pytest.mark.unit
    def test_valid_model(self):
        m = ServiceMetrics(
            service="test",
            timestamp="2026-03-18T10:00:00Z",
            uptime_seconds=100.0,
            counters={"a": 1},
            gauges={"b": 2.0},
            timers={"c": {"avg_ms": 3.0}},
            system={"cpu": {"percent": 10}},
        )
        assert m.service == "test"
        assert m.uptime_seconds == 100.0

    @pytest.mark.unit
    def test_empty_dicts(self):
        m = ServiceMetrics(
            service="s",
            timestamp="t",
            uptime_seconds=0,
            counters={},
            gauges={},
            timers={},
            system={},
        )
        assert m.counters == {}


# ---------------------------------------------------------------------------
# GET /metrics
# ---------------------------------------------------------------------------

class TestGetAdminMetrics:

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_collector_metrics(self):
        collector = _make_collector()
        ep = _make_endpoints(collector)

        # Resolve the route handler
        handler = _get_route_handler(ep, "/metrics", "GET")
        result = await handler()

        assert result["service"] == "admin-api"
        assert result["counters"]["request_count"] == 100
        collector.get_all_metrics.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_collector_error_raises_500(self):
        collector = _make_collector()
        collector.get_all_metrics.side_effect = RuntimeError("boom")
        ep = _make_endpoints(collector)

        handler = _get_route_handler(ep, "/metrics", "GET")
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await handler()
        assert exc_info.value.status_code == 500
        assert "boom" in exc_info.value.detail


# ---------------------------------------------------------------------------
# GET /metrics/system
# ---------------------------------------------------------------------------

class TestGetSystemMetrics:

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_system_metrics(self):
        collector = _make_collector()
        ep = _make_endpoints(collector)
        handler = _get_route_handler(ep, "/metrics/system", "GET")

        result = await handler()

        assert result["cpu"]["percent"] == 22.5
        assert result["memory"]["rss_mb"] == 128.0
        collector.get_system_metrics.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_system_metrics_error_raises_500(self):
        collector = _make_collector()
        collector.get_system_metrics.side_effect = RuntimeError("fail")
        ep = _make_endpoints(collector)
        handler = _get_route_handler(ep, "/metrics/system", "GET")

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await handler()
        assert exc_info.value.status_code == 500


# ---------------------------------------------------------------------------
# POST /metrics/reset
# ---------------------------------------------------------------------------

class TestResetMetrics:

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_reset_success(self):
        collector = _make_collector()
        ep = _make_endpoints(collector)
        handler = _get_route_handler(ep, "/metrics/reset", "POST")

        result = await handler()

        assert result["status"] == "success"
        assert "timestamp" in result
        collector.reset_metrics.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_reset_error_raises_500(self):
        collector = _make_collector()
        collector.reset_metrics.side_effect = RuntimeError("reset failed")
        ep = _make_endpoints(collector)
        handler = _get_route_handler(ep, "/metrics/reset", "POST")

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await handler()
        assert exc_info.value.status_code == 500


# ---------------------------------------------------------------------------
# GET /metrics/all
# ---------------------------------------------------------------------------

class TestGetAllServicesMetrics:

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_aggregates_from_multiple_services(self):
        collector = _make_collector()
        ep = _make_endpoints(collector)
        handler = _get_route_handler(ep, "/metrics/all", "GET")

        remote_metrics = {
            "service": "websocket-ingestion",
            "timestamp": "2026-03-18T10:00:00Z",
            "uptime_seconds": 7200.0,
            "counters": {},
            "gauges": {},
            "timers": {},
            "system": {},
        }

        mock_resp = _mock_aiohttp_response(status=200, json_data=remote_metrics)

        with patch("src.metrics_endpoints.aiohttp.ClientSession") as mock_session_cls:
            session_ctx = AsyncMock()
            session_ctx.__aenter__ = AsyncMock(return_value=session_ctx)
            session_ctx.__aexit__ = AsyncMock(return_value=False)
            session_ctx.get.return_value.__aenter__ = AsyncMock(return_value=mock_resp)
            session_ctx.get.return_value.__aexit__ = AsyncMock(return_value=False)

            mock_session_cls.return_value = session_ctx

            result = await handler()

        assert "admin-api" in result

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_graceful_degradation_service_down(self):
        """When a remote service is unreachable, it should be skipped."""
        collector = _make_collector()
        ep = _make_endpoints(collector)
        handler = _get_route_handler(ep, "/metrics/all", "GET")

        with patch("src.metrics_endpoints.aiohttp.ClientSession") as mock_session_cls:
            session_ctx = AsyncMock()
            session_ctx.__aenter__ = AsyncMock(return_value=session_ctx)
            session_ctx.__aexit__ = AsyncMock(return_value=False)
            session_ctx.get.side_effect = ConnectionError("service down")

            mock_session_cls.return_value = session_ctx

            result = await handler()

        # Only admin-api should be present (remote services failed gracefully)
        assert "admin-api" in result

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_non_200_response_skipped(self):
        """Services returning non-200 are logged and skipped."""
        collector = _make_collector()
        ep = _make_endpoints(collector)
        handler = _get_route_handler(ep, "/metrics/all", "GET")

        mock_resp = _mock_aiohttp_response(status=503, json_data={})

        with patch("src.metrics_endpoints.aiohttp.ClientSession") as mock_session_cls:
            session_ctx = AsyncMock()
            session_ctx.__aenter__ = AsyncMock(return_value=session_ctx)
            session_ctx.__aexit__ = AsyncMock(return_value=False)
            session_ctx.get.return_value.__aenter__ = AsyncMock(return_value=mock_resp)
            session_ctx.get.return_value.__aexit__ = AsyncMock(return_value=False)

            mock_session_cls.return_value = session_ctx

            result = await handler()

        assert "admin-api" in result

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_collector_error_on_all_raises_500(self):
        collector = _make_collector()
        collector.get_all_metrics.side_effect = RuntimeError("total failure")
        ep = _make_endpoints(collector)
        handler = _get_route_handler(ep, "/metrics/all", "GET")

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await handler()
        assert exc_info.value.status_code == 500


# ---------------------------------------------------------------------------
# GET /metrics/summary
# ---------------------------------------------------------------------------

class TestGetMetricsSummary:

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_summary_admin_only(self):
        """Summary with only admin-api (remote services fail)."""
        collector = _make_collector()
        ep = _make_endpoints(collector)
        handler = _get_route_handler(ep, "/metrics/summary", "GET")

        with patch("src.metrics_endpoints.aiohttp.ClientSession") as mock_session_cls:
            session_ctx = AsyncMock()
            session_ctx.__aenter__ = AsyncMock(return_value=session_ctx)
            session_ctx.__aexit__ = AsyncMock(return_value=False)
            session_ctx.get.side_effect = ConnectionError("unreachable")

            mock_session_cls.return_value = session_ctx

            result = await handler()

        assert result["services_count"] == 1
        assert "admin-api" in result["services"]
        assert "timestamp" in result
        assert result["aggregate"]["total_cpu_percent"] == 22.5
        assert result["aggregate"]["total_memory_mb"] == 128.0
        assert result["aggregate"]["total_uptime_seconds"] == 3600.0
        assert result["aggregate"]["total_requests"] == 100
        assert result["aggregate"]["avg_response_time_ms"] == 12.5

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_summary_aggregation_with_remote(self):
        """Summary aggregates CPU/memory/requests across services."""
        remote_metrics = {
            "service": "websocket-ingestion",
            "uptime_seconds": 1800.0,
            "counters": {"request_total": 50, "call_count": 20},
            "gauges": {},
            "timers": {"response_time": {"avg_ms": 8.0}},
            "system": {
                "cpu": {"percent": 10.0},
                "memory": {"rss_mb": 64.0},
            },
        }
        collector = _make_collector()
        ep = _make_endpoints(collector)
        handler = _get_route_handler(ep, "/metrics/summary", "GET")

        mock_resp = _mock_aiohttp_response(status=200, json_data=remote_metrics)

        with patch("src.metrics_endpoints.aiohttp.ClientSession") as mock_session_cls:
            session_ctx = AsyncMock()
            session_ctx.__aenter__ = AsyncMock(return_value=session_ctx)
            session_ctx.__aexit__ = AsyncMock(return_value=False)
            session_ctx.get.return_value.__aenter__ = AsyncMock(return_value=mock_resp)
            session_ctx.get.return_value.__aexit__ = AsyncMock(return_value=False)

            mock_session_cls.return_value = session_ctx

            result = await handler()

        # At minimum admin-api is present
        assert result["services_count"] >= 1
        assert result["aggregate"]["total_cpu_percent"] >= 22.5
        assert result["aggregate"]["total_uptime_seconds"] >= 3600.0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_summary_no_timers_avg_zero(self):
        """When no timer data, avg_response_time_ms stays 0."""
        collector = _make_collector(all_metrics={
            "service": "admin-api",
            "timestamp": "2026-03-18T10:00:00Z",
            "uptime_seconds": 100.0,
            "counters": {},
            "gauges": {},
            "timers": {},
            "system": {},
        })
        ep = _make_endpoints(collector)
        handler = _get_route_handler(ep, "/metrics/summary", "GET")

        with patch("src.metrics_endpoints.aiohttp.ClientSession") as mock_session_cls:
            session_ctx = AsyncMock()
            session_ctx.__aenter__ = AsyncMock(return_value=session_ctx)
            session_ctx.__aexit__ = AsyncMock(return_value=False)
            session_ctx.get.side_effect = ConnectionError("down")

            mock_session_cls.return_value = session_ctx

            result = await handler()

        assert result["aggregate"]["avg_response_time_ms"] == 0.0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_summary_collector_error_gracefully_skipped(self):
        """When admin-api collector raises, summary continues with 0 services."""
        collector = _make_collector()
        collector.get_all_metrics.side_effect = RuntimeError("explode")
        ep = _make_endpoints(collector)
        handler = _get_route_handler(ep, "/metrics/summary", "GET")

        with patch("src.metrics_endpoints.aiohttp.ClientSession") as mock_session_cls:
            session_ctx = AsyncMock()
            session_ctx.__aenter__ = AsyncMock(return_value=session_ctx)
            session_ctx.__aexit__ = AsyncMock(return_value=False)
            session_ctx.get.side_effect = ConnectionError("down")
            mock_session_cls.return_value = session_ctx

            result = await handler()

        # admin-api failed, remote services failed — empty result
        assert result["services_count"] == 0
        assert result["services"] == []


# ---------------------------------------------------------------------------
# create_metrics_router factory
# ---------------------------------------------------------------------------

class TestCreateMetricsRouter:

    @pytest.mark.unit
    def test_returns_api_router(self):
        from fastapi import APIRouter
        collector = _make_collector()
        router = create_metrics_router(collector)
        assert isinstance(router, APIRouter)

    @pytest.mark.unit
    def test_router_has_expected_routes(self):
        collector = _make_collector()
        router = create_metrics_router(collector)
        paths = [r.path for r in router.routes]
        assert "/metrics" in paths
        assert "/metrics/all" in paths
        assert "/metrics/system" in paths
        assert "/metrics/summary" in paths
        assert "/metrics/reset" in paths

    @pytest.mark.unit
    def test_factory_with_none_uses_default(self):
        with patch("src.metrics_endpoints.get_metrics_collector") as mock_get:
            mock_get.return_value = _make_collector()
            router = create_metrics_router(None)
            mock_get.assert_called_once_with("admin-api")
            assert router is not None


# ---------------------------------------------------------------------------
# MetricsEndpoints init
# ---------------------------------------------------------------------------

class TestMetricsEndpointsInit:

    @pytest.mark.unit
    def test_default_service_urls(self):
        collector = _make_collector()
        ep = _make_endpoints(collector)
        assert "websocket-ingestion" in ep.service_urls
        assert "data-retention" in ep.service_urls
        assert "log-aggregator" in ep.service_urls

    @pytest.mark.unit
    def test_custom_service_urls_via_env(self):
        collector = _make_collector()
        with patch.dict("os.environ", {
            "WEBSOCKET_INGESTION_URL": "http://custom:9000",
        }):
            ep = MetricsEndpoints(metrics_collector=collector)
            assert ep.service_urls["websocket-ingestion"] == "http://custom:9000"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_route_handler(ep: MetricsEndpoints, path: str, method: str = "GET"):
    """Extract the route handler function from the router."""
    for route in ep.router.routes:
        if hasattr(route, "path") and route.path == path:
            if method.upper() in [m.upper() for m in route.methods]:
                return route.endpoint
    raise ValueError(f"Route {method} {path} not found")
