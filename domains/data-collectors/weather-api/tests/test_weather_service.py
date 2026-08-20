"""
Tests for Weather Service
Epic 31, Stories 31.2-31.3
"""

import pytest

pytest.importorskip("influxdb_client_3", reason="influxdb_client_3 required by src.main")

from types import SimpleNamespace

from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)


def test_current_weather_endpoint_exists():
    """Test that current weather endpoint is accessible"""
    # Note: Will return 503 without valid API key, but endpoint exists
    response = client.get("/current-weather")
    # Either 200 (if key configured) or 503 (no data)
    assert response.status_code in [200, 503]


def test_cache_stats_endpoint():
    """Test cache statistics endpoint"""
    import src.main as main_module

    stub = SimpleNamespace(
        cache_hits=3, cache_misses=1, cache_ttl=900, cache_time=None, fetch_count=4
    )
    original = main_module.weather_service
    main_module.weather_service = stub
    try:
        response = client.get("/cache/stats")
    finally:
        main_module.weather_service = original

    assert response.status_code == 200
    data = response.json()
    assert "hits" in data
    assert "misses" in data
    assert "hit_rate" in data
    assert "ttl_seconds" in data


def test_service_root():
    """The weather routes exist on the app.

    The old assertion read an `endpoints` list from a root handler that was
    dead code -- create_app()'s `/` shadowed it (TAP-6183). The real check is
    the routing table itself.
    """
    paths = {getattr(route, "path", None) for route in app.routes}
    assert "/current-weather" in paths
    assert "/cache/stats" in paths
