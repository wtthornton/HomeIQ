"""
Discovery Service Integration Tests
Epic 50 Story 50.3: Integration Test Suite

Tests for DiscoveryService (HA device/entity registry and HTTP APIs).
DiscoveryService uses HA HTTP/WebSocket, not data-api, for discover_devices/entities.
"""

import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from src.discovery_service import DiscoveryService


@pytest.fixture
def mock_ha_device_list():
    """Mock HA device registry list response."""
    return [
        {"id": "device_123", "name": "Living Room Lamp", "manufacturer": "Philips", "model": "Hue"}
    ]


@pytest.fixture
def mock_ha_states_list():
    """Mock HA /api/states response (list of state objects)."""
    return [{"entity_id": "switch.living_room_lamp"}, {"entity_id": "light.office"}]


@pytest.fixture
async def discovery_service():
    """Create discovery service; set env so discover_entities does not exit early."""
    os.environ["DATA_API_URL"] = "http://test-data-api:8006"
    os.environ["HA_HTTP_URL"] = "http://test-ha:8123"
    os.environ["HA_TOKEN"] = "test-token"
    service = DiscoveryService()
    yield service


# --- discover_devices: returns list from HA WebSocket or HTTP ---


@pytest.mark.asyncio
async def test_device_discovery(discovery_service, mock_ha_device_list):
    """discover_devices returns a list of devices from HA (HTTP/WebSocket)."""
    with patch.object(
        DiscoveryService, "_discover_devices_http", new_callable=AsyncMock, return_value=mock_ha_device_list
    ):
        devices = await discovery_service.discover_devices()
    assert devices is not None
    assert isinstance(devices, list)
    assert len(devices) >= 1
    assert devices[0].get("name") == "Living Room Lamp"


@pytest.mark.asyncio
async def test_entity_discovery(discovery_service, mock_ha_states_list):
    """discover_entities returns a list of entities from HA /api/states."""
    # discover_entities uses aiohttp.ClientSession().get(...) to /api/states
    class FakeGetCM:
        async def __aenter__(self):
            r = MagicMock()
            r.status = 200
            r.json = AsyncMock(return_value=mock_ha_states_list)
            return r

        async def __aexit__(self, *a):
            return None

    mock_sess = MagicMock()
    mock_sess.get = lambda *a, **k: FakeGetCM()
    mock_sess.__aenter__ = AsyncMock(return_value=mock_sess)
    mock_sess.__aexit__ = AsyncMock(return_value=None)

    with patch("aiohttp.ClientSession", return_value=mock_sess):
        entities = await discovery_service.discover_entities()
    assert entities is not None
    assert isinstance(entities, list)
    assert len(entities) >= 1
    assert entities[0].get("entity_id") == "switch.living_room_lamp"


# --- Cache helpers: get_device_id, get_area_id, get_device_metadata ---


def test_get_device_id(discovery_service):
    """get_device_id returns device_id from entity_to_device cache."""
    discovery_service.entity_to_device["switch.living_room_lamp"] = "device_123"
    assert discovery_service.get_device_id("switch.living_room_lamp") == "device_123"
    assert discovery_service.get_device_id("unknown") is None


def test_get_area_id(discovery_service):
    """get_area_id returns area_id from entity_to_area or device_to_area cache."""
    discovery_service.entity_to_area["switch.living_room_lamp"] = "area_living_room"
    assert discovery_service.get_area_id("switch.living_room_lamp") == "area_living_room"
    assert discovery_service.get_area_id("unknown") is None


def test_get_device_metadata(discovery_service):
    """get_device_metadata returns metadata from device_metadata cache."""
    discovery_service.device_metadata["device_123"] = {
        "manufacturer": "Philips",
        "model": "Hue",
        "name": "Living Room Lamp",
    }
    meta = discovery_service.get_device_metadata("device_123")
    assert meta is not None
    assert meta.get("manufacturer") == "Philips"
    assert discovery_service.get_device_metadata("unknown") is None


# --- Discovery returns fresh data when HTTP/WS are available ---


@pytest.mark.asyncio
async def test_discover_devices_and_entities_return_lists(discovery_service, mock_ha_device_list, mock_ha_states_list):
    """discover_devices and discover_entities return lists when HA is available (mocked)."""
    class FakeGetCM:
        async def __aenter__(self):
            r = MagicMock()
            r.status = 200
            r.json = AsyncMock(return_value=mock_ha_states_list)
            return r

        async def __aexit__(self, *a):
            return None

    mock_sess = MagicMock()
    mock_sess.get = lambda *a, **k: FakeGetCM()
    mock_sess.__aenter__ = AsyncMock(return_value=mock_sess)
    mock_sess.__aexit__ = AsyncMock(return_value=None)

    with patch.object(
        DiscoveryService, "_discover_devices_http", new_callable=AsyncMock, return_value=mock_ha_device_list
    ), patch("aiohttp.ClientSession", return_value=mock_sess):
        devices = await discovery_service.discover_devices()
        entities = await discovery_service.discover_entities()
    assert isinstance(devices, list) and len(devices) >= 1
    assert isinstance(entities, list) and len(entities) >= 1


# --- Error handling: empty list when HA/HTTP fails ---


@pytest.mark.asyncio
async def test_discovery_error_handling(discovery_service):
    """When HA device discovery fails, discover_devices returns an empty list."""
    with patch.object(
        DiscoveryService, "_discover_devices_http", new_callable=AsyncMock, return_value=[]
    ):
        devices = await discovery_service.discover_devices()
    assert isinstance(devices, list)
    assert len(devices) == 0


# --- store_discovery_results calls data-api; minimal smoke test ---


@pytest.mark.asyncio
async def test_store_discovery_results_posts_to_data_api(discovery_service, mock_ha_device_list, mock_ha_states_list):
    """store_discovery_results POSTs devices/entities to data-api (mocked)."""
    with patch("aiohttp.ClientSession") as MockSession:
        mock_post = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(return_value={"upserted": 1})
        mock_post.return_value.__aenter__.return_value = mock_resp
        mock_post.return_value.__aexit__ = AsyncMock(return_value=None)

        mock_sess = MagicMock()
        mock_sess.post = mock_post
        mock_sess.__aenter__ = AsyncMock(return_value=mock_sess)
        mock_sess.__aexit__ = AsyncMock(return_value=None)
        MockSession.return_value = mock_sess

        ok = await discovery_service.store_discovery_results(
            mock_ha_device_list,
            [{"entity_id": e["entity_id"]} for e in mock_ha_states_list],
            [],
            None,
        )
    assert ok is True
    assert mock_post.called
