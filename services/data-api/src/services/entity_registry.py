"""
EntityRegistry Service

Provides relationship query methods for entity registry with device and area relationships.
"""

import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ..models.entity import Entity
from ..models.device import Device
from ..models.entity_registry_entry import EntityRegistryEntry

logger = logging.getLogger(__name__)


class EntityRegistry:
    """Entity registry with relationship queries"""
    
    def __init__(self, db: AsyncSession):
        """
        Initialize EntityRegistry service
        
        Args:
            db: Async database session
        """
        self.db = db
        # Simple in-memory cache for frequently accessed relationships
        self._cache: Dict[str, Any] = {}
        self._cache_ttl = 300  # 5 minutes cache TTL
    
    async def get_entities_by_device(self, device_id: str) -> List[EntityRegistryEntry]:
        """
        Get all entities for a device
        
        Args:
            device_id: Device ID
            
        Returns:
            List of EntityRegistryEntry instances
        """
        try:
            # Query entities with device relationship
            result = await self.db.execute(
                select(Entity)
                .where(Entity.device_id == device_id)
                .options(selectinload(Entity.device))
            )
            entities = result.scalars().all()
            
            # Get device for metadata
            device_result = await self.db.execute(
                select(Device).where(Device.device_id == device_id)
            )
            device = device_result.scalar_one_or_none()
            
            # Convert to EntityRegistryEntry
            registry_entries = []
            entity_ids = [e.entity_id for e in entities]
            
            for entity in entities:
                # Get sibling entities (all entities from same device)
                related_entities = [eid for eid in entity_ids if eid != entity.entity_id]
                
                entry = EntityRegistryEntry.from_entity_and_device(
                    entity=entity,
                    device=device,
                    related_entities=related_entities
                )
                registry_entries.append(entry)
            
            return registry_entries
            
        except Exception as e:
            logger.error(f"Error getting entities by device {device_id}: {e}")
            return []
    
    async def get_device_for_entity(self, entity_id: str) -> Optional[Device]:
        """
        Get device for an entity
        
        Args:
            entity_id: Entity ID
            
        Returns:
            Device instance or None
        """
        try:
            result = await self.db.execute(
                select(Entity)
                .where(Entity.entity_id == entity_id)
                .options(selectinload(Entity.device))
            )
            entity = result.scalar_one_or_none()
            
            if entity and entity.device_id:
                device_result = await self.db.execute(
                    select(Device).where(Device.device_id == entity.device_id)
                )
                return device_result.scalar_one_or_none()
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting device for entity {entity_id}: {e}")
            return None
    
    async def get_sibling_entities(self, entity_id: str) -> List[EntityRegistryEntry]:
        """
        Get entities from same device (siblings)
        
        Args:
            entity_id: Entity ID
            
        Returns:
            List of EntityRegistryEntry instances (sibling entities)
        """
        try:
            # Get the entity first
            result = await self.db.execute(
                select(Entity)
                .where(Entity.entity_id == entity_id)
                .options(selectinload(Entity.device))
            )
            entity = result.scalar_one_or_none()
            
            if not entity or not entity.device_id:
                return []
            
            # Get all entities from same device
            return await self.get_entities_by_device(entity.device_id)
            
        except Exception as e:
            logger.error(f"Error getting sibling entities for {entity_id}: {e}")
            return []
    
    async def get_entities_in_area(self, area_id: str) -> List[EntityRegistryEntry]:
        """
        Get all entities in an area
        
        Args:
            area_id: Area ID
            
        Returns:
            List of EntityRegistryEntry instances
        """
        try:
            # Query entities by area_id
            result = await self.db.execute(
                select(Entity)
                .where(Entity.area_id == area_id)
                .options(selectinload(Entity.device))
            )
            entities = result.scalars().all()
            
            # Get devices for metadata
            device_ids = {e.device_id for e in entities if e.device_id}
            devices = {}
            if device_ids:
                devices_result = await self.db.execute(
                    select(Device).where(Device.device_id.in_(device_ids))
                )
                for device in devices_result.scalars().all():
                    devices[device.device_id] = device
            
            # Convert to EntityRegistryEntry
            registry_entries = []
            
            # Group entities by device for related_entities
            entities_by_device: Dict[str, List[Entity]] = {}
            for entity in entities:
                if entity.device_id:
                    if entity.device_id not in entities_by_device:
                        entities_by_device[entity.device_id] = []
                    entities_by_device[entity.device_id].append(entity)
            
            for entity in entities:
                device = devices.get(entity.device_id) if entity.device_id else None
                
                # Get sibling entities from same device
                related_entities = []
                if entity.device_id and entity.device_id in entities_by_device:
                    related_entities = [
                        e.entity_id for e in entities_by_device[entity.device_id]
                        if e.entity_id != entity.entity_id
                    ]
                
                entry = EntityRegistryEntry.from_entity_and_device(
                    entity=entity,
                    device=device,
                    related_entities=related_entities
                )
                registry_entries.append(entry)
            
            return registry_entries
            
        except Exception as e:
            logger.error(f"Error getting entities in area {area_id}: {e}")
            return []
    
    async def get_entities_by_config_entry(self, config_entry_id: str) -> List[EntityRegistryEntry]:
        """
        Get entities by config entry ID
        
        Args:
            config_entry_id: Config entry ID
            
        Returns:
            List of EntityRegistryEntry instances
        """
        try:
            # Query entities by config_entry_id
            result = await self.db.execute(
                select(Entity)
                .where(Entity.config_entry_id == config_entry_id)
                .options(selectinload(Entity.device))
            )
            entities = result.scalars().all()
            
            # Get devices for metadata
            device_ids = {e.device_id for e in entities if e.device_id}
            devices = {}
            if device_ids:
                devices_result = await self.db.execute(
                    select(Device).where(Device.device_id.in_(device_ids))
                )
                for device in devices_result.scalars().all():
                    devices[device.device_id] = device
            
            # Convert to EntityRegistryEntry
            registry_entries = []
            
            # Group entities by device for related_entities
            entities_by_device: Dict[str, List[Entity]] = {}
            for entity in entities:
                if entity.device_id:
                    if entity.device_id not in entities_by_device:
                        entities_by_device[entity.device_id] = []
                    entities_by_device[entity.device_id].append(entity)
            
            for entity in entities:
                device = devices.get(entity.device_id) if entity.device_id else None
                
                # Get sibling entities from same device
                related_entities = []
                if entity.device_id and entity.device_id in entities_by_device:
                    related_entities = [
                        e.entity_id for e in entities_by_device[entity.device_id]
                        if e.entity_id != entity.entity_id
                    ]
                
                entry = EntityRegistryEntry.from_entity_and_device(
                    entity=entity,
                    device=device,
                    related_entities=related_entities
                )
                registry_entries.append(entry)
            
            return registry_entries
            
        except Exception as e:
            logger.error(f"Error getting entities by config entry {config_entry_id}: {e}")
            return []
    
    async def get_device_hierarchy(self, device_id: str) -> Dict[str, Any]:
        """
        Get device hierarchy (via_device relationships)
        
        Args:
            device_id: Device ID
            
        Returns:
            Dictionary with device hierarchy information
        """
        try:
            # Get the device
            result = await self.db.execute(
                select(Device).where(Device.device_id == device_id)
            )
            device = result.scalar_one_or_none()
            
            if not device:
                return {
                    'device_id': device_id,
                    'device': None,
                    'parent_device': None,
                    'child_devices': []
                }
            
            # Get parent device (via via_device)
            parent_device = None
            if device.via_device:
                parent_result = await self.db.execute(
                    select(Device).where(Device.device_id == device.via_device)
                )
                parent_device = parent_result.scalar_one_or_none()
            
            # Get child devices (devices that have this device as via_device)
            child_result = await self.db.execute(
                select(Device).where(Device.via_device == device_id)
            )
            child_devices = child_result.scalars().all()
            
            return {
                'device_id': device_id,
                'device': {
                    'device_id': device.device_id,
                    'name': device.name,
                    'manufacturer': device.manufacturer,
                    'model': device.model,
                    'via_device': device.via_device,
                    'config_entry_id': device.config_entry_id
                },
                'parent_device': {
                    'device_id': parent_device.device_id,
                    'name': parent_device.name,
                    'manufacturer': parent_device.manufacturer,
                    'model': parent_device.model
                } if parent_device else None,
                'child_devices': [
                    {
                        'device_id': child.device_id,
                        'name': child.name,
                        'manufacturer': child.manufacturer,
                        'model': child.model
                    }
                    for child in child_devices
                ]
            }
            
        except Exception as e:
            logger.error(f"Error getting device hierarchy for {device_id}: {e}")
            return {
                'device_id': device_id,
                'device': None,
                'parent_device': None,
                'child_devices': []
            }

