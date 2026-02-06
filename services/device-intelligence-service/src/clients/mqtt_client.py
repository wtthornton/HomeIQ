"""
Device Intelligence Service - MQTT Client

MQTT client for connecting to Zigbee2MQTT bridge and discovering device capabilities.
"""

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any
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
    manufacturer_code: str | None
    power_source: str | None
    model_id: str | None
    hardware_version: str | None
    software_build_id: str | None
    date_code: str | None
    last_seen: datetime | None
    definition: dict[str, Any] | None
    exposes: list[dict[str, Any]]
    capabilities: dict[str, Any]
    # Zigbee2MQTT-specific fields
    lqi: int | None = None  # Link Quality Indicator (0-255)
    availability: str | None = None  # "enabled", "disabled", "unavailable"
    battery: int | None = None  # Battery level 0-100
    battery_low: bool | None = None  # Battery low warning
    device_type: str | None = None  # Device type from Zigbee2MQTT
    network_address: int | None = None  # Zigbee network address
    supported: bool | None = None  # Is device supported by Zigbee2MQTT
    interview_completed: bool | None = None  # Has interview completed
    settings: dict[str, Any] | None = None  # Device settings


@dataclass
class ZigbeeGroup:
    """Zigbee2MQTT group representation."""
    id: int
    friendly_name: str
    members: list[str]
    scenes: list[dict[str, Any]]


