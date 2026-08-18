"""Tests for StandardHealthCheck.

Covers:
  - Healthy status when all checks pass
  - Degraded status when some checks fail
  - Unhealthy status when all checks fail
  - No checks registered returns healthy
  - Exception in check function treated as unhealthy
  - Router provides /health endpoint
  - Timestamp and uptime in response
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from homeiq_resilience.health_check import StandardHealthCheck
from httpx import ASGITransport, AsyncClient


@pytest.fixture
def health() -> StandardHealthCheck:
    return StandardHealthCheck(service_name="test-service", version="1.2.3")


@pytest.fixture
def app(health: StandardHealthCheck) -> FastAPI:
    app = FastAPI()
    app.include_router(health.router)
    return app


class TestStandardHealthCheck:
    @pytest.mark.asyncio
    async def test_healthy_no_checks(self, health: StandardHealthCheck) -> None:
        result = await health.get_status()
        assert result["status"] == "healthy"
        assert result["service"] == "test-service"
        assert result["version"] == "1.2.3"
        assert "uptime_seconds" in result
        assert "timestamp" in result
        assert "checks" not in result

    @pytest.mark.asyncio
    async def test_healthy_all_pass(self, health: StandardHealthCheck) -> None:
        async def check_db() -> bool:
            return True

        async def check_redis() -> bool:
            return True

        health.register_check("database", check_db)
        health.register_check("redis", check_redis)

        result = await health.get_status()
        assert result["status"] == "healthy"
        assert len(result["checks"]) == 2
        assert all(c["status"] == "healthy" for c in result["checks"])
        assert all("latency_ms" in c for c in result["checks"])

    @pytest.mark.asyncio
    async def test_degraded_partial_failure(self, health: StandardHealthCheck) -> None:
        async def check_ok() -> bool:
            return True

        async def check_fail() -> bool:
            return False

        health.register_check("ok-service", check_ok)
        health.register_check("failing-service", check_fail)

        result = await health.get_status()
        assert result["status"] == "degraded"

    @pytest.mark.asyncio
    async def test_unhealthy_all_fail(self, health: StandardHealthCheck) -> None:
        async def check_fail() -> bool:
            return False

        health.register_check("db", check_fail)
        health.register_check("redis", check_fail)

        result = await health.get_status()
        assert result["status"] == "unhealthy"

    @pytest.mark.asyncio
    async def test_exception_treated_as_unhealthy(self, health: StandardHealthCheck) -> None:
        async def check_explode() -> bool:
            raise RuntimeError("boom")

        health.register_check("exploding", check_explode)
        result = await health.get_status()
        assert result["status"] == "unhealthy"
        assert result["checks"][0]["status"] == "unhealthy"

    @pytest.mark.asyncio
    async def test_no_timestamp_when_disabled(self) -> None:
        health = StandardHealthCheck(
            service_name="test",
            version="1.0.0",
            include_timestamp=False,
        )
        result = await health.get_status()
        assert "timestamp" not in result

    @pytest.mark.asyncio
    async def test_http_endpoint(self, app: FastAPI) -> None:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["service"] == "test-service"


class TestReadyEndpoint:
    """/ready is strict, dependency-aware readiness (TAP-5903)."""

    @pytest.mark.asyncio
    async def test_no_checks_registered_is_not_ready(self, app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            resp = await c.get("/ready")
        assert resp.status_code == 503
        body = resp.json()
        assert body["ready"] is False
        assert "no readiness checks registered" in body["reason"]

    @pytest.mark.asyncio
    async def test_all_passing_checks_is_ready(self, health, app):
        async def ok_check() -> bool:
            return True

        health.register_check("upstream", ok_check)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            resp = await c.get("/ready")
        assert resp.status_code == 200
        assert resp.json()["ready"] is True

    @pytest.mark.asyncio
    async def test_failing_check_is_503_and_named(self, health, app):
        async def ok_check() -> bool:
            return True

        async def stale_fetch() -> bool:
            return False

        health.register_check("upstream", ok_check)
        health.register_check("recent_fetch", stale_fetch)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            resp = await c.get("/ready")
        assert resp.status_code == 503
        body = resp.json()
        assert body["ready"] is False
        assert "recent_fetch" in body["reason"]

    @pytest.mark.asyncio
    async def test_detail_dict_passes_through(self, health, app):
        async def detail_check():
            return {"ok": True, "last_successful_fetch_age_s": 42, "credential_present": True}

        health.register_check("feed", detail_check)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            resp = await c.get("/ready")
        assert resp.status_code == 200
        check = resp.json()["checks"][0]
        assert check["ok"] is True
        assert check["detail"]["last_successful_fetch_age_s"] == 42
        assert check["detail"]["credential_present"] is True

    @pytest.mark.asyncio
    async def test_health_stays_liveness_200_while_ready_is_503(self, health, app):
        async def failing() -> bool:
            return False

        health.register_check("dep", failing)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            health_resp = await c.get("/health")
            ready_resp = await c.get("/ready")
        assert health_resp.status_code == 200  # Docker restarts on this; body may degrade
        assert health_resp.json()["status"] == "unhealthy"
        assert ready_resp.status_code == 503
