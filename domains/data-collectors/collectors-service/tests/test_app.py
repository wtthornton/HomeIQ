"""Generic app-level behavior for the merged collectors service.

Each of the six retired services carried its own near-identical copy of
these assertions (root/CORS/docs/openapi/health/metrics all come from the
shared `homeiq_resilience.create_app()` factory, not from adapter-specific
code). Consolidated here to one copy per TAP-7274 section C1 — see the PR
body for the enumerated list of per-service duplicates this replaces.
"""

from __future__ import annotations

from src.config import settings
from src.main import __version__


def test_root_is_sports_adapter_root(collectors_client):
    """ "/" is owned by the sports adapter (unchanged from sports-api's own root);
    create_app()'s generic root is explicitly stripped in src/main.py so the
    two don't collide."""
    response = collectors_client.get("/")

    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "sports-api"
    assert data["status"] == "running"


def test_health_endpoint(collectors_client):
    response = collectors_client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["service"] == settings.service_name
    assert "uptime_seconds" in data


def test_metrics_endpoint(collectors_client):
    response = collectors_client.get("/metrics")

    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    assert "# HELP" in response.text


def test_cors_headers(collectors_client):
    response = collectors_client.get("/", headers={"Origin": "http://localhost:3000"})

    assert response.status_code == 200
    assert "access-control-allow-origin" in response.headers


def test_openapi_docs_available(collectors_client):
    response = collectors_client.get("/docs")

    assert response.status_code == 200


def test_openapi_json(collectors_client):
    response = collectors_client.get("/openapi.json")

    assert response.status_code == 200
    schema = response.json()
    assert schema["info"]["title"] == "Collectors Service"
    assert schema["info"]["version"] == __version__
