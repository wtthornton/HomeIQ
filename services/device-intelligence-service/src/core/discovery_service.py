"""
Device Intelligence Service - Discovery Service

Main discovery service that orchestrates device discovery from multiple sources.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from ..clients.ha_client import HADevice, HAEntity, HAArea
from ..clients.mqtt_client import MQTTClient, ZigbeeDevice, ZigbeeGroup
from .device_parser import DeviceParser, UnifiedDevice
from ..services.device_service import DeviceService
from ..core.database import get_db_session
from ..config import Settings

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../shared'))

from shared.enhanced_ha_connection_manager import ha_connection_manager

logger = logging.getLogger(__name__)


@dataclass
class DiscoveryStatus:
    """Discovery service status."""
    service_running: bool
    ha_connected: bool
    mqtt_connected: bool
    last_discovery: Optional[datetime]
    devices_count: int
    areas_count: int
    errors: List[str]


class DiscoveryService:
    """Main discovery service orchestrating device discovery from multiple sources."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        
        # Clients - HA client will be initialized with unified connection manager
        self.ha_client = None  # Will be initialized in start() method
        self.mqtt_client = MQTTClient(
            settings.MQTT_BROKER,
            settings.MQTT_USERNAME,
            settings.MQTT_PASSWORD
        )
        
        # Parser
        self.device_parser = DeviceParser()
        
        # State
        self.running = False
        self.discovery_task: Optional[asyncio.Task] = None
        self.last_discovery: Optional[datetime] = None
        self.errors: List[str] = []
        
        # Data
        self.unified_devices: Dict[str, UnifiedDevice] = {}
        self.ha_devices: List[HADevice] = []
        self.ha_entities: List[HAEntity] = []
        self.ha_areas: List[HAArea] = []
        self.zigbee_devices: Dict[str, ZigbeeDevice] = {}
        self.zigbee_groups: Dict[int, ZigbeeGroup] = {}
    
    async def start(self) -> bool:
        """Start the discovery service."""
        try:
            logger.info("🚀 Starting Device Intelligence Discovery Service")
            
            # Get HA connection using the enhanced connection manager with circuit breaker protection
            connection_config = await ha_connection_manager.get_connection_with_circuit_breaker()
            
            if not connection_config:
                logger.error("❌ No Home Assistant connections available")
                return False
            
            logger.info(f"✅ Using HA connection: {connection_config.name} ({connection_config.url})")
            
            # Initialize HA client with the connection from unified manager
            from ..clients.ha_client import HomeAssistantClient
            self.ha_client = HomeAssistantClient(
                connection_config.url, 
                None,  # No fallback needed - unified manager handles this
                connection_config.token
            )
            
            # Connect to Home Assistant
            if not await self.ha_client.connect():
                logger.error("❌ Failed to connect to Home Assistant")
                return False
            
            # Start HA message handler
            await self.ha_client.start_message_handler()
            
            # Connect to MQTT broker
            if not await self.mqtt_client.connect():
                logger.error("❌ Failed to connect to MQTT broker")
                return False
            
            # Register MQTT message handlers
            self.mqtt_client.register_message_handler("devices", self._on_zigbee_devices_update)
            self.mqtt_client.register_message_handler("groups", self._on_zigbee_groups_update)
            
            # Start discovery task
            self.running = True
            self.discovery_task = asyncio.create_task(self._discovery_loop())
            
            logger.info("✅ Discovery service started successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start discovery service: {e}")
            self.errors.append(f"Startup error: {str(e)}")
            return False
    
    async def stop(self):
        """Stop the discovery service."""
        logger.info("🛑 Stopping Discovery Service")
        
        self.running = False
        
        # Cancel discovery task
        if self.discovery_task:
            self.discovery_task.cancel()
            try:
                await self.discovery_task
            except asyncio.CancelledError:
                pass
        
        # Disconnect clients
        if self.ha_client:
            await self.ha_client.disconnect()
        await self.mqtt_client.disconnect()
        
        logger.info("✅ Discovery service stopped")
    
    async def _discovery_loop(self):
        """Main discovery loop."""
        logger.info("🔄 Starting discovery loop")
        
        # Initial discovery
        await self._perform_discovery()
        
        # Periodic discovery
        while self.running:
            try:
                await asyncio.sleep(300)  # 5 minutes
                if self.running:
                    await self._perform_discovery()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Error in discovery loop: {e}")
                self.errors.append(f"Discovery loop error: {str(e)}")
                await asyncio.sleep(60)  # Wait before retry
    
    async def _perform_discovery(self):
        """Perform full device discovery."""
        try:
            logger.info("🔍 Performing device discovery")
            
            # Discover Home Assistant data
            await self._discover_home_assistant()
            
            # Discover Zigbee2MQTT data (already handled by MQTT callbacks)
            # But we can trigger a refresh if needed
            await self._refresh_zigbee_data()
            
            # Parse and unify device data
            await self._unify_device_data()
            
            self.last_discovery = datetime.now(timezone.utc)
            logger.info(f"✅ Discovery completed: {len(self.unified_devices)} devices")
            
        except Exception as e:
            logger.error(f"❌ Error during discovery: {e}")
            self.errors.append(f"Discovery error: {str(e)}")
    
    async def _discover_home_assistant(self):
        """Discover devices, entities, and areas from Home Assistant."""
        try:
            logger.info("🏠 Discovering Home Assistant data")
            
            # Get device registry
            self.ha_devices = await self.ha_client.get_device_registry()
            
            # Get entity registry
            self.ha_entities = await self.ha_client.get_entity_registry()
            
            # Get area registry
            self.ha_areas = await self.ha_client.get_area_registry()
            
            # Update parser with areas
            self.device_parser.update_areas(self.ha_areas)
            
            logger.info(f"📱 HA Discovery: {len(self.ha_devices)} devices, {len(self.ha_entities)} entities, {len(self.ha_areas)} areas")
            
        except Exception as e:
            logger.error(f"❌ Error discovering Home Assistant data: {e}")
            raise
    
    async def _refresh_zigbee_data(self):
        """Refresh Zigbee2MQTT data by requesting bridge info."""
        try:
            # Request bridge devices (this will trigger MQTT callback)
            if self.mqtt_client.is_connected():
                # Publish request for bridge devices
                self.mqtt_client.client.publish("zigbee2mqtt/bridge/request/device/list")
                logger.debug("📡 Requested Zigbee2MQTT device list refresh")
            
        except Exception as e:
            logger.error(f"❌ Error refreshing Zigbee data: {e}")
    
    async def _unify_device_data(self):
        """Unify device data from all sources."""
        try:
            logger.info("🔄 Unifying device data from all sources")
            
            # Parse devices
            unified_devices = self.device_parser.parse_devices(
                self.ha_devices,
                self.ha_entities,
                self.zigbee_devices
            )
            
            # Update unified devices in memory
            self.unified_devices = {device.id: device for device in unified_devices}
            
            # Store devices in database
            await self._store_devices_in_database(unified_devices)
            
            logger.info(f"✅ Unified {len(self.unified_devices)} devices")
            
        except Exception as e:
            logger.error(f"❌ Error unifying device data: {e}")
            raise
    
    async def _store_devices_in_database(self, unified_devices: List[UnifiedDevice]):
        """Store unified devices in the database."""
        try:
            logger.info(f"💾 Storing {len(unified_devices)} devices in database")
            
            # Convert UnifiedDevice objects to database format
            devices_data = []
            for device in unified_devices:
                device_data = {
                    "id": device.id,
                    "name": device.name,
                    "manufacturer": device.manufacturer,
                    "model": device.model,
                    "area_id": device.area_id,
                    "integration": device.integration or "unknown",  # Provide default for NOT NULL constraint
                    "sw_version": device.sw_version,
                    "hw_version": device.hw_version,
                    "power_source": device.power_source,
                    "via_device_id": device.via_device_id,
                    "disabled_by": device.disabled_by,
                    "last_seen": device.last_seen,
                    "health_score": device.health_score,
                    "created_at": device.created_at,
                    "updated_at": device.updated_at
                }
                devices_data.append(device_data)
            
            # Store in database using DeviceService
            async for session in get_db_session():
                device_service = DeviceService(session)
                await device_service.bulk_upsert_devices(devices_data)
                break  # Only need one session
            
            logger.info(f"✅ Stored {len(devices_data)} devices in database")
            
        except Exception as e:
            logger.error(f"❌ Error storing devices in database: {e}")
            raise
    
    async def _on_zigbee_devices_update(self, data: List[Dict[str, Any]]):
        """Handle Zigbee2MQTT devices update."""
        try:
            logger.info(f"📱 Zigbee2MQTT devices updated: {len(data)} devices")
            
            # Update Zigbee devices
            for device_data in data:
                zigbee_device = ZigbeeDevice(
                    ieee_address=device_data["ieee_address"],
                    friendly_name=device_data["friendly_name"],
                    model=device_data.get("model", ""),
                    description=device_data.get("description", ""),
                    manufacturer=device_data.get("manufacturer", ""),
                    manufacturer_code=device_data.get("manufacturer_code"),
                    power_source=device_data.get("power_source"),
                    model_id=device_data.get("model_id"),
                    hardware_version=device_data.get("hardware_version"),
                    software_build_id=device_data.get("software_build_id"),
                    date_code=device_data.get("date_code"),
                    last_seen=datetime.fromisoformat(device_data["last_seen"].replace('Z', '+00:00')) if device_data.get("last_seen") else None,
                    definition=device_data.get("definition"),
                    exposes=device_data.get("definition", {}).get("exposes", []),
                    capabilities={}
                )
                
                self.zigbee_devices[zigbee_device.ieee_address] = zigbee_device
            
            # Trigger device unification
            await self._unify_device_data()
            
        except Exception as e:
            logger.error(f"❌ Error handling Zigbee devices update: {e}")
    
    async def _on_zigbee_groups_update(self, data: List[Dict[str, Any]]):
        """Handle Zigbee2MQTT groups update."""
        try:
            logger.info(f"👥 Zigbee2MQTT groups updated: {len(data)} groups")
            
            # Update Zigbee groups
            for group_data in data:
                group = ZigbeeGroup(
                    id=group_data["id"],
                    friendly_name=group_data["friendly_name"],
                    members=group_data.get("members", []),
                    scenes=group_data.get("scenes", [])
                )
                
                self.zigbee_groups[group.id] = group
            
        except Exception as e:
            logger.error(f"❌ Error handling Zigbee groups update: {e}")
    
    async def force_refresh(self) -> bool:
        """Force a complete discovery refresh."""
        try:
            logger.info("🔄 Forcing discovery refresh")
            await self._perform_discovery()
            return True
        except Exception as e:
            logger.error(f"❌ Error during forced refresh: {e}")
            return False
    
    def get_status(self) -> DiscoveryStatus:
        """Get discovery service status."""
        return DiscoveryStatus(
            service_running=self.running,
            ha_connected=self.ha_client.is_connected() if self.ha_client else False,
            mqtt_connected=self.mqtt_client.is_connected(),
            last_discovery=self.last_discovery,
            devices_count=len(self.unified_devices),
            areas_count=len(self.ha_areas),
            errors=self.errors[-10:]  # Last 10 errors
        )
    
    def get_devices(self) -> List[UnifiedDevice]:
        """Get all discovered devices."""
        return list(self.unified_devices.values())
    
    def get_device(self, device_id: str) -> Optional[UnifiedDevice]:
        """Get specific device by ID."""
        return self.unified_devices.get(device_id)
    
    def get_devices_by_area(self, area_id: str) -> List[UnifiedDevice]:
        """Get devices by area ID."""
        return [d for d in self.unified_devices.values() if d.area_id == area_id]
    
    def get_devices_by_integration(self, integration: str) -> List[UnifiedDevice]:
        """Get devices by integration type."""
        return [d for d in self.unified_devices.values() if d.integration == integration]
    
    def get_areas(self) -> List[HAArea]:
        """Get all discovered areas."""
        return self.ha_areas.copy()
    
    def get_zigbee_groups(self) -> List[ZigbeeGroup]:
        """Get all discovered Zigbee groups."""
        return list(self.zigbee_groups.values())
