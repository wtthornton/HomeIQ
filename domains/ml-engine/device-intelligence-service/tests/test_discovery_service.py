"""
Device Intelligence Service - Discovery Service Tests
"""

import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from src.clients.ha_client import HAArea, HADevice
from src.clients.mqtt_client import ZigbeeDevice
from src.config import Settings
from src.core.discovery_service import DiscoveryService


@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    settings = Settings()
    settings.HA_URL = "http://localhost:8123"
    settings.HA_TOKEN = "test_token"
    settings.MQTT_BROKER = "mqtt://localhost:1883"
    return settings


@pytest.fixture
def mock_ha_device():
    """Mock HA device for testing."""
    return HADevice(
        id="test_device_1",
        name="Test Device",
        name_by_user=None,
        manufacturer="Test Manufacturer",
        model="Test Model",
        area_id="living_room",
        suggested_area=None,
        integration="zigbee2mqtt",
        entry_type=None,
        configuration_url=None,
        config_entries=["test_entry"],
        identifiers=[["ieee_address", "00:11:22:33:44:55:66:77"]],
        connections=[],
        sw_version="1.0.0",
        hw_version="1.0",
        via_device_id=None,
        disabled_by=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.fixture
def mock_zigbee_device():
    """Mock Zigbee device for testing."""
    return ZigbeeDevice(
        ieee_address="00:11:22:33:44:55:66:77",
        friendly_name="Test Device",
        model="Test Model",
        description="Test Description",
        manufacturer="Test Manufacturer",
        manufacturer_code="1234",
        power_source="Mains (single phase)",
        model_id="test_model_id",
        hardware_version="1.0",
        software_build_id="1.0.0",
        date_code="20240101",
        last_seen=datetime.now(UTC),
        definition={
            "exposes": [{"name": "state", "type": "binary", "properties": {"state": "ON"}}]
        },
        exposes=[{"name": "state", "type": "binary", "properties": {"state": "ON"}}],
        capabilities={},
    )


@pytest.fixture
def mock_ha_area():
    """Mock HA area for testing."""
    return HAArea(
        area_id="living_room",
        name="Living Room",
        normalized_name="living_room",
        aliases=[],
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.mark.asyncio
async def test_discovery_service_initialization(mock_settings):
    """Test discovery service initialization."""
    service = DiscoveryService(mock_settings)

    assert service.settings == mock_settings
    assert not service.running
    assert service.unified_devices == {}
    assert service.errors == []


@pytest.mark.asyncio
async def test_discovery_service_start_failure(mock_settings):
    """Test discovery service startup failure."""
    service = DiscoveryService(mock_settings)

    # Mock failed connection
    with patch("src.clients.ha_client.HomeAssistantClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.connect.return_value = False
        mock_client_cls.return_value = mock_client

        result = await service.start()

        assert not result
        assert not service.running
        mock_client.connect.assert_awaited()


@pytest.mark.asyncio
async def test_discovery_service_start_success(mock_settings):
    """Test discovery service startup success."""
    service = DiscoveryService(mock_settings)

    # Mock successful connections
    with (
        patch("src.clients.ha_client.HomeAssistantClient") as mock_client_cls,
        patch.object(service.mqtt_client, "connect", return_value=True),
    ):
        mock_client = AsyncMock()
        mock_client.connect.return_value = True
        mock_client.start_message_handler.return_value = None
        mock_client_cls.return_value = mock_client

        result = await service.start()

        assert result
        assert service.running
        mock_client.connect.assert_awaited()
        mock_client.start_message_handler.assert_awaited()


@pytest.mark.asyncio
async def test_discovery_service_stop(mock_settings):
    """Test discovery service stop."""
    service = DiscoveryService(mock_settings)
    service.running = True
    service.ha_client = AsyncMock()

    # Create a real task that can be cancelled
    async def dummy_task():
        while True:
            await asyncio.sleep(0.1)

    service.discovery_task = asyncio.create_task(dummy_task())

    with patch.object(service.mqtt_client, "disconnect", return_value=None):
        await service.stop()
        assert not service.running


@pytest.mark.asyncio
async def test_get_status(mock_settings):
    """Test getting discovery service status."""
    service = DiscoveryService(mock_settings)
    service.running = True
    service.last_discovery = datetime.now(UTC)
    service.unified_devices = {"device1": MagicMock()}
    service.ha_areas = [MagicMock()]

    service.ha_client = MagicMock()
    service.ha_client.is_connected.return_value = True
    service.mqtt_client.is_connected = MagicMock(return_value=True)

    status = service.get_status()

    assert status.service_running is True
    assert status.ha_connected is True
    assert status.mqtt_connected is True
    assert status.devices_count == 1
    assert status.areas_count == 1


@pytest.mark.asyncio
async def test_force_refresh(mock_settings):
    """Test forcing discovery refresh."""
    service = DiscoveryService(mock_settings)

    with patch.object(service, "_perform_discovery", return_value=None) as mock_discovery:
        result = await service.force_refresh()

        assert result is True
        mock_discovery.assert_called_once()


@pytest.mark.asyncio
async def test_get_devices(mock_settings):
    """Test getting all devices."""
    service = DiscoveryService(mock_settings)

    mock_device = MagicMock()
    service.unified_devices = {"device1": mock_device, "device2": mock_device}

    devices = service.get_devices()
    assert len(devices) == 2


@pytest.mark.asyncio
async def test_get_device_by_id(mock_settings):
    """Test getting specific device by ID."""
    service = DiscoveryService(mock_settings)

    mock_device = MagicMock()
    service.unified_devices = {"device1": mock_device}

    device = service.get_device("device1")
    assert device == mock_device

    device = service.get_device("nonexistent")
    assert device is None


@pytest.mark.asyncio
async def test_get_devices_by_area(mock_settings):
    """Test getting devices by area."""
    service = DiscoveryService(mock_settings)

    mock_device1 = MagicMock()
    mock_device1.area_id = "living_room"
    mock_device2 = MagicMock()
    mock_device2.area_id = "bedroom"

    service.unified_devices = {"device1": mock_device1, "device2": mock_device2}

    devices = service.get_devices_by_area("living_room")
    assert len(devices) == 1
    assert devices[0] == mock_device1


@pytest.mark.asyncio
async def test_get_devices_by_integration(mock_settings):
    """Test getting devices by integration."""
    service = DiscoveryService(mock_settings)

    mock_device1 = MagicMock()
    mock_device1.integration = "zigbee2mqtt"
    mock_device2 = MagicMock()
    mock_device2.integration = "homeassistant"

    service.unified_devices = {"device1": mock_device1, "device2": mock_device2}

    devices = service.get_devices_by_integration("zigbee2mqtt")
    assert len(devices) == 1
    assert devices[0] == mock_device1


@pytest.mark.asyncio
async def test_absent_devices_are_marked_unavailable_never_deleted(mock_settings):
    """TAP-6249: a device missing from the snapshot keeps its row.

    The reconciliation issues one UPDATE (availability only, last_seen
    untouched) and never a DELETE; an empty snapshot is skipped entirely
    because it means discovery failed, not that the home is empty.
    """
    service = DiscoveryService(mock_settings)

    device = MagicMock()
    device.id = "dev_present"
    device.zigbee_device = None
    device.ha_device = None
    service.unified_devices = {"dev_present": device}

    executed: list[tuple[str, dict]] = []

    class FakeResult:
        def fetchall(self):
            return [("dev_gone", None)]

    class FakeSession:
        async def execute(self, query, params=None):
            executed.append((str(query), params or {}))
            return FakeResult()

        async def commit(self):
            pass

    async def fake_get_db_session():
        yield FakeSession()

    with patch("src.core.discovery_service.get_db_session", fake_get_db_session):
        await service._reconcile_absent_devices()

    assert len(executed) == 1
    sql, params = executed[0]
    assert "UPDATE devices" in sql
    assert "availability_status" in sql
    assert "DELETE" not in sql.upper()
    assert "last_seen" not in sql  # retained, not rewritten
    assert params["current_ids"] == ["dev_present"]


@pytest.mark.asyncio
async def test_an_empty_snapshot_does_not_mark_the_fleet_unavailable(mock_settings):
    service = DiscoveryService(mock_settings)
    service.unified_devices = {}

    called = False

    async def fake_get_db_session():
        nonlocal called
        called = True
        yield None

    with patch("src.core.discovery_service.get_db_session", fake_get_db_session):
        await service._reconcile_absent_devices()

    assert called is False


def test_auto_generate_flag_on_constructs_the_name_pipeline(mock_settings):
    """TAP-6235: the pipeline must actually light up when the flag is set —
    'implemented behind a flag' is only true if flag=True builds the machinery.
    The default stays False; flipping it is a product decision, not a bug fix."""
    mock_settings.AUTO_GENERATE_NAME_SUGGESTIONS = True

    service = DiscoveryService(mock_settings)

    assert service.auto_generate_name_suggestions is True
    assert service.name_generator is not None
    assert service.name_validator is not None
    assert service.batch_processor is not None
    assert service.preference_learner is not None


def test_auto_generate_flag_off_keeps_the_pipeline_dark(mock_settings):
    service = DiscoveryService(mock_settings)

    assert service.auto_generate_name_suggestions is False
    assert service.name_generator is None
    assert service.name_validator is None
    assert service.preference_learner is None
    assert service.batch_processor is None
