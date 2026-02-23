"""
Integration tests for EntityRegistry relationship query endpoints

Tests the new relationship query API endpoints:
- GET /api/entities/by-device/{device_id}
- GET /api/entities/{entity_id}/siblings
- GET /api/entities/{entity_id}/device
- GET /api/entities/by-area/{area_id}
- GET /api/entities/by-config-entry/{config_entry_id}
- GET /api/devices/{device_id}/hierarchy
"""


import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from src.database import AsyncSessionLocal, init_db
from src.main import app
from src.models import Device, Entity


@pytest_asyncio.fixture
async def test_client():
    """Fixture for async HTTP client"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_get_entities_by_device_endpoint(test_client):
    """Test GET /api/entities/by-device/{device_id} endpoint"""
    await init_db()

    async with AsyncSessionLocal() as session:
        # Setup: Create device with entities
        device = Device(device_id="test_device_api", name="Test Device", config_entry_id="entry_123")
        session.add(device)

        entity1 = Entity(entity_id="light.api_test_1", device_id="test_device_api", domain="light", platform="test")
        entity2 = Entity(entity_id="sensor.api_test_1", device_id="test_device_api", domain="sensor", platform="test")
        session.add(entity1)
        session.add(entity2)
        await session.commit()

    # Test endpoint
    response = await test_client.get("/api/entities/by-device/test_device_api")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["device_id"] == "test_device_api"
    assert data["count"] == 2
    assert len(data["entities"]) == 2

    entity_ids = [e["entity_id"] for e in data["entities"]]
    assert "light.api_test_1" in entity_ids
    assert "sensor.api_test_1" in entity_ids

    # Cleanup
    async with AsyncSessionLocal() as session:
        entities = (await session.execute(select(Entity).where(Entity.device_id == "test_device_api"))).scalars().all()
        for entity in entities:
            await session.delete(entity)
        device = (await session.execute(select(Device).where(Device.device_id == "test_device_api"))).scalar_one()
        await session.delete(device)
        await session.commit()


@pytest.mark.asyncio
async def test_get_sibling_entities_endpoint(test_client):
    """Test GET /api/entities/{entity_id}/siblings endpoint"""
    await init_db()

    async with AsyncSessionLocal() as session:
        # Setup: Create device with multiple entities
        device = Device(device_id="test_device_siblings", name="Test Device")
        session.add(device)

        entity1 = Entity(entity_id="light.sibling_test", device_id="test_device_siblings", domain="light", platform="test")
        entity2 = Entity(entity_id="sensor.sibling_test", device_id="test_device_siblings", domain="sensor", platform="test")
        session.add(entity1)
        session.add(entity2)
        await session.commit()

    # Test endpoint
    response = await test_client.get("/api/entities/light.sibling_test/siblings")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["entity_id"] == "light.sibling_test"
    assert data["count"] == 1  # Should not include the entity itself
    assert len(data["siblings"]) == 1
    assert data["siblings"][0]["entity_id"] == "sensor.sibling_test"

    # Cleanup
    async with AsyncSessionLocal() as session:
        entities = (await session.execute(select(Entity).where(Entity.device_id == "test_device_siblings"))).scalars().all()
        for entity in entities:
            await session.delete(entity)
        device = (await session.execute(select(Device).where(Device.device_id == "test_device_siblings"))).scalar_one()
        await session.delete(device)
        await session.commit()


@pytest.mark.asyncio
async def test_get_device_for_entity_endpoint(test_client):
    """Test GET /api/entities/{entity_id}/device endpoint"""
    await init_db()

    async with AsyncSessionLocal() as session:
        # Setup: Create device and entity
        device = Device(
            device_id="test_device_for_entity",
            name="Test Device",
            manufacturer="Test Co",
            model="Model X",
            config_entry_id="entry_456",
            via_device=None
        )
        session.add(device)

        entity = Entity(entity_id="light.device_test", device_id="test_device_for_entity", domain="light", platform="test")
        session.add(entity)
        await session.commit()

    # Test endpoint
    response = await test_client.get("/api/entities/light.device_test/device")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["entity_id"] == "light.device_test"
    assert data["device"] is not None
    assert data["device"]["device_id"] == "test_device_for_entity"
    assert data["device"]["name"] == "Test Device"
    assert data["device"]["manufacturer"] == "Test Co"
    assert data["device"]["config_entry_id"] == "entry_456"

    # Cleanup
    async with AsyncSessionLocal() as session:
        entity = (await session.execute(select(Entity).where(Entity.entity_id == "light.device_test"))).scalar_one()
        await session.delete(entity)
        device = (await session.execute(select(Device).where(Device.device_id == "test_device_for_entity"))).scalar_one()
        await session.delete(device)
        await session.commit()


@pytest.mark.asyncio
async def test_get_entities_in_area_endpoint(test_client):
    """Test GET /api/entities/by-area/{area_id} endpoint"""
    await init_db()

    async with AsyncSessionLocal() as session:
        # Setup: Create entities in same area
        device1 = Device(device_id="test_device_area_1", name="Device 1", area_id="test_area")
        device2 = Device(device_id="test_device_area_2", name="Device 2", area_id="test_area")
        session.add(device1)
        session.add(device2)

        entity1 = Entity(entity_id="light.area_test_1", device_id="test_device_area_1", domain="light", area_id="test_area", platform="test")
        entity2 = Entity(entity_id="light.area_test_2", device_id="test_device_area_2", domain="light", area_id="test_area", platform="test")
        session.add(entity1)
        session.add(entity2)
        await session.commit()

    # Test endpoint
    response = await test_client.get("/api/entities/by-area/test_area")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["area_id"] == "test_area"
    assert data["count"] == 2
    assert len(data["entities"]) == 2

    entity_ids = [e["entity_id"] for e in data["entities"]]
    assert "light.area_test_1" in entity_ids
    assert "light.area_test_2" in entity_ids

    # Cleanup
    async with AsyncSessionLocal() as session:
        entities = (await session.execute(select(Entity).where(Entity.area_id == "test_area"))).scalars().all()
        for entity in entities:
            await session.delete(entity)
        devices = (await session.execute(select(Device).where(Device.area_id == "test_area"))).scalars().all()
        for device in devices:
            await session.delete(device)
        await session.commit()


@pytest.mark.asyncio
async def test_get_entities_by_config_entry_endpoint(test_client):
    """Test GET /api/entities/by-config-entry/{config_entry_id} endpoint"""
    await init_db()

    async with AsyncSessionLocal() as session:
        # Setup: Create entities with same config_entry_id
        device = Device(device_id="test_device_config", name="Device", config_entry_id="entry_789")
        session.add(device)

        entity1 = Entity(entity_id="light.config_test_1", device_id="test_device_config", domain="light", config_entry_id="entry_789", platform="test")
        entity2 = Entity(entity_id="sensor.config_test_1", device_id="test_device_config", domain="sensor", config_entry_id="entry_789", platform="test")
        session.add(entity1)
        session.add(entity2)
        await session.commit()

    # Test endpoint
    response = await test_client.get("/api/entities/by-config-entry/entry_789")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["config_entry_id"] == "entry_789"
    assert data["count"] == 2
    assert len(data["entities"]) == 2

    entity_ids = [e["entity_id"] for e in data["entities"]]
    assert "light.config_test_1" in entity_ids
    assert "sensor.config_test_1" in entity_ids

    # Cleanup
    async with AsyncSessionLocal() as session:
        entities = (await session.execute(select(Entity).where(Entity.config_entry_id == "entry_789"))).scalars().all()
        for entity in entities:
            await session.delete(entity)
        device = (await session.execute(select(Device).where(Device.device_id == "test_device_config"))).scalar_one()
        await session.delete(device)
        await session.commit()


@pytest.mark.asyncio
async def test_get_device_hierarchy_endpoint(test_client):
    """Test GET /api/devices/{device_id}/hierarchy endpoint"""
    await init_db()

    async with AsyncSessionLocal() as session:
        # Setup: Create parent and child devices
        parent_device = Device(device_id="parent_device_hierarchy", name="Parent Device", manufacturer="Test Co")
        session.add(parent_device)

        child_device = Device(
            device_id="child_device_hierarchy",
            name="Child Device",
            manufacturer="Test Co",
            via_device="parent_device_hierarchy"
        )
        session.add(child_device)
        await session.commit()

    # Test endpoint for child device
    response = await test_client.get("/api/devices/child_device_hierarchy/hierarchy")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["device_id"] == "child_device_hierarchy"
    assert data["device"] is not None
    assert data["device"]["device_id"] == "child_device_hierarchy"
    assert data["parent_device"] is not None
    assert data["parent_device"]["device_id"] == "parent_device_hierarchy"
    assert data["child_devices"] == []

    # Test endpoint for parent device
    response = await test_client.get("/api/devices/parent_device_hierarchy/hierarchy")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["device_id"] == "parent_device_hierarchy"
    assert data["parent_device"] is None
    assert len(data["child_devices"]) == 1
    assert data["child_devices"][0]["device_id"] == "child_device_hierarchy"

    # Cleanup
    async with AsyncSessionLocal() as session:
        child_device = (await session.execute(select(Device).where(Device.device_id == "child_device_hierarchy"))).scalar_one()
        await session.delete(child_device)
        parent_device = (await session.execute(select(Device).where(Device.device_id == "parent_device_hierarchy"))).scalar_one()
        await session.delete(parent_device)
        await session.commit()


@pytest.mark.asyncio
async def test_get_entities_by_device_not_found(test_client):
    """Test GET /api/entities/by-device/{device_id} with non-existent device"""
    await init_db()

    response = await test_client.get("/api/entities/by-device/nonexistent_device")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["count"] == 0
    assert len(data["entities"]) == 0


@pytest.mark.asyncio
async def test_get_device_for_entity_not_found(test_client):
    """Test GET /api/entities/{entity_id}/device with non-existent entity"""
    await init_db()

    response = await test_client.get("/api/entities/nonexistent.entity/device")

    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()


@pytest.mark.asyncio
async def test_get_sibling_entities_no_siblings(test_client):
    """Test GET /api/entities/{entity_id}/siblings when entity has no siblings"""
    await init_db()

    async with AsyncSessionLocal() as session:
        # Setup: Create device with single entity
        device = Device(device_id="test_device_single", name="Test Device")
        session.add(device)

        entity = Entity(entity_id="light.single_test", device_id="test_device_single", domain="light", platform="test")
        session.add(entity)
        await session.commit()

    # Test endpoint
    response = await test_client.get("/api/entities/light.single_test/siblings")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["count"] == 0
    assert len(data["siblings"]) == 0

    # Cleanup
    async with AsyncSessionLocal() as session:
        entity = (await session.execute(select(Entity).where(Entity.entity_id == "light.single_test"))).scalar_one()
        await session.delete(entity)
        device = (await session.execute(select(Device).where(Device.device_id == "test_device_single"))).scalar_one()
        await session.delete(device)
        await session.commit()

