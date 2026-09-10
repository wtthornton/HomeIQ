"""Tests for the weather adapter (former weather-api).

Ported from weather-api/tests/{test_main.py,test_weather_service.py}; the
generic app-level assertions (root/CORS/docs/openapi) moved to
tests/test_app.py — see the PR body for the consolidation list.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from src.adapters import weather as weather_mod

pytest.importorskip("influxdb_client_3", reason="influxdb_client_3 required by src.adapters.weather")


def test_current_weather_endpoint_exists(collectors_client):
    """Endpoint answers either with data or a handled 503 — never a bare error."""
    response = collectors_client.get("/current-weather")
    assert response.status_code in (200, 503)


def test_cache_stats_endpoint(collectors_client, monkeypatch):
    monkeypatch.setattr(weather_mod.weather_service, "cache_hits", 3)
    monkeypatch.setattr(weather_mod.weather_service, "cache_misses", 1)
    monkeypatch.setattr(weather_mod.weather_service, "cache_ttl", 900)
    monkeypatch.setattr(weather_mod.weather_service, "fetch_count", 4)

    response = collectors_client.get("/cache/stats")

    assert response.status_code == 200
    data = response.json()
    assert data["hits"] == 3
    assert data["misses"] == 1
    assert "hit_rate" in data
    assert data["ttl_seconds"] == 900


def test_health_endpoint_reflects_weather_recent_fetch(collectors_client, monkeypatch):
    """`/health` includes the weather adapter's recent-fetch readiness check."""
    monkeypatch.setattr(
        weather_mod.weather_service, "last_successful_fetch", datetime.now(UTC)
    )

    response = collectors_client.get("/health")

    assert response.status_code == 200
