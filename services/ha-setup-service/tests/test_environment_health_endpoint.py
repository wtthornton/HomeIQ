"""Tests for HA Setup Service environment health endpoint."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient
from src.database import get_db
from src.health_service import HealthMonitoringService
from src.main import app, health_services
from src.schemas import IntegrationStatus


def test_environment_health_includes_check_details() -> None:
    """Endpoint should surface integration check details without raising errors."""

    monitor = HealthMonitoringService()

    mock_ha_core = {"status": "healthy", "version": "2025.10.0"}
    mock_integrations = [
        {
            "name": "MQTT",
            "type": "mqtt",
            "status": IntegrationStatus.HEALTHY,
            "is_configured": True,
            "is_connected": True,
            "error_message": None,
            "check_details": {"broker": "mqtt.local", "port": 1883},
            "last_check": datetime.now(timezone.utc),
            "extra_field": "ignored",
        },
    ]
    mock_performance = {
        "response_time_ms": 12.5,
        "cpu_usage_percent": 3.4,
        "memory_usage_mb": 256.0,
        "uptime_seconds": 3600,
    }

    monitor._check_ha_core = AsyncMock(return_value=mock_ha_core)  # type: ignore[attr-defined]
    monitor._check_integrations = AsyncMock(return_value=mock_integrations)  # type: ignore[attr-defined]
    monitor._check_performance = AsyncMock(return_value=mock_performance)  # type: ignore[attr-defined]
    monitor._store_health_metric = AsyncMock()  # type: ignore[attr-defined]
    monitor.scoring_algorithm.calculate_score = MagicMock(return_value=(95, {}))

    previous_monitor = health_services.get("monitor")
    health_services["monitor"] = monitor

    async def override_get_db() -> AsyncGenerator[AsyncMock, None]:
        yield AsyncMock()

    app.dependency_overrides[get_db] = override_get_db

    original_lifespan = app.router.lifespan_context

    @asynccontextmanager
    async def noop_lifespan(_app):
        yield

    app.router.lifespan_context = noop_lifespan

    try:
        with TestClient(app) as client:
            response = client.get("/api/health/environment")

        assert response.status_code == 200
        payload = response.json()

        assert payload["health_score"] == 95
        assert payload["ha_status"] == "healthy"
        assert payload["ha_version"] == "2025.10.0"

        assert payload["integrations"], "Integrations list should not be empty"
        integration = payload["integrations"][0]
        assert integration["name"] == "MQTT"
        assert integration["status"] == "healthy"
        assert integration["check_details"] == {"broker": "mqtt.local", "port": 1883}

        monitor._store_health_metric.assert_awaited_once()  # type: ignore[attr-defined]
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.router.lifespan_context = original_lifespan
        if previous_monitor is None:
            health_services.pop("monitor", None)
        else:
            health_services["monitor"] = previous_monitor

