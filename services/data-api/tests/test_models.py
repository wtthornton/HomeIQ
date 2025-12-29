"""
Tests for Device and Entity models
Story 22.2
"""


import pytest
from sqlalchemy import select
from src.database import AsyncSessionLocal
from src.models import Device, Entity


@pytest.mark.asyncio
async def test_device_creation(fresh_db):
    """Test creating a device"""

    async with AsyncSessionLocal() as session:
        device = Device(
            device_id="test_device_1",
            name="Test Device",
            manufacturer="Test Co",
            model="Model X",
            area_id="living_room"
        )
        session.add(device)
        await session.commit()

        # Verify
        result = await session.execute(select(Device).where(Device.device_id == "test_device_1"))
        saved_device = result.scalar_one()
        assert saved_device.name == "Test Device"
        assert saved_device.manufacturer == "Test Co"

        # Cleanup
        await session.delete(saved_device)
        await session.commit()


@pytest.mark.asyncio
async def test_entity_with_foreign_key(fresh_db):
    """Test entity with foreign key to device"""

    async with AsyncSessionLocal() as session:
        # Create device first
        device = Device(
            device_id="test_device_2",
            name="Test Device 2"
        )
        session.add(device)
        await session.commit()

        # Create entity
        entity = Entity(
            entity_id="light.test",
            device_id="test_device_2",
            domain="light",
            platform="test"
        )
        session.add(entity)
        await session.commit()

        # Verify relationship
        result = await session.execute(
            select(Entity).where(Entity.entity_id == "light.test")
        )
        saved_entity = result.scalar_one()
        assert saved_entity.device_id == "test_device_2"
        assert saved_entity.domain == "light"

        # Cleanup
        await session.delete(saved_entity)
        await session.delete(device)
        await session.commit()


@pytest.mark.asyncio
async def test_device_cascade_delete(fresh_db):
    """Test that deleting device cascades to entities"""

    async with AsyncSessionLocal() as session:
        # Create device with entity
        device = Device(device_id="test_device_3", name="Test Device 3")
        entity = Entity(entity_id="sensor.test", device_id="test_device_3", domain="sensor")

        session.add(device)
        session.add(entity)
        await session.commit()

        # Delete device
        await session.delete(device)
        await session.commit()

        # Verify entity deleted too
        result = await session.execute(select(Entity).where(Entity.entity_id == "sensor.test"))
        entity_check = result.scalar_one_or_none()
        assert entity_check is None  # Cascade delete worked


@pytest.mark.asyncio
async def test_device_query_by_area(fresh_db):
    """Test filtering devices by area"""

    async with AsyncSessionLocal() as session:
        # Create test devices
        device1 = Device(device_id="d1", name="Device 1", area_id="kitchen")
        device2 = Device(device_id="d2", name="Device 2", area_id="bedroom")
        session.add_all([device1, device2])
        await session.commit()

        # Query by area
        result = await session.execute(select(Device).where(Device.area_id == "kitchen"))
        devices = result.scalars().all()
        assert len(devices) == 1
        assert devices[0].device_id == "d1"

        # Cleanup
        await session.delete(device1)
        await session.delete(device2)
        await session.commit()

