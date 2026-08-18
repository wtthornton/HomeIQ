"""Tests for device health tool (TAP-5295)."""

from __future__ import annotations

import respx
from httpx import Response
from src.auth import READ_SCOPES
from src.tools import device_health


async def test_get_device_health_single_device_no_trend(registry, backings) -> None:
    """Test get_device_health for a single device without trend."""
    device_health.register(registry, backings)

    device_score = {
        "device_id": "device_abc123",
        "overall_score": 92.5,
        "health_status": "healthy",
        "factor_scores": {
            "response_time": 95.0,
            "error_rate": 90.0,
            "battery_level": 85.0,
        },
    }

    with respx.mock:
        respx.get("http://devint.test:8028/api/health/scores/device_abc123").mock(
            return_value=Response(200, json=device_score)
        )

        payload = await registry.call(
            "get_device_health",
            {"device_id": "device_abc123"},
            scopes=READ_SCOPES,
        )

        assert "device" in payload
        assert payload["device"]["device_id"] == "device_abc123"
        assert payload["device"]["overall_score"] == 92.5
        assert payload["device"]["health_status"] == "healthy"
        assert payload["device"]["factor_scores"] == {
            "response_time": 95.0,
            "error_rate": 90.0,
            "battery_level": 85.0,
        }
        assert "summary" not in payload  # Single device, no summary
        assert "devices" not in payload  # Single device, no array
        assert payload["truncated"] is False


async def test_get_device_health_single_device_with_trend(registry, backings) -> None:
    """Test get_device_health for a single device with trend."""
    device_health.register(registry, backings)

    device_score = {
        "device_id": "device_abc123",
        "overall_score": 92.5,
        "health_status": "healthy",
        "factor_scores": {"response_time": 95.0},
    }

    trends = {
        "device_id": "device_abc123",
        "trends": [
            {
                "timestamp": "2026-08-10T00:00:00Z",
                "overall_score": 88.0,
                "health_status": "healthy",
            },
            {
                "timestamp": "2026-08-11T00:00:00Z",
                "overall_score": 90.0,
                "health_status": "healthy",
            },
            {
                "timestamp": "2026-08-12T00:00:00Z",
                "overall_score": 92.5,
                "health_status": "healthy",
            },
        ],
    }

    with respx.mock:
        respx.get("http://devint.test:8028/api/health/scores/device_abc123").mock(
            return_value=Response(200, json=device_score)
        )
        respx.get(
            "http://devint.test:8028/api/health/trends/device_abc123",
            params={"days": 7},
        ).mock(return_value=Response(200, json=trends))

        payload = await registry.call(
            "get_device_health",
            {"device_id": "device_abc123", "include_trend": True, "trend_days": 7},
            scopes=READ_SCOPES,
        )

        assert "device" in payload
        assert "trend" in payload["device"]
        assert len(payload["device"]["trend"]) == 3
        assert payload["device"]["trend"][0]["t"] == "2026-08-10T00:00:00Z"
        assert payload["device"]["trend"][0]["score"] == 88.0


async def test_get_device_health_fleet_summary(registry, backings) -> None:
    """Test get_device_health for fleet summary (no device_id)."""
    device_health.register(registry, backings)

    scores_response = {
        "health_scores": [
            {"device_id": "device_1", "overall_score": 95.0, "health_status": "healthy"},
            {"device_id": "device_2", "overall_score": 75.0, "health_status": "degraded"},
            {"device_id": "device_3", "overall_score": 45.0, "health_status": "critical"},
        ],
        "summary": {
            "total_devices": 3,
            "avg_score": 71.67,
        },
        "timestamp": "2026-08-17T12:00:00Z",
    }

    with respx.mock:
        respx.get("http://devint.test:8028/api/health/scores").mock(
            return_value=Response(200, json=scores_response)
        )

        payload = await registry.call(
            "get_device_health",
            {},
            scopes=READ_SCOPES,
        )

        assert "summary" in payload
        assert payload["summary"]["total"] == 3
        assert payload["summary"]["healthy"] == 1
        assert payload["summary"]["degraded"] == 1
        assert payload["summary"]["critical"] == 1
        assert "devices" in payload
        assert len(payload["devices"]) == 3
        assert payload["devices"][0]["device_id"] == "device_1"
        assert payload["truncated"] is False


