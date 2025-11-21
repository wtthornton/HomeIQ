"""
Unit Tests for Device Intelligence Database Models (Epic AI-2, Story AI2.2)

Tests DeviceCapability and DeviceFeatureUsage models, CRUD operations,
and database migrations.
"""


import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from src.database.crud import (
    get_all_capabilities,
    get_capability_stats,
    get_device_capability,
    get_device_feature_usage,
    initialize_feature_usage,
    upsert_device_capability,
)
from src.database.models import Base

# ============================================================================
# Test Database Fixture
# ============================================================================

@pytest_asyncio.fixture
async def db_engine():
    """Create in-memory SQLite database for testing"""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Cleanup
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine):
    """Create database session for testing"""
    async_session = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        yield session


# ============================================================================
# DeviceCapability Model Tests
# ============================================================================

class TestDeviceCapabilityModel:
    """Test DeviceCapability model and CRUD operations"""

    @pytest.mark.asyncio
    async def test_create_device_capability(self, db_session):
        """Test creating device capability record"""
        capability = await upsert_device_capability(
            db=db_session,
            device_model="VZM31-SN",
            manufacturer="Inovelli",
            description="Red Series Dimmer Switch",
            capabilities={
                "light_control": {"type": "composite"},
                "smart_bulb_mode": {"type": "enum"},
            },
            mqtt_exposes=[{"type": "light"}],
        )

        assert capability.device_model == "VZM31-SN"
        assert capability.manufacturer == "Inovelli"
        assert capability.integration_type == "zigbee2mqtt"
        assert len(capability.capabilities) == 2
        assert "light_control" in capability.capabilities
        assert "smart_bulb_mode" in capability.capabilities

    @pytest.mark.asyncio
    async def test_upsert_updates_existing_capability(self, db_session):
        """Test upsert updates existing record instead of creating duplicate"""
        # First insert
        cap1 = await upsert_device_capability(
            db=db_session,
            device_model="VZM31-SN",
            manufacturer="Inovelli",
            description="Version 1",
            capabilities={"light_control": {}},
            mqtt_exposes=[],
        )

        # Second upsert with same model (should update)
        cap2 = await upsert_device_capability(
            db=db_session,
            device_model="VZM31-SN",  # Same primary key
            manufacturer="Inovelli",
            description="Version 2 Updated",  # Updated description
            capabilities={"light_control": {}, "smart_bulb_mode": {}},  # Added capability
            mqtt_exposes=[{"type": "light"}],
        )

        # Should be same record (same primary key)
        assert cap1.device_model == cap2.device_model

        # Should have updated values
        assert cap2.description == "Version 2 Updated"
        assert len(cap2.capabilities) == 2

        # Verify only one record exists
        all_caps = await get_all_capabilities(db_session)
        assert len(all_caps) == 1

    @pytest.mark.asyncio
    async def test_get_device_capability_found(self, db_session):
        """Test retrieving existing capability"""
        # Create capability
        await upsert_device_capability(
            db=db_session,
            device_model="MCCGQ11LM",
            manufacturer="Aqara",
            description="Contact Sensor",
            capabilities={"contact": {}, "vibration": {}},
            mqtt_exposes=[],
        )

        # Retrieve it
        capability = await get_device_capability(db_session, "MCCGQ11LM")

        assert capability is not None
        assert capability.device_model == "MCCGQ11LM"
        assert capability.manufacturer == "Aqara"
        assert len(capability.capabilities) == 2

    @pytest.mark.asyncio
    async def test_get_device_capability_not_found(self, db_session):
        """Test retrieving non-existent capability returns None"""
        capability = await get_device_capability(db_session, "NONEXISTENT")

        assert capability is None

    @pytest.mark.asyncio
    async def test_get_all_capabilities_no_filter(self, db_session):
        """Test retrieving all capabilities"""
        # Create multiple capabilities
        await upsert_device_capability(
            db=db_session,
            device_model="VZM31-SN",
            manufacturer="Inovelli",
            description="Switch",
            capabilities={"light": {}},
            mqtt_exposes=[],
        )
        await upsert_device_capability(
            db=db_session,
            device_model="MCCGQ11LM",
            manufacturer="Aqara",
            description="Sensor",
            capabilities={"contact": {}},
            mqtt_exposes=[],
        )

        capabilities = await get_all_capabilities(db_session)

        assert len(capabilities) == 2

    @pytest.mark.asyncio
    async def test_get_all_capabilities_filter_by_manufacturer(self, db_session):
        """Test filtering capabilities by manufacturer"""
        # Create capabilities from multiple manufacturers
        await upsert_device_capability(
            db=db_session,
            device_model="VZM31-SN",
            manufacturer="Inovelli",
            description="Switch",
            capabilities={"light": {}},
            mqtt_exposes=[],
        )
        await upsert_device_capability(
            db=db_session,
            device_model="MCCGQ11LM",
            manufacturer="Aqara",
            description="Sensor",
            capabilities={"contact": {}},
            mqtt_exposes=[],
        )
        await upsert_device_capability(
            db=db_session,
            device_model="LED1624G9",
            manufacturer="IKEA",
            description="Bulb",
            capabilities={"light": {}},
            mqtt_exposes=[],
        )

        # Filter by Inovelli
        inovelli_caps = await get_all_capabilities(db_session, manufacturer="Inovelli")
        assert len(inovelli_caps) == 1
        assert inovelli_caps[0].manufacturer == "Inovelli"

        # Filter by Aqara
        aqara_caps = await get_all_capabilities(db_session, manufacturer="Aqara")
        assert len(aqara_caps) == 1
        assert aqara_caps[0].manufacturer == "Aqara"


