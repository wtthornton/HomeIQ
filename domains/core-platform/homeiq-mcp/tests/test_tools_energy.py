"""Tests for energy summary tool (TAP-5295)."""

from __future__ import annotations

import respx
from httpx import Response
from src.auth import READ_SCOPES
from src.tools import energy


async def test_get_energy_summary_happy_path(registry, backings) -> None:
    """Test get_energy_summary with all data available."""
    energy.register(registry, backings)

    energy_stats = {
        "current_power_w": 2500.5,
        "daily_kwh": 45.3,
        "peak_power_w": 5200.0,
        "peak_time": "2026-08-17T14:30:00Z",
        "average_power_w": 1875.0,
        "total_correlations": 42,
    }

    consumers_list = [
        {
            "entity_id": "switch.water_heater",
            "domain": "switch",
            "average_power_on_w": 4500.0,
            "average_power_off_w": 0.0,
            "total_state_changes": 15,
            "estimated_daily_kwh": 36.0,
            "estimated_monthly_cost": 129.6,
        },
        {
            "entity_id": "climate.thermostat",
            "domain": "climate",
            "average_power_on_w": 2000.0,
            "average_power_off_w": 100.0,
            "total_state_changes": 120,
            "estimated_daily_kwh": 16.0,
            "estimated_monthly_cost": 57.6,
        },
    ]

    carbon = {
        "timestamp": "2026-08-17T14:35:00Z",
        "intensity": 385.5,
        "renewable_percentage": 45.2,
        "fossil_percentage": 54.8,
        "forecast_1h": 390.0,
        "forecast_24h": 395.0,
        "region": "us-west-1",
        "grid_operator": "CAISO",
    }

    with respx.mock:
        respx.get("http://data-api.test:8006/api/v1/energy/statistics").mock(
            return_value=Response(200, json=energy_stats)
        )
        respx.get("http://data-api.test:8006/api/v1/energy/top-consumers").mock(
            return_value=Response(200, json=consumers_list)
        )
        respx.get("http://data-api.test:8006/api/v1/energy/carbon-intensity/current").mock(
            return_value=Response(200, json=carbon)
        )

        payload = await registry.call("get_energy_summary", {}, scopes=READ_SCOPES)

        assert payload["current_power_w"] == 2500.5
        assert payload["daily_kwh"] == 45.3
        assert payload["peak_power_w"] == 5200.0
        assert payload["peak_time"] == "2026-08-17T14:30:00Z"
        assert payload["average_power_w"] == 1875.0
        assert len(payload["top_consumers"]) == 2
        assert payload["top_consumers"][0]["entity_id"] == "switch.water_heater"
        assert payload["carbon"]["grams_per_kwh"] == 385.5
        assert payload["carbon"]["source"] == "CAISO"
        assert payload["truncated"] is False


async def test_get_energy_summary_with_top_n(registry, backings) -> None:
    """Test get_energy_summary with top_n parameter."""
    energy.register(registry, backings)

    energy_stats = {
        "current_power_w": 1000.0,
        "daily_kwh": 20.0,
        "peak_power_w": 3000.0,
        "peak_time": None,
        "average_power_w": 800.0,
        "total_correlations": 10,
    }

    consumers_list = [
        {
            "entity_id": f"device_{i}",
            "domain": "switch",
            "average_power_on_w": 1000.0 - (i * 50),
            "average_power_off_w": 0.0,
            "total_state_changes": 5,
            "estimated_daily_kwh": 8.0,
            "estimated_monthly_cost": 28.8,
        }
        for i in range(5)
    ]

    with respx.mock:
        respx.get(
            "http://data-api.test:8006/api/v1/energy/statistics",
        ).mock(return_value=Response(200, json=energy_stats))

        respx.get(
            "http://data-api.test:8006/api/v1/energy/top-consumers",
            params={"limit": 5},
        ).mock(return_value=Response(200, json=consumers_list))

        respx.get("http://data-api.test:8006/api/v1/energy/carbon-intensity/current").mock(
            return_value=Response(404, json={"detail": "No data"})
        )

        payload = await registry.call("get_energy_summary", {"top_n": 5}, scopes=READ_SCOPES)

        assert len(payload["top_consumers"]) == 5
        assert "carbon" not in payload  # No carbon data available
        assert payload["truncated"] is False


