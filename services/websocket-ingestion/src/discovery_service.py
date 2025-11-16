"""
Home Assistant Device & Entity Discovery Service

Queries Home Assistant registries to discover connected devices, entities, and integrations.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from aiohttp import ClientWebSocketResponse

from models import Device, Entity, ConfigEntry

logger = logging.getLogger(__name__)


class DiscoveryService:
    """Service for discovering devices and entities from Home Assistant registries"""
    
    def __init__(self, influxdb_manager=None):
        self.message_id_counter = 1000  # Start at 1000 to avoid conflicts
        self.pending_responses: Dict[int, asyncio.Future] = {}
        self.influxdb_manager = influxdb_manager
        
        # Epic 23.2: Device and area mapping caches for event enrichment
        self.entity_to_device: Dict[str, str] = {}  # entity_id → device_id
        self.device_to_area: Dict[str, str] = {}    # device_id → area_id
        self.entity_to_area: Dict[str, str] = {}    # entity_id → area_id (direct assignment)
        self.device_metadata: Dict[str, Dict[str, Any]] = {}  # device_id → {manufacturer, model, sw_version}
        
        logger.info("Discovery service initialized with device/area mapping caches")
        
    def _get_next_id(self) -> int:
        """Get next message ID"""
        self.message_id_counter += 1
        return self.message_id_counter
    
    async def discover_devices(self, websocket: ClientWebSocketResponse) -> List[Dict[str, Any]]:
        """
        Discover all devices from Home Assistant device registry
        
        Args:
            websocket: Connected WebSocket client
            
        Returns:
            List of device dictionaries
            
        Raises:
            Exception: If command fails or response is invalid
        """
        try:
            message_id = self._get_next_id()
            logger.info("=" * 80)
            logger.info(f"📱 DISCOVERING DEVICES (message_id: {message_id})")
            logger.info("=" * 80)
            
            # Send device registry list command
            await websocket.send_json({
                "id": message_id,
                "type": "config/device_registry/list"
            })
            
            logger.info("✅ Device registry command sent, waiting for response...")
            
            # Wait for response
            response = await self._wait_for_response(websocket, message_id, timeout=10.0)
            
            if not response:
                logger.error("❌ No response received for device registry command")
                return []
            
            if not response.get("success"):
                error_msg = response.get("error", {}).get("message", "Unknown error")
                logger.error(f"❌ Device registry command failed: {error_msg}")
                return []
            
            devices = response.get("result", [])
            device_count = len(devices)
            
            logger.info(f"✅ Discovered {device_count} devices")
            
            # Epic 23.2: Build device → area mapping cache
            # Epic 23.5: Build device metadata cache
            for device in devices:
                device_id = device.get("id")
                if device_id:
                    # Store device → area mapping
                    area_id = device.get("area_id")
                    if area_id:
                        self.device_to_area[device_id] = area_id
                    
                    # Epic 23.5: Store device metadata (manufacturer, model, version)
                    self.device_metadata[device_id] = {
                        "manufacturer": device.get("manufacturer"),
                        "model": device.get("model"),
                        "sw_version": device.get("sw_version"),
                        "name": device.get("name"),
                        "name_by_user": device.get("name_by_user")
                    }
            
            logger.info(f"📍 Cached {len(self.device_to_area)} device → area mappings")
            logger.info(f"🏷️  Cached {len(self.device_metadata)} device metadata entries")
            
            # Log sample device if available
            if devices:
                sample = devices[0]
                logger.info(f"📱 Sample device: {sample.get('name', 'Unknown')} "
                          f"(manufacturer: {sample.get('manufacturer', 'Unknown')}, "
                          f"model: {sample.get('model', 'Unknown')})")
            
            return devices
            
        except asyncio.TimeoutError:
            logger.error("❌ Timeout waiting for device registry response")
            return []
        except Exception as e:
            logger.error(f"❌ Error discovering devices: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    async def discover_entities(self, websocket: ClientWebSocketResponse) -> List[Dict[str, Any]]:
        """
        Discover all entities from Home Assistant entity registry
        
        Args:
            websocket: Connected WebSocket client
            
        Returns:
            List of entity dictionaries
            
        Raises:
            Exception: If command fails or response is invalid
        """
        try:
            message_id = self._get_next_id()
            logger.info("=" * 80)
            logger.info(f"🔌 DISCOVERING ENTITIES (message_id: {message_id})")
            logger.info("=" * 80)
            
            # Send entity registry list command
            await websocket.send_json({
                "id": message_id,
                "type": "config/entity_registry/list"
            })
            
            logger.info("✅ Entity registry command sent, waiting for response...")
            
            # Wait for response
            response = await self._wait_for_response(websocket, message_id, timeout=10.0)
            
            if not response:
                logger.error("❌ No response received for entity registry command")
                return []
            
            if not response.get("success"):
                error_msg = response.get("error", {}).get("message", "Unknown error")
                logger.error(f"❌ Entity registry command failed: {error_msg}")
                return []
            
            entities = response.get("result", [])
            entity_count = len(entities)
            
            logger.info(f"✅ Discovered {entity_count} entities")
            
            # Epic 23.2: Build entity → device and entity → area mapping caches
            for entity in entities:
                entity_id = entity.get("entity_id")
                if entity_id:
                    # Store entity → device mapping
                    device_id = entity.get("device_id")
                    if device_id:
                        self.entity_to_device[entity_id] = device_id
                    
                    # Store entity → area mapping (direct assignment)
                    area_id = entity.get("area_id")
                    if area_id:
                        self.entity_to_area[entity_id] = area_id
            
            logger.info(f"🔗 Cached {len(self.entity_to_device)} entity → device mappings")
            logger.info(f"📍 Cached {len(self.entity_to_area)} entity → area mappings (direct)")
            
            # Log sample entity if available
            if entities:
                sample = entities[0]
                entity_id = sample.get('entity_id', 'Unknown')
                domain = entity_id.split('.')[0] if '.' in entity_id else 'Unknown'
                logger.info(f"🔌 Sample entity: {entity_id} "
                          f"(platform: {sample.get('platform', 'Unknown')}, "
                          f"domain: {domain})")
            
            return entities
            
        except asyncio.TimeoutError:
            logger.error("❌ Timeout waiting for entity registry response")
            return []
        except Exception as e:
            logger.error(f"❌ Error discovering entities: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    async def discover_config_entries(self, websocket: ClientWebSocketResponse) -> List[Dict[str, Any]]:
        """
        Discover all config entries (integrations) from Home Assistant
        
        Args:
            websocket: Connected WebSocket client
            
        Returns:
            List of config entry dictionaries
            
        Raises:
            Exception: If command fails or response is invalid
        """
        try:
            message_id = self._get_next_id()
            logger.info("=" * 80)
            logger.info(f"🔧 DISCOVERING CONFIG ENTRIES (message_id: {message_id})")
            logger.info("=" * 80)
            
            # Send config entries list command
            await websocket.send_json({
                "id": message_id,
                "type": "config_entries/list"
            })
            
            logger.info("✅ Config entries command sent, waiting for response...")
            
            # Wait for response
            response = await self._wait_for_response(websocket, message_id, timeout=10.0)
            
            if not response:
                logger.error("❌ No response received for config entries command")
                return []
            
            if not response.get("success"):
                error_msg = response.get("error", {}).get("message", "Unknown error")
                logger.error(f"❌ Config entries command failed: {error_msg}")
                return []
            
            config_entries = response.get("result", [])
            entry_count = len(config_entries)
            
            logger.info(f"✅ Discovered {entry_count} config entries")
            
            # Log sample config entry if available
            if config_entries:
                sample = config_entries[0]
                logger.info(f"🔧 Sample config entry: {sample.get('title', 'Unknown')} "
                          f"(domain: {sample.get('domain', 'Unknown')}, "
                          f"state: {sample.get('state', 'Unknown')})")
            
            return config_entries
            
        except asyncio.TimeoutError:
            logger.error("❌ Timeout waiting for config entries response")
            return []
        except Exception as e:
            logger.error(f"❌ Error discovering config entries: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    async def _wait_for_response(
        self, 
        websocket: ClientWebSocketResponse, 
        message_id: int,
        timeout: float = 10.0
    ) -> Optional[Dict[str, Any]]:
        """
        Wait for response with specific message ID
        
        Args:
            websocket: WebSocket connection
            message_id: Message ID to wait for
            timeout: Timeout in seconds
            
        Returns:
            Response dictionary or None if timeout/error
        """
        try:
            start_time = asyncio.get_event_loop().time()
            
            while True:
                # Check timeout
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed > timeout:
                    raise asyncio.TimeoutError(f"Timeout waiting for message {message_id}")
                
                # Wait for message with remaining timeout
                remaining_timeout = timeout - elapsed
                msg = await asyncio.wait_for(
                    websocket.receive(),
                    timeout=remaining_timeout
                )
                
                if msg.type == 1:  # TEXT message
                    data = msg.json()
                    
                    # Check if this is our response
                    if data.get("id") == message_id:
                        return data
                    else:
                        # Log and continue waiting for our message
                        logger.debug(f"Received message for different ID: {data.get('id')}, waiting for {message_id}")
                        continue
                else:
                    logger.warning(f"Received non-text message type: {msg.type}")
                    continue
                    
        except asyncio.TimeoutError:
            raise
        except Exception as e:
            logger.error(f"Error waiting for response: {e}")
            return None
    
    async def discover_all(self, websocket: ClientWebSocketResponse, store: bool = True) -> Dict[str, Any]:
        """
        Discover all devices, entities, and config entries
        
        Args:
            websocket: Connected WebSocket client
            store: Whether to store results in InfluxDB (default: True)
            
        Returns:
            Dictionary with 'devices', 'entities', and 'config_entries' keys
        """
        logger.info("=" * 80)
        logger.info("🚀 STARTING COMPLETE HOME ASSISTANT DISCOVERY")
        logger.info("=" * 80)
        
        devices_data = await self.discover_devices(websocket)
        entities_data = await self.discover_entities(websocket)
        # TEMPORARY: Skip config entries - command not supported in this HA version
        config_entries_data = []  # await self.discover_config_entries(websocket)
        
        logger.info("=" * 80)
        logger.info("✅ DISCOVERY COMPLETE")
        logger.info(f"   Devices: {len(devices_data)}")
        logger.info(f"   Entities: {len(entities_data)}")
        logger.info(f"   Config Entries: {len(config_entries_data)}")
        logger.info("=" * 80)
        
        # Convert to models and store if requested
        if store and self.influxdb_manager:
            logger.info("💾 Storing discovered data in InfluxDB...")
            await self.store_discovery_results(devices_data, entities_data, config_entries_data)
        elif store and not self.influxdb_manager:
            logger.warning("⚠️  Storage requested but no InfluxDB manager available")
        
        return {
            "devices": devices_data,
            "entities": entities_data,
            "config_entries": config_entries_data
        }
    
    async def store_discovery_results(
        self,
        devices_data: List[Dict[str, Any]],
        entities_data: List[Dict[str, Any]],
        config_entries_data: List[Dict[str, Any]]
    ) -> bool:
        """
        Store discovery results to SQLite (via data-api) and optionally to InfluxDB
        
        Args:
            devices_data: List of device dictionaries from HA
            entities_data: List of entity dictionaries from HA
            config_entries_data: List of config entry dictionaries from HA
            
        Returns:
            True if storage successful
        """
        import aiohttp
        import os
        
        try:
            # Primary storage: SQLite via data-api (simple HTTP POST)
            data_api_url = os.getenv('DATA_API_URL', 'http://homeiq-data-api:8006')
            api_key = os.getenv('DATA_API_API_KEY') or os.getenv('DATA_API_KEY') or os.getenv('API_KEY')
            
            # Create session with proper connector (disable SSL for internal HTTP)
            connector = aiohttp.TCPConnector(ssl=False)
            timeout = aiohttp.ClientTimeout(total=30)
            
            async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                # Store devices to SQLite
                if devices_data:
                    try:
                        async with session.post(
                            f"{data_api_url}/internal/devices/bulk_upsert",
                            json=devices_data,
                            headers={"Authorization": f"Bearer {api_key}"} if api_key else None,
                            timeout=aiohttp.ClientTimeout(total=30)
                        ) as response:
                            if response.status == 200:
                                result = await response.json()
                                logger.info(f"✅ Stored {result.get('upserted', 0)} devices to SQLite")
                            else:
                                error_text = await response.text()
                                logger.error(f"❌ Failed to store devices to SQLite: {response.status} - {error_text}")
                    except Exception as e:
                        logger.error(f"❌ Error posting devices to data-api: {e}")
                
                # Store entities to SQLite
                if entities_data:
                    try:
                        async with session.post(
                            f"{data_api_url}/internal/entities/bulk_upsert",
                            json=entities_data,
                            headers={"Authorization": f"Bearer {api_key}"} if api_key else None,
                            timeout=aiohttp.ClientTimeout(total=30)
                        ) as response:
                            if response.status == 200:
                                result = await response.json()
                                logger.info(f"✅ Stored {result.get('upserted', 0)} entities to SQLite")
                            else:
                                error_text = await response.text()
                                logger.error(f"❌ Failed to store entities to SQLite: {response.status} - {error_text}")
                    except Exception as e:
                        logger.error(f"❌ Error posting entities to data-api: {e}")
            
            # Optional: Store snapshot to InfluxDB for historical tracking
            store_influx_history = os.getenv('STORE_DEVICE_HISTORY_IN_INFLUXDB', 'false').lower() == 'true'
            
            if store_influx_history and self.influxdb_manager:
                logger.info("📊 Storing device history snapshot to InfluxDB...")
                
                # Convert devices to models for InfluxDB
                devices = []
                for device_data in devices_data:
                    try:
                        device = Device.from_ha_device(device_data)
                        device.validate()
                        devices.append(device)
                    except Exception as e:
                        logger.warning(f"⚠️  Skipping invalid device for InfluxDB: {e}")
                
                # Convert entities to models for InfluxDB
                entities = []
                for entity_data in entities_data:
                    try:
                        entity = Entity.from_ha_entity(entity_data)
                        entity.validate()
                        entities.append(entity)
                    except Exception as e:
                        logger.warning(f"⚠️  Skipping invalid entity for InfluxDB: {e}")
                
                # Batch write to InfluxDB
                if devices:
                    device_points = [d.to_influx_point() for d in devices]
                    success = await self.influxdb_manager.batch_write_devices(device_points, bucket="home_assistant_events")
                    if success:
                        logger.info(f"✅ Stored {len(devices)} devices history to InfluxDB")
                
                if entities:
                    entity_points = [e.to_influx_point() for e in entities]
                    success = await self.influxdb_manager.batch_write_entities(entity_points, bucket="home_assistant_events")
                    if success:
                        logger.info(f"✅ Stored {len(entities)} entities history to InfluxDB")
            
            logger.info("=" * 80)
            logger.info("✅ STORAGE COMPLETE")
            logger.info("=" * 80)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error storing discovery results: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    async def subscribe_to_device_registry_events(self, websocket: ClientWebSocketResponse) -> bool:
        """
        Subscribe to device registry update events
        
        Args:
            websocket: Connected WebSocket client
            
        Returns:
            True if subscription successful
        """
        try:
            message_id = self._get_next_id()
            logger.info("📱 Subscribing to device registry update events...")
            
            await websocket.send_json({
                "id": message_id,
                "type": "subscribe_events",
                "event_type": "device_registry_updated"
            })
            
            # Wait for subscription confirmation
            response = await self._wait_for_response(websocket, message_id, timeout=5.0)
            
            if response and response.get("success"):
                logger.info("✅ Subscribed to device registry events")
                return True
            else:
                logger.error("❌ Failed to subscribe to device registry events")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error subscribing to device registry events: {e}")
            return False
    
    async def subscribe_to_entity_registry_events(self, websocket: ClientWebSocketResponse) -> bool:
        """
        Subscribe to entity registry update events
        
        Args:
            websocket: Connected WebSocket client
            
        Returns:
            True if subscription successful
        """
        try:
            message_id = self._get_next_id()
            logger.info("🔌 Subscribing to entity registry update events...")
            
            await websocket.send_json({
                "id": message_id,
                "type": "subscribe_events",
                "event_type": "entity_registry_updated"
            })
            
            # Wait for subscription confirmation
            response = await self._wait_for_response(websocket, message_id, timeout=5.0)
            
            if response and response.get("success"):
                logger.info("✅ Subscribed to entity registry events")
                return True
            else:
                logger.error("❌ Failed to subscribe to entity registry events")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error subscribing to entity registry events: {e}")
            return False
    
    async def handle_device_registry_event(self, event: Dict[str, Any]) -> bool:
        """
        Handle device registry update event
        
        Args:
            event: Event data from Home Assistant
            
        Returns:
            True if handled successfully
        """
        try:
            data = event.get("data", {})
            action = data.get("action", "unknown")
            device_data = data.get("device", {})
            device_id = data.get("device_id", "unknown")
            
            logger.info("=" * 80)
            logger.info(f"📱 DEVICE REGISTRY EVENT: {action.upper()}")
            logger.info(f"   Device ID: {device_id}")
            if device_data:
                logger.info(f"   Name: {device_data.get('name', 'Unknown')}")
                logger.info(f"   Manufacturer: {device_data.get('manufacturer', 'Unknown')}")
            logger.info("=" * 80)
            
            # Store update if we have InfluxDB and device data
            if self.influxdb_manager and device_data:
                try:
                    device = Device.from_ha_device(device_data)
                    device.validate()
                    point = device.to_influx_point()
                    await self.influxdb_manager.write_device(point, bucket="home_assistant_events")
                    logger.info(f"✅ Stored device update in InfluxDB")
                except Exception as e:
                    logger.warning(f"⚠️  Failed to store device update: {e}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error handling device registry event: {e}")
            return False
    
    async def handle_entity_registry_event(self, event: Dict[str, Any]) -> bool:
        """
        Handle entity registry update event
        
        Args:
            event: Event data from Home Assistant
            
        Returns:
            True if handled successfully
        """
        try:
            data = event.get("data", {})
            action = data.get("action", "unknown")
            entity_data = data.get("entity", {})
            entity_id = data.get("entity_id", "unknown")
            
            logger.info("=" * 80)
            logger.info(f"🔌 ENTITY REGISTRY EVENT: {action.upper()}")
            logger.info(f"   Entity ID: {entity_id}")
            if entity_data:
                logger.info(f"   Platform: {entity_data.get('platform', 'Unknown')}")
            logger.info("=" * 80)
            
            # Store update if we have InfluxDB and entity data
            if self.influxdb_manager and entity_data:
                try:
                    entity = Entity.from_ha_entity(entity_data)
                    entity.validate()
                    point = entity.to_influx_point()
                    await self.influxdb_manager.write_entity(point, bucket="home_assistant_events")
                    logger.info(f"✅ Stored entity update in InfluxDB")
                except Exception as e:
                    logger.warning(f"⚠️  Failed to store entity update: {e}")
            
            # Epic 23.2: Update mapping caches on entity registry events
            if entity_id and entity_data:
                device_id = entity_data.get("device_id")
                if device_id:
                    self.entity_to_device[entity_id] = device_id
                
                area_id = entity_data.get("area_id")
                if area_id:
                    self.entity_to_area[entity_id] = area_id
                
                logger.debug(f"Updated mapping cache for entity {entity_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error handling entity registry event: {e}")
            return False
    
    # Epic 23.2: Helper methods for device/area lookup
    def get_device_id(self, entity_id: str) -> Optional[str]:
        """
        Get device_id for an entity
        
        Args:
            entity_id: The entity ID to look up
            
        Returns:
            device_id if found, None otherwise
        """
        return self.entity_to_device.get(entity_id)
    
    def get_area_id(self, entity_id: str, device_id: Optional[str] = None) -> Optional[str]:
        """
        Get area_id for an entity or device
        
        Checks in this order:
        1. Entity direct area assignment
        2. Device area assignment (if device_id provided or looked up)
        
        Args:
            entity_id: The entity ID to look up
            device_id: Optional device ID (will be looked up if not provided)
            
        Returns:
            area_id if found, None otherwise
        """
        # Check entity-level area first (direct assignment)
        entity_area = self.entity_to_area.get(entity_id)
        if entity_area:
            return entity_area
        
        # Fallback to device-level area
        if not device_id:
            device_id = self.get_device_id(entity_id)
        
        if device_id:
            return self.device_to_area.get(device_id)
        
        return None
    
    # Epic 23.5: Helper method for device metadata lookup
    def get_device_metadata(self, device_id: str) -> Optional[Dict[str, Any]]:
        """
        Get device metadata (manufacturer, model, sw_version)
        
        Args:
            device_id: The device ID to look up
            
        Returns:
            Device metadata dict if found, None otherwise
        """
        return self.device_metadata.get(device_id)
    
    def get_cache_statistics(self) -> Dict[str, int]:
        """
        Get statistics about mapping caches
        
        Returns:
            Dictionary with cache statistics
        """
        return {
            "entity_to_device_mappings": len(self.entity_to_device),
            "device_to_area_mappings": len(self.device_to_area),
            "entity_to_area_mappings": len(self.entity_to_area),
            "device_metadata_entries": len(self.device_metadata)
        }