# ============================================================================
# DeviceFeatureUsage Model Tests
# ============================================================================

class TestDeviceFeatureUsageModel:
    """Test DeviceFeatureUsage model and CRUD operations"""

    @pytest.mark.asyncio
    async def test_initialize_feature_usage(self, db_session):
        """Test initializing feature usage tracking for a device"""
        features = ["led_notifications", "smart_bulb_mode", "auto_off_timer"]

        usage_records = await initialize_feature_usage(
            db=db_session,
            device_id="light.kitchen_switch",
            features=features,
        )

        assert len(usage_records) == 3

        # All should be unconfigured initially
        assert all(not u.configured for u in usage_records)

        # All should have same device_id
        assert all(u.device_id == "light.kitchen_switch" for u in usage_records)

        # Feature names should match
        feature_names = {u.feature_name for u in usage_records}
        assert feature_names == set(features)

    @pytest.mark.asyncio
    async def test_get_device_feature_usage(self, db_session):
        """Test retrieving feature usage for a device"""
        # Initialize usage
        features = ["led_notifications", "smart_bulb_mode"]
        await initialize_feature_usage(
            db=db_session,
            device_id="light.kitchen_switch",
            features=features,
        )

        # Retrieve usage
        usage = await get_device_feature_usage(db_session, "light.kitchen_switch")

        assert len(usage) == 2
        assert all(u.device_id == "light.kitchen_switch" for u in usage)

    @pytest.mark.asyncio
    async def test_feature_usage_composite_primary_key(self, db_session):
        """Test composite primary key prevents duplicates"""
        # Initialize same device+feature twice
        await initialize_feature_usage(
            db=db_session,
            device_id="light.kitchen",
            features=["led_notifications"],
        )

        # Initialize again (should merge, not duplicate)
        await initialize_feature_usage(
            db=db_session,
            device_id="light.kitchen",
            features=["led_notifications"],
        )

        # Should still only have 1 record
        usage = await get_device_feature_usage(db_session, "light.kitchen")
        assert len(usage) == 1


# ============================================================================
# Integration Tests (Models + CRUD)
# ============================================================================

