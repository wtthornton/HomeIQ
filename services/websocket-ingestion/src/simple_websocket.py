#!/usr/bin/env python3
"""
Simple Home Assistant WebSocket Event Subscription Service
Based on the working ha_event_logger.py test
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from typing import Dict, Any, Optional
import aiohttp
from aiohttp import web

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SimpleHAWebSocketService:
    """Simple Home Assistant WebSocket service based on working test"""
    
    def __init__(self):
        self.ha_url = os.getenv("HOME_ASSISTANT_URL", "http://homeassistant.local:8123")
        self.ha_token = os.getenv("HOME_ASSISTANT_TOKEN")
        self.ws_url = self.ha_url.replace("http://", "ws://").replace("https://", "wss://") + "/api/websocket"
        
        self.ws = None
        self.session = None
        self.running = False
        self.event_count = 0
        self.start_time = None
        self.is_connected = False
        self.is_authenticated = False
        self.connection_attempts = 0
        
    async def connect(self) -> bool:
        """Connect to Home Assistant WebSocket"""
        try:
            self.connection_attempts += 1
            logger.info(f"Connection attempt {self.connection_attempts} to {self.ws_url}")
            
            self.session = aiohttp.ClientSession()
            self.ws = await self.session.ws_connect(self.ws_url)
            
            # Authenticate
            if not await self._authenticate():
                return False
                
            # Subscribe to events
            await self._subscribe_to_events()
            
            self.is_connected = True
            logger.info("✅ Connected to Home Assistant successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to Home Assistant: {e}")
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
                "access_token": self.ha_token
            }
            await self.ws.send_json(auth_msg)
            
            # Receive auth response
            auth_response = await self.ws.receive_json()
            logger.info(f"Auth response: {auth_response}")
            
            if auth_response.get("type") == "auth_ok":
                self.is_authenticated = True
                logger.info("✅ Authentication successful")
                return True
            else:
                logger.error(f"❌ Authentication failed: {auth_response}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Authentication error: {e}")
            return False
    
    async def _subscribe_to_events(self):
        """Subscribe to all Home Assistant events"""
        subscribe_msg = {
            "id": 1,
            "type": "subscribe_events"
        }
        await self.ws.send_json(subscribe_msg)
        
        # Receive subscription confirmation
        response = await self.ws.receive_json()
        logger.info(f"Event subscription: {response}")
    
    async def start_event_processing(self):
        """Start processing events"""
        self.running = True
        self.start_time = datetime.now()
        
        logger.info("🚀 Starting event processing...")
        
        try:
            while self.running:
                try:
                    # Receive message with timeout
                    msg = await asyncio.wait_for(self.ws.receive_json(), timeout=1.0)
                    await self._process_message(msg)
                    
                except asyncio.TimeoutError:
                    # No message received, continue
                    continue
                except Exception as e:
                    logger.error(f"❌ Error processing message: {e}")
                    
        except KeyboardInterrupt:
            logger.info("🛑 Interrupted by user")
        finally:
            await self._print_summary()
    
    async def _process_message(self, msg: Dict[str, Any]):
        """Process incoming WebSocket message"""
        if msg.get("type") == "event":
            self.event_count += 1
            event_data = msg.get("event", {})
            event_type = event_data.get("event_type", "unknown")
            
            # Log event details
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            logger.info(f"📨 [{timestamp}] Event #{self.event_count}: {event_type}")
            
            # Extract entity information if available
            data = event_data.get("data", {})
            entity_id = data.get("entity_id")
            if entity_id:
                logger.info(f"   🏠 Entity: {entity_id}")
    
    async def _print_summary(self):
        """Print processing summary"""
        if self.start_time:
            duration = datetime.now() - self.start_time
            events_per_minute = (self.event_count / duration.total_seconds()) * 60 if duration.total_seconds() > 0 else 0
            
            logger.info("=" * 60)
            logger.info("📊 EVENT PROCESSING SUMMARY")
            logger.info("=" * 60)
            logger.info(f"⏱️  Duration: {duration}")
            logger.info(f"📨 Total Events: {self.event_count}")
            logger.info(f"📈 Events per minute: {events_per_minute:.1f}")
            logger.info("=" * 60)
    
    async def stop(self):
        """Stop the service"""
        self.running = False
        if self.ws:
            await self.ws.close()
        if self.session:
            await self.session.close()
        logger.info("🛑 WebSocket service stopped")
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status for health check endpoint"""
        return {
            "status": "healthy" if self.is_connected else "unhealthy",
            "is_connected": self.is_connected,
            "is_authenticated": self.is_authenticated,
            "connection_attempts": self.connection_attempts,
            "event_count": self.event_count,
            "uptime": str(datetime.now() - self.start_time) if self.start_time else "0:00:00",
            "timestamp": datetime.now().isoformat()
        }

# Global service instance
websocket_service = SimpleHAWebSocketService()

async def health_check(request):
    """Health check endpoint"""
    status = websocket_service.get_health_status()
    return web.json_response(status)

async def start_service():
    """Start the WebSocket service"""
    if not websocket_service.ha_token:
        logger.error("❌ Home Assistant token not found in environment variables")
        logger.info("💡 Set HOME_ASSISTANT_TOKEN environment variable")
        return False
    
    logger.info(f"🔗 Connecting to: {websocket_service.ws_url}")
    
    # Connect and start processing
    if await websocket_service.connect():
        # Start HTTP server for health checks
        app = web.Application()
        app.router.add_get('/health', health_check)
        
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', 8000)
        await site.start()
        
        logger.info("🌐 Health check server started on port 8000")
        
        # Start event processing
        await websocket_service.start_event_processing()
        return True
    else:
        logger.error("❌ Failed to connect to Home Assistant")
        return False

async def main():
    """Main function"""
    try:
        await start_service()
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
    finally:
        await websocket_service.stop()

if __name__ == "__main__":
    asyncio.run(main())