class MQTTClient:
    """MQTT client for Zigbee2MQTT bridge integration."""

    def __init__(
        self,
        broker_url: str,
        username: str | None = None,
        password: str | None = None,
        base_topic: str = "zigbee2mqtt",
        subscribe_discovery_configs: bool = False,
        subscribe_device_states: bool = False
    ):
        self.broker_url = broker_url
        self.username = username
        self.password = password
        self.base_topic = base_topic.rstrip('/')  # Remove trailing slash if present

        # Optional feature flags
        self.subscribe_discovery_configs = subscribe_discovery_configs
        self.subscribe_device_states = subscribe_device_states

        # Parse broker URL
        parsed = urlparse(broker_url)
        self.host = parsed.hostname or "localhost"
        self.port = parsed.port or 1883
        self.use_tls = parsed.scheme == "mqtts"

        # MQTT client
        self.client: mqtt.Client | None = None
        self.connected = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.reconnect_delay = 5.0

        # Event loop for async callbacks from MQTT thread
        self.event_loop: asyncio.AbstractEventLoop | None = None

        # Message handlers
        self.message_handlers: dict[str, Callable[[dict[str, Any]], Awaitable[None]]] = {}

        # Data storage
        self.devices: dict[str, ZigbeeDevice] = {}
        self.groups: dict[int, ZigbeeGroup] = {}
        self.network_map: dict[str, Any] | None = None

    async def connect(self) -> bool:
        """Establish MQTT connection to Zigbee2MQTT bridge."""
        try:
            logger.info(f"Connecting to MQTT broker: {self.host}:{self.port}")

            # Store event loop for use in MQTT callbacks (which run in different thread)
            self.event_loop = asyncio.get_running_loop()

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
                logger.info("Successfully connected to MQTT broker")
                self.reconnect_attempts = 0
                return True
            else:
                logger.error("Failed to connect to MQTT broker")
                return False

        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")
            return False

    async def disconnect(self):
        """Disconnect from MQTT broker."""
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
            self.client = None
        self.connected = False
        logger.info("Disconnected from MQTT broker")

    def _on_connect(self, client, userdata, flags, rc):
        """MQTT connection callback."""
        if rc == 0:
            self.connected = True
            logger.info("MQTT broker connected")

            # Subscribe to Zigbee2MQTT topics
            self._subscribe_to_topics()
        else:
            logger.error(f"MQTT broker connection failed with code {rc}")
            self.connected = False

    def _on_disconnect(self, client, userdata, rc):
        """MQTT disconnection callback."""
        self.connected = False
        if rc != 0:
            logger.warning("MQTT broker disconnected unexpectedly (code: %d)", rc)
            # Use run_coroutine_threadsafe since this callback runs in MQTT thread (HIGH-2)
            if self.event_loop and self.event_loop.is_running():
                asyncio.run_coroutine_threadsafe(self._handle_reconnection(), self.event_loop)
            else:
                logger.error("Cannot schedule reconnection: event loop not available")
        else:
            logger.info("MQTT broker disconnected")

    def _on_message(self, client, userdata, msg):
        """MQTT message callback."""
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            
            # Enhanced logging: Log ALL received MQTT messages for debugging
            payload_preview = payload[:200] if len(payload) > 200 else payload
            logger.debug(f"MQTT message received: topic={topic}, payload_size={len(payload)} bytes, preview={payload_preview}...")

            # Parse JSON payload
            try:
                data = json.loads(payload)
            except json.JSONDecodeError:
                logger.warning(f"Non-JSON message on topic {topic}: {payload[:100]}")
                return

            # Handle message based on topic
            # Use run_coroutine_threadsafe since this callback runs in MQTT client thread
            if self.event_loop and self.event_loop.is_running():
                asyncio.run_coroutine_threadsafe(self._handle_message(topic, data), self.event_loop)
            else:
                logger.error(f"Cannot handle MQTT message: event loop not available for topic {topic}")

        except Exception as e:
            logger.error(f"Error handling MQTT message: {e}")

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

        # Optional: Subscribe to Home Assistant discovery config topics
        if self.subscribe_discovery_configs:
            topics.append("homeassistant/+/+/+/config")
            logger.info("Discovery config subscription enabled")

        # Optional: Subscribe to Zigbee2MQTT device state topics
        if self.subscribe_device_states:
            topics.append(f"{self.base_topic}/+")
            logger.info("Device state subscription enabled (high volume)")

        for topic in topics:
            self.client.subscribe(topic)
            logger.info(f"Subscribed to {topic}")

    async def _handle_message(self, topic: str, data: dict[str, Any]):
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
                        logger.warning(f"Unexpected device list format on {topic}: {type(data)}")
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
                        logger.warning(f"Unexpected group list format on {topic}: {type(data)}")
                        return
                await self._handle_groups_message(data)
            elif topic == f"{self.base_topic}/bridge/info":
                await self._handle_info_message(data)
            elif topic == f"{self.base_topic}/bridge/networkmap":
                await self._handle_networkmap_message(data)
            elif topic.startswith("homeassistant/") and topic.endswith("/config"):
                # Home Assistant discovery config message
                await self._handle_discovery_config(topic, data)
            elif (
                self.subscribe_device_states
                and topic.startswith(f"{self.base_topic}/")
                and not topic.startswith(f"{self.base_topic}/bridge/")
            ):
                # Zigbee2MQTT device state message (not bridge messages)
                await self._handle_device_state(topic, data)
            else:
                logger.debug(f"Unhandled message on topic {topic}")

        except Exception as e:
            logger.error(f"Error handling message on topic {topic}: {e}")

    async def _handle_devices_message(self, data: list[dict[str, Any]]):
        """Handle devices message from Zigbee2MQTT bridge."""
        logger.info(f"Received {len(data)} devices from Zigbee2MQTT bridge")

        # Store all devices first
        for device_data in data:
            try:
                # Parse last_seen with timezone handling
                last_seen = None
                if device_data.get("last_seen"):
                    try:
                        last_seen_str = device_data["last_seen"].replace('Z', '+00:00')
                        last_seen = datetime.fromisoformat(last_seen_str)
                    except Exception as e:
                        logger.debug(f"Could not parse last_seen for {device_data.get('ieee_address')}: {e}")
                
                # Extract Zigbee2MQTT-specific fields
                definition = device_data.get("definition", {})
                
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
                    last_seen=last_seen,
                    definition=definition,
                    exposes=definition.get("exposes", []),
                    capabilities={},  # Will be populated by capability parser
                    # Zigbee2MQTT-specific fields
                    lqi=device_data.get("lqi"),
                    availability=device_data.get("availability"),  # "enabled", "disabled", "unavailable"
                    battery=device_data.get("battery"),
                    battery_low=device_data.get("battery_low"),
                    device_type=device_data.get("type"),
                    network_address=device_data.get("network_address"),
                    supported=device_data.get("supported"),
                    interview_completed=device_data.get("interview_completed"),
                    settings=device_data.get("settings")
                )

                self.devices[device.ieee_address] = device

            except Exception as e:
                logger.error(f"Error parsing device {device_data.get('ieee_address', 'unknown')}: {e}")

        # Call message handler with full list (after all devices are stored)
        if "devices" in self.message_handlers:
            await self.message_handlers["devices"](data)

    async def _handle_groups_message(self, data: list[dict[str, Any]]):
        """Handle groups message from Zigbee2MQTT bridge."""
        logger.info(f"Received {len(data)} groups from Zigbee2MQTT bridge")

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
                logger.error(f"Error parsing group {group_data.get('id', 'unknown')}: {e}")

        # Call message handler with full list (after all groups are stored)
        if "groups" in self.message_handlers:
            await self.message_handlers["groups"](data)

    async def _handle_info_message(self, data: dict[str, Any]):
        """Handle info message from Zigbee2MQTT bridge."""
        logger.info(f"Received Zigbee2MQTT bridge info: {data.get('version', 'unknown version')}")

        # Call message handler if registered
        if "info" in self.message_handlers:
            await self.message_handlers["info"](data)

    async def _handle_networkmap_message(self, data: dict[str, Any]):
        """Handle network map message from Zigbee2MQTT bridge."""
        logger.info("Received Zigbee2MQTT network map")

        self.network_map = data

        # Call message handler if registered
        if "networkmap" in self.message_handlers:
            await self.message_handlers["networkmap"](data)

    async def _handle_discovery_config(self, topic: str, data: dict[str, Any]):
        """Handle Home Assistant discovery config message."""
        # Parse topic: homeassistant/<component>/<device_id>/<object_id>/config
        topic_parts = topic.split("/")
        if len(topic_parts) >= 5:
            component = topic_parts[1]
            device_id = topic_parts[2]
            object_id = topic_parts[3] if len(topic_parts) > 3 else None
            
            logger.debug(f"Received HA discovery config: {component}/{device_id}/{object_id}")
            
            # Call message handler if registered
            if "discovery_config" in self.message_handlers:
                await self.message_handlers["discovery_config"]({
                    "topic": topic,
                    "component": component,
                    "device_id": device_id,
                    "object_id": object_id,
                    "config": data
                })
        else:
            logger.debug(f"Received HA discovery config: {topic}")

    async def _handle_device_state(self, topic: str, data: dict[str, Any]):
        """Handle Zigbee2MQTT device state message."""
        # Extract device friendly_name from topic: zigbee2mqtt/<friendly_name>
        friendly_name = topic.replace(f"{self.base_topic}/", "")
        
        logger.debug(f"Received Zigbee2MQTT device state: {friendly_name}")
        
        # Call message handler if registered
        if "device_state" in self.message_handlers:
            await self.message_handlers["device_state"]({
                "topic": topic,
                "friendly_name": friendly_name,
                "state": data
            })

    async def _handle_reconnection(self):
        """Handle automatic reconnection."""
        if self.reconnect_attempts >= self.max_reconnect_attempts:
            logger.error("Max reconnection attempts reached")
            return

        self.reconnect_attempts += 1
        delay = self.reconnect_delay * self.reconnect_attempts

        logger.info(f"Attempting MQTT reconnection {self.reconnect_attempts}/{self.max_reconnect_attempts} in {delay}s")
        await asyncio.sleep(delay)

        if await self.connect():
            logger.info("MQTT reconnection successful")

    def register_message_handler(self, topic: str, handler: Callable[[dict[str, Any]], Awaitable[None]]):
        """Register a message handler for a specific topic."""
        self.message_handlers[topic] = handler
        logger.info(f"Registered message handler for {topic}")

    def get_devices(self) -> dict[str, ZigbeeDevice]:
        """Get all discovered Zigbee devices."""
        return self.devices.copy()

    def get_groups(self) -> dict[int, ZigbeeGroup]:
        """Get all discovered Zigbee groups."""
        return self.groups.copy()

    def get_network_map(self) -> dict[str, Any] | None:
        """Get the Zigbee network map."""
        return self.network_map

    def is_connected(self) -> bool:
        """Check if connected to MQTT broker."""
        return self.connected and self.client is not None