async def test_get_device_health_fleet_with_filters(registry, backings) -> None:
    """Test get_device_health fleet with min_score and health_status filters."""
    device_health.register(registry, backings)

    scores_response = {
        "health_scores": [
            {"device_id": "device_1", "overall_score": 95.0, "health_status": "healthy"},
        ],
        "summary": {"total_devices": 1, "avg_score": 95.0},
        "timestamp": "2026-08-17T12:00:00Z",
    }

    with respx.mock:
        respx.get(
            "http://devint.test:8028/api/health/scores",
            params={
                "skip": 0,
                "limit": 50,
                "min_score": 90,
                "health_status": "healthy",
            },
        ).mock(return_value=Response(200, json=scores_response))

        payload = await registry.call(
            "get_device_health",
            {"min_score": 90, "health_status": "healthy", "limit": 50},
            scopes=READ_SCOPES,
        )

        assert payload["summary"]["total"] == 1
        assert len(payload["devices"]) == 1


async def test_get_device_health_fleet_row_cap(registry, backings) -> None:
    """Test get_device_health applies the 100-row cap for fleet."""
    device_health.register(registry, backings)

    # Create 150 device scores; upstream returns 100+ which triggers budget capping
    health_scores = [
        {
            "device_id": f"device_{i}",
            "overall_score": 50.0 + (i % 50),
            "health_status": "healthy" if i % 3 == 0 else "degraded",
        }
        for i in range(150)
    ]

    scores_response = {
        "health_scores": health_scores,
        "summary": {"total_devices": 150},
        "timestamp": "2026-08-17T12:00:00Z",
    }

    with respx.mock:
        respx.get("http://devint.test:8028/api/health/scores").mock(
            return_value=Response(200, json=scores_response)
        )

        payload = await registry.call(
            "get_device_health",
            {"limit": 100},
            scopes=READ_SCOPES,
        )

        # Budget enforcement will cap to <= 100 rows
        assert payload["truncated"] is True or len(payload.get("devices", [])) <= 100
        assert payload["summary"]["total"] == 150  # Total before capping


async def test_get_device_health_fleet_status_counts(registry, backings) -> None:
    """Test get_device_health correctly counts devices by health_status."""
    device_health.register(registry, backings)

    scores_response = {
        "health_scores": [
            {"device_id": f"healthy_{i}", "overall_score": 90.0, "health_status": "healthy"}
            for i in range(5)
        ]
        + [
            {"device_id": f"degraded_{i}", "overall_score": 70.0, "health_status": "degraded"}
            for i in range(3)
        ]
        + [
            {"device_id": f"critical_{i}", "overall_score": 30.0, "health_status": "critical"}
            for i in range(2)
        ],
        "timestamp": "2026-08-17T12:00:00Z",
    }

    with respx.mock:
        respx.get("http://devint.test:8028/api/health/scores").mock(
            return_value=Response(200, json=scores_response)
        )

        payload = await registry.call(
            "get_device_health",
            {},
            scopes=READ_SCOPES,
        )

        assert payload["summary"]["healthy"] == 5
        assert payload["summary"]["degraded"] == 3
        assert payload["summary"]["critical"] == 2
        assert payload["summary"]["avg_score"] > 0


async def test_get_device_health_empty_fleet(registry, backings) -> None:
    """Test get_device_health handles empty device list."""
    device_health.register(registry, backings)

    scores_response = {
        "health_scores": [],
        "timestamp": "2026-08-17T12:00:00Z",
    }

    with respx.mock:
        respx.get("http://devint.test:8028/api/health/scores").mock(
            return_value=Response(200, json=scores_response)
        )

        payload = await registry.call(
            "get_device_health",
            {},
            scopes=READ_SCOPES,
        )

        assert payload["truncated"] is False
        assert payload["devices"] == []
        assert payload["summary"] == {
            "total": 0,
            "avg_score": 0.0,
            "healthy": 0,
            "degraded": 0,
            "critical": 0,
        }


def test_registry_names_after_device_health_register(registry, backings) -> None:
    """Test that register() adds the expected tool names."""
    device_health.register(registry, backings)

    names = registry.names()
    assert "get_device_health" in names
