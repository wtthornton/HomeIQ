"""
Device Intelligence Service - Discovery Service

Main discovery service that orchestrates device discovery from multiple sources.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from ..clients.ha_client import HADevice, HAEntity, HAArea
from ..clients.mqtt_client import MQTTClient, ZigbeeDevice, ZigbeeGroup
from .device_parser import DeviceParser, UnifiedDevice
from .cache import get_device_cache
from ..services.device_service import DeviceService
from ..services.hygiene_analyzer import DeviceHygieneAnalyzer
from ..core.database import get_db_session
from ..config import Settings

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
            settings.MQTT_PASSWORD,
            settings.ZIGBEE2MQTT_BASE_TOPIC
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
            
            # Initialize HA client with configured settings
            from ..clients.ha_client import HomeAssistantClient
            self.ha_client = HomeAssistantClient(
                self.settings.HA_URL,
                None,  # No fallback URL for now
                self.settings.HA_TOKEN
            )
            
            # Connect to Home Assistant
            if not await self.ha_client.connect():
                logger.error("❌ Failed to connect to Home Assistant")
                return False
            
            # Start HA message handler
            await self.ha_client.start_message_handler()
            
            # Subscribe to registry update events for real-time cache updates
            await self._subscribe_to_registry_updates()
            
            # Connect to MQTT broker (optional - can discover HA devices without Zigbee)
            if await self.mqtt_client.connect():
                logger.info("✅ Connected to MQTT broker")
                # Register MQTT message handlers
                self.mqtt_client.register_message_handler("devices", self._on_zigbee_devices_update)
                self.mqtt_client.register_message_handler("groups", self._on_zigbee_groups_update)
            else:
                logger.warning("⚠️  MQTT broker connection failed - will continue without Zigbee devices")
            
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
            await self._run_hygiene_analysis()
            
            self.last_discovery = datetime.now(timezone.utc)
            logger.info(f"✅ Discovery completed: {len(self.unified_devices)} devices")
            
        except Exception as e:
            logger.error(f"❌ Error during discovery: {e}")
            self.errors.append(f"Discovery error: {str(e)}")
    
    async def _run_hygiene_analysis(self):
        """Analyze device hygiene and persist findings."""
        try:
            async for session in get_db_session():
                analyzer = DeviceHygieneAnalyzer(session)
                await analyzer.analyze(self.ha_devices, self.ha_entities, self.ha_areas)
                break
        except Exception as e:
            logger.error(f"❌ Error during hygiene analysis: {e}")
            self.errors.append(f"Hygiene analysis error: {str(e)}")

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
    
    async def _subscribe_to_registry_updates(self):
        """
        Subscribe to entity and device registry update events.
        
        This keeps the cache fresh by triggering discovery when entities/devices
        are added, removed, or modified in Home Assistant.
        """
        try:
            async def handle_entity_registry_update(event_data: Dict[str, Any]):
                """Handle entity registry update event."""
                action = event_data.get("event", {}).get("action", "unknown")
                entity_id = event_data.get("event", {}).get("entity_id", "unknown")
                logger.info(f"📋 Entity registry updated: {action} - {entity_id}")
                
                # Trigger incremental update for entity changes
                if action in ["create", "update", "remove"]:
                    logger.info(f"🔄 Triggering incremental discovery due to entity {action}")
                    # Perform a lightweight discovery update (just HA entities)
                    await self._discover_home_assistant()
                    await self._unify_device_data()
            
            async def handle_device_registry_update(event_data: Dict[str, Any]):
                """Handle device registry update event."""
                action = event_data.get("event", {}).get("action", "unknown")
                device_id = event_data.get("event", {}).get("device_id", "unknown")
                logger.info(f"📱 Device registry updated: {action} - {device_id}")
                
                # Trigger incremental update for device changes
                if action in ["create", "update", "remove"]:
                    logger.info(f"🔄 Triggering incremental discovery due to device {action}")
                    # Perform a lightweight discovery update (just HA devices/entities)
                    await self._discover_home_assistant()
                    await self._unify_device_data()
            
            await self.ha_client.subscribe_to_registry_updates(
                entity_callback=handle_entity_registry_update,
                device_callback=handle_device_registry_update
            )
            
            logger.info("✅ Subscribed to registry update events")
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to subscribe to registry updates: {e}")
            # Don't fail startup if subscriptions fail - we still have periodic discovery
    
    async def _refresh_zigbee_data(self):
        """Refresh Zigbee2MQTT data by requesting bridge info."""
        try:
            # Request bridge devices (this will trigger MQTT callback)
            if self.mqtt_client.is_connected():
                base_topic = self.mqtt_client.base_topic
                # Publish request for bridge devices
                request_topic = f"{base_topic}/bridge/request/device/list"
                self.mqtt_client.client.publish(request_topic, "{}")  # Empty JSON payload
                logger.debug(f"📡 Requested Zigbee2MQTT device list refresh via {request_topic}")
                
                # Also request groups
                group_request_topic = f"{base_topic}/bridge/request/group/list"
                self.mqtt_client.client.publish(group_request_topic, "{}")
                logger.debug(f"📡 Requested Zigbee2MQTT group list refresh via {group_request_topic}")
            
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
            
            # Invalidate cache for all updated devices (device-level invalidation)
            cache = get_device_cache()
            for device in unified_devices:
                await cache.delete(device.id)
            
            if unified_devices:
                logger.info(f"✅ Unified {len(self.unified_devices)} devices and invalidated cache")
            
        except Exception as e:
            logger.error(f"❌ Error unifying device data: {e}")
            raise
    
    async def _store_devices_in_database(self, unified_devices: List[UnifiedDevice]):
        """Store unified devices and their capabilities in the database."""
        try:
            logger.info(f"💾 Storing {len(unified_devices)} devices in database")
            
            # Convert UnifiedDevice objects to database format
            devices_data = []
            capabilities_data = []
            missing_integrations = []
            
            for device in unified_devices:
                integration_value = (device.integration or "").strip()
                if not integration_value:
                    missing_integrations.append(device.id)
                    integration_value = "unknown"

                device_data = {
                    "id": device.id,
                    "name": device.name,
                    "manufacturer": device.manufacturer,
                    "model": device.model,
                    "area_id": device.area_id,
                    "area_name": device.area_name,  # Include area_name
                    "integration": integration_value,
                    "device_class": device.device_class,
                    "sw_version": device.sw_version,
                    "hw_version": device.hw_version,
                    "power_source": device.power_source,
                    "via_device_id": device.via_device_id,
                    "disabled_by": device.disabled_by,
                    "last_seen": device.last_seen,
                    "health_score": device.health_score,
                    "is_battery_powered": device.power_source == "Battery" if device.power_source else False,
                    "created_at": device.created_at,
                    "updated_at": device.updated_at
                }
                
                # Add additional fields if available
                if device.ha_device:
                    if device.ha_device.config_entries:
                        device_data["config_entry_id"] = device.ha_device.config_entries[0] if device.ha_device.config_entries else None
                    if device.ha_device.connections:
                        device_data["connections_json"] = json.dumps(device.ha_device.connections)
                    if device.ha_device.identifiers:
                        device_data["identifiers_json"] = json.dumps(device.ha_device.identifiers)
                    # Add new HA device attributes
                    device_data["name_by_user"] = device.ha_device.name_by_user
                    device_data["suggested_area"] = device.ha_device.suggested_area
                    device_data["entry_type"] = device.ha_device.entry_type
                    device_data["configuration_url"] = device.ha_device.configuration_url
                
                devices_data.append(device_data)
                
                # Store capabilities for this device
                if device.capabilities:
                    for capability in device.capabilities:
                        capability_data = {
                            "device_id": device.id,
                            "capability_name": capability.get("name", ""),
                            "capability_type": capability.get("type", ""),
                            "properties": capability.get("properties", {}),
                            "exposed": capability.get("exposed", True),
                            "configured": capability.get("configured", True),
                            "source": capability.get("source", "unknown"),
                            "last_updated": datetime.now(timezone.utc)
                        }
                        capabilities_data.append(capability_data)
            
            if missing_integrations:
                logger.warning(
                    "⚠️ %d devices missing integration metadata (showing up to 5 IDs): %s",
                    len(missing_integrations),
                    missing_integrations[:5],
                )
            
            # Store in database using DeviceService
            async for session in get_db_session():
                device_service = DeviceService(session)
                await device_service.bulk_upsert_devices(devices_data)
                
                # Store capabilities if any
                if capabilities_data:
                    await device_service.bulk_upsert_capabilities(capabilities_data)
                
                break  # Only need one session
            
            logger.info(f"✅ Stored {len(devices_data)} devices and {len(capabilities_data)} capabilities in database")
            
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
