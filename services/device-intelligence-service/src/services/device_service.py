"""
Device Intelligence Service - Device Service

Simple device service for database operations.
"""

import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from datetime import datetime, timezone

from ..models.database import Device, DeviceCapability, DeviceHealthMetric

logger = logging.getLogger(__name__)

class DeviceService:
    """Simple device service for database operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_all_devices(self, limit: int = 100) -> List[Device]:
        """Get all devices with limit."""
        try:
            stmt = select(Device).limit(limit)
            result = await self.session.execute(stmt)
            devices = result.scalars().all()
            logger.info(f"Retrieved {len(devices)} devices")
            return devices
        except Exception as e:
            logger.error(f"Error retrieving devices: {e}")
            return []
    
    async def upsert_device(self, device_data: Dict[str, Any]) -> Device:
        """Upsert a device (insert or update)."""
        try:
            # Check if device exists
            stmt = select(Device).where(Device.id == device_data["id"])
            result = await self.session.execute(stmt)
            existing_device = result.scalar_one_or_none()
            
            if existing_device:
                # Update existing device
                for key, value in device_data.items():
                    if hasattr(existing_device, key):
                        setattr(existing_device, key, value)
                existing_device.updated_at = datetime.now(timezone.utc)
                await self.session.commit()
                logger.debug(f"Updated device: {device_data['id']}")
                return existing_device
            else:
                # Create new device
                device = Device(**device_data)
                self.session.add(device)
                await self.session.commit()
                logger.debug(f"Created device: {device_data['id']}")
                return device
                
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error upserting device {device_data.get('id', 'unknown')}: {e}")
            raise
    
    async def bulk_upsert_devices(self, devices_data: List[Dict[str, Any]]) -> List[Device]:
        """Bulk upsert multiple devices using a single transaction."""
        if not devices_data:
            return []

        try:
            sanitized_payload: List[Dict[str, Any]] = []
            missing_integrations: List[str] = []

            for entry in devices_data:
                integration_value = (entry.get("integration") or "").strip()
                if not integration_value:
                    integration_value = "unknown"
                    missing_integrations.append(entry.get("id", "unknown"))

                sanitized_entry = dict(entry)
                sanitized_entry["integration"] = integration_value
                sanitized_payload.append(sanitized_entry)

            stmt = sqlite_insert(Device).values(sanitized_payload)

            update_fields = {
                key: stmt.excluded[key]
                for key in sanitized_payload[0].keys()
                if key not in {"id", "created_at"}
            }

            stmt = stmt.on_conflict_do_update(
                index_elements=[Device.id],
                set_=update_fields,
            )

            await self.session.execute(stmt)
            await self.session.commit()

            device_ids = [payload["id"] for payload in sanitized_payload]
            result = await self.session.execute(
                select(Device).where(Device.id.in_(device_ids))
            )
            devices = result.scalars().all()

            if missing_integrations:
                logger.warning(
                    "⚠️ Missing integration metadata for %d devices during bulk upsert (showing up to 5 IDs): %s",
                    len(missing_integrations),
                    missing_integrations[:5],
                )

            logger.info(f"Bulk upserted {len(devices)} devices with single transaction")
            return devices

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error bulk upserting devices: {e}")
            raise

    async def get_device_by_id(self, device_id: str) -> Optional[Device]:
        """Get device by ID."""
        try:
            stmt = select(Device).where(Device.id == device_id)
            result = await self.session.execute(stmt)
            device = result.scalar_one_or_none()
            if device:
                logger.info(f"Retrieved device: {device_id}")
            else:
                logger.info(f"Device not found: {device_id}")
            return device
        except Exception as e:
            logger.error(f"Error retrieving device {device_id}: {e}")
            return None
    
    async def bulk_upsert_capabilities(self, capabilities_data: List[Dict[str, Any]]) -> int:
        """Bulk upsert device capabilities with a single transaction."""
        if not capabilities_data:
            return 0

        try:
            stmt = sqlite_insert(DeviceCapability).values(capabilities_data)
            stmt = stmt.on_conflict_do_update(
                index_elements=["device_id", "capability_name"],
                set_={
                    "capability_type": stmt.excluded.capability_type,
                    "properties": stmt.excluded.properties,
                    "exposed": stmt.excluded.exposed,
                    "configured": stmt.excluded.configured,
                    "source": stmt.excluded.source,
                    "last_updated": stmt.excluded.last_updated,
                },
            )

            await self.session.execute(stmt)
            await self.session.commit()

            logger.info("Bulk upserted %d capabilities", len(capabilities_data))
            return len(capabilities_data)

        except Exception as e:
            await self.session.rollback()
            logger.error("Error bulk upserting capabilities: %s", e)
            raise
    
    async def get_device_capabilities(self, device_id: str) -> List[DeviceCapability]:
        """Get capabilities for a device."""
        try:
            stmt = select(DeviceCapability).where(DeviceCapability.device_id == device_id)
            result = await self.session.execute(stmt)
            capabilities = result.scalars().all()
            logger.info(f"Retrieved {len(capabilities)} capabilities for device {device_id}")
            return capabilities
        except Exception as e:
            logger.error(f"Error retrieving capabilities for device {device_id}: {e}")
            return []
    
    async def get_device_health_metrics(self, device_id: str, limit: int = 100) -> List[DeviceHealthMetric]:
        """Get health metrics for a device."""
        try:
            stmt = select(DeviceHealthMetric).where(
                DeviceHealthMetric.device_id == device_id
            ).order_by(DeviceHealthMetric.timestamp.desc()).limit(limit)
            result = await self.session.execute(stmt)
            metrics = result.scalars().all()
            logger.info(f"Retrieved {len(metrics)} health metrics for device {device_id}")
            return metrics
        except Exception as e:
            logger.error(f"Error retrieving health metrics for device {device_id}: {e}")
            return []
    
    async def get_devices_by_area(self, area_id: str) -> List[Device]:
        """Get devices by area."""
        try:
            stmt = select(Device).where(Device.area_id == area_id)
            result = await self.session.execute(stmt)
            devices = result.scalars().all()
            logger.info(f"Retrieved {len(devices)} devices for area {area_id}")
            return devices
        except Exception as e:
            logger.error(f"Error retrieving devices for area {area_id}: {e}")
            return []
    
    async def get_devices_by_integration(self, integration: str) -> List[Device]:
        """Get devices by integration."""
        try:
            stmt = select(Device).where(Device.integration == integration)
            result = await self.session.execute(stmt)
            devices = result.scalars().all()
            logger.info(f"Retrieved {len(devices)} devices for integration {integration}")
            return devices
        except Exception as e:
            logger.error(f"Error retrieving devices for integration {integration}: {e}")
            return []
    
    async def get_device_stats(self) -> Dict[str, Any]:
        """Get device statistics."""
        try:
            # Total devices
            total_devices_stmt = select(func.count(Device.id))
            total_devices_result = await self.session.execute(total_devices_stmt)
            total_devices = total_devices_result.scalar() or 0
            
            # Devices by integration
            integration_stmt = select(Device.integration, func.count(Device.id)).group_by(Device.integration)
            integration_result = await self.session.execute(integration_stmt)
            devices_by_integration = {row[0]: row[1] for row in integration_result}
            
            # Devices by area
            area_stmt = select(Device.area_id, func.count(Device.id)).group_by(Device.area_id)
            area_result = await self.session.execute(area_stmt)
            devices_by_area = {row[0]: row[1] for row in area_result if row[0]}
            
            # Average health score
            health_stmt = select(func.avg(Device.health_score)).where(Device.health_score.isnot(None))
            health_result = await self.session.execute(health_stmt)
            average_health_score = float(health_result.scalar() or 0)
            
            # Total capabilities
            capabilities_stmt = select(func.count(DeviceCapability.device_id))
            capabilities_result = await self.session.execute(capabilities_stmt)
            total_capabilities = capabilities_result.scalar() or 0
            
            stats = {
                "total_devices": total_devices,
                "devices_by_integration": devices_by_integration,
                "devices_by_area": devices_by_area,
                "average_health_score": average_health_score,
                "total_capabilities": total_capabilities
            }
            
            logger.info(f"Retrieved device statistics: {total_devices} devices, {total_capabilities} capabilities")
            return stats
            
        except Exception as e:
            logger.error(f"Error retrieving device statistics: {e}")
            return {
                "total_devices": 0,
                "devices_by_integration": {},
                "devices_by_area": {},
                "average_health_score": 0.0,
                "total_capabilities": 0
            }
