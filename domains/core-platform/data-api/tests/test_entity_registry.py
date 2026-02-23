"""
Unit tests for EntityRegistry service

Tests relationship query methods for entity registry with device and area relationships.
"""


import pytest
from src.database import AsyncSessionLocal, init_db
from src.models import Device, Entity
from src.models.entity_registry_entry import EntityRegistryEntry
from src.services.entity_registry import EntityRegistry


@pytest.mark.asyncio
async def test_get_entities_by_device():
    """Test getting all entities for a device"""
    await init_db()

    async with AsyncSessionLocal() as session:
        # Create device
        device = Device(
            device_id="test_device_1",
            name="Test Device",
            manufacturer="Test Co",
            model="Model X",
            config_entry_id="entry_123"
        )
        session.add(device)

        # Create entities
        entity1 = Entity(
            entity_id="light.test_1",
            device_id="test_device_1",
            domain="light",
            platform="test",
            config_entry_id="entry_123"
        )
        entity2 = Entity(
            entity_id="sensor.test_1",
            device_id="test_device_1",
            domain="sensor",
            platform="test",
            config_entry_id="entry_123"
        )
        session.add(entity1)
        session.add(entity2)
        await session.commit()

        # Test EntityRegistry
        registry = EntityRegistry(session)
        entities = await registry.get_entities_by_device("test_device_1")

        assert len(entities) == 2
        entity_ids = [e.entity_id for e in entities]
        assert "light.test_1" in entity_ids
        assert "sensor.test_1" in entity_ids

        # Verify related_entities includes siblings
        for entity in entities:
            if entity.entity_id == "light.test_1":
                assert "sensor.test_1" in entity.related_entities
            elif entity.entity_id == "sensor.test_1":
                assert "light.test_1" in entity.related_entities

        # Cleanup
        await session.delete(entity1)
        await session.delete(entity2)
        await session.delete(device)
        await session.commit()


@pytest.mark.asyncio
async def test_get_device_for_entity():
    """Test getting device for an entity"""
    await init_db()

    async with AsyncSessionLocal() as session:
        # Create device and entity
        device = Device(
            device_id="test_device_2",
            name="Test Device 2",
            manufacturer="Test Co",
            config_entry_id="entry_456"
        )
        session.add(device)

        entity = Entity(
            entity_id="light.test_2",
            device_id="test_device_2",
            domain="light",
            platform="test"
        )
        session.add(entity)
        await session.commit()

        # Test EntityRegistry
        registry = EntityRegistry(session)
        device_result = await registry.get_device_for_entity("light.test_2")

        assert device_result is not None
        assert device_result.device_id == "test_device_2"
        assert device_result.name == "Test Device 2"

        # Cleanup
        await session.delete(entity)
        await session.delete(device)
        await session.commit()


@pytest.mark.asyncio
async def test_get_sibling_entities():
    """Test getting sibling entities (same device)"""
    await init_db()

    async with AsyncSessionLocal() as session:
        # Create device with multiple entities
        device = Device(device_id="test_device_3", name="Test Device 3")
        session.add(device)

        entity1 = Entity(entity_id="light.test_3", device_id="test_device_3", domain="light", platform="test")
        entity2 = Entity(entity_id="sensor.test_3", device_id="test_device_3", domain="sensor", platform="test")
        entity3 = Entity(entity_id="switch.test_3", device_id="test_device_3", domain="switch", platform="test")

        session.add(entity1)
        session.add(entity2)
        session.add(entity3)
        await session.commit()

        # Test EntityRegistry
        registry = EntityRegistry(session)
        siblings = await registry.get_sibling_entities("light.test_3")

        # Should include all entities from same device
        assert len(siblings) == 3
        sibling_ids = [s.entity_id for s in siblings]
        assert "light.test_3" in sibling_ids
        assert "sensor.test_3" in sibling_ids
        assert "switch.test_3" in sibling_ids

        # Cleanup
        await session.delete(entity1)
        await session.delete(entity2)
        await session.delete(entity3)
        await session.delete(device)
        await session.commit()


@pytest.mark.asyncio
async def test_get_entities_in_area():
    """Test getting all entities in an area"""
    await init_db()

    async with AsyncSessionLocal() as session:
        # Create devices and entities in same area
        device1 = Device(device_id="test_device_4", name="Device 4", area_id="living_room")
        device2 = Device(device_id="test_device_5", name="Device 5", area_id="living_room")
        session.add(device1)
        session.add(device2)

        entity1 = Entity(entity_id="light.living_room_1", device_id="test_device_4", domain="light", area_id="living_room", platform="test")
        entity2 = Entity(entity_id="light.living_room_2", device_id="test_device_5", domain="light", area_id="living_room", platform="test")
        entity3 = Entity(entity_id="sensor.living_room", device_id="test_device_4", domain="sensor", area_id="living_room", platform="test")

        session.add(entity1)
        session.add(entity2)
        session.add(entity3)
        await session.commit()

        # Test EntityRegistry
        registry = EntityRegistry(session)
        entities = await registry.get_entities_in_area("living_room")

        assert len(entities) == 3
        entity_ids = [e.entity_id for e in entities]
        assert "light.living_room_1" in entity_ids
        assert "light.living_room_2" in entity_ids
        assert "sensor.living_room" in entity_ids

        # Cleanup
        await session.delete(entity1)
        await session.delete(entity2)
        await session.delete(entity3)
        await session.delete(device1)
        await session.delete(device2)
        await session.commit()


