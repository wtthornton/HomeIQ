"""
Device Intelligence Service - Storage API Tests

Tests for the storage API endpoints.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
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
        last_seen=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
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
        last_updated=datetime.now(timezone.utc),
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
        timestamp=datetime.now(timezone.utc),
    )

class TestStorageAPI:
    """Test storage API endpoints."""

    @patch("src.api.storage.get_device_service")
    def test_get_devices(self, mock_get_service, client: TestClient, mock_device):
        """Test get all devices endpoint."""
        mock_service = AsyncMock()
        mock_service.get_all_devices.return_value = [mock_device]
        mock_get_service.return_value = mock_service

        response = client.get("/api/devices")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == "test-device-1"

    @patch("src.api.storage.get_device_service")
    def test_get_device_by_id(self, mock_get_service, client: TestClient, mock_device):
        """Test get device by ID endpoint."""
        mock_service = AsyncMock()
        mock_service.get_device_by_id.return_value = mock_device
        mock_get_service.return_value = mock_service

        response = client.get("/api/devices/test-device-1")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "test-device-1"

    @patch("src.api.storage.get_device_service")
    def test_get_device_by_id_not_found(self, mock_get_service, client: TestClient):
        """Test get device by ID endpoint when device not found."""
        mock_service = AsyncMock()
        mock_service.get_device_by_id.return_value = None
        mock_get_service.return_value = mock_service

        response = client.get("/api/devices/nonexistent-device")
        assert response.status_code == 404
        assert "Device not found" in response.json()["detail"]

    @patch("src.api.storage.get_device_service")
    def test_get_device_capabilities(self, mock_get_service, client: TestClient, mock_capability):
        """Test get device capabilities endpoint."""
        mock_service = AsyncMock()
        mock_service.get_device_capabilities.return_value = [mock_capability]
        mock_get_service.return_value = mock_service

        response = client.get("/api/devices/test-device-1/capabilities")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["capability_name"] == "on_off"

    @patch("src.api.storage.get_device_service")
    def test_get_device_health(self, mock_get_service, client: TestClient, mock_health_metric):
        """Test get device health metrics endpoint."""
        mock_service = AsyncMock()
        mock_service.get_device_health_metrics.return_value = [mock_health_metric]
        mock_get_service.return_value = mock_service

        response = client.get("/api/devices/test-device-1/health")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["metric_name"] == "response_time"

    @patch("src.api.storage.get_device_service")
    def test_get_devices_by_area(self, mock_get_service, client: TestClient, mock_device):
        """Test get devices by area endpoint."""
        mock_service = AsyncMock()
        mock_service.get_devices_by_area.return_value = [mock_device]
        mock_get_service.return_value = mock_service

        response = client.get("/api/devices/area/living_room")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["area_id"] == "living_room"

    @patch("src.api.storage.get_device_service")
    def test_get_devices_by_integration(self, mock_get_service, client: TestClient, mock_device):
        """Test get devices by integration endpoint."""
        mock_service = AsyncMock()
        mock_service.get_devices_by_integration.return_value = [mock_device]
        mock_get_service.return_value = mock_service

        response = client.get("/api/devices/integration/test_integration")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["integration"] == "test_integration"

    @patch("src.api.storage.get_device_service")
    def test_get_device_stats(self, mock_get_service, client: TestClient):
        """Test get device statistics endpoint."""
        mock_service = AsyncMock()
        mock_service.get_device_stats.return_value = {
            "total_devices": 5,
            "devices_by_integration": {"test": 3, "other": 2},
            "devices_by_area": {"living_room": 2, "bedroom": 3},
            "average_health_score": 85.5,
            "total_capabilities": 15,
        }
        mock_get_service.return_value = mock_service

        response = client.get("/api/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["total_devices"] == 5
        assert data["average_health_score"] == 85.5

    @patch("src.api.storage.get_device_cache")
    def test_invalidate_device_cache(self, mock_get_cache, client: TestClient):
        """Test invalidate device cache endpoint."""
        mock_cache = AsyncMock()
        mock_get_cache.return_value = mock_cache

        response = client.post("/api/cache/invalidate/test-device-1")
        assert response.status_code == 200
        assert "Cache invalidated" in response.json()["message"]

    @patch("src.api.storage.get_device_cache")
    def test_invalidate_all_caches(self, mock_get_cache, client: TestClient):
        """Test invalidate all caches endpoint."""
        mock_cache = AsyncMock()
        mock_get_cache.return_value = mock_cache

        response = client.post("/api/cache/invalidate-all")
        assert response.status_code == 200
        assert "All caches invalidated" in response.json()["message"]
