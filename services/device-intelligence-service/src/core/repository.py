"""
Device Intelligence Service - Data Access Layer

Optimized data access layer using SQLAlchemy 2.0 async patterns and bulk operations.
Based on Context7 best practices for SQLite performance.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import bindparam, func, insert, select, update
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.cache import DeviceCache
from ..models.database import (
    Device,
    DeviceCapability,
    DeviceHealthMetric,
)

logger = logging.getLogger(__name__)


class DeviceRepository:
    """Repository for device data operations with caching and bulk operations."""

    def __init__(self, cache: DeviceCache):
        self.cache = cache

    # Device Operations
    async def get_device(self, session: AsyncSession, device_id: str) -> Device | None:
        """Get device by ID with cache."""
        # Try cache first
        cached_device = await self.cache.get_device(device_id)
        if cached_device:
            logger.debug(f"📦 Cache hit for device {device_id}")
            # Convert cached dict back to Device object
            return self._dict_to_device(cached_device)

        # Cache miss - query database
        logger.debug(f"📦 Cache miss for device {device_id}")
        stmt = select(Device).where(Device.id == device_id)
        result = await session.execute(stmt)
        device = result.scalar_one_or_none()

        if device:
            # Cache the result
            await self.cache.set_device(device_id, self._device_to_dict(device))

        return device

    async def get_all_devices(self, session: AsyncSession, limit: int = 1000) -> list[Device]:
        """Get all devices with pagination."""
        stmt = select(Device).limit(limit)
        result = await session.execute(stmt)
        return result.scalars().all()

    async def get_devices_by_area(self, session: AsyncSession, area_id: str) -> list[Device]:
        """Get devices by area with cache."""
        # Try cache first
        cached_devices = await self.cache.get_devices_by_area(area_id)
        if cached_devices:
            logger.debug(f"📦 Cache hit for area {area_id}")
            return [self._dict_to_device(d) for d in cached_devices]

        # Cache miss - query database
        logger.debug(f"📦 Cache miss for area {area_id}")
        stmt = select(Device).where(Device.area_id == area_id)
        result = await session.execute(stmt)
        devices = result.scalars().all()

        # Cache the result
        device_dicts = [self._device_to_dict(d) for d in devices]
        await self.cache.set_devices_by_area(area_id, device_dicts)

        return devices

    async def get_devices_by_integration(self, session: AsyncSession, integration: str) -> list[Device]:
        """Get devices by integration with cache."""
        # Try cache first
        cached_devices = await self.cache.get_devices_by_integration(integration)
        if cached_devices:
            logger.debug(f"📦 Cache hit for integration {integration}")
            return [self._dict_to_device(d) for d in cached_devices]

        # Cache miss - query database
        logger.debug(f"📦 Cache miss for integration {integration}")
        stmt = select(Device).where(Device.integration == integration)
        result = await session.execute(stmt)
        devices = result.scalars().all()

        # Cache the result
        device_dicts = [self._device_to_dict(d) for d in devices]
        await self.cache.set_devices_by_integration(integration, device_dicts)

        return devices

    async def create_device(self, session: AsyncSession, device_data: dict[str, Any]) -> Device:
        """Create new device."""
        device = Device(**device_data)
        session.add(device)
        await session.commit()
        await session.refresh(device)

        # Cache the new device
        await self.cache.set_device(device.id, self._device_to_dict(device))

        # Invalidate related caches
        if device.area_id:
            await self.cache.invalidate_area_cache(device.area_id)
        await self.cache.invalidate_integration_cache(device.integration)

        logger.info(f"✅ Created device {device.id}")
        return device

    async def update_device(self, session: AsyncSession, device_id: str, update_data: dict[str, Any]) -> Device | None:
        """Update device with cache invalidation."""
        stmt = select(Device).where(Device.id == device_id)
        result = await session.execute(stmt)
        device = result.scalar_one_or_none()

        if device:
            # Store old values for cache invalidation
            old_area_id = device.area_id
            old_integration = device.integration

            # Update device
            for key, value in update_data.items():
                if hasattr(device, key):
                    setattr(device, key, value)

            device.updated_at = datetime.now(timezone.utc)
            await session.commit()
            await session.refresh(device)

            # Update cache
            await self.cache.set_device(device.id, self._device_to_dict(device))

            # Invalidate related caches if changed
            if old_area_id != device.area_id:
                if old_area_id:
                    await self.cache.invalidate_area_cache(old_area_id)
                if device.area_id:
                    await self.cache.invalidate_area_cache(device.area_id)

            if old_integration != device.integration:
                await self.cache.invalidate_integration_cache(old_integration)
                await self.cache.invalidate_integration_cache(device.integration)

            logger.info(f"✅ Updated device {device_id}")

        return device

    async def delete_device(self, session: AsyncSession, device_id: str) -> bool:
        """Delete device with cache invalidation."""
        stmt = select(Device).where(Device.id == device_id)
        result = await session.execute(stmt)
        device = result.scalar_one_or_none()

        if device:
            # Store values for cache invalidation
            area_id = device.area_id
            integration = device.integration

            # Delete device (cascade will handle related records)
            await session.delete(device)
            await session.commit()

            # Invalidate caches
            await self.cache.invalidate_device(device_id)
            if area_id:
                await self.cache.invalidate_area_cache(area_id)
            if integration:
                await self.cache.invalidate_integration_cache(integration)

            logger.info(f"✅ Deleted device {device_id}")
            return True

        return False

    # Bulk Operations (Context7 optimized patterns)
    async def bulk_create_devices(self, session: AsyncSession, devices_data: list[dict[str, Any]]) -> list[Device]:
        """Bulk create devices using optimized SQLAlchemy patterns."""
        if not devices_data:
            return []

        # Use bulk insert for performance
        stmt = insert(Device)
        result = await session.execute(stmt, devices_data)
        await session.commit()

        # Get created devices
        device_ids = [d["id"] for d in devices_data]
        stmt = select(Device).where(Device.id.in_(device_ids))
        result = await session.execute(stmt)
        devices = result.scalars().all()

        # Cache all devices
        for device in devices:
            await self.cache.set_device(device.id, self._device_to_dict(device))

        # Invalidate related caches
        await self.cache.invalidate_all_device_cache()

        logger.info(f"✅ Bulk created {len(devices)} devices")
        return devices

    async def bulk_update_devices(self, session: AsyncSession, updates: list[dict[str, Any]]) -> int:
        """Bulk update devices using bindparam pattern."""
        if not updates:
            return 0

        # Use bindparam for bulk updates
        stmt = (
            update(Device)
            .where(Device.id == bindparam("device_id"))
            .values(
                name=bindparam("name"),
                manufacturer=bindparam("manufacturer"),
                model=bindparam("model"),
                area_id=bindparam("area_id"),
                health_score=bindparam("health_score"),
                updated_at=func.now()
            )
        )

        result = await session.execute(stmt, updates)
        await session.commit()

        # Invalidate caches for updated devices
        for update_data in updates:
            device_id = update_data["device_id"]
            await self.cache.invalidate_device(device_id)

        logger.info(f"✅ Bulk updated {result.rowcount} devices")
        return result.rowcount

    # Device Capabilities Operations
    async def get_device_capabilities(self, session: AsyncSession, device_id: str) -> list[DeviceCapability]:
        """Get device capabilities with eager loading."""
        stmt = (
            select(DeviceCapability)
            .where(DeviceCapability.device_id == device_id)
            .order_by(DeviceCapability.capability_name)
        )
        result = await session.execute(stmt)
        return result.scalars().all()

    async def bulk_upsert_capabilities(self, session: AsyncSession, capabilities_data: list[dict[str, Any]]) -> int:
        """Bulk upsert capabilities using SQLite UPSERT."""
        if not capabilities_data:
            return 0

        # Use SQLite UPSERT for efficiency
        stmt = sqlite_insert(DeviceCapability).values(capabilities_data)
        stmt = stmt.on_conflict_do_update(
            index_elements=["device_id", "capability_name"],
            set_={
                "capability_type": stmt.excluded.capability_type,
                "properties": stmt.excluded.properties,
                "exposed": stmt.excluded.exposed,
                "configured": stmt.excluded.configured,
                "source": stmt.excluded.source,
                "last_updated": func.now()
            }
        )

        result = await session.execute(stmt)
        await session.commit()

        logger.info(f"✅ Bulk upserted {len(capabilities_data)} capabilities")
        return len(capabilities_data)

    # Device Health Operations
    async def record_health_metric(self, session: AsyncSession, device_id: str, metric_name: str,
                                 metric_value: float, metric_unit: str | None = None,
                                 metadata_json: dict[str, Any] | None = None) -> DeviceHealthMetric:
        """Record a health metric for a device."""
        metric = DeviceHealthMetric(
            device_id=device_id,
            metric_name=metric_name,
            metric_value=metric_value,
            metric_unit=metric_unit,
            metadata_json=metadata_json
        )
        session.add(metric)
        await session.commit()
        await session.refresh(metric)

        logger.debug(f"📊 Recorded health metric {metric_name} for device {device_id}")
        return metric

    async def get_device_health_metrics(self, session: AsyncSession, device_id: str,
                                     limit: int = 100) -> list[DeviceHealthMetric]:
        """Get recent health metrics for a device."""
        stmt = (
            select(DeviceHealthMetric)
            .where(DeviceHealthMetric.device_id == device_id)
            .order_by(DeviceHealthMetric.timestamp.desc())
            .limit(limit)
        )
        result = await session.execute(stmt)
        return result.scalars().all()

    async def get_all_device_metrics(self, session: AsyncSession) -> list[dict[str, Any]]:
        """Get all device metrics for training purposes."""
        stmt = (
            select(DeviceHealthMetric)
            .order_by(DeviceHealthMetric.timestamp.desc())
            .limit(1000)  # Limit for training data
        )
        result = await session.execute(stmt)
        metrics = result.scalars().all()

        # Convert to dictionary format for ML training
        training_data = []
        for metric in metrics:
            training_data.append({
                "device_id": metric.device_id,
                "response_time": metric.response_time or 0,
                "error_rate": metric.error_rate or 0,
                "battery_level": metric.battery_level or 0,
                "signal_strength": metric.signal_strength or 0,
                "usage_frequency": metric.usage_frequency or 0,
                "temperature": metric.temperature or 0,
                "humidity": metric.humidity or 0,
                "uptime_hours": metric.uptime_hours or 0,
                "restart_count": metric.restart_count or 0,
                "connection_drops": metric.connection_drops or 0,
                "data_transfer_rate": metric.data_transfer_rate or 0,
                "failure_imminent": 0  # Default to no failure for training
            })

        return training_data

    # Statistics and Analytics
    async def get_device_stats(self, session: AsyncSession) -> dict[str, Any]:
        """Get device statistics."""
        stats = {}

        # Total devices
        result = await session.execute(select(func.count(Device.id)))
        stats["total_devices"] = result.scalar()

        # Devices by integration
        result = await session.execute(
            select(Device.integration, func.count(Device.id))
            .group_by(Device.integration)
        )
        stats["devices_by_integration"] = dict(result.all())

        # Devices by area
        result = await session.execute(
            select(Device.area_id, func.count(Device.id))
            .where(Device.area_id.isnot(None))
            .group_by(Device.area_id)
        )
        stats["devices_by_area"] = dict(result.all())

        # Average health score
        result = await session.execute(
            select(func.avg(Device.health_score))
            .where(Device.health_score.isnot(None))
        )
        stats["average_health_score"] = round(result.scalar() or 0, 2)

        # Total capabilities
        result = await session.execute(select(func.count(DeviceCapability.device_id)))
        stats["total_capabilities"] = result.scalar()

        return stats

    # Cache Management
    async def invalidate_device_cache(self, device_id: str):
        """Invalidate device cache."""
        await self.cache.invalidate_device(device_id)

    async def invalidate_all_caches(self):
        """Invalidate all device caches."""
        await self.cache.invalidate_all_device_cache()

    # Helper Methods
    def _device_to_dict(self, device: Device) -> dict[str, Any]:
        """Convert Device object to dictionary for caching."""
        return {
            "id": device.id,
            "name": device.name,
            "manufacturer": device.manufacturer,
            "model": device.model,
            "area_id": device.area_id,
            "area_name": device.area_name,
            "integration": device.integration,
            "sw_version": device.sw_version,
            "hw_version": device.hw_version,
            "power_source": device.power_source,
            "via_device_id": device.via_device_id,
            "ha_device_id": device.ha_device_id,
            "zigbee_device_id": device.zigbee_device_id,
            "last_seen": device.last_seen.isoformat() if device.last_seen else None,
            "health_score": device.health_score,
            "disabled_by": device.disabled_by,
            "created_at": device.created_at.isoformat(),
            "updated_at": device.updated_at.isoformat()
        }

    def _dict_to_device(self, device_dict: dict[str, Any]) -> Device:
        """Convert dictionary to Device object."""
        # Parse datetime fields
        if device_dict.get("last_seen"):
            device_dict["last_seen"] = datetime.fromisoformat(device_dict["last_seen"])
        if device_dict.get("created_at"):
            device_dict["created_at"] = datetime.fromisoformat(device_dict["created_at"])
        if device_dict.get("updated_at"):
            device_dict["updated_at"] = datetime.fromisoformat(device_dict["updated_at"])

        return Device(**device_dict)