async def test_get_energy_summary_consumer_row_cap(registry, backings) -> None:
    """Test get_energy_summary caps consumers at 20 rows."""
    energy.register(registry, backings)

    energy_stats = {
        "current_power_w": 1000.0,
        "daily_kwh": 20.0,
        "peak_power_w": 3000.0,
        "peak_time": None,
        "average_power_w": 800.0,
        "total_correlations": 10,
    }

    # Create 30 consumers to exceed the 20-row cap
    consumers_list = [
        {
            "entity_id": f"device_{i}",
            "domain": "switch",
            "average_power_on_w": 1000.0 - (i * 10),
            "average_power_off_w": 0.0,
            "total_state_changes": 5,
            "estimated_daily_kwh": 8.0,
            "estimated_monthly_cost": 28.8,
        }
        for i in range(30)
    ]

    with respx.mock:
        respx.get("http://data-api.test:8006/api/v1/energy/statistics").mock(
            return_value=Response(200, json=energy_stats)
        )
        respx.get("http://data-api.test:8006/api/v1/energy/top-consumers").mock(
            return_value=Response(200, json=consumers_list)
        )
        respx.get("http://data-api.test:8006/api/v1/energy/carbon-intensity/current").mock(
            return_value=Response(404)
        )

        payload = await registry.call("get_energy_summary", {}, scopes=READ_SCOPES)

        assert payload["truncated"] is True
        assert len(payload["top_consumers"]) <= 20
        assert payload["top_consumers"][0]["entity_id"] == "device_0"


async def test_get_energy_summary_missing_optional_fields(registry, backings) -> None:
    """Test get_energy_summary handles missing optional upstream fields."""
    energy.register(registry, backings)

    # Minimal upstream response
    energy_stats = {
        "current_power_w": 1000.0,
        "daily_kwh": 20.0,
        "peak_power_w": None,
        "peak_time": None,
        "average_power_w": None,
        "total_correlations": 0,
    }

    with respx.mock:
        respx.get("http://data-api.test:8006/api/v1/energy/statistics").mock(
            return_value=Response(200, json=energy_stats)
        )
        respx.get("http://data-api.test:8006/api/v1/energy/top-consumers").mock(
            return_value=Response(200, json=[])
        )
        respx.get("http://data-api.test:8006/api/v1/energy/carbon-intensity/current").mock(
            return_value=Response(404)
        )

        payload = await registry.call("get_energy_summary", {}, scopes=READ_SCOPES)

        assert payload["current_power_w"] == 1000.0
        assert payload["daily_kwh"] == 20.0
        assert "peak_power_w" not in payload  # None values omitted
        assert "peak_time" not in payload
        assert "average_power_w" not in payload
        assert "carbon" not in payload
        assert len(payload["top_consumers"]) == 0
        assert payload["truncated"] is False


async def test_get_energy_summary_consumer_minimal_fields(registry, backings) -> None:
    """Test get_energy_summary handles consumers with only required entity_id."""
    energy.register(registry, backings)

    energy_stats = {
        "current_power_w": 1000.0,
        "daily_kwh": 20.0,
        "peak_power_w": None,
        "peak_time": None,
        "average_power_w": None,
        "total_correlations": 0,
    }

    consumers_list = [
        {
            "entity_id": "device_1",
            "domain": "switch",
            "average_power_on_w": None,
            "average_power_off_w": None,
            "total_state_changes": 0,
            "estimated_daily_kwh": None,
            "estimated_monthly_cost": None,
        }
    ]

    with respx.mock:
        respx.get("http://data-api.test:8006/api/v1/energy/statistics").mock(
            return_value=Response(200, json=energy_stats)
        )
        respx.get("http://data-api.test:8006/api/v1/energy/top-consumers").mock(
            return_value=Response(200, json=consumers_list)
        )
        respx.get("http://data-api.test:8006/api/v1/energy/carbon-intensity/current").mock(
            return_value=Response(404)
        )

        payload = await registry.call("get_energy_summary", {}, scopes=READ_SCOPES)

        assert len(payload["top_consumers"]) == 1
        assert payload["top_consumers"][0]["entity_id"] == "device_1"
        assert "average_power_on_w" not in payload["top_consumers"][0]


def test_registry_names_after_energy_register(registry, backings) -> None:
    """Test that register() adds the expected tool names."""
    energy.register(registry, backings)

    names = registry.names()
    assert "get_energy_summary" in names
