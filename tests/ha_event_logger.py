#!/usr/bin/env python3
"""
Simple Home Assistant Event Logger
Connects to HA WebSocket and logs all incoming events to establish baseline event volume.
"""

import asyncio
import json
import logging
import os
import signal
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import aiohttp

# Try to load .env file if python-dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # If python-dotenv is not available, try to load .env manually
    def load_env_manual():
        env_files = [".env", "infrastructure/.env", "infrastructure/env.production"]
        for env_file in env_files:
            if Path(env_file).exists():
                with open(env_file) as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            key, value = line.split("=", 1)
                            os.environ[key.strip()] = value.strip().strip('"').strip("'")
                break

    load_env_manual()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("ha_events.log"),
    ],
)
logger = logging.getLogger(__name__)

class HAEventLogger:
    """Simple Home Assistant event logger for baseline measurement"""

    def __init__(self, ha_url: str, ha_token: str):
        self.ha_url = ha_url
        self.ha_token = ha_token
        self.ws = None
        self.session = None
        self.running = False
        self.event_count = 0
        self.start_time = None
        self.event_types = {}
        self.entity_counts = {}

    async def connect(self) -> bool:
        """Connect to Home Assistant WebSocket"""
        try:
            self.session = aiohttp.ClientSession()
            self.ws = await self.session.ws_connect(self.ha_url)

            # Authenticate
            if not await self._authenticate():
                return False

            # Subscribe to events
            await self._subscribe_to_events()

            logger.info("✅ Connected to Home Assistant successfully")
            return True

        except Exception as e:
            logger.exception(f"❌ Failed to connect to Home Assistant: {e}")
            return False

    async def _authenticate(self) -> bool:
        """Authenticate with Home Assistant"""
        try:
            # Receive auth_required
            auth_required = await self.ws.receive_json()
            logger.info(f"Auth required: {auth_required}")

            # Send authentication
            auth_msg = {
                "type": "auth",
                "access_token": self.ha_token,
            }
            await self.ws.send_json(auth_msg)

            # Receive auth response
            auth_response = await self.ws.receive_json()
            logger.info(f"Auth response: {auth_response}")

            if auth_response.get("type") == "auth_ok":
                logger.info("✅ Authentication successful")
                return True
            logger.error(f"❌ Authentication failed: {auth_response}")
            return False

        except Exception as e:
            logger.exception(f"❌ Authentication error: {e}")
            return False

    async def _subscribe_to_events(self):
        """Subscribe to all Home Assistant events"""
        subscribe_msg = {
            "id": 1,
            "type": "subscribe_events",
        }
        await self.ws.send_json(subscribe_msg)

        # Receive subscription confirmation
        response = await self.ws.receive_json()
        logger.info(f"Event subscription: {response}")

    async def start_logging(self, duration_minutes: int = 5):
        """Start logging events for specified duration"""
        self.running = True
        self.start_time = datetime.now()
        end_time = self.start_time.replace(minute=self.start_time.minute + duration_minutes)

        logger.info(f"🚀 Starting event logging for {duration_minutes} minutes...")
        logger.info(f"📊 Will log until: {end_time.strftime('%H:%M:%S')}")

        try:
            while self.running and datetime.now() < end_time:
                try:
                    # Receive message with timeout
                    msg = await asyncio.wait_for(self.ws.receive_json(), timeout=1.0)
                    await self._process_message(msg)

                except asyncio.TimeoutError:
                    # No message received, continue
                    continue
                except Exception as e:
                    logger.exception(f"❌ Error processing message: {e}")

        except KeyboardInterrupt:
            logger.info("🛑 Interrupted by user")
        finally:
            await self._print_summary()

    async def _process_message(self, msg: dict[str, Any]):
        """Process incoming WebSocket message"""
        if msg.get("type") == "event":
            self.event_count += 1
            event_data = msg.get("event", {})
            event_type = event_data.get("event_type", "unknown")

            # Count event types
            self.event_types[event_type] = self.event_types.get(event_type, 0) + 1

            # Extract entity information if available
            data = event_data.get("data", {})
            entity_id = data.get("entity_id")
            if entity_id:
                self.entity_counts[entity_id] = self.entity_counts.get(entity_id, 0) + 1

            # Log event details
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            logger.info(f"📨 [{timestamp}] Event #{self.event_count}: {event_type}")

            if entity_id:
                logger.info(f"   🏠 Entity: {entity_id}")

            # Log every 10th event with more detail
            if self.event_count % 10 == 0:
                logger.info(f"   📊 Event data: {json.dumps(data, indent=2)[:200]}...")

    async def _print_summary(self):
        """Print logging summary"""
        if self.start_time:
            duration = datetime.now() - self.start_time
            events_per_minute = (self.event_count / duration.total_seconds()) * 60 if duration.total_seconds() > 0 else 0

            logger.info("=" * 60)
            logger.info("📊 EVENT LOGGING SUMMARY")
            logger.info("=" * 60)
            logger.info(f"⏱️  Duration: {duration}")
            logger.info(f"📨 Total Events: {self.event_count}")
            logger.info(f"📈 Events per minute: {events_per_minute:.1f}")
            logger.info(f"📈 Events per second: {events_per_minute/60:.2f}")

            logger.info("\n🏷️  Event Types:")
            for event_type, count in sorted(self.event_types.items(), key=lambda x: x[1], reverse=True):
                percentage = (count / self.event_count) * 100 if self.event_count > 0 else 0
                logger.info(f"   {event_type}: {count} ({percentage:.1f}%)")

            logger.info("\n🏠 Top Entities:")
            for entity_id, count in sorted(self.entity_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
                percentage = (count / self.event_count) * 100 if self.event_count > 0 else 0
                logger.info(f"   {entity_id}: {count} ({percentage:.1f}%)")

            logger.info("=" * 60)

    async def stop(self):
        """Stop the event logger"""
        self.running = False
        if self.ws:
            await self.ws.close()
        if self.session:
            await self.session.close()
        logger.info("🛑 Event logger stopped")

async def main():
    """Main function"""
    # Configuration - try multiple environment variable names
    ha_url = os.getenv("HA_WEBSOCKET_URL") or os.getenv("HOME_ASSISTANT_WEBSOCKET_URL")
    if not ha_url:
        # Try to construct from HOME_ASSISTANT_URL
        base_url = os.getenv("HOME_ASSISTANT_URL", "http://homeassistant.local:8123")
        if base_url.startswith("http://"):
            ha_url = base_url.replace("http://", "ws://") + "/api/websocket"
        elif base_url.startswith("https://"):
            ha_url = base_url.replace("https://", "wss://") + "/api/websocket"
        else:
            ha_url = "ws://homeassistant.local:8123/api/websocket"

    # Try multiple token environment variable names
    ha_token = (os.getenv("HA_ACCESS_TOKEN") or
                os.getenv("HOME_ASSISTANT_TOKEN") or
                os.getenv("HA_TOKEN"))

    duration = int(os.getenv("LOG_DURATION_MINUTES", "5"))

    if not ha_token:
        logger.error("❌ Home Assistant token not found in environment variables")
        logger.info("💡 Set one of these environment variables:")
        logger.info("   - HA_ACCESS_TOKEN")
        logger.info("   - HOME_ASSISTANT_TOKEN")
        logger.info("   - HA_TOKEN")
        logger.info("💡 Or add HOME_ASSISTANT_TOKEN to your .env file")
        logger.info("💡 Available .env files checked: .env, infrastructure/.env, infrastructure/env.production")
        sys.exit(1)

    logger.info(f"🔗 Connecting to: {ha_url}")
    logger.info(f"⏱️  Logging duration: {duration} minutes")

    # Create and start logger
    logger_instance = HAEventLogger(ha_url, ha_token)

    # Setup signal handler for graceful shutdown
    def signal_handler(signum, frame):
        logger.info("🛑 Received shutdown signal")
        asyncio.create_task(logger_instance.stop())

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Connect and start logging
        if await logger_instance.connect():
            await logger_instance.start_logging(duration)
        else:
            logger.error("❌ Failed to connect to Home Assistant")
            sys.exit(1)

    except Exception as e:
        logger.exception(f"❌ Unexpected error: {e}")
        sys.exit(1)
    finally:
        await logger_instance.stop()

if __name__ == "__main__":
    asyncio.run(main())
