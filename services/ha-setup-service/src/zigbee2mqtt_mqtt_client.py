"""
Zigbee2MQTT MQTT Client for Health Monitoring

Subscribes to Zigbee2MQTT MQTT topics to monitor bridge status, devices, and events.
Uses MQTT subscription instead of HA API polling for real-time monitoring.

Based on 2025 Zigbee2MQTT MQTT topic structure:
- zigbee2mqtt/bridge/state - Bridge online/offline status
- zigbee2mqtt/bridge/devices - Complete device list
- zigbee2mqtt/bridge/info - Bridge information
- zigbee2mqtt/bridge/event - Bridge events (device_joined, device_leave, etc.)

Epic 31: Direct MQTT subscription pattern (following external services architecture)
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
from urllib.parse import urlparse

import paho.mqtt.client as mqtt

from .config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class Zigbee2MQTTMQTTClient:
    """
    MQTT client for monitoring Zigbee2MQTT via MQTT topics.
    
    Subscribes to bridge topics for real-time health monitoring.
    This is a generic solution that works with any Zigbee2MQTT setup.
    
    Security: READ-ONLY subscription. Never publishes to zigbee2mqtt/* topics.
    """
    
    def __init__(self):
        """Initialize MQTT client with settings."""
        # Parse broker URL
        parsed = urlparse(settings.mqtt_broker_url)
        self.host = parsed.hostname or "localhost"
        self.port = parsed.port or 1883
        self.use_tls = parsed.scheme == "mqtts"
        self.username = settings.mqtt_username
        self.password = settings.mqtt_password
        self.base_topic = settings.zigbee2mqtt_base_topic.rstrip('/')
        
        # MQTT client
        self.client: Optional[mqtt.Client] = None
        self.connected = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.reconnect_delay = 5.0
        
        # State storage
        self.bridge_state: Optional[str] = None  # "online" or "offline"
        self.bridge_info: Optional[Dict[str, Any]] = None
        self.devices: List[Dict[str, Any]] = []
        self.last_update: Optional[datetime] = None
        
        # Callbacks
        self.on_bridge_state_changed: Optional[Callable[[str], None]] = None
        self.on_devices_updated: Optional[Callable[[List[Dict[str, Any]]], None]] = None
        
    async def connect(self) -> bool:
        """
        Connect to MQTT broker and subscribe to Zigbee2MQTT topics.
        
        Returns:
            True if connection successful
        """
        try:
            logger.info(f"🔌 Connecting to MQTT broker: {self.host}:{self.port}")
            
            # Create MQTT client with unique ID
            import uuid
            client_id = f"ha-setup-service-{uuid.uuid4().hex[:8]}"
            self.client = mqtt.Client(client_id=client_id)
            
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
            
            # Subscribe to Zigbee2MQTT bridge topics
            topics = [
                f"{self.base_topic}/bridge/state",      # Bridge online/offline
                f"{self.base_topic}/bridge/devices",    # Device list (retained)
                f"{self.base_topic}/bridge/info",       # Bridge information
                f"{self.base_topic}/bridge/event",      # Bridge events
            ]
            
            for topic in topics:
                result, mid = client.subscribe(topic, qos=1)
                if result == mqtt.MQTT_ERR_SUCCESS:
                    logger.info(f"📡 Subscribed to {topic}")
                else:
                    logger.error(f"❌ Failed to subscribe to {topic}: {result}")
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
        """
        MQTT message callback.
        
        Processes messages from Zigbee2MQTT bridge topics.
        """
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            
            # Parse JSON payload
            try:
                data = json.loads(payload)
            except json.JSONDecodeError:
                # Bridge state might be a plain string
                if topic == f"{self.base_topic}/bridge/state":
                    data = payload
                else:
                    logger.warning(f"⚠️ Non-JSON message on topic {topic}")
                    return
            
            # Handle message based on topic
            asyncio.create_task(self._handle_message(topic, data))
            
        except Exception as e:
            logger.error(f"❌ Error handling MQTT message: {e}")
    
    async def _handle_message(self, topic: str, data: Any):
        """Handle incoming MQTT messages asynchronously."""
        try:
            if topic == f"{self.base_topic}/bridge/state":
                # Bridge state: "online" or "offline"
                state = str(data).lower() if isinstance(data, str) else "unknown"
                old_state = self.bridge_state
                self.bridge_state = state
                self.last_update = datetime.now()
                
                logger.info(f"📊 Zigbee2MQTT bridge state: {state}")
                
                if old_state != state and self.on_bridge_state_changed:
                    self.on_bridge_state_changed(state)
                    
            elif topic == f"{self.base_topic}/bridge/devices":
                # Device list: array of device objects
                if isinstance(data, list):
                    old_count = len(self.devices)
                    self.devices = data
                    self.last_update = datetime.now()
                    
                    logger.info(f"📱 Zigbee2MQTT devices updated: {len(data)} devices")
                    
                    if old_count != len(data) and self.on_devices_updated:
                        self.on_devices_updated(data)
                else:
                    logger.warning(f"⚠️ Unexpected device list format: {type(data)}")
                    
            elif topic == f"{self.base_topic}/bridge/info":
                # Bridge info: version, coordinator, etc.
                self.bridge_info = data if isinstance(data, dict) else {}
                self.last_update = datetime.now()
                
                version = self.bridge_info.get('version', 'unknown')
                logger.info(f"ℹ️ Zigbee2MQTT bridge info: version {version}")
                
            elif topic == f"{self.base_topic}/bridge/event":
                # Bridge events: device_joined, device_leave, etc.
                if isinstance(data, dict):
                    event_type = data.get('type', 'unknown')
                    logger.info(f"📡 Zigbee2MQTT event: {event_type}")
                    
        except Exception as e:
            logger.error(f"❌ Error processing message from {topic}: {e}")
    
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
    
    def get_bridge_status(self) -> Dict[str, Any]:
        """
        Get current bridge status from MQTT data.
        
        Returns:
            Dict with bridge status information
        """
        is_online = self.bridge_state == "online"
        device_count = len(self.devices)
        
        # Extract coordinator info from bridge_info
        coordinator_info = {}
        if self.bridge_info:
            coordinator_info = {
                "type": self.bridge_info.get("coordinator", {}).get("type", "unknown"),
                "ieee_address": self.bridge_info.get("coordinator", {}).get("ieee_address", "unknown"),
                "version": self.bridge_info.get("version", "unknown"),
            }
        
        return {
            "is_online": is_online,
            "state": self.bridge_state or "unknown",
            "device_count": device_count,
            "coordinator": coordinator_info,
            "last_update": self.last_update.isoformat() if self.last_update else None,
        }
    
    def is_connected(self) -> bool:
        """Check if connected to MQTT broker."""
        return self.connected and self.client is not None

