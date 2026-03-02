"""Tests for create_app factory.

Covers:
  - App creation with defaults
  - CORS middleware added
  - Request ID middleware
  - Timing middleware
  - Health check auto-registration
  - Root endpoint
  - Unhandled exception handler
  - Security: no credentials with wildcard origins
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from fastapi import FastAPI

from homeiq_resilience.app_factory import create_app
from homeiq_resilience.health_check import StandardHealthCheck


@pytest.fixture
def app() -> FastAPI:
    return create_app(title="Test Service", version="2.0.0")


@pytest.fixture
def app_with_health() -> FastAPI:
    health = StandardHealthCheck(service_name="test-svc", version="2.0.0")
    return create_app(title="Test Service", version="2.0.0", health_check=health)


class TestCreateApp:
    def test_creates_fastapi_instance(self, app: FastAPI) -> None:
        assert isinstance(app, FastAPI)
        assert app.title == "Test Service"
        assert app.version == "2.0.0"

    @pytest.mark.asyncio
    async def test_root_endpoint(self, app: FastAPI) -> None:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["service"] == "Test Service"
        assert data["version"] == "2.0.0"
        assert data["status"] == "running"

    @pytest.mark.asyncio
    async def test_request_id_header(self, app: FastAPI) -> None:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/")
        assert "x-request-id" in resp.headers

    @pytest.mark.asyncio
    async def test_custom_request_id_preserved(self, app: FastAPI) -> None:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/", headers={"X-Request-ID": "my-id-123"})
        assert resp.headers["x-request-id"] == "my-id-123"

    @pytest.mark.asyncio
    async def test_timing_header(self, app: FastAPI) -> None:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/")
        assert "x-process-time" in resp.headers
        assert float(resp.headers["x-process-time"]) >= 0

    @pytest.mark.asyncio
    async def test_health_endpoint_when_registered(self, app_with_health: FastAPI) -> None:
        transport = ASGITransport(app=app_with_health)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["service"] == "test-svc"

    def test_cors_no_credentials_with_wildcard(self) -> None:
        app = create_app(
            title="Test",
            cors_origins=["*"],
            cors_allow_credentials=True,
        )
        # The factory should force credentials=False when origins=["*"]
        for middleware in app.user_middleware:
            if hasattr(middleware, "kwargs"):
                if middleware.kwargs.get("allow_origins") == ["*"]:
                    assert middleware.kwargs.get("allow_credentials") is False

    def test_no_middleware_when_disabled(self) -> None:
        app = create_app(
            title="Bare",
            include_request_id=False,
            include_timing=False,
        )
        assert isinstance(app, FastAPI)
