"""
Home Assistant WebSocket Client

Epic A2: WebSocket client with auth, resubscribe, heartbeat, metrics
"""

import asyncio
import json
import logging
import random
import time
from typing import Any, Callable, Dict, Optional, Set

import websockets
from websockets.client import WebSocketClientProtocol

from ..config import settings

logger = logging.getLogger(__name__)


class HAWebSocketClient:
    """
    Async WebSocket client for Home Assistant API.
    
    Features:
    - Connect + authenticate using HA WebSocket API protocol
    - Subscribe to state_changed events
    - Resubscribe on reconnect with jittered backoff
    - Heartbeat/ping mechanism
    - Metrics: disconnect count, reconnect latency
    """
    
    def __init__(
        self,
        ha_url: Optional[str] = None,
        access_token: Optional[str] = None,
        ping_interval: int = 20,
        ping_timeout: int = 10
    ):
        """
        Initialize HA WebSocket client.
        
        Args:
            ha_url: Home Assistant WebSocket URL (defaults to settings)
            access_token: Long-lived access token (defaults to settings)
            ping_interval: Ping interval in seconds
            ping_timeout: Ping timeout in seconds
        """
        self.ha_url = ha_url or settings.ha_ws_url or settings.ha_url or ""
        self.access_token = access_token or settings.ha_token or ""
        self.ping_interval = ping_interval
        self.ping_timeout = ping_timeout
        
        # Ensure WebSocket URL format
        if self.ha_url.startswith('http://'):
            self.ha_url = self.ha_url.replace('http://', 'ws://')
        elif self.ha_url.startswith('https://'):
            self.ha_url = self.ha_url.replace('https://', 'wss://')
        
        if not self.ha_url.endswith('/api/websocket'):
            if not self.ha_url.endswith('/'):
                self.ha_url += '/'
            self.ha_url += 'api/websocket'
        
        # Connection state
        self.websocket: Optional[WebSocketClientProtocol] = None
        self.connected: bool = False
        self.authenticated: bool = False
        self.message_id: int = 0
        self.subscriptions: Set[int] = set()
        self.event_handlers: Dict[int, Callable] = {}
        
        # Metrics
        self.disconnect_count: int = 0
        self.reconnect_count: int = 0
        self.last_connect_time: Optional[float] = None
        self.last_disconnect_time: Optional[float] = None
        self.reconnect_latencies: list[float] = []
        
        # Background tasks
        self._receive_task: Optional[asyncio.Task] = None
        self._ping_task: Optional[asyncio.Task] = None
        self._running: bool = False
        
        logger.info(f"HA WebSocket client initialized with url={self._redact_url(self.ha_url)}")
    
    def _redact_url(self, url: str) -> str:
        """Redact sensitive parts of URL in logs"""
        return url.replace(self.access_token, "[REDACTED]") if self.access_token else url
    
    def _next_id(self) -> int:
        """Get next message ID"""
        self.message_id += 1
        return self.message_id
    
    async def connect(self) -> bool:
        """
        Connect and authenticate to HA WebSocket.
        
        Returns:
            True if connection successful
        """
        if self.connected:
            logger.warning("Already connected")
            return True
        
        start_time = time.time()
        
        try:
            logger.info(f"Connecting to HA WebSocket: {self._redact_url(self.ha_url)}")
            
            # Connect to WebSocket
            self.websocket = await websockets.connect(
                self.ha_url,
                ping_interval=None,  # We'll handle ping manually
                ping_timeout=None,
                close_timeout=10
            )
            
            # Wait for auth_required message
            auth_response = await self.websocket.recv()
            auth_data = json.loads(auth_response)
            
            if auth_data.get("type") != "auth_required":
                logger.error(f"Unexpected auth response: {auth_data}")
                await self.websocket.close()
                return False
            
            # Send authentication
            auth_message = {
                "type": "auth",
                "access_token": self.access_token
            }
            await self.websocket.send(json.dumps(auth_message))
            
            # Wait for auth_ok
            auth_result = await self.websocket.recv()
            auth_result_data = json.loads(auth_result)
            
            if auth_result_data.get("type") != "auth_ok":
                error_msg = auth_result_data.get("message", "Unknown error")
                logger.error(f"Authentication failed: {error_msg}")
                await self.websocket.close()
                return False
            
            self.connected = True
            self.authenticated = True
            self.last_connect_time = time.time()
            
            connect_latency = time.time() - start_time
            logger.info(f"Connected and authenticated (latency: {connect_latency:.2f}s)")
            
            # Start background tasks
            self._running = True
            self._receive_task = asyncio.create_task(self._receive_loop())
            self._ping_task = asyncio.create_task(self._ping_loop())
            
            # Resubscribe to previous subscriptions
            await self._resubscribe_all()
            
            return True
            
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            self.connected = False
            self.authenticated = False
            return False
    
    async def disconnect(self):
        """Disconnect from HA WebSocket"""
        self._running = False
        
        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass
        
        if self._ping_task:
            self._ping_task.cancel()
            try:
                await self._ping_task
            except asyncio.CancelledError:
                pass
        
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
        
        self.connected = False
        self.authenticated = False
        self.last_disconnect_time = time.time()
        self.disconnect_count += 1
        
        logger.info("Disconnected from HA WebSocket")
    
    async def reconnect(self) -> bool:
        """
        Reconnect with jittered backoff.
        
        Returns:
            True if reconnection successful
        """
        self.reconnect_count += 1
        reconnect_delay = settings.ws_reconnect_delay
        
        for attempt in range(settings.ws_max_reconnect_attempts):
            # Jittered backoff
            jitter = random.uniform(0, reconnect_delay * 0.3)
            delay = reconnect_delay + jitter
            
            logger.info(f"Reconnect attempt {attempt + 1}/{settings.ws_max_reconnect_attempts} in {delay:.2f}s")
            await asyncio.sleep(delay)
            
            start_time = time.time()
            if await self.connect():
                latency = time.time() - start_time
                self.reconnect_latencies.append(latency)
                logger.info(f"Reconnected successfully (latency: {latency:.2f}s)")
                return True
            
            # Exponential backoff
            reconnect_delay *= 2
        
        logger.error("Failed to reconnect after all attempts")
        return False
    
    async def subscribe_events(
        self,
        event_type: Optional[str] = None,
        handler: Optional[Callable] = None
    ) -> int:
        """
        Subscribe to HA events.
        
        Args:
            event_type: Event type to subscribe to (None for all events)
            handler: Callback function for events
        
        Returns:
            Subscription ID
        """
        if not self.connected or not self.authenticated:
            raise RuntimeError("Not connected or authenticated")
        
        sub_id = self._next_id()
        message = {
            "id": sub_id,
            "type": "subscribe_events",
        }
        
        if event_type:
            message["event_type"] = event_type
        
        await self.websocket.send(json.dumps(message))
        self.subscriptions.add(sub_id)
        
        if handler:
            self.event_handlers[sub_id] = handler
        
        logger.info(f"Subscribed to events (type={event_type}, id={sub_id})")
        return sub_id
    
    async def _resubscribe_all(self):
        """Resubscribe to all previous subscriptions"""
        # Re-subscribe to state_changed events (most common)
        await self.subscribe_events("state_changed")
        logger.info("Resubscribed to all events")
    
    async def _receive_loop(self):
        """Background task to receive WebSocket messages"""
        try:
            while self._running and self.websocket:
                try:
                    message = await asyncio.wait_for(
                        self.websocket.recv(),
                        timeout=1.0
                    )
                    await self._handle_message(message)
                except asyncio.TimeoutError:
                    continue
                except websockets.exceptions.ConnectionClosed:
                    logger.warning("WebSocket connection closed")
                    self.connected = False
                    self.authenticated = False
                    break
                except Exception as e:
                    logger.error(f"Error receiving message: {e}")
        except asyncio.CancelledError:
            logger.info("Receive loop cancelled")
        except Exception as e:
            logger.error(f"Receive loop error: {e}")
    
    async def _handle_message(self, message: str):
        """Handle incoming WebSocket message"""
        try:
            data = json.loads(message)
            msg_type = data.get("type")
            
            if msg_type == "event":
                # Handle event
                sub_id = data.get("id")
                event = data.get("event", {})
                
                if sub_id in self.event_handlers:
                    handler = self.event_handlers[sub_id]
                    try:
                        await handler(event)
                    except Exception as e:
                        logger.error(f"Error in event handler: {e}")
                else:
                    logger.debug(f"Unhandled event: {event}")
            
            elif msg_type == "result":
                # Handle result message
                logger.debug(f"Result message: {data}")
            
            elif msg_type == "pong":
                # Handle pong
                logger.debug("Received pong")
            
            else:
                logger.debug(f"Unknown message type: {msg_type}")
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse message: {e}")
        except Exception as e:
            logger.error(f"Error handling message: {e}")
    
    async def _ping_loop(self):
        """Background task to send periodic pings"""
        try:
            while self._running and self.websocket:
                await asyncio.sleep(self.ping_interval)
                
                if self.connected and self.websocket:
                    try:
                        # Send ping via HA ping message
                        ping_id = self._next_id()
                        ping_message = {
                            "id": ping_id,
                            "type": "ping"
                        }
                        await self.websocket.send(json.dumps(ping_message))
                        logger.debug("Sent ping")
                    except Exception as e:
                        logger.error(f"Error sending ping: {e}")
                        self.connected = False
        except asyncio.CancelledError:
            logger.info("Ping loop cancelled")
        except Exception as e:
            logger.error(f"Ping loop error: {e}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get WebSocket connection metrics"""
        avg_reconnect_latency = (
            sum(self.reconnect_latencies) / len(self.reconnect_latencies)
            if self.reconnect_latencies else 0.0
        )
        
        return {
            "connected": self.connected,
            "authenticated": self.authenticated,
            "disconnect_count": self.disconnect_count,
            "reconnect_count": self.reconnect_count,
            "subscriptions": len(self.subscriptions),
            "last_connect_time": self.last_connect_time,
            "last_disconnect_time": self.last_disconnect_time,
            "avg_reconnect_latency": avg_reconnect_latency,
            "reconnect_latencies": self.reconnect_latencies[-10:],  # Last 10
        }
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.disconnect()
