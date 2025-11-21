"""
Tests for Devices & Entities Endpoints
"""

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

# Mock influxdb_client before importing
with patch("src.devices_endpoints.AdminAPIInfluxDBClient"):
    from fastapi import FastAPI

    from src.devices_endpoints import _build_devices_query, _build_entities_query, router

app = FastAPI()
app.include_router(router)
client = TestClient(app)


class TestDevicesEndpoints:
    """Test cases for devices endpoints"""

    def test_build_devices_query_no_filters(self):
        """Test building devices query without filters"""
        query = _build_devices_query({}, 100)

        assert 'from(bucket: "devices")' in query
        assert '|> filter(fn: (r) => r["_measurement"] == "devices")' in query
        assert "|> limit(n: 100)" in query

    def test_build_devices_query_with_filters(self):
        """Test building devices query with filters"""
        filters = {
            "manufacturer": "Philips",
            "model": "Hue Bulb",
            "area_id": "living_room",
        }
        query = _build_devices_query(filters, 50)

        assert 'r["manufacturer"] == "Philips"' in query
        assert 'r["model"] == "Hue Bulb"' in query
        assert 'r["area_id"] == "living_room"' in query
        assert "|> limit(n: 50)" in query

    def test_build_entities_query_no_filters(self):
        """Test building entities query without filters"""
        query = _build_entities_query({}, 100)

        assert 'from(bucket: "entities")' in query
        assert '|> filter(fn: (r) => r["_measurement"] == "entities")' in query
        assert "|> limit(n: 100)" in query

    def test_build_entities_query_with_filters(self):
        """Test building entities query with filters"""
        filters = {
            "domain": "light",
            "platform": "hue",
            "device_id": "dev123",
        }
        query = _build_entities_query(filters, 25)

        assert 'r["domain"] == "light"' in query
        assert 'r["platform"] == "hue"' in query
        assert 'r["device_id"] == "dev123"' in query
        assert "|> limit(n: 25)" in query

    @patch("src.devices_endpoints.influxdb_client")
    def test_list_devices_endpoint(self, mock_influx):
        """Test GET /api/devices endpoint"""
        # Mock query response
        mock_influx.query = AsyncMock(return_value=[
            {
                "device_id": "dev1",
                "name": "Living Room Light",
                "manufacturer": "Philips",
                "model": "Hue Bulb",
                "sw_version": "1.58.0",
                "area_id": "living_room",
                "entity_count": 3,
                "time": "2025-10-12T10:30:00Z",
            },
            {
                "device_id": "dev2",
                "name": "Bedroom Switch",
                "manufacturer": "Lutron",
                "model": "Caseta",
                "area_id": "bedroom",
                "entity_count": 1,
                "time": "2025-10-12T10:30:00Z",
            },
        ])

        response = client.get("/api/devices")

        assert response.status_code == 200
        data = response.json()
        assert "devices" in data
        assert data["count"] == 2
        assert data["limit"] == 100
        assert len(data["devices"]) == 2
        assert data["devices"][0]["device_id"] == "dev1"

    @patch("src.devices_endpoints.influxdb_client")
    def test_list_devices_with_filters(self, mock_influx):
        """Test GET /api/devices with filters"""
        mock_influx.query = AsyncMock(return_value=[])

        response = client.get("/api/devices?manufacturer=Philips&limit=50")

        assert response.status_code == 200
        data = response.json()
        assert data["limit"] == 50

    @patch("src.devices_endpoints.influxdb_client")
    def test_get_device_endpoint(self, mock_influx):
        """Test GET /api/devices/{device_id} endpoint"""
        mock_influx.query = AsyncMock(return_value=[
            {
                "device_id": "dev1",
                "name": "Living Room Light",
                "manufacturer": "Philips",
                "model": "Hue Bulb",
                "time": "2025-10-12T10:30:00Z",
            },
        ])

        response = client.get("/api/devices/dev1")

        assert response.status_code == 200
        device = response.json()
        assert device["device_id"] == "dev1"
        assert device["name"] == "Living Room Light"

    @patch("src.devices_endpoints.influxdb_client")
    def test_get_device_not_found(self, mock_influx):
        """Test GET /api/devices/{device_id} with non-existent device"""
        mock_influx.query = AsyncMock(return_value=[])

        response = client.get("/api/devices/nonexistent")

        assert response.status_code == 404

    @patch("src.devices_endpoints.influxdb_client")
    def test_list_entities_endpoint(self, mock_influx):
        """Test GET /api/entities endpoint"""
        mock_influx.query = AsyncMock(return_value=[
            {
                "entity_id": "light.living_room",
                "device_id": "dev1",
                "domain": "light",
                "platform": "hue",
                "unique_id": "hue123",
                "area_id": "living_room",
                "disabled": False,
                "time": "2025-10-12T10:30:00Z",
            },
        ])

        response = client.get("/api/entities")

        assert response.status_code == 200
        data = response.json()
        assert "entities" in data
        assert data["count"] == 1
        assert data["entities"][0]["entity_id"] == "light.living_room"

    @patch("src.devices_endpoints.influxdb_client")
    def test_list_entities_with_filters(self, mock_influx):
        """Test GET /api/entities with filters"""
        mock_influx.query = AsyncMock(return_value=[])

        response = client.get("/api/entities?domain=light&platform=hue")

        assert response.status_code == 200

    @patch("src.devices_endpoints.influxdb_client")
    def test_get_entity_endpoint(self, mock_influx):
        """Test GET /api/entities/{entity_id} endpoint"""
        mock_influx.query = AsyncMock(return_value=[
            {
                "entity_id": "sensor.temperature",
                "domain": "sensor",
                "platform": "mqtt",
                "time": "2025-10-12T10:30:00Z",
            },
        ])

        response = client.get("/api/entities/sensor.temperature")

        assert response.status_code == 200
        entity = response.json()
        assert entity["entity_id"] == "sensor.temperature"

    @patch("src.devices_endpoints.influxdb_client")
    def test_get_entity_not_found(self, mock_influx):
        """Test GET /api/entities/{entity_id} with non-existent entity"""
        mock_influx.query = AsyncMock(return_value=[])

        response = client.get("/api/entities/nonexistent.entity")

        assert response.status_code == 404

    @patch("src.devices_endpoints.influxdb_client")
    def test_list_integrations_endpoint(self, mock_influx):
        """Test GET /api/integrations endpoint"""
        mock_influx.query = AsyncMock(return_value=[
            {
                "entry_id": "entry1",
                "domain": "hue",
                "title": "Philips Hue",
                "state": "loaded",
                "version": 2,
                "time": "2025-10-12T10:30:00Z",
            },
        ])

        response = client.get("/api/integrations")

        assert response.status_code == 200
        data = response.json()
        assert "integrations" in data
        assert data["count"] == 1
        assert data["integrations"][0]["domain"] == "hue"