class TestDeviceIntelligenceDatabaseIntegration:
    """Test integration between DeviceCapability and DeviceFeatureUsage"""

    @pytest.mark.asyncio
    async def test_full_capability_storage_workflow(self, db_session):
        """
        Test complete workflow: Store capability → Query capability

        Simulates what happens when MQTTCapabilityListener receives
        a device from Zigbee2MQTT bridge.
        """
        # Step 1: Store device capability (what listener does)
        capability = await upsert_device_capability(
            db=db_session,
            device_model="VZM31-SN",
            manufacturer="Inovelli",
            description="Red Series Dimmer Switch",
            capabilities={
                "light_control": {"type": "composite"},
                "smart_bulb_mode": {"type": "enum"},
                "auto_off_timer": {"type": "numeric"},
                "led_notifications": {"type": "composite"},
            },
            mqtt_exposes=[{"type": "light"}, {"type": "enum", "name": "smartBulbMode"}],
        )

        assert len(capability.capabilities) == 4

        # Step 2: Query capability (what Feature Analyzer will do in Story 2.3)
        retrieved = await get_device_capability(db_session, "VZM31-SN")

        assert retrieved is not None
        assert retrieved.device_model == "VZM31-SN"
        assert len(retrieved.capabilities) == 4

    @pytest.mark.asyncio
    async def test_capability_stats(self, db_session):
        """Test get_capability_stats returns correct statistics"""
        # Create capabilities from multiple manufacturers
        await upsert_device_capability(
            db=db_session,
            device_model="VZM31-SN",
            manufacturer="Inovelli",
            description="Switch",
            capabilities={"light": {}},
            mqtt_exposes=[],
        )
        await upsert_device_capability(
            db=db_session,
            device_model="VZM35-SN",
            manufacturer="Inovelli",
            description="Fan Switch",
            capabilities={"fan": {}},
            mqtt_exposes=[],
        )
        await upsert_device_capability(
            db=db_session,
            device_model="MCCGQ11LM",
            manufacturer="Aqara",
            description="Sensor",
            capabilities={"contact": {}},
            mqtt_exposes=[],
        )

        # Initialize some feature usage
        await initialize_feature_usage(
            db=db_session,
            device_id="switch1",
            features=["light", "timer"],
        )

        # Get stats
        stats = await get_capability_stats(db_session)

        assert stats["total_models"] == 3
        assert stats["by_manufacturer"]["Inovelli"] == 2
        assert stats["by_manufacturer"]["Aqara"] == 1
        assert stats["total_usage_records"] == 2
        assert stats["unconfigured_features"] == 2  # All initially unconfigured


# ============================================================================
# Performance Tests
# ============================================================================

class TestDeviceIntelligenceDatabasePerformance:
    """Test database performance (NFR13: <100ms per device)"""

    @pytest.mark.asyncio
    async def test_upsert_performance(self, db_session):
        """Test upsert operation completes quickly"""
        import time

        start = time.time()

        await upsert_device_capability(
            db=db_session,
            device_model="VZM31-SN",
            manufacturer="Inovelli",
            description="Switch",
            capabilities={"light": {}, "mode": {}, "timer": {}},
            mqtt_exposes=[{"type": "light"}],
        )

        duration = time.time() - start

        # Should complete in <100ms (NFR13)
        assert duration < 0.1  # 100ms

    @pytest.mark.asyncio
    async def test_bulk_capability_storage(self, db_session):
        """Test storing 100 device models performs well"""
        import time

        start = time.time()

        # Store 100 device capabilities
        for i in range(100):
            await upsert_device_capability(
                db=db_session,
                device_model=f"Model{i}",
                manufacturer="Manufacturer",
                description=f"Device {i}",
                capabilities={"light": {}},
                mqtt_exposes=[],
            )

        duration = time.time() - start

        # Should complete in reasonable time
        # 100 devices * 100ms = 10s max
        assert duration < 10

        # Verify all stored
        all_caps = await get_all_capabilities(db_session)
        assert len(all_caps) == 100

    @pytest.mark.asyncio
    async def test_index_performance(self, db_session):
        """Test manufacturer index improves query performance"""
        # Create many capabilities
        for i in range(50):
            await upsert_device_capability(
                db=db_session,
                device_model=f"Inovelli-{i}",
                manufacturer="Inovelli",
                description="Device",
                capabilities={"light": {}},
                mqtt_exposes=[],
            )
        for i in range(50):
            await upsert_device_capability(
                db=db_session,
                device_model=f"Aqara-{i}",
                manufacturer="Aqara",
                description="Sensor",
                capabilities={"contact": {}},
                mqtt_exposes=[],
            )

        import time
        start = time.time()

        # Query by manufacturer (should use index)
        inovelli_caps = await get_all_capabilities(db_session, manufacturer="Inovelli")

        duration = time.time() - start

        # Should be fast with index
        assert duration < 0.1  # 100ms
        assert len(inovelli_caps) == 50


# ============================================================================
# Multi-Manufacturer Tests
# ============================================================================

