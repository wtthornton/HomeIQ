"""
Device Intelligence Service - MQTT Client

MQTT client for connecting to Zigbee2MQTT bridge and discovering device capabilities.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Callable, Awaitable
from dataclasses import dataclass
from urllib.parse import urlparse

import paho.mqtt.client as mqtt

logger = logging.getLogger(__name__)


@dataclass
class ZigbeeDevice:
    """Zigbee2MQTT device representation."""
    ieee_address: str
    friendly_name: str
    model: str
    description: str
    manufacturer: str
    manufacturer_code: Optional[str]
    power_source: Optional[str]
    model_id: Optional[str]
    hardware_version: Optional[str]
    software_build_id: Optional[str]
    date_code: Optional[str]
    last_seen: Optional[datetime]
    definition: Optional[Dict[str, Any]]
    exposes: List[Dict[str, Any]]
    capabilities: Dict[str, Any]


@dataclass
class ZigbeeGroup:
    """Zigbee2MQTT group representation."""
    id: int
    friendly_name: str
    members: List[str]
    scenes: List[Dict[str, Any]]


class MQTTClient:
    """MQTT client for Zigbee2MQTT bridge integration."""
    
    def __init__(self, broker_url: str, username: Optional[str] = None, password: Optional[str] = None, base_topic: str = "zigbee2mqtt"):
        self.broker_url = broker_url
        self.username = username
        self.password = password
        self.base_topic = base_topic.rstrip('/')  # Remove trailing slash if present
        
        # Parse broker URL
        parsed = urlparse(broker_url)
        self.host = parsed.hostname or "localhost"
        self.port = parsed.port or 1883
        self.use_tls = parsed.scheme == "mqtts"
        
        # MQTT client
        self.client: Optional[mqtt.Client] = None
        self.connected = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.reconnect_delay = 5.0
        
        # Message handlers
        self.message_handlers: Dict[str, Callable[[Dict[str, Any]], Awaitable[None]]] = {}
        
        # Data storage
        self.devices: Dict[str, ZigbeeDevice] = {}
        self.groups: Dict[int, ZigbeeGroup] = {}
        self.network_map: Optional[Dict[str, Any]] = None
        
    async def connect(self) -> bool:
        """Establish MQTT connection to Zigbee2MQTT bridge."""
        try:
            logger.info(f"🔌 Connecting to MQTT broker: {self.host}:{self.port}")
            
            # Create MQTT client
            self.client = mqtt.Client()
            
            # Set authentication if provided
            if self.username and self.password:
                self.client.username_pw_set(self.username, self.password)
            
            # Set TLS if required
            if self.use_tls:
                self.client.tls_set()
            
            # Set callbacks
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            self.client.on_message = self._on_message
            self.client.on_log = self._on_log
            
            # Connect
            self.client.connect(self.host, self.port, 60)
            self.client.loop_start()
            
            # Wait for connection
            await asyncio.sleep(1)
            
            if self.connected:
                logger.info("✅ Successfully connected to MQTT broker")
                self.reconnect_attempts = 0
                return True
            else:
                logger.error("❌ Failed to connect to MQTT broker")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to connect to MQTT broker: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from MQTT broker."""
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
            self.client = None
        self.connected = False
        logger.info("🔌 Disconnected from MQTT broker")
    
    def _on_connect(self, client, userdata, flags, rc):
        """MQTT connection callback."""
        if rc == 0:
            self.connected = True
            logger.info("✅ MQTT broker connected")
            
            # Subscribe to Zigbee2MQTT topics
            self._subscribe_to_topics()
        else:
            logger.error(f"❌ MQTT broker connection failed with code {rc}")
            self.connected = False
    
    def _on_disconnect(self, client, userdata, rc):
        """MQTT disconnection callback."""
        self.connected = False
        if rc != 0:
            logger.warning(f"🔌 MQTT broker disconnected unexpectedly (code: {rc})")
            asyncio.create_task(self._handle_reconnection())
        else:
            logger.info("🔌 MQTT broker disconnected")
    
    def _on_message(self, client, userdata, msg):
        """MQTT message callback."""
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            
            # Parse JSON payload
            try:
                data = json.loads(payload)
            except json.JSONDecodeError:
                logger.warning(f"⚠️ Non-JSON message on topic {topic}")
                return
            
            # Handle message based on topic
            asyncio.create_task(self._handle_message(topic, data))
            
        except Exception as e:
            logger.error(f"❌ Error handling MQTT message: {e}")
    
    def _on_log(self, client, userdata, level, buf):
        """MQTT log callback."""
        if level == mqtt.MQTT_LOG_ERR:
            logger.error(f"MQTT Error: {buf}")
        elif level == mqtt.MQTT_LOG_WARNING:
            logger.warning(f"MQTT Warning: {buf}")
        elif level == mqtt.MQTT_LOG_INFO:
            logger.info(f"MQTT Info: {buf}")
    
    def _subscribe_to_topics(self):
        """Subscribe to Zigbee2MQTT topics."""
        topics = [
            f"{self.base_topic}/bridge/devices",  # Retained device list (published on startup)
            f"{self.base_topic}/bridge/groups",  # Retained group list
            f"{self.base_topic}/bridge/info",  # Bridge information
            f"{self.base_topic}/bridge/networkmap",  # Network map
            f"{self.base_topic}/bridge/response/device/list",  # Response to device list request
            f"{self.base_topic}/bridge/response/group/list",  # Response to group list request
        ]
        
        for topic in topics:
            self.client.subscribe(topic)
            logger.info(f"📡 Subscribed to {topic}")
    
    async def _handle_message(self, topic: str, data: Dict[str, Any]):
        """Handle incoming MQTT messages."""
        try:
            # Handle device list messages (both retained and response)
            if topic == f"{self.base_topic}/bridge/devices" or topic == f"{self.base_topic}/bridge/response/device/list":
                # Extract data from response if it's a response message
                if topic == f"{self.base_topic}/bridge/response/device/list":
                    # Response format: {"data": {...}, "status": "ok"}
                    if isinstance(data, dict) and "data" in data:
                        data = data["data"]
                    elif isinstance(data, dict) and "result" in data:
                        data = data["result"]
                    # If it's already a list, use it directly
                    if not isinstance(data, list):
                        logger.warning(f"⚠️ Unexpected device list format on {topic}: {type(data)}")
                        return
                await self._handle_devices_message(data)
            # Handle group list messages (both retained and response)
            elif topic == f"{self.base_topic}/bridge/groups" or topic == f"{self.base_topic}/bridge/response/group/list":
                # Extract data from response if it's a response message
                if topic == f"{self.base_topic}/bridge/response/group/list":
                    if isinstance(data, dict) and "data" in data:
                        data = data["data"]
                    elif isinstance(data, dict) and "result" in data:
                        data = data["result"]
                    if not isinstance(data, list):
                        logger.warning(f"⚠️ Unexpected group list format on {topic}: {type(data)}")
                        return
                await self._handle_groups_message(data)
            elif topic == f"{self.base_topic}/bridge/info":
                await self._handle_info_message(data)
            elif topic == f"{self.base_topic}/bridge/networkmap":
                await self._handle_networkmap_message(data)
            else:
                logger.debug(f"📨 Unhandled message on topic {topic}")
                
        except Exception as e:
            logger.error(f"❌ Error handling message on topic {topic}: {e}")
    
    async def _handle_devices_message(self, data: List[Dict[str, Any]]):
        """Handle devices message from Zigbee2MQTT bridge."""
        logger.info(f"📱 Received {len(data)} devices from Zigbee2MQTT bridge")
        
        # Store all devices first
        for device_data in data:
            try:
                device = ZigbeeDevice(
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
                    capabilities={}  # Will be populated by capability parser
                )
                
                self.devices[device.ieee_address] = device
                    
            except Exception as e:
                logger.error(f"❌ Error parsing device {device_data.get('ieee_address', 'unknown')}: {e}")
        
        # Call message handler with full list (after all devices are stored)
        if "devices" in self.message_handlers:
            await self.message_handlers["devices"](data)
    
    async def _handle_groups_message(self, data: List[Dict[str, Any]]):
        """Handle groups message from Zigbee2MQTT bridge."""
        logger.info(f"👥 Received {len(data)} groups from Zigbee2MQTT bridge")
        
        # Store all groups first
        for group_data in data:
            try:
                group = ZigbeeGroup(
                    id=group_data["id"],
                    friendly_name=group_data["friendly_name"],
                    members=group_data.get("members", []),
                    scenes=group_data.get("scenes", [])
                )
                
                self.groups[group.id] = group
                    
            except Exception as e:
                logger.error(f"❌ Error parsing group {group_data.get('id', 'unknown')}: {e}")
        
        # Call message handler with full list (after all groups are stored)
        if "groups" in self.message_handlers:
            await self.message_handlers["groups"](data)
    
    async def _handle_info_message(self, data: Dict[str, Any]):
        """Handle info message from Zigbee2MQTT bridge."""
        logger.info(f"ℹ️ Received Zigbee2MQTT bridge info: {data.get('version', 'unknown version')}")
        
        # Call message handler if registered
        if "info" in self.message_handlers:
            await self.message_handlers["info"](data)
    
    async def _handle_networkmap_message(self, data: Dict[str, Any]):
        """Handle network map message from Zigbee2MQTT bridge."""
        logger.info("🗺️ Received Zigbee2MQTT network map")
        
        self.network_map = data
        
        # Call message handler if registered
        if "networkmap" in self.message_handlers:
            await self.message_handlers["networkmap"](data)
    
    async def _handle_reconnection(self):
        """Handle automatic reconnection."""
        if self.reconnect_attempts >= self.max_reconnect_attempts:
            logger.error("❌ Max reconnection attempts reached")
            return
        
        self.reconnect_attempts += 1
        delay = self.reconnect_delay * self.reconnect_attempts
        
        logger.info(f"🔄 Attempting MQTT reconnection {self.reconnect_attempts}/{self.max_reconnect_attempts} in {delay}s")
        await asyncio.sleep(delay)
        
        if await self.connect():
            logger.info("✅ MQTT reconnection successful")
    
    def register_message_handler(self, topic: str, handler: Callable[[Dict[str, Any]], Awaitable[None]]):
        """Register a message handler for a specific topic."""
        self.message_handlers[topic] = handler
        logger.info(f"📡 Registered message handler for {topic}")
    
    def get_devices(self) -> Dict[str, ZigbeeDevice]:
        """Get all discovered Zigbee devices."""
        return self.devices.copy()
    
    def get_groups(self) -> Dict[int, ZigbeeGroup]:
        """Get all discovered Zigbee groups."""
        return self.groups.copy()
    
    def get_network_map(self) -> Optional[Dict[str, Any]]:
        """Get the Zigbee network map."""
        return self.network_map
    
    def is_connected(self) -> bool:
        """Check if connected to MQTT broker."""
        return self.connected and self.client is not None
