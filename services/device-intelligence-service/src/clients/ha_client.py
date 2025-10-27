"""
Device Intelligence Service - Home Assistant WebSocket Client

WebSocket client for connecting to Home Assistant and discovering devices, entities, and areas.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Callable, Awaitable
from dataclasses import dataclass

import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException

logger = logging.getLogger(__name__)


@dataclass
class HADevice:
    """Home Assistant device representation."""
    id: str
    name: str
    manufacturer: Optional[str]
    model: Optional[str]
    area_id: Optional[str]
    integration: str
    config_entries: List[str]
    identifiers: List[List[str]]
    connections: List[List[str]]
    sw_version: Optional[str]
    hw_version: Optional[str]
    via_device_id: Optional[str]
    disabled_by: Optional[str]
    created_at: datetime
    updated_at: datetime


@dataclass
class HAEntity:
    """Home Assistant entity representation."""
    entity_id: str
    name: Optional[str]
    original_name: Optional[str]
    device_id: Optional[str]
    area_id: Optional[str]
    platform: str
    domain: str
    disabled_by: Optional[str]
    entity_category: Optional[str]
    hidden_by: Optional[str]
    has_entity_name: bool
    original_icon: Optional[str]
    unique_id: str
    translation_key: Optional[str]
    created_at: datetime
    updated_at: datetime


@dataclass
class HAArea:
    """Home Assistant area representation."""
    area_id: str
    name: str
    normalized_name: str
    aliases: List[str]
    created_at: datetime
    updated_at: datetime


class HomeAssistantClient:
    """WebSocket client for Home Assistant integration."""
    
    def __init__(self, primary_url: str, fallback_url: Optional[str], token: str):
        self.primary_url = primary_url.rstrip('/')
        self.fallback_url = fallback_url.rstrip('/') if fallback_url else None
        self.token = token
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.connected = False
        self.message_id = 0
        self.pending_messages: Dict[int, asyncio.Future] = {}
        self.subscriptions: Dict[str, Callable] = {}
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.reconnect_delay = 5.0
        self.current_url = None  # Track which URL is currently being used
        
    async def connect(self) -> bool:
        """Establish WebSocket connection to Home Assistant with automatic fallback."""
        # Try primary URL first, then fallback URL
        urls_to_try = [self.primary_url]
        if self.fallback_url:
            urls_to_try.append(self.fallback_url)
        
        for url in urls_to_try:
            try:
                # Use the URL as-is if it's already a WebSocket URL, otherwise convert
                if url.startswith('ws://') or url.startswith('wss://'):
                    ws_url = url
                else:
                    ws_url = url.replace('http://', 'ws://').replace('https://', 'wss://')
                    ws_url = f"{ws_url}/api/websocket"
                
                logger.info(f"🔌 Connecting to Home Assistant WebSocket: {ws_url}")
                
                # Connect with authentication header
                headers = {"Authorization": f"Bearer {self.token}"}
                
                self.websocket = await websockets.connect(
                    ws_url,
                    extra_headers=headers,
                    ping_interval=20,
                    ping_timeout=10,
                    close_timeout=10
                )
                
                self.current_url = url
                logger.info(f"✅ Successfully connected to Home Assistant at {url}")
                
                # Handle authentication response
                auth_response = await self.websocket.recv()
                auth_data = json.loads(auth_response)
                
                if auth_data.get("type") == "auth_required":
                    logger.info("🔐 Authentication required, sending token...")
                    await self.websocket.send(json.dumps({"type": "auth", "access_token": self.token}))
                    
                    auth_result = await self.websocket.recv()
                    auth_result_data = json.loads(auth_result)
                    
                    if auth_result_data.get("type") == "auth_ok":
                        logger.info("✅ Successfully authenticated with Home Assistant")
                        self.connected = True
                        self.reconnect_attempts = 0
                        return True
                    else:
                        logger.error(f"❌ Authentication failed: {auth_result_data}")
                        return False
                elif auth_data.get("type") == "auth_ok":
                    logger.info("✅ Already authenticated with Home Assistant")
                    self.connected = True
                    self.reconnect_attempts = 0
                    return True
                else:
                    logger.error(f"❌ Unexpected authentication response: {auth_data}")
                    return False
                
                break
                
            except Exception as e:
                logger.warning(f"❌ Failed to connect to {url}: {e}")
                if url == urls_to_try[-1]:  # Last URL failed
                    logger.error(f"❌ Failed to connect to any Home Assistant URL")
                    return False
                continue
    
    async def disconnect(self):
        """Disconnect from Home Assistant."""
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
        self.connected = False
        logger.info("🔌 Disconnected from Home Assistant")
    
    async def send_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Send a message and wait for response."""
        if not self.connected or not self.websocket:
            raise ConnectionError("Not connected to Home Assistant")
        
        # Add message ID for tracking
        self.message_id += 1
        message["id"] = self.message_id
        
        # Create future for response
        future = asyncio.Future()
        self.pending_messages[self.message_id] = future
        
        try:
            # Send message
            await self.websocket.send(json.dumps(message))
            
            # Wait for response with timeout
            response = await asyncio.wait_for(future, timeout=30.0)
            return response
            
        except asyncio.TimeoutError:
            logger.error(f"⏰ Timeout waiting for response to message {self.message_id}")
            raise
        except Exception as e:
            logger.error(f"❌ Error sending message: {e}")
            raise
        finally:
            # Clean up pending message
            self.pending_messages.pop(self.message_id, None)
    
    async def _handle_messages(self):
        """Handle incoming WebSocket messages."""
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    
                    # Handle responses to our messages
                    if "id" in data and data["id"] in self.pending_messages:
                        future = self.pending_messages[data["id"]]
                        if not future.done():
                            future.set_result(data)
                        continue
                    
                    # Handle subscription messages
                    if "type" in data:
                        await self._handle_subscription_message(data)
                        
                except json.JSONDecodeError as e:
                    logger.error(f"❌ Failed to parse WebSocket message: {e}")
                except Exception as e:
                    logger.error(f"❌ Error handling WebSocket message: {e}")
                    
        except ConnectionClosed:
            logger.warning("🔌 WebSocket connection closed")
            self.connected = False
            await self._handle_reconnection()
        except Exception as e:
            logger.error(f"❌ WebSocket error: {e}")
            self.connected = False
    
    async def _handle_subscription_message(self, data: Dict[str, Any]):
        """Handle subscription messages."""
        message_type = data.get("type")
        
        if message_type == "event":
            event_type = data.get("event", {}).get("event_type")
            if event_type in self.subscriptions:
                try:
                    await self.subscriptions[event_type](data)
                except Exception as e:
                    logger.error(f"❌ Error in subscription handler for {event_type}: {e}")
    
    async def _handle_reconnection(self):
        """Handle automatic reconnection."""
        if self.reconnect_attempts >= self.max_reconnect_attempts:
            logger.error("❌ Max reconnection attempts reached")
            return
        
        self.reconnect_attempts += 1
        delay = self.reconnect_delay * self.reconnect_attempts
        
        logger.info(f"🔄 Attempting reconnection {self.reconnect_attempts}/{self.max_reconnect_attempts} in {delay}s")
        await asyncio.sleep(delay)
        
        if await self.connect():
            # Restart message handling
            asyncio.create_task(self._handle_messages())
    
    def _parse_timestamp(self, timestamp) -> datetime:
        """Parse timestamp from Home Assistant (handles both float and string formats)."""
        if timestamp is None:
            return datetime.now(timezone.utc)
        
        try:
            # Handle float timestamps (Unix timestamp)
            if isinstance(timestamp, (int, float)):
                return datetime.fromtimestamp(timestamp, tz=timezone.utc)
            
            # Handle string timestamps (ISO format)
            if isinstance(timestamp, str):
                # Remove 'Z' suffix and add timezone info
                if timestamp.endswith('Z'):
                    timestamp = timestamp[:-1] + '+00:00'
                return datetime.fromisoformat(timestamp)
            
            # Fallback to current time
            return datetime.now(timezone.utc)
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to parse timestamp {timestamp}: {e}")
            return datetime.now(timezone.utc)
    
    async def get_device_registry(self) -> List[HADevice]:
        """Get all devices from Home Assistant device registry."""
        try:
            response = await self.send_message({
                "type": "config/device_registry/list"
            })
            
            devices = []
            for device_data in response.get("result", []):
                # Debug logging to verify what HA actually returns
                logger.debug(f"Device {device_data.get('name')}: manufacturer={device_data.get('manufacturer')}, integration={device_data.get('integration')}")
                
                device = HADevice(
                    id=device_data["id"],
                    name=device_data["name"],
                    manufacturer=device_data.get("manufacturer"),
                    model=device_data.get("model"),
                    area_id=device_data.get("area_id"),
                    integration=device_data.get("integration"),
                    config_entries=device_data.get("config_entries", []),
                    identifiers=device_data.get("identifiers", []),
                    connections=device_data.get("connections", []),
                    sw_version=device_data.get("sw_version"),
                    hw_version=device_data.get("hw_version"),
                    via_device_id=device_data.get("via_device_id"),
                    disabled_by=device_data.get("disabled_by"),
                    created_at=self._parse_timestamp(device_data.get("created_at")),
                    updated_at=self._parse_timestamp(device_data.get("updated_at"))
                )
                devices.append(device)
            
            logger.info(f"📱 Discovered {len(devices)} devices from Home Assistant")
            return devices
            
        except Exception as e:
            logger.error(f"❌ Failed to get device registry: {e}")
            return []
    
    async def get_entity_registry(self) -> List[HAEntity]:
        """Get all entities from Home Assistant entity registry."""
        try:
            response = await self.send_message({
                "type": "config/entity_registry/list"
            })
            
            entities = []
            for entity_data in response.get("result", []):
                entity = HAEntity(
                    entity_id=entity_data["entity_id"],
                    name=entity_data.get("name"),
                    original_name=entity_data.get("original_name"),
                    device_id=entity_data.get("device_id"),
                    area_id=entity_data.get("area_id"),
                    platform=entity_data.get("platform", "unknown"),
                    domain=entity_data.get("domain", "unknown"),
                    disabled_by=entity_data.get("disabled_by"),
                    entity_category=entity_data.get("entity_category"),
                    hidden_by=entity_data.get("hidden_by"),
                    has_entity_name=entity_data.get("has_entity_name", False),
                    original_icon=entity_data.get("original_icon"),
                    unique_id=entity_data["unique_id"],
                    translation_key=entity_data.get("translation_key"),
                    created_at=self._parse_timestamp(entity_data.get("created_at")),
                    updated_at=self._parse_timestamp(entity_data.get("updated_at"))
                )
                entities.append(entity)
            
            logger.info(f"🔧 Discovered {len(entities)} entities from Home Assistant")
            return entities
            
        except Exception as e:
            logger.error(f"❌ Failed to get entity registry: {e}")
            return []
    
    async def get_area_registry(self) -> List[HAArea]:
        """Get all areas from Home Assistant area registry."""
        try:
            response = await self.send_message({
                "type": "config/area_registry/list"
            })
            
            areas = []
            for area_data in response.get("result", []):
                area = HAArea(
                    area_id=area_data["area_id"],
                    name=area_data["name"],
                    normalized_name=area_data.get("normalized_name", area_data["name"].lower().replace(" ", "_")),
                    aliases=area_data.get("aliases", []),
                    created_at=self._parse_timestamp(area_data.get("created_at")),
                    updated_at=self._parse_timestamp(area_data.get("updated_at"))
                )
                areas.append(area)
            
            logger.info(f"🏠 Discovered {len(areas)} areas from Home Assistant")
            return areas
            
        except Exception as e:
            logger.error(f"❌ Failed to get area registry: {e}")
            return []
    
    async def subscribe_to_events(self, event_type: str, callback: Callable[[Dict[str, Any]], Awaitable[None]]):
        """Subscribe to Home Assistant events."""
        try:
            self.subscriptions[event_type] = callback
            
            await self.send_message({
                "type": "subscribe_events",
                "event_type": event_type
            })
            
            logger.info(f"📡 Subscribed to {event_type} events")
            
        except Exception as e:
            logger.error(f"❌ Failed to subscribe to {event_type} events: {e}")
    
    async def start_message_handler(self):
        """Start the message handler task."""
        if self.connected and self.websocket:
            asyncio.create_task(self._handle_messages())
    
    def is_connected(self) -> bool:
        """Check if connected to Home Assistant."""
        return self.connected and self.websocket is not None