@pytest.mark.asyncio
async def test_get_entities_by_config_entry():
    """Test getting entities by config entry ID"""
    await init_db()

    async with AsyncSessionLocal() as session:
        # Create entities with same config_entry_id
        device1 = Device(device_id="test_device_6", name="Device 6", config_entry_id="entry_789")
        device2 = Device(device_id="test_device_7", name="Device 7", config_entry_id="entry_789")
        session.add(device1)
        session.add(device2)

        entity1 = Entity(entity_id="light.test_6", device_id="test_device_6", domain="light", config_entry_id="entry_789", platform="test")
        entity2 = Entity(entity_id="sensor.test_6", device_id="test_device_6", domain="sensor", config_entry_id="entry_789", platform="test")
        entity3 = Entity(entity_id="light.test_7", device_id="test_device_7", domain="light", config_entry_id="entry_789", platform="test")

        session.add(entity1)
        session.add(entity2)
        session.add(entity3)
        await session.commit()

        # Test EntityRegistry
        registry = EntityRegistry(session)
        entities = await registry.get_entities_by_config_entry("entry_789")

        assert len(entities) == 3
        entity_ids = [e.entity_id for e in entities]
        assert "light.test_6" in entity_ids
        assert "sensor.test_6" in entity_ids
        assert "light.test_7" in entity_ids

        # Cleanup
        await session.delete(entity1)
        await session.delete(entity2)
        await session.delete(entity3)
        await session.delete(device1)
        await session.delete(device2)
        await session.commit()


@pytest.mark.asyncio
async def test_get_device_hierarchy():
    """Test getting device hierarchy (via_device relationships)"""
    await init_db()

    async with AsyncSessionLocal() as session:
        # Create parent device
        parent_device = Device(device_id="parent_device", name="Parent Device", manufacturer="Test Co")
        session.add(parent_device)

        # Create child device with via_device
        child_device = Device(
            device_id="child_device",
            name="Child Device",
            manufacturer="Test Co",
            via_device="parent_device"
        )
        session.add(child_device)
        await session.commit()

        # Test EntityRegistry
        registry = EntityRegistry(session)
        hierarchy = await registry.get_device_hierarchy("child_device")

        assert hierarchy["device_id"] == "child_device"
        assert hierarchy["parent_device"] is not None
        assert hierarchy["parent_device"]["device_id"] == "parent_device"
        assert hierarchy["child_devices"] == []

        # Test parent device hierarchy
        parent_hierarchy = await registry.get_device_hierarchy("parent_device")
        assert parent_hierarchy["device_id"] == "parent_device"
        assert parent_hierarchy["parent_device"] is None
        assert len(parent_hierarchy["child_devices"]) == 1
        assert parent_hierarchy["child_devices"][0]["device_id"] == "child_device"

        # Cleanup
        await session.delete(child_device)
        await session.delete(parent_device)
        await session.commit()


@pytest.mark.asyncio
async def test_get_entities_by_device_no_device():
    """Test getting entities by device when device doesn't exist"""
    await init_db()

    async with AsyncSessionLocal() as session:
        registry = EntityRegistry(session)
        entities = await registry.get_entities_by_device("nonexistent_device")

        assert len(entities) == 0


@pytest.mark.asyncio
async def test_get_sibling_entities_no_device():
    """Test getting sibling entities when entity has no device"""
    await init_db()

    async with AsyncSessionLocal() as session:
        # Create entity without device_id
        entity = Entity(entity_id="light.orphan", domain="light", platform="test")
        session.add(entity)
        await session.commit()

        registry = EntityRegistry(session)
        siblings = await registry.get_sibling_entities("light.orphan")

        assert len(siblings) == 0

        # Cleanup
        await session.delete(entity)
        await session.commit()


@pytest.mark.asyncio
async def test_entity_registry_entry_from_entity_and_device():
    """Test EntityRegistryEntry creation from Entity and Device models"""
    await init_db()

    async with AsyncSessionLocal() as session:
        # Create device and entity
        device = Device(
            device_id="test_device_8",
            name="Test Device 8",
            manufacturer="Test Co",
            model="Model Y",
            sw_version="1.0.0",
            via_device=None,
            config_entry_id="entry_999"
        )
        session.add(device)

        entity = Entity(
            entity_id="light.test_8",
            device_id="test_device_8",
            domain="light",
            platform="test",
            config_entry_id="entry_999",
            name="Test Light",
            name_by_user="My Light",
            friendly_name="My Light"
        )
        session.add(entity)
        await session.commit()

        # Create EntityRegistryEntry
        entry = EntityRegistryEntry.from_entity_and_device(
            entity=entity,
            device=device,
            related_entities=["sensor.test_8"]
        )

        assert entry.entity_id == "light.test_8"
        assert entry.device_id == "test_device_8"
        assert entry.manufacturer == "Test Co"
        assert entry.model == "Model Y"
        assert entry.config_entry_id == "entry_999"
        assert entry.name == "Test Light"
        assert entry.name_by_user == "My Light"
        assert entry.friendly_name == "My Light"
        assert "sensor.test_8" in entry.related_entities

        # Test to_dict
        entry_dict = entry.to_dict()
        assert entry_dict["entity_id"] == "light.test_8"
        assert entry_dict["device_id"] == "test_device_8"
        assert entry_dict["manufacturer"] == "Test Co"

        # Cleanup
        await session.delete(entity)
        await session.delete(device)
        await session.commit()

