#!/usr/bin/env python3
"""
Simple test to verify Nabu Casa connection from host system
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path

import websockets


def load_env_file(env_path: str = ".env"):
    """Load environment variables from .env file"""
    env_file = Path(env_path)
    if env_file.exists():
        logger.info(f"📁 Loading environment from {env_path}")
        try:
            with open(env_file, encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        try:
                            key, value = line.split("=", 1)
                            # Remove quotes if present and strip whitespace
                            key = key.strip()
                            value = value.strip().strip('"\'')
                            # Skip if value contains null characters
                            if "\x00" not in value:
                                os.environ[key] = value
                        except Exception as e:
                            logger.warning(f"⚠️  Error parsing line {line_num}: {line} - {e}")
            logger.info("✅ Environment variables loaded from .env file")
        except Exception as e:
            logger.exception(f"❌ Error reading .env file: {e}")
    else:
        logger.warning(f"⚠️  .env file not found at {env_path}")
        logger.info("You can create a .env file with: NABU_CASA_TOKEN=your_token_here")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

async def test_nabu_casa_connection():
    """Test connection to Nabu Casa"""

    # Load environment from .env file
    load_env_file()

    # Get token from environment or command line
    token = os.getenv("NABU_CASA_TOKEN")
    if not token and len(sys.argv) > 1:
        token = sys.argv[1]

    if not token:
        logger.error("❌ NABU_CASA_TOKEN not provided")
        logger.info("Usage: python test_nabu_casa_simple.py YOUR_TOKEN")
        logger.info("Or create a .env file with: NABU_CASA_TOKEN=your_token")
        logger.info("Or set: export NABU_CASA_TOKEN=your_token")
        return False

    # Nabu Casa WebSocket URL
    ws_url = "wss://lwzisze94hrpqde9typkwgu5pptxdkoh.ui.nabu.casa/api/websocket"

    try:
        logger.info("🔗 Connecting to Nabu Casa WebSocket...")
        logger.info(f"🌐 URL: {ws_url}")

        # Connect to WebSocket
        async with websockets.connect(ws_url) as websocket:
            logger.info("✅ WebSocket connection established")

            # Wait for auth_required
            auth_required = await websocket.recv()
            auth_data = json.loads(auth_required)
            logger.info(f"🔐 Auth required: {auth_data}")

            if auth_data.get("type") != "auth_required":
                logger.error("❌ Expected auth_required message")
                return False

            # Send authentication
            auth_message = {
                "type": "auth",
                "access_token": token,
            }
            await websocket.send(json.dumps(auth_message))

            # Wait for auth response
            auth_response = await websocket.recv()
            auth_result = json.loads(auth_response)
            logger.info(f"🔑 Auth response: {auth_result}")

            if auth_result.get("type") == "auth_ok":
                logger.info("✅ Authentication successful")

                # Test event subscription
                subscribe_message = {
                    "id": 1,
                    "type": "subscribe_events",
                }
                await websocket.send(json.dumps(subscribe_message))

                # Wait for subscription confirmation
                response = await websocket.recv()
                result = json.loads(response)
                logger.info(f"📡 Event subscription: {result}")

                if result.get("type") == "result" and result.get("success"):
                    logger.info("✅ Event subscription successful")

                    # Wait for a few events
                    logger.info("⏳ Waiting for events (5 seconds)...")
                    event_count = 0

                    try:
                        while event_count < 3:
                            event = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                            event_data = json.loads(event)

                            if event_data.get("type") == "event":
                                event_count += 1
                                event_type = event_data.get("event", {}).get("event_type", "unknown")
                                logger.info(f"📨 Event {event_count}: {event_type}")

                    except asyncio.TimeoutError:
                        logger.info("⏰ Timeout waiting for events (this is normal)")

                    logger.info(f"✅ Received {event_count} events")
                    return True
                logger.error(f"❌ Event subscription failed: {result}")
                return False
            logger.error(f"❌ Authentication failed: {auth_result}")
            return False

    except Exception as e:
        logger.exception(f"❌ Connection error: {e}")
        return False

async def main():
    """Main test function"""
    logger.info("🚀 Starting Nabu Casa connection test...")

    success = await test_nabu_casa_connection()

    if success:
        logger.info("🎉 Nabu Casa connection test completed successfully!")
        logger.info("✅ Your Nabu Casa token is valid and working")
        logger.info("🔄 You can now use the fallback functionality")
    else:
        logger.error("❌ Nabu Casa connection test failed")
        logger.error("Please check your token and network connectivity")

    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
