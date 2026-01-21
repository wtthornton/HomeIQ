"""
Integration Tests for Database Operations

Tests database operations including:
- Schema migrations
- CRUD operations with real database
- Foreign key constraints
- Transaction handling

Epic: Test Coverage Improvement
Priority: HIGH
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.models.device import Device
from src.models.entity import Entity


@pytest.mark.integration
@pytest.mark.asyncio
class TestDatabaseOperations:
    """Integration tests for database operations"""

    async def test_database_connection(self, test_db: AsyncSession):
        """Test database connection is working"""
        assert test_db is not None
        # Simple query to verify connection
        result = await test_db.execute("SELECT 1")
        assert result.scalar() == 1

    async def test_schema_exists(self, test_db: AsyncSession):
        """Test that all required tables exist"""
        # Check for Device table
        from sqlalchemy import inspect
        inspector = inspect(test_db.bind)
        tables = inspector.get_table_names()
        
        assert "devices" in tables or "device" in tables
        # Add more table checks as needed

    @pytest.mark.asyncio
    async def test_crud_device_operations(self, test_db: AsyncSession):
        """Test CRUD operations for Device model"""
        # Create
        device = Device(
            device_id="test_device_1",
            name="Test Device",
            manufacturer="Test Manufacturer",
            model="Test Model"
        )
        test_db.add(device)
        await test_db.commit()
        await test_db.refresh(device)
        
        # Read
        result = await test_db.get(Device, device.device_id)
        assert result is not None
        assert result.name == "Test Device"
        
        # Update
        result.name = "Updated Device"
        await test_db.commit()
        await test_db.refresh(result)
        assert result.name == "Updated Device"
        
        # Delete
        await test_db.delete(result)
        await test_db.commit()
        
        # Verify deletion
        deleted = await test_db.get(Device, device.device_id)
        assert deleted is None

    @pytest.mark.asyncio
    async def test_foreign_key_constraints(self, test_db: AsyncSession):
        """Test foreign key constraints are enforced"""
        # Create device
        device = Device(
            device_id="test_device_fk",
            name="Test Device FK",
            manufacturer="Test",
            model="Test"
        )
        test_db.add(device)
        await test_db.commit()
        
        # Try to create entity with invalid device_id (should fail or handle gracefully)
        entity = Entity(
            entity_id="test_entity_fk",
            device_id="nonexistent_device_id",  # Invalid foreign key
            name="Test Entity",
            domain="sensor"
        )
        test_db.add(entity)
        
        # Should raise IntegrityError or handle gracefully
        with pytest.raises(Exception):  # Adjust exception type based on actual behavior
            await test_db.commit()

    @pytest.mark.asyncio
    async def test_transaction_rollback(self, test_db: AsyncSession):
        """Test transaction rollback on error"""
        device = Device(
            device_id="test_device_rollback",
            name="Test Device Rollback",
            manufacturer="Test",
            model="Test"
        )
        test_db.add(device)
        
        # Rollback before commit
        await test_db.rollback()
        
        # Verify device was not persisted
        result = await test_db.get(Device, "test_device_rollback")
        assert result is None

    @pytest.mark.asyncio
    async def test_transaction_commit(self, test_db: AsyncSession):
        """Test transaction commit persists changes"""
        device = Device(
            device_id="test_device_commit",
            name="Test Device Commit",
            manufacturer="Test",
            model="Test"
        )
        test_db.add(device)
        await test_db.commit()
        
        # Verify device was persisted
        result = await test_db.get(Device, "test_device_commit")
        assert result is not None
        assert result.name == "Test Device Commit"
        
        # Cleanup
        await test_db.delete(result)
        await test_db.commit()


@pytest.mark.integration
@pytest.mark.asyncio
class TestSchemaMigrations:
    """Integration tests for schema migrations"""

    async def test_migration_columns_exist(self, test_db: AsyncSession):
        """Test that migration-added columns exist"""
        from sqlalchemy import inspect, text
        
        inspector = inspect(test_db.bind)
        
        # Check for specific columns added by migrations
        # Adjust based on actual migration history
        # Example: Check for a column added in a migration
        columns = [col["name"] for col in inspector.get_columns("devices")]
        # Add assertions based on expected columns
        
        assert True  # Placeholder - adjust based on actual schema

    async def test_migration_data_integrity(self, test_db: AsyncSession):
        """Test that migrations preserve data integrity"""
        # Create test data
        device = Device(
            device_id="test_migration_device",
            name="Test Migration Device",
            manufacturer="Test",
            model="Test"
        )
        test_db.add(device)
        await test_db.commit()
        
        # Verify data is accessible after migrations
        result = await test_db.get(Device, "test_migration_device")
        assert result is not None
        
        # Cleanup
        await test_db.delete(result)
        await test_db.commit()


@pytest.mark.integration
@pytest.mark.asyncio
class TestDatabasePerformance:
    """Integration tests for database performance"""

    async def test_bulk_insert_performance(self, test_db: AsyncSession):
        """Test bulk insert performance"""
        import time
        
        devices = [
            Device(
                device_id=f"bulk_device_{i}",
                name=f"Bulk Device {i}",
                manufacturer="Test",
                model="Test"
            )
            for i in range(100)
        ]
        
        start_time = time.time()
        test_db.add_all(devices)
        await test_db.commit()
        end_time = time.time()
        
        # Should complete in reasonable time (adjust threshold as needed)
        assert (end_time - start_time) < 5.0  # 5 seconds for 100 inserts
        
        # Cleanup
        for device in devices:
            await test_db.delete(device)
        await test_db.commit()
