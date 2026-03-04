"""Unit tests for ha-setup-service main module endpoints."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


def _make_app() -> FastAPI:
    """Build a minimal FastAPI app importing only routes from main."""
    # Import app directly — lifespan won't run with TestClient
    from src.main import app

    return app


# ---------------------------------------------------------------------------
# Health endpoint
# ---------------------------------------------------------------------------


def test_health_endpoint_returns_200() -> None:
    """GET /health returns 200 with healthy status."""
    app = _make_app()
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data


# ---------------------------------------------------------------------------
# Root endpoint
# ---------------------------------------------------------------------------


def test_root_endpoint() -> None:
    """GET / returns service info."""
    app = _make_app()
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["service"] == "HA Setup & Recommendation Service"
    assert "endpoints" in data
    assert "features" in data


# ---------------------------------------------------------------------------
# Verify API key dependency
# ---------------------------------------------------------------------------


def test_verify_api_key_no_key_configured() -> None:
    """verify_api_key raises 503 when no API key configured."""
    from src.main import verify_api_key

    import asyncio

    with patch("src.main._api_key", ""):
        with pytest.raises(Exception) as exc_info:
            asyncio.get_event_loop().run_until_complete(verify_api_key("test-key"))
        assert "503" in str(exc_info.value.status_code)


def test_verify_api_key_wrong_key() -> None:
    """verify_api_key raises 403 with wrong key."""
    from src.main import verify_api_key

    import asyncio

    with patch("src.main._api_key", "correct-key"):
        with pytest.raises(Exception) as exc_info:
            asyncio.get_event_loop().run_until_complete(verify_api_key("wrong-key"))
        assert "403" in str(exc_info.value.status_code)


def test_verify_api_key_correct_key() -> None:
    """verify_api_key returns key when correct."""
    from src.main import verify_api_key

    import asyncio

    with patch("src.main._api_key", "my-secret"):
        result = asyncio.get_event_loop().run_until_complete(verify_api_key("my-secret"))
        assert result == "my-secret"


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


def test_apply_fix_request_model() -> None:
    """ApplyFixRequest validates fields."""
    from src.main import ApplyFixRequest

    req = ApplyFixRequest(entity_id="light.office", area_id="office")
    assert req.entity_id == "light.office"
    assert req.area_id == "office"


def test_bulk_fix_request_model() -> None:
    """BulkFixRequest validates fixes list."""
    from src.main import BulkFixRequest

    req = BulkFixRequest(fixes=[{"entity_id": "light.x", "area_id": "y"}])
    assert len(req.fixes) == 1
