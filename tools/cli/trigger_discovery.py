#!/usr/bin/env python3
"""
Manual Device Discovery Trigger Script

This script manually triggers device discovery by calling the discovery service
through the websocket connection.
"""

import asyncio
import json
import logging
import os
import sys
from typing import Any, Dict

from aiohttp import ClientSession, ClientWebSocketResponse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DiscoveryTrigger:
    """Manually trigger device discovery"""
    
    def __init__(self):
        self.home_assistant_url = os.getenv('HOME_ASSISTANT_URL', 'http://localhost:8123')
        self.home_assistant_token = os.getenv('HOME_ASSISTANT_TOKEN')
        self.message_id_counter = 1000
        
    async def connect_and_discover(self):
        """Connect to Home Assistant and trigger discovery"""
        if not self.home_assistant_token:
            logger.error("HOME_ASSISTANT_TOKEN environment variable not set")
            return False
            
        try:
            # Create WebSocket URL
            ws_url = f"{self.home_assistant_url.replace('http', 'ws')}/api/websocket"
            logger.info(f"Connecting to {ws_url}")
            
            async with ClientSession() as session:
                async with session.ws_connect(
                    ws_url,
                    headers={
                        'Authorization': f'Bearer {self.home_assistant_token}',
                        'User-Agent': 'HA-Ingestor-Discovery/1.0'
                    }
                ) as websocket:
                    logger.info("Connected to Home Assistant WebSocket")
                    
                    # Authenticate
                    if not await self._authenticate(websocket):
                        logger.error("Authentication failed")
                        return False
                    
                    logger.info("Authentication successful")
                    
                    # Trigger device discovery
                    devices = await self._discover_devices(websocket)
                    entities = await self._discover_entities(websocket)
                    
                    logger.info(f"Discovery complete: {len(devices)} devices, {len(entities)} entities")
                    
                    # Print sample data
                    if devices:
                        logger.info(f"Sample device: {devices[0].get('name', 'Unknown')}")
                    if entities:
                        logger.info(f"Sample entity: {entities[0].get('entity_id', 'Unknown')}")
                    
                    return True
                    
        except Exception as e:
            logger.error(f"Error during discovery: {e}")
            return False
    
    async def _authenticate(self, websocket: ClientWebSocketResponse) -> bool:
        """Authenticate with Home Assistant"""
        try:
            # Wait for auth_required message
            auth_required_msg = await websocket.receive()
            auth_data = json.loads(auth_required_msg.data)
            
            if auth_data.get('type') != 'auth_required':
                logger.error(f"Expected auth_required, got: {auth_data}")
                return False
            
            # Send authentication
            auth_message = {
                'type': 'auth',
                'access_token': self.home_assistant_token
            }
            
            await websocket.send_str(json.dumps(auth_message))
            
            # Wait for auth result
            auth_result_msg = await websocket.receive()
            auth_result = json.loads(auth_result_msg.data)
            
            if auth_result.get('type') == 'auth_ok':
                logger.info("Authentication successful")
                return True
            else:
                logger.error(f"Authentication failed: {auth_result}")
                return False
                
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return False
    
    async def _discover_devices(self, websocket: ClientWebSocketResponse) -> list:
        """Discover devices from Home Assistant"""
        try:
            message_id = self._get_next_id()
            logger.info(f"Discovering devices (message_id: {message_id})")
            
            # Send device registry list command
            await websocket.send_str(json.dumps({
                "id": message_id,
                "type": "config/device_registry/list"
            }))
            
            # Wait for response
            response = await self._wait_for_response(websocket, message_id, timeout=10.0)
            
            if not response or not response.get("success"):
                logger.error(f"Device discovery failed: {response}")
                return []
            
            devices = response.get("result", [])
            logger.info(f"Discovered {len(devices)} devices")
            
            return devices
            
        except Exception as e:
            logger.error(f"Error discovering devices: {e}")
            return []
    
    async def _discover_entities(self, websocket: ClientWebSocketResponse) -> list:
        """Discover entities from Home Assistant"""
        try:
            message_id = self._get_next_id()
            logger.info(f"Discovering entities (message_id: {message_id})")
            
            # Send entity registry list command
            await websocket.send_str(json.dumps({
                "id": message_id,
                "type": "config/entity_registry/list"
            }))
            
            # Wait for response
            response = await self._wait_for_response(websocket, message_id, timeout=10.0)
            
            if not response or not response.get("success"):
                logger.error(f"Entity discovery failed: {response}")
                return []
            
            entities = response.get("result", [])
            logger.info(f"Discovered {len(entities)} entities")
            
            return entities
            
        except Exception as e:
            logger.error(f"Error discovering entities: {e}")
            return []
    
    async def _wait_for_response(self, websocket: ClientWebSocketResponse, message_id: int, timeout: float = 10.0) -> Dict[str, Any]:
        """Wait for response with specific message ID"""
        try:
            start_time = asyncio.get_event_loop().time()
            
            while True:
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed > timeout:
                    raise TimeoutError(f"Timeout waiting for message {message_id}")
                
                remaining_timeout = timeout - elapsed
                msg = await asyncio.wait_for(websocket.receive(), timeout=remaining_timeout)
                
                if msg.type == 1:  # TEXT message
                    data = json.loads(msg.data)
                    
                    if data.get("id") == message_id:
                        return data
                    else:
                        logger.debug(f"Received message for different ID: {data.get('id')}, waiting for {message_id}")
                        continue
                else:
                    logger.warning(f"Received non-text message type: {msg.type}")
                    continue
                    
        except TimeoutError:
            raise
        except Exception as e:
            logger.error(f"Error waiting for response: {e}")
            return None
    
    def _get_next_id(self) -> int:
        """Get next message ID"""
        self.message_id_counter += 1
        return self.message_id_counter

async def main():
    """Main entry point"""
    logger.info("Starting manual device discovery trigger")
    
    trigger = DiscoveryTrigger()
    success = await trigger.connect_and_discover()
    
    if success:
        logger.info("Discovery completed successfully")
        sys.exit(0)
    else:
        logger.error("Discovery failed")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