class TestMultiManufacturerSupport:
    """Test database handles multiple manufacturers correctly"""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(("manufacturer", "model", "capabilities"), [
        ("Inovelli", "VZM31-SN", {"light": {}, "mode": {}}),
        ("Aqara", "MCCGQ11LM", {"contact": {}, "vibration": {}}),
        ("IKEA", "LED1624G9", {"light": {}, "color_temp": {}}),
        ("Xiaomi", "WSDCGQ11LM", {"temperature": {}, "humidity": {}}),
        ("Sonoff", "SNZB-01", {"action": {}}),
    ])
    async def test_store_various_manufacturers(self, db_session, manufacturer, model, capabilities):
        """Test storing capabilities from various manufacturers"""
        capability = await upsert_device_capability(
            db=db_session,
            device_model=model,
            manufacturer=manufacturer,
            description="Test Device",
            capabilities=capabilities,
            mqtt_exposes=[],
        )

        assert capability.device_model == model
        assert capability.manufacturer == manufacturer
        assert len(capability.capabilities) == len(capabilities)

    @pytest.mark.asyncio
    async def test_query_by_manufacturer(self, db_session):
        """Test querying capabilities by manufacturer"""
        # Create mixed manufacturers
        manufacturers_data = [
            ("Inovelli", "VZM31-SN"),
            ("Inovelli", "VZM35-SN"),
            ("Aqara", "MCCGQ11LM"),
            ("Aqara", "RTCGQ11LM"),
            ("Aqara", "WSDCGQ11LM"),
            ("IKEA", "LED1624G9"),
        ]

        for manuf, model in manufacturers_data:
            await upsert_device_capability(
                db=db_session,
                device_model=model,
                manufacturer=manuf,
                description="Device",
                capabilities={"test": {}},
                mqtt_exposes=[],
            )

        # Query by manufacturer
        inovelli = await get_all_capabilities(db_session, manufacturer="Inovelli")
        aqara = await get_all_capabilities(db_session, manufacturer="Aqara")
        ikea = await get_all_capabilities(db_session, manufacturer="IKEA")

        assert len(inovelli) == 2
        assert len(aqara) == 3
        assert len(ikea) == 1


# ============================================================================
# JSON Column Tests
# ============================================================================

class TestJSONCapabilitiesColumn:
    """Test JSON column functionality for capabilities"""

    @pytest.mark.asyncio
    async def test_json_capabilities_structure(self, db_session):
        """Test complex JSON capabilities are stored correctly"""
        complex_capabilities = {
            "led_notifications": {
                "type": "composite",
                "mqtt_name": "led_effect",
                "description": "7 individually addressable RGB LEDs",
                "complexity": "medium",
                "features": ["color", "brightness", "effect"],
            },
            "smart_bulb_mode": {
                "type": "enum",
                "mqtt_name": "smartBulbMode",
                "values": ["Disabled", "Enabled"],
                "complexity": "easy",
            },
            "auto_off_timer": {
                "type": "numeric",
                "mqtt_name": "autoTimerOff",
                "min": 0,
                "max": 32767,
                "unit": "seconds",
                "complexity": "medium",
            },
        }

        capability = await upsert_device_capability(
            db=db_session,
            device_model="VZM31-SN",
            manufacturer="Inovelli",
            description="Switch",
            capabilities=complex_capabilities,
            mqtt_exposes=[],
        )

        # Verify JSON structure preserved
        assert capability.capabilities["led_notifications"]["type"] == "composite"
        assert len(capability.capabilities["led_notifications"]["features"]) == 3
        assert capability.capabilities["smart_bulb_mode"]["values"] == ["Disabled", "Enabled"]
        assert capability.capabilities["auto_off_timer"]["max"] == 32767

    @pytest.mark.asyncio
    async def test_mqtt_exposes_stored_as_json(self, db_session):
        """Test raw MQTT exposes are stored correctly"""
        mqtt_exposes = [
            {"type": "light", "features": [{"name": "state"}, {"name": "brightness"}]},
            {"type": "enum", "name": "smartBulbMode", "values": ["Disabled", "Enabled"]},
        ]

        capability = await upsert_device_capability(
            db=db_session,
            device_model="VZM31-SN",
            manufacturer="Inovelli",
            description="Switch",
            capabilities={"light": {}},
            mqtt_exposes=mqtt_exposes,
        )

        # Verify raw exposes preserved
        assert len(capability.mqtt_exposes) == 2
        assert capability.mqtt_exposes[0]["type"] == "light"
        assert capability.mqtt_exposes[1]["type"] == "enum"

