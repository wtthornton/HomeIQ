"""
Device Intelligence Service - Storage API Tests

Tests for the storage API endpoints.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from src.api.storage import get_device_cache, get_device_service
from src.main import app
from src.models.database import Device, DeviceCapability, DeviceHealthMetric


@pytest.fixture
def mock_device():
    """Mock device for testing."""
    return Device(
        id="test-device-1",
        name="Test Device",
        manufacturer="Test Manufacturer",
        model="Test Model",
        area_id="living_room",
        integration="test_integration",
        health_score=85,
        last_seen=datetime.now(UTC),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.fixture
def mock_capability():
    """Mock device capability for testing."""
    return DeviceCapability(
        device_id="test-device-1",
        capability_name="on_off",
        capability_type="switch",
        properties={"state": "on"},
        exposed=True,
        configured=True,
        source="ha",
        last_updated=datetime.now(UTC),
    )


@pytest.fixture
def mock_health_metric():
    """Mock health metric for testing."""
    return DeviceHealthMetric(
        device_id="test-device-1",
        metric_name="response_time",
        metric_value=150.5,
        metric_unit="ms",
        metadata_json={"source": "ping"},
        timestamp=datetime.now(UTC),
    )


class TestStorageAPI:
    """Test storage API endpoints.

    `get_device_service`/`get_device_cache` are FastAPI `Depends(...)`
    callables: each route captures the function object at decoration time,
    so `unittest.mock.patch` on the module attribute never reaches an
    already-registered route. `app.dependency_overrides` is the mechanism
    FastAPI provides for substituting a dependency at request time.
    """

    @pytest.fixture(autouse=True)
    def _clear_overrides(self):
        yield
        app.dependency_overrides.clear()

    def test_get_devices(self, client: TestClient, mock_device):
        """Test get all devices endpoint."""
        mock_service = AsyncMock()
        mock_service.get_all_devices.return_value = [mock_device]
        app.dependency_overrides[get_device_service] = lambda: mock_service

        response = client.get("/api/devices")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert data["devices"][0]["device_id"] == "test-device-1"

    def test_get_device_by_id(self, client: TestClient, mock_device):
        """Test get device by ID endpoint."""
        mock_service = AsyncMock()
        mock_service.get_device_by_id.return_value = mock_device
        app.dependency_overrides[get_device_service] = lambda: mock_service

        response = client.get("/api/devices/test-device-1")
        assert response.status_code == 200
        data = response.json()
        assert data["device_id"] == "test-device-1"

    def test_get_device_by_id_not_found(self, client: TestClient):
        """Test get device by ID endpoint when device not found."""
        mock_service = AsyncMock()
        mock_service.get_device_by_id.return_value = None
        app.dependency_overrides[get_device_service] = lambda: mock_service

        response = client.get("/api/devices/nonexistent-device")
        assert response.status_code == 404
        assert "Device not found" in response.json()["detail"]

    def test_get_device_capabilities(self, client: TestClient, mock_capability):
        """Test get device capabilities endpoint."""
        mock_service = AsyncMock()
        mock_service.get_device_capabilities.return_value = [mock_capability]
        app.dependency_overrides[get_device_service] = lambda: mock_service

        response = client.get("/api/devices/test-device-1/capabilities")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["capability_name"] == "on_off"

    def test_get_device_health(self, client: TestClient, mock_health_metric):
        """Test get device health metrics endpoint."""
        mock_service = AsyncMock()
        mock_service.get_device_health_metrics.return_value = [mock_health_metric]
        app.dependency_overrides[get_device_service] = lambda: mock_service

        response = client.get("/api/devices/test-device-1/health")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["metric_name"] == "response_time"

    def test_get_devices_by_area(self, client: TestClient, mock_device):
        """Test get devices by area endpoint."""
        mock_service = AsyncMock()
        mock_service.get_devices_by_area.return_value = [mock_device]
        app.dependency_overrides[get_device_service] = lambda: mock_service

        response = client.get("/api/devices/area/living_room")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["area_id"] == "living_room"

    def test_get_devices_by_integration(self, client: TestClient, mock_device):
        """Test get devices by integration endpoint."""
        mock_service = AsyncMock()
        mock_service.get_devices_by_integration.return_value = [mock_device]
        app.dependency_overrides[get_device_service] = lambda: mock_service

        response = client.get("/api/devices/integration/test_integration")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["integration"] == "test_integration"

    def test_get_device_stats(self, client: TestClient):
        """Test get device statistics endpoint."""
        mock_service = AsyncMock()
        mock_service.get_device_stats.return_value = {
            "total_devices": 5,
            "devices_by_integration": {"test": 3, "other": 2},
            "devices_by_area": {"living_room": 2, "bedroom": 3},
            "average_health_score": 85.5,
            "total_capabilities": 15,
        }
        app.dependency_overrides[get_device_service] = lambda: mock_service

        response = client.get("/api/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["total_devices"] == 5
        assert data["average_health_score"] == 85.5

    def test_invalidate_device_cache(self, client: TestClient):
        """Test invalidate device cache endpoint."""
        mock_cache = AsyncMock()
        app.dependency_overrides[get_device_cache] = lambda: mock_cache

        response = client.post("/api/cache/invalidate/test-device-1")
        assert response.status_code == 200
        assert "Cache invalidated" in response.json()["message"]

    def test_invalidate_all_caches(self, client: TestClient):
        """Test invalidate all caches endpoint."""
        mock_cache = AsyncMock()
        app.dependency_overrides[get_device_cache] = lambda: mock_cache

        response = client.post("/api/cache/invalidate-all")
        assert response.status_code == 200
        assert "All caches invalidated" in response.json()["message"]
