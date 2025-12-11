#!/usr/bin/env python3
"""
Enhanced Home Assistant WebSocket Service with Fallback
Using BMAD Context7 KB patterns for optimal implementation
"""

import asyncio
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

import aiohttp
from aiohttp import ClientTimeout, ClientWebSocketResponse, web

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ConnectionState(Enum):
    """Connection state enumeration"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    AUTHENTICATING = "authenticating"
    CONNECTED = "connected"
    FAILED = "failed"
    RECONNECTING = "reconnecting"

@dataclass
class ConnectionConfig:
    """Connection configuration with Context7 KB patterns"""
    name: str
    url: str
    token: str
    priority: int = 1
    timeout: int = 30
    heartbeat: float = 20.0
    max_retries: int = 3
    retry_delay: float = 5.0

    @property
    def ws_url(self) -> str:
        """Convert HTTP URL to WebSocket URL"""
        return self.url.replace("http://", "ws://").replace("https://", "wss://") + "/api/websocket"

@dataclass
class ConnectionStats:
    """Connection statistics tracking"""
    connection_attempts: int = 0
    successful_connections: int = 0
    failed_connections: int = 0
    last_connection: datetime | None = None
    last_success: datetime | None = None
    total_uptime: timedelta = timedelta(0)
    current_uptime: datetime | None = None

class EnhancedHAWebSocketService:
    """
    Enhanced Home Assistant WebSocket service with fallback
    Using Context7 KB patterns for optimal performance
    """

    def __init__(self):
        # Connection configurations
        self.connections: list[ConnectionConfig] = []
        self.connection_stats: dict[str, ConnectionStats] = {}
        self.current_connection: ConnectionConfig | None = None

        # Connection state
        self.state = ConnectionState.DISCONNECTED
        self.ws: ClientWebSocketResponse | None = None
        self.session: aiohttp.ClientSession | None = None
        self.running = False

        # Event processing
        self.event_count = 0
        self.start_time = None
        self.is_authenticated = False

        # Service configuration
        self.weather_service_url = os.getenv("WEATHER_SERVICE_URL", "http://weather-api:8001")
        self.enrichment_service_url = os.getenv("ENRICHMENT_SERVICE_URL", "http://enrichment-pipeline:8002")
        self.weather_enrichment_enabled = os.getenv("ENABLE_WEATHER_API", "true").lower() == "true"

        # Load configurations
        self._load_connection_configs()

        # Statistics
        self.fallback_attempts = 0
        self.successful_fallbacks = 0
        self.weather_enrichments = 0

    def _load_connection_configs(self):
        """Load connection configurations using Context7 KB patterns"""

        # Primary connection (HA Simulator)
        primary_url = os.getenv("HOME_ASSISTANT_URL", "http://ha-simulator:8123")
        primary_token = os.getenv("HOME_ASSISTANT_TOKEN", "dev_simulator_token")

        if primary_url and primary_token:
            config = ConnectionConfig(
                name="Primary (HA Simulator)",
                url=primary_url,
                token=primary_token,
                priority=1,
                timeout=30,
                heartbeat=20.0,
                max_retries=3,
                retry_delay=5.0
            )
            self.connections.append(config)
            self.connection_stats[config.name] = ConnectionStats()

        # Nabu Casa fallback
        nabu_casa_url = os.getenv("NABU_CASA_URL", "https://lwzisze94hrpqde9typkwgu5pptxdkoh.ui.nabu.casa")
        nabu_casa_token = os.getenv("NABU_CASA_TOKEN")

        if nabu_casa_url and nabu_casa_token:
            config = ConnectionConfig(
                name="Nabu Casa Fallback",
                url=nabu_casa_url,
                token=nabu_casa_token,
                priority=2,
                timeout=45,  # Longer timeout for cloud connection
                heartbeat=30.0,  # Longer heartbeat for cloud
                max_retries=5,
                retry_delay=10.0
            )
            self.connections.append(config)
            self.connection_stats[config.name] = ConnectionStats()

        # Local Home Assistant fallback
        local_ha_url = os.getenv("LOCAL_HA_URL")
        local_ha_token = os.getenv("LOCAL_HA_TOKEN")

        if local_ha_url and local_ha_token:
            config = ConnectionConfig(
                name="Local Home Assistant",
                url=local_ha_url,
                token=local_ha_token,
                priority=3,
                timeout=30,
                heartbeat=20.0,
                max_retries=3,
                retry_delay=5.0
            )
            self.connections.append(config)
            self.connection_stats[config.name] = ConnectionStats()

        # Sort by priority
        self.connections.sort(key=lambda x: x.priority)

        logger.info(f"📋 Loaded {len(self.connections)} Home Assistant connection(s):")
        for conn in self.connections:
            logger.info(f"  - {conn.name}: {conn.url} (Priority: {conn.priority})")

    def _get_next_connection(self) -> ConnectionConfig | None:
        """Get the next available connection using Context7 KB patterns"""
        # Filter connections by availability and sort by priority
        available_connections = []

        for conn in self.connections:
            stats = self.connection_stats[conn.name]
            # Skip if too many recent failures
            if stats.failed_connections > conn.max_retries:
                continue
            available_connections.append(conn)

        # Sort by priority and success rate
        available_connections.sort(key=lambda x: (
            x.priority,
            self.connection_stats[x.name].failed_connections
        ))

        return available_connections[0] if available_connections else None

    async def connect(self) -> bool:
        """Connect to Home Assistant using Context7 KB WebSocket patterns"""
        # Try each connection in priority order
        tried_connections = set()

        for attempt in range(len(self.connections)):
            # Get next untried connection
            connection = None
            for conn in sorted(self.connections, key=lambda x: x.priority):
                if conn.name not in tried_connections:
                    connection = conn
                    break

            if not connection:
                logger.error("❌ No more Home Assistant connections to try")
                break

            tried_connections.add(connection.name)
            stats = self.connection_stats[connection.name]
            stats.connection_attempts += 1

            logger.info(f"🔗 Attempt {attempt + 1}/{len(self.connections)}: Connecting to {connection.name}")
            logger.info(f"🌐 URL: {connection.ws_url}")

            try:
                self.state = ConnectionState.CONNECTING
                stats.last_connection = datetime.now()

                # Create session with Context7 KB patterns
                timeout = ClientTimeout(total=connection.timeout)
                self.session = aiohttp.ClientSession(timeout=timeout)

                # Connect using Context7 KB WebSocket patterns
                self.ws = await self.session.ws_connect(
                    connection.ws_url,
                    autoclose=True,
                    autoping=True,
                    heartbeat=connection.heartbeat,
                    headers={
                        'User-Agent': 'HomeIQ/1.0',
                        'Origin': connection.url
                    }
                )

                logger.info(f"✅ WebSocket connection established to {connection.name}")

                # Authenticate using Context7 KB patterns
                if not await self._authenticate(connection):
                    raise Exception("Authentication failed")

                # Subscribe to events
                await self._subscribe_to_events()

                # Success!
                self.current_connection = connection
                self.state = ConnectionState.CONNECTED
                stats.successful_connections += 1
                stats.last_success = datetime.now()
                stats.current_uptime = datetime.now()
                stats.failed_connections = 0  # Reset failure count on success

                logger.info(f"✅ Connected to {connection.name} successfully")

                # Log fallback if this wasn't the first attempt
                if attempt > 0:
                    self.successful_fallbacks += 1
                    self.fallback_attempts += 1
                    logger.info(f"🔄 Fallback successful: Using {connection.name}")

                return True

            except Exception as e:
                logger.error(f"❌ Failed to connect to {connection.name}: {e}")
                self.state = ConnectionState.FAILED
                stats.failed_connections += 1
                self.fallback_attempts += 1

                # Clean up failed connection
                await self._cleanup_connection()

                # Wait before trying next connection
                if attempt < len(self.connections) - 1:
                    logger.info(f"⏳ Waiting {connection.retry_delay} seconds before trying next connection...")
                    await asyncio.sleep(connection.retry_delay)

        logger.error("❌ All Home Assistant connections failed")
        return False

    async def _authenticate(self, connection: ConnectionConfig) -> bool:
        """Authenticate with Home Assistant using Context7 KB patterns"""
        try:
            self.state = ConnectionState.AUTHENTICATING

            # Receive auth_required message
            auth_required_msg = await self.ws.receive_json()
            logger.info(f"🔐 Auth required from {connection.name}: {auth_required_msg}")

            if auth_required_msg.get("type") != "auth_required":
                logger.error(f"❌ Expected auth_required message from {connection.name}")
                return False

            # Send authentication using Context7 KB patterns
            auth_message = {
                "type": "auth",
                "access_token": connection.token
            }
            await self.ws.send_json(auth_message)

            # Receive auth response
            auth_response = await self.ws.receive_json()
            logger.info(f"🔑 Auth response from {connection.name}: {auth_response}")

            if auth_response.get("type") == "auth_ok":
                self.is_authenticated = True
                logger.info(f"✅ Authentication successful with {connection.name}")
                return True
            else:
                logger.error(f"❌ Authentication failed with {connection.name}: {auth_response}")
                return False

        except Exception as e:
            logger.error(f"❌ Authentication error with {connection.name}: {e}")
            return False

    async def _subscribe_to_events(self):
        """Subscribe to Home Assistant events using Context7 KB patterns"""
        try:
            subscribe_msg = {
                "id": 1,
                "type": "subscribe_events"
            }
            await self.ws.send_json(subscribe_msg)

            # Wait for subscription confirmation
            response = await self.ws.receive_json()
            logger.info(f"📡 Event subscription: {response}")

            if response.get("type") == "result" and response.get("success"):
                logger.info("✅ Event subscription successful")
            else:
                raise Exception(f"Event subscription failed: {response}")

        except Exception as e:
            logger.error(f"❌ Event subscription error: {e}")
            raise

    async def _cleanup_connection(self):
        """Clean up connection resources using Context7 KB patterns"""
        if self.ws:
            try:
                await self.ws.close()
            except Exception as e:
                logger.warning(f"⚠️  Error closing WebSocket: {e}")
            finally:
                self.ws = None

        if self.session:
            try:
                await self.session.close()
            except Exception as e:
                logger.warning(f"⚠️  Error closing session: {e}")
            finally:
                self.session = None

    async def _reconnect_with_fallback(self):
        """Reconnect with fallback using Context7 KB patterns"""
        logger.info("🔄 Attempting reconnection with fallback...")
        self.fallback_attempts += 1

        # Reset connection state
        self.state = ConnectionState.RECONNECTING
        self.is_authenticated = False

        # Update stats
        if self.current_connection:
            stats = self.connection_stats[self.current_connection.name]
            if stats.current_uptime:
                stats.total_uptime += datetime.now() - stats.current_uptime
                stats.current_uptime = None

        # Try to reconnect
        if await self.connect():
            logger.info("✅ Reconnection successful")
        else:
            logger.error("❌ Reconnection failed, will retry in 30 seconds")
            await asyncio.sleep(30)

    async def process_events(self):
        """Process incoming events using Context7 KB patterns"""
        logger.info("🚀 Starting event processing...")

        while self.running:
            try:
                if self.state != ConnectionState.CONNECTED:
                    await self._reconnect_with_fallback()
                    continue

                # Receive event using Context7 KB patterns
                message = await self.ws.receive_json()

                if message.get("type") == "event":
                    await self._handle_event(message)
                elif message.get("type") == "pong":
                    # Handle pong response
                    logger.debug("📨 Received pong")
                else:
                    logger.debug(f"📨 Received message: {message}")

            except Exception as e:
                logger.error(f"❌ Error processing events: {e}")
                self.state = ConnectionState.FAILED
                await asyncio.sleep(5)

    async def _handle_event(self, message: dict[str, Any]):
        """Handle a single Home Assistant event using Context7 KB patterns"""
        try:
            self.event_count += 1
            event = message.get("event", {})
            event_type = event.get("event_type", "unknown")

            logger.info(f"📨 Event #{self.event_count}: {event_type}")

            # Enrich with weather data if enabled
            if self.weather_enrichment_enabled:
                await self._enrich_with_weather(event)

            # Send to enrichment pipeline
            await self._send_to_enrichment_pipeline(event)

        except Exception as e:
            logger.error(f"❌ Error handling event: {e}")

    async def _enrich_with_weather(self, event: dict[str, Any]):
        """Enrich event with weather data using Context7 KB patterns"""
        try:
            # Check if weather data is needed for this event type
            weather_events = ["state_changed", "weather_updated", "sun_updated"]
            if event.get("event_type") not in weather_events:
                return

            # Get weather data using Context7 KB patterns
            timeout = ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(f"{self.weather_service_url}/weather/current") as response:
                    if response.status == 200:
                        weather_data = await response.json()
                        event["weather_enrichment"] = weather_data
                        self.weather_enrichments += 1
                        logger.debug("🌤️  Weather enrichment added")
                    else:
                        logger.warning(f"⚠️  Weather API unavailable: {response.status}")

        except Exception as e:
            logger.error(f"❌ Weather enrichment error: {e}")

    async def _send_to_enrichment_pipeline(self, event: dict[str, Any]):
        """Send event to enrichment pipeline using Context7 KB patterns"""
        try:
            timeout = ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session, session.post(
                f"{self.enrichment_service_url}/enrich",
                json=event,
                headers={'Content-Type': 'application/json'}
            ) as response:
                if response.status == 200:
                    logger.debug("📤 Event sent to enrichment pipeline")
                else:
                    logger.warning(f"⚠️  Enrichment pipeline error: {response.status}")

        except Exception as e:
            logger.error(f"❌ Enrichment pipeline error: {e}")

    async def start_health_server(self):
        """Start health check server using Context7 KB patterns"""
        app = web.Application()

        async def health_check(request):
            """Health check endpoint with comprehensive stats"""
            stats = {
                "status": "healthy" if self.state == ConnectionState.CONNECTED else "unhealthy",
                "state": self.state.value,
                "connected_to": self.current_connection.name if self.current_connection else None,
                "event_count": self.event_count,
                "fallback_attempts": self.fallback_attempts,
                "successful_fallbacks": self.successful_fallbacks,
                "weather_enrichments": self.weather_enrichments,
                "uptime_seconds": (datetime.now() - self.start_time).seconds if self.start_time else 0,
                "available_connections": len([c for c in self.connections if self.connection_stats[c.name].failed_connections <= c.max_retries]),
                "total_connections": len(self.connections),
                "connection_stats": {
                    name: {
                        "connection_attempts": stats.connection_attempts,
                        "successful_connections": stats.successful_connections,
                        "failed_connections": stats.failed_connections,
                        "last_connection": stats.last_connection.isoformat() if stats.last_connection else None,
                        "last_success": stats.last_success.isoformat() if stats.last_success else None,
                        "total_uptime_seconds": stats.total_uptime.total_seconds(),
                        "current_uptime_seconds": (datetime.now() - stats.current_uptime).seconds if stats.current_uptime else 0
                    }
                    for name, stats in self.connection_stats.items()
                }
            }
            return web.json_response(stats)

        app.router.add_get('/health', health_check)

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', 8000)
        await site.start()
        logger.info("🌐 Health check server started on port 8000")

    async def run(self):
        """Main service loop using Context7 KB patterns"""
        logger.info("🚀 Starting Enhanced Home Assistant WebSocket Service with Fallback")
        logger.info("📚 Using BMAD Context7 KB patterns for optimal performance")
        self.start_time = datetime.now()
        self.running = True

        # Start health server
        await self.start_health_server()

        # Connect to Home Assistant
        if not await self.connect():
            logger.error("❌ Failed to connect to any Home Assistant instance")
            return

        # Process events
        try:
            await self.process_events()
        except KeyboardInterrupt:
            logger.info("🛑 Service stopped by user")
        except Exception as e:
            logger.error(f"❌ Service error: {e}")
        finally:
            await self.cleanup()

    async def cleanup(self):
        """Clean up resources using Context7 KB patterns"""
        self.running = False

        # Update final stats
        if self.current_connection and self.connection_stats[self.current_connection.name].current_uptime:
            stats = self.connection_stats[self.current_connection.name]
            stats.total_uptime += datetime.now() - stats.current_uptime

        await self._cleanup_connection()

        logger.info("🧹 Cleanup completed")

async def main():
    """Main entry point using Context7 KB patterns"""
    service = EnhancedHAWebSocketService()
    await service.run()

if __name__ == "__main__":
    asyncio.run(main())
