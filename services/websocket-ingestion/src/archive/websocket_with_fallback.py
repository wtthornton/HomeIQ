#!/usr/bin/env python3
"""
Enhanced Home Assistant WebSocket Event Subscription Service with Fallback
Supports multiple Home Assistant instances with automatic fallback
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Any

import aiohttp
from aiohttp import web

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

class HAConnectionConfig:
    """Configuration for a Home Assistant connection"""

    def __init__(self, name: str, url: str, token: str, priority: int = 1):
        self.name = name
        self.url = url
        self.token = token
        self.priority = priority  # Lower number = higher priority
        self.ws_url = url.replace("http://", "ws://").replace("https://", "wss://") + "/api/websocket"
        self.last_attempt = None
        self.last_success = None
        self.failure_count = 0
        self.is_available = True

class EnhancedHAWebSocketService:
    """Enhanced Home Assistant WebSocket service with fallback support"""

    def __init__(self):
        # Initialize connection configurations
        self.connections: list[HAConnectionConfig] = []
        self.current_connection: HAConnectionConfig | None = None

        # Load connection configurations
        self._load_connection_configs()

        # Service configuration
        self.weather_service_url = os.getenv("WEATHER_SERVICE_URL", "http://weather-api:8001")
        self.weather_enrichment_enabled = os.getenv("ENABLE_WEATHER_API", "true").lower() == "true"
        self.enrichment_service_url = os.getenv("ENRICHMENT_SERVICE_URL", "http://enrichment-pipeline:8002")

        # Connection state
        self.ws = None
        self.session = None
        self.running = False
        self.event_count = 0
        self.start_time = None
        self.is_connected = False
        self.is_authenticated = False
        self.connection_attempts = 0
        self.reconnect_interval = 30  # seconds

        # Weather enrichment stats
        self.weather_api_calls = 0
        self.weather_cache_hits = 0
        self.weather_enrichments = 0

        # Fallback stats
        self.fallback_attempts = 0
        self.successful_fallbacks = 0

    def _load_connection_configs(self):
        """Load Home Assistant connection configurations"""

        # Primary connection (HA Simulator for development)
        primary_url = os.getenv("HOME_ASSISTANT_URL", "http://ha-simulator:8123")
        primary_token = os.getenv("HOME_ASSISTANT_TOKEN", "dev_simulator_token")

        if primary_url and primary_token:
            self.connections.append(HAConnectionConfig(
                name="Primary (HA Simulator)",
                url=primary_url,
                token=primary_token,
                priority=1,
            ))

        # Nabu Casa fallback connection
        nabu_casa_url = os.getenv("NABU_CASA_URL", "https://lwzisze94hrpqde9typkwgu5pptxdkoh.ui.nabu.casa")
        nabu_casa_token = os.getenv("NABU_CASA_TOKEN")

        if nabu_casa_url and nabu_casa_token:
            self.connections.append(HAConnectionConfig(
                name="Nabu Casa Fallback",
                url=nabu_casa_url,
                token=nabu_casa_token,
                priority=2,
            ))

        # Additional fallback connections can be added here
        # Example: Local Home Assistant instance
        local_ha_url = os.getenv("LOCAL_HA_URL")
        local_ha_token = os.getenv("LOCAL_HA_TOKEN")

        if local_ha_url and local_ha_token:
            self.connections.append(HAConnectionConfig(
                name="Local Home Assistant",
                url=local_ha_url,
                token=local_ha_token,
                priority=3,
            ))

        # Sort by priority
        self.connections.sort(key=lambda x: x.priority)

        logger.info(f"📋 Loaded {len(self.connections)} Home Assistant connection(s):")
        for conn in self.connections:
            logger.info(f"  - {conn.name}: {conn.url} (Priority: {conn.priority})")

    def _get_next_connection(self) -> HAConnectionConfig | None:
        """Get the next available connection to try"""
        # Filter available connections and sort by priority
        available_connections = [conn for conn in self.connections if conn.is_available]
        available_connections.sort(key=lambda x: (x.priority, x.failure_count))

        if available_connections:
            return available_connections[0]
        return None

    async def connect(self) -> bool:
        """Connect to Home Assistant with fallback support"""
        max_attempts = len(self.connections)
        attempt = 0

        while attempt < max_attempts:
            connection = self._get_next_connection()
            if not connection:
                logger.error("❌ No available Home Assistant connections")
                return False

            attempt += 1
            self.connection_attempts += 1

            logger.info(f"🔗 Attempt {attempt}/{max_attempts}: Connecting to {connection.name}")
            logger.info(f"🌐 URL: {connection.ws_url}")

            try:
                connection.last_attempt = datetime.now()

                # Create new session for this connection
                if self.session:
                    await self.session.close()

                self.session = aiohttp.ClientSession()
                self.ws = await self.session.ws_connect(
                    connection.ws_url,
                    timeout=aiohttp.ClientTimeout(total=30),
                )

                # Authenticate
                if not await self._authenticate(connection):
                    msg = "Authentication failed"
                    raise Exception(msg)

                # Subscribe to events
                await self._subscribe_to_events()

                # Success!
                self.current_connection = connection
                connection.last_success = datetime.now()
                connection.failure_count = 0
                connection.is_available = True
                self.is_connected = True

                logger.info(f"✅ Connected to {connection.name} successfully")

                # If this was a fallback, log it
                if attempt > 1:
                    self.successful_fallbacks += 1
                    logger.info(f"🔄 Fallback successful: Using {connection.name}")

                return True

            except Exception as e:
                logger.exception(f"❌ Failed to connect to {connection.name}: {e}")
                connection.failure_count += 1
                connection.is_available = False

                # Mark connection as temporarily unavailable
                logger.warning(f"⏸️  Marking {connection.name} as temporarily unavailable")

                # Clean up failed connection
                if self.ws:
                    await self.ws.close()
                if self.session:
                    await self.session.close()

                # Wait before trying next connection
                if attempt < max_attempts:
                    logger.info("⏳ Waiting 5 seconds before trying next connection...")
                    await asyncio.sleep(5)

        logger.error("❌ All Home Assistant connections failed")
        return False

    async def _authenticate(self, connection: HAConnectionConfig) -> bool:
        """Authenticate with Home Assistant"""
        try:
            # Receive auth_required
            auth_required = await self.ws.receive_json()
            logger.info(f"🔐 Auth required from {connection.name}: {auth_required}")

            # Send authentication
            auth_msg = {
                "type": "auth",
                "access_token": connection.token,
            }
            await self.ws.send_json(auth_msg)

            # Receive auth response
            auth_response = await self.ws.receive_json()
            logger.info(f"🔑 Auth response from {connection.name}: {auth_response}")

            if auth_response.get("type") == "auth_ok":
                self.is_authenticated = True
                logger.info(f"✅ Authentication successful with {connection.name}")
                return True
            logger.error(f"❌ Authentication failed with {connection.name}: {auth_response}")
            return False

        except Exception as e:
            logger.exception(f"❌ Authentication error with {connection.name}: {e}")
            return False

    async def _subscribe_to_events(self):
        """Subscribe to Home Assistant events"""
        try:
            subscribe_msg = {
                "id": 1,
                "type": "subscribe_events",
            }
            await self.ws.send_json(subscribe_msg)

            # Wait for subscription confirmation
            response = await self.ws.receive_json()
            logger.info(f"📡 Event subscription: {response}")

            if response.get("type") == "result" and response.get("success"):
                logger.info("✅ Event subscription successful")
            else:
                msg = f"Event subscription failed: {response}"
                raise Exception(msg)

        except Exception as e:
            logger.exception(f"❌ Event subscription error: {e}")
            raise

    async def _reconnect_with_fallback(self):
        """Reconnect with fallback support"""
        logger.info("🔄 Attempting reconnection with fallback...")
        self.fallback_attempts += 1

        # Reset connection state
        self.is_connected = False
        self.is_authenticated = False

        # Try to reconnect
        if await self.connect():
            logger.info("✅ Reconnection successful")
        else:
            logger.error("❌ Reconnection failed, will retry in 30 seconds")
            await asyncio.sleep(self.reconnect_interval)

    async def process_events(self):
        """Process incoming events"""
        logger.info("🚀 Starting event processing...")

        while self.running:
            try:
                if not self.is_connected:
                    await self._reconnect_with_fallback()
                    continue

                # Receive event
                message = await self.ws.receive_json()

                if message.get("type") == "event":
                    await self._handle_event(message)
                elif message.get("type") == "pong":
                    # Handle pong response
                    pass
                else:
                    logger.debug(f"📨 Received message: {message}")

            except Exception as e:
                logger.exception(f"❌ Error processing events: {e}")
                self.is_connected = False
                await asyncio.sleep(5)

    async def _handle_event(self, message: dict[str, Any]):
        """Handle a single Home Assistant event"""
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
            logger.exception(f"❌ Error handling event: {e}")

    async def _enrich_with_weather(self, event: dict[str, Any]):
        """Enrich event with weather data"""
        try:
            # Check if weather data is needed for this event type
            weather_events = ["state_changed", "weather_updated", "sun_updated"]
            if event.get("event_type") not in weather_events:
                return

            # Get weather data
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.weather_service_url}/weather/current") as response:
                    if response.status == 200:
                        weather_data = await response.json()
                        event["weather_enrichment"] = weather_data
                        self.weather_enrichments += 1
                        logger.debug("🌤️  Weather enrichment added")
                    else:
                        logger.warning(f"⚠️  Weather API unavailable: {response.status}")

        except Exception as e:
            logger.exception(f"❌ Weather enrichment error: {e}")

    async def _send_to_enrichment_pipeline(self, event: dict[str, Any]):
        """Send event to enrichment pipeline"""
        try:
            async with aiohttp.ClientSession() as session, session.post(
                f"{self.enrichment_service_url}/enrich",
                json=event,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                if response.status == 200:
                    logger.debug("📤 Event sent to enrichment pipeline")
                else:
                    logger.warning(f"⚠️  Enrichment pipeline error: {response.status}")

        except Exception as e:
            logger.exception(f"❌ Enrichment pipeline error: {e}")

    async def start_health_server(self):
        """Start health check server"""
        app = web.Application()

        async def health_check(request):
            stats = {
                "status": "healthy" if self.is_connected else "unhealthy",
                "connected_to": self.current_connection.name if self.current_connection else None,
                "event_count": self.event_count,
                "connection_attempts": self.connection_attempts,
                "fallback_attempts": self.fallback_attempts,
                "successful_fallbacks": self.successful_fallbacks,
                "weather_enrichments": self.weather_enrichments,
                "uptime_seconds": (datetime.now() - self.start_time).seconds if self.start_time else 0,
                "available_connections": len([c for c in self.connections if c.is_available]),
                "total_connections": len(self.connections),
            }
            return web.json_response(stats)

        app.router.add_get("/health", health_check)

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", 8000)
        await site.start()
        logger.info("🌐 Health check server started on port 8000")

    async def run(self):
        """Main service loop"""
        logger.info("🚀 Starting Enhanced Home Assistant WebSocket Service with Fallback")
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
            logger.exception(f"❌ Service error: {e}")
        finally:
            await self.cleanup()

    async def cleanup(self):
        """Clean up resources"""
        self.running = False

        if self.ws:
            await self.ws.close()
        if self.session:
            await self.session.close()

        logger.info("🧹 Cleanup completed")

async def main():
    """Main entry point"""
    service = EnhancedHAWebSocketService()
    await service.run()

if __name__ == "__main__":
    asyncio.run(main())
