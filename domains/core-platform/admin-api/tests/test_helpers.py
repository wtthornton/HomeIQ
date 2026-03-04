"""Tests for Admin API helper functions."""

from unittest.mock import AsyncMock, patch

import pytest
from src.helpers import (
    build_health_summary,
    compute_error_rate,
    empty_real_time_metrics,
    format_uptime,
    gather_dependency_checks,
)


class TestFormatUptime:
    """Tests for format_uptime helper."""

    def test_zero_seconds(self) -> None:
        assert format_uptime(0.0) == "0h 0m 0s"

    def test_seconds_only(self) -> None:
        assert format_uptime(45.0) == "0h 0m 45s"

    def test_minutes_and_seconds(self) -> None:
        assert format_uptime(125.0) == "0h 2m 5s"

    def test_hours_minutes_seconds(self) -> None:
        assert format_uptime(3661.0) == "1h 1m 1s"

    def test_large_uptime(self) -> None:
        assert format_uptime(90061.0) == "25h 1m 1s"


class TestComputeErrorRate:
    """Tests for compute_error_rate helper."""

    def test_zero_requests(self) -> None:
        assert compute_error_rate(0, 0) == 0.0

    def test_no_errors(self) -> None:
        assert compute_error_rate(100, 0) == 0.0

    def test_all_errors(self) -> None:
        assert compute_error_rate(10, 10) == 100.0

    def test_partial_errors(self) -> None:
        assert compute_error_rate(200, 5) == 2.5

    def test_rounds_to_two_decimal_places(self) -> None:
        result = compute_error_rate(3, 1)
        assert result == 33.33


class TestBuildHealthSummary:
    """Tests for build_health_summary helper."""

    def test_all_healthy(self) -> None:
        stats = {
            "active_calls": 10,
            "inactive_apis": 0,
            "error_apis": 0,
            "total_apis": 10,
        }
        result = build_health_summary(stats)
        assert result["healthy"] == 10
        assert result["unhealthy"] == 0
        assert result["total"] == 10
        assert result["health_percentage"] == 100.0

    def test_some_unhealthy(self) -> None:
        stats = {
            "active_calls": 7,
            "inactive_apis": 2,
            "error_apis": 1,
            "total_apis": 10,
        }
        result = build_health_summary(stats)
        assert result["healthy"] == 7
        assert result["unhealthy"] == 3
        assert result["health_percentage"] == 70.0

    def test_zero_total(self) -> None:
        stats = {
            "active_calls": 0,
            "inactive_apis": 0,
            "error_apis": 0,
            "total_apis": 0,
        }
        result = build_health_summary(stats)
        assert result["health_percentage"] == 0


class TestEmptyRealTimeMetrics:
    """Tests for empty_real_time_metrics helper."""

    def test_without_error(self) -> None:
        result = empty_real_time_metrics()
        assert result["events_per_hour"] == 0
        assert result["api_calls_active"] == 0
        assert result["total_apis"] == 0
        assert "timestamp" in result
        assert "error" not in result

    def test_with_error(self) -> None:
        result = empty_real_time_metrics(error="Connection refused")
        assert result["error"] == "Connection refused"
        assert result["events_per_hour"] == 0
        assert "timestamp" in result


class TestGatherDependencyChecks:
    """Tests for gather_dependency_checks helper."""

    @pytest.mark.asyncio
    async def test_all_healthy(self) -> None:
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.get.return_value = mock_response
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("src.helpers.aiohttp.ClientSession", return_value=mock_session):
            results = await gather_dependency_checks()

        assert len(results) == 3
        assert all(r["status"] == "healthy" for r in results)

    @pytest.mark.asyncio
    async def test_connection_failure(self) -> None:
        mock_session = AsyncMock()
        mock_session.get.side_effect = ConnectionError("Connection refused")
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("src.helpers.aiohttp.ClientSession", return_value=mock_session):
            results = await gather_dependency_checks()

        assert len(results) == 3
        assert all(r["status"] == "unhealthy" for r in results)
