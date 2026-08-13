"""Tests for the real-time-metrics fetch budget (TAP-5439).

The endpoint must answer within its budget even when a downstream stats
fetch hangs, degrading that fetch to its fallback rather than stalling the
dashboard's poll loop.
"""

import asyncio
import time

import pytest
from src.endpoints import (
    _RT_METRICS_BUDGET_SECONDS,
    _build_real_time_metrics,
    _empty_api_metrics,
)


class HealthyStats:
    """StatsEndpoints stand-in whose fetches answer immediately."""

    async def _get_current_event_rate(self) -> float:
        return 2.5

    async def _get_all_api_metrics(self) -> dict:
        return {
            "active_calls": 3,
            "api_metrics": [{"service": "weather-api", "status": "active"}],
            "inactive_apis": 1,
            "error_apis": 0,
            "total_apis": 4,
        }

    async def _get_active_data_sources(self) -> list[str]:
        return ["home_assistant_events"]


class HungStats(HealthyStats):
    """The api-metrics fetch hangs far past the budget; the rest answer."""

    async def _get_all_api_metrics(self) -> dict:
        await asyncio.sleep(60)
        raise AssertionError("unreachable")


@pytest.mark.asyncio
async def test_healthy_fetches_pass_through():
    result = await _build_real_time_metrics(HealthyStats())
    assert result["events_per_hour"] == 2.5 * 3600
    assert result["api_calls_active"] == 3
    assert result["total_apis"] == 4
    assert result["data_sources_active"] == ["home_assistant_events"]
    assert result["health_summary"]["healthy"] == 3


@pytest.mark.asyncio
async def test_hung_fetch_degrades_to_fallback_within_budget():
    started = time.monotonic()
    result = await _build_real_time_metrics(HungStats())
    elapsed = time.monotonic() - started

    # Answers promptly (budget plus scheduling slack), never the 10s the
    # serial weather-api double-fetch used to impose.
    assert elapsed < _RT_METRICS_BUDGET_SECONDS + 0.5

    # The hung fetch degraded to its fallback...
    assert result["total_apis"] == 0
    assert result["api_metrics"] == []
    assert result["health_summary"] == {
        "healthy": 0,
        "unhealthy": 0,
        "total": 0,
        "health_percentage": 0,
    }
    # ...while the healthy fetches still delivered real data.
    assert result["events_per_hour"] == 2.5 * 3600
    assert result["data_sources_active"] == ["home_assistant_events"]
    assert "error" not in result


def test_fallback_dict_is_fresh_per_call():
    first = _empty_api_metrics()
    first["api_metrics"].append("mutated")
    assert _empty_api_metrics()["api_metrics"] == []
