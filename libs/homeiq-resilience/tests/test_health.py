"""Tests for GroupHealthCheck and DependencyStatus.

Covers:
  - Healthy status when all deps are up
  - Degraded status when some deps are down
  - Unhealthy status when all deps are down
  - Structured response format
  - No-dependency edge case
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest
from shared.resilience.health import DependencyStatus, GroupHealthCheck


@pytest.fixture
def health_check() -> GroupHealthCheck:
    """Create a health checker for tests."""
    hc = GroupHealthCheck(group_name="automation-intelligence", version="1.2.3")
    hc.register_dependency("data-api", "http://data-api:8006")
    hc.register_dependency("ai-core-service", "http://ai-core-service:8018")
    return hc


# ------------------------------------------------------------------
# DependencyStatus dataclass
# ------------------------------------------------------------------


class TestDependencyStatus:
    def test_defaults(self) -> None:
        dep = DependencyStatus(name="data-api")
        assert dep.name == "data-api"
        assert dep.status == "unknown"
        assert dep.latency_ms is None
        assert dep.last_seen is None

    def test_full_construction(self) -> None:
        dep = DependencyStatus(
            name="data-api",
            status="healthy",
            latency_ms=12.5,
            last_seen="2026-02-22T10:00:00+00:00",
        )
        assert dep.status == "healthy"
        assert dep.latency_ms == 12.5


# ------------------------------------------------------------------
# Healthy: all dependencies up
# ------------------------------------------------------------------


def _make_ok_response() -> httpx.Response:
    """Create a mock 200 response."""
    return httpx.Response(status_code=200, request=httpx.Request("GET", "http://test"))


def _make_500_response() -> httpx.Response:
    """Create a mock 500 response."""
    return httpx.Response(status_code=500, request=httpx.Request("GET", "http://test"))


class TestAllHealthy:
    @pytest.mark.asyncio
    async def test_status_healthy_when_all_deps_up(
        self, health_check: GroupHealthCheck
    ) -> None:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=_make_ok_response())

        with patch("shared.resilience.health.httpx.AsyncClient", return_value=mock_client):
            result = await health_check.to_dict()

        assert result["status"] == "healthy"
        assert result["group"] == "automation-intelligence"
        assert result["version"] == "1.2.3"
        assert "data-api" in result["dependencies"]
        assert result["dependencies"]["data-api"]["status"] == "healthy"
        assert "ai-core-service" in result["dependencies"]
        assert result["dependencies"]["ai-core-service"]["status"] == "healthy"


# ------------------------------------------------------------------
# Degraded: some deps down
# ------------------------------------------------------------------


class TestDegraded:
    @pytest.mark.asyncio
    async def test_status_degraded_when_some_deps_down(
        self, health_check: GroupHealthCheck
    ) -> None:
        call_count = 0

        async def mock_get(_url: str) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _make_ok_response()
            raise httpx.ConnectError("Connection refused")

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = mock_get

        with patch("shared.resilience.health.httpx.AsyncClient", return_value=mock_client):
            result = await health_check.to_dict()

        assert result["status"] == "degraded"
        statuses = [d["status"] for d in result["dependencies"].values()]
        assert "healthy" in statuses
        assert "unreachable" in statuses


# ------------------------------------------------------------------
# Unhealthy: all deps down
# ------------------------------------------------------------------


class TestUnhealthy:
    @pytest.mark.asyncio
    async def test_status_unhealthy_when_all_deps_down(
        self, health_check: GroupHealthCheck
    ) -> None:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(
            side_effect=httpx.ConnectError("Connection refused")
        )

        with patch("shared.resilience.health.httpx.AsyncClient", return_value=mock_client):
            result = await health_check.to_dict()

        assert result["status"] == "unhealthy"
        for dep in result["dependencies"].values():
            assert dep["status"] == "unreachable"

    @pytest.mark.asyncio
    async def test_unhealthy_http_status(
        self, health_check: GroupHealthCheck
    ) -> None:
        """Non-200 responses are 'unhealthy' (not 'unreachable')."""
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=_make_500_response())

        with patch("shared.resilience.health.httpx.AsyncClient", return_value=mock_client):
            result = await health_check.to_dict()

        assert result["status"] == "unhealthy"
        for dep in result["dependencies"].values():
            assert dep["status"] == "unhealthy"


# ------------------------------------------------------------------
# Structured response format
# ------------------------------------------------------------------


class TestResponseFormat:
    @pytest.mark.asyncio
    async def test_response_has_all_required_fields(
        self, health_check: GroupHealthCheck
    ) -> None:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=_make_ok_response())

        with patch("shared.resilience.health.httpx.AsyncClient", return_value=mock_client):
            result = await health_check.to_dict()

        required_keys = {
            "status",
            "group",
            "version",
            "uptime_seconds",
            "dependencies",
            "degraded_features",
        }
        assert required_keys.issubset(result.keys())
        assert isinstance(result["uptime_seconds"], int)
        assert isinstance(result["dependencies"], dict)
        assert isinstance(result["degraded_features"], list)

    @pytest.mark.asyncio
    async def test_latency_is_rounded(
        self, health_check: GroupHealthCheck
    ) -> None:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=_make_ok_response())

        with patch("shared.resilience.health.httpx.AsyncClient", return_value=mock_client):
            result = await health_check.to_dict()

        for dep in result["dependencies"].values():
            if "latency_ms" in dep:
                # Check it's rounded to 1 decimal
                assert dep["latency_ms"] == round(dep["latency_ms"], 1)


# ------------------------------------------------------------------
# No dependencies registered
# ------------------------------------------------------------------


class TestNoDependencies:
    @pytest.mark.asyncio
    async def test_healthy_with_no_deps(self) -> None:
        hc = GroupHealthCheck(group_name="standalone", version="1.0.0")
        result = await hc.to_dict()

        assert result["status"] == "healthy"
        assert result["dependencies"] == {}


# ------------------------------------------------------------------
# Degraded features
# ------------------------------------------------------------------


class TestDegradedFeatures:
    @pytest.mark.asyncio
    async def test_degraded_features_listed(self) -> None:
        hc = GroupHealthCheck(group_name="test", version="1.0.0")
        hc.add_degraded_feature("ml-powered suggestions (using rule-based fallback)")
        result = await hc.to_dict()

        assert "ml-powered suggestions (using rule-based fallback)" in result["degraded_features"]

    @pytest.mark.asyncio
    async def test_remove_degraded_feature(self) -> None:
        hc = GroupHealthCheck(group_name="test", version="1.0.0")
        hc.add_degraded_feature("some-feature")
        hc.remove_degraded_feature("some-feature")
        result = await hc.to_dict()

        assert result["degraded_features"] == []

    @pytest.mark.asyncio
    async def test_no_duplicate_degraded_features(self) -> None:
        hc = GroupHealthCheck(group_name="test", version="1.0.0")
        hc.add_degraded_feature("same-feature")
        hc.add_degraded_feature("same-feature")
        result = await hc.to_dict()

        assert result["degraded_features"].count("same-feature") == 1
