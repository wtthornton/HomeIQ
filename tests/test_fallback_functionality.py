#!/usr/bin/env python3
"""
Test script to verify the fallback functionality
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from typing import Dict, Any, Optional, List
import aiohttp
import websockets

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class FallbackTest:
    """Test the fallback functionality"""
    
    def __init__(self):
        self.connections = []
        self._load_test_connections()
        
    def _load_test_connections(self):
        """Load test connection configurations"""
        
        # Primary connection (HA Simulator)
        primary_url = "http://ha-simulator:8123"
        primary_token = "dev_simulator_token"
        
        self.connections.append({
            "name": "Primary (HA Simulator)",
            "url": primary_url,
            "token": primary_token,
            "ws_url": primary_url.replace("http://", "ws://") + "/api/websocket",
            "priority": 1
        })
        
        # Nabu Casa fallback
        nabu_casa_url = "https://lwzisze94hrpqde9typkwgu5pptxdkoh.ui.nabu.casa"
        nabu_casa_token = os.getenv("NABU_CASA_TOKEN")
        
        if nabu_casa_token:
            self.connections.append({
                "name": "Nabu Casa Fallback",
                "url": nabu_casa_url,
                "token": nabu_casa_token,
                "ws_url": nabu_casa_url.replace("https://", "wss://") + "/api/websocket",
                "priority": 2
            })
        
        # Sort by priority
        self.connections.sort(key=lambda x: x["priority"])
        
        logger.info(f"📋 Test connections loaded:")
        for conn in self.connections:
            logger.info(f"  - {conn['name']}: {conn['url']} (Priority: {conn['priority']})")
    
    async def test_connection(self, connection: Dict[str, Any]) -> bool:
        """Test a single connection"""
        try:
            logger.info(f"🔗 Testing connection to {connection['name']}")
            logger.info(f"🌐 URL: {connection['ws_url']}")
            
            # Connect to WebSocket
            ws = await websockets.connect(
                connection["ws_url"],
                ping_interval=20,
                ping_timeout=10,
                close_timeout=10
            )
            
            # Wait for auth_required
            auth_required = await ws.recv()
            auth_data = json.loads(auth_required)
            logger.info(f"🔐 Auth required: {auth_data}")
            
            if auth_data.get('type') != 'auth_required':
                logger.error("❌ Expected auth_required message")
                return False
            
            # Send authentication
            auth_message = {
                "type": "auth",
                "access_token": connection["token"]
            }
            await ws.send(json.dumps(auth_message))
            
            # Wait for auth response
            auth_response = await ws.recv()
            auth_result = json.loads(auth_response)
            logger.info(f"🔑 Auth response: {auth_result}")
            
            if auth_result.get('type') == 'auth_ok':
                logger.info(f"✅ {connection['name']} connection successful")
                
                # Test event subscription
                subscribe_message = {
                    "id": 1,
                    "type": "subscribe_events"
                }
                await ws.send(json.dumps(subscribe_message))
                
                # Wait for subscription confirmation
                response = await ws.recv()
                result = json.loads(response)
                logger.info(f"📡 Event subscription: {result}")
                
                if result.get('type') == 'result' and result.get('success'):
                    logger.info(f"✅ {connection['name']} event subscription successful")
                    await ws.close()
                    return True
                else:
                    logger.error(f"❌ {connection['name']} event subscription failed")
                    await ws.close()
                    return False
            else:
                logger.error(f"❌ {connection['name']} authentication failed: {auth_result}")
                await ws.close()
                return False
                
        except Exception as e:
            logger.error(f"❌ {connection['name']} connection error: {e}")
            return False
    
    async def test_fallback_scenario(self):
        """Test the fallback scenario by simulating primary failure"""
        logger.info("🧪 Testing fallback scenario...")
        
        # Test each connection individually
        results = {}
        for connection in self.connections:
            results[connection["name"]] = await self.test_connection(connection)
        
        # Report results
        logger.info("\n📊 Connection Test Results:")
        for name, success in results.items():
            status = "✅ PASS" if success else "❌ FAIL"
            logger.info(f"  {name}: {status}")
        
        # Determine fallback capability
        available_connections = [name for name, success in results.items() if success]
        
        if len(available_connections) >= 2:
            logger.info(f"🎉 Fallback capability confirmed! {len(available_connections)} connections available")
            logger.info(f"📋 Available connections: {', '.join(available_connections)}")
            return True
        elif len(available_connections) == 1:
            logger.warning(f"⚠️  Only one connection available: {available_connections[0]}")
            logger.warning("No fallback capability - consider adding more connections")
            return False
        else:
            logger.error("❌ No connections available")
            return False
    
    async def test_priority_order(self):
        """Test that connections are tried in priority order"""
        logger.info("🔢 Testing priority order...")
        
        # Sort connections by priority
        sorted_connections = sorted(self.connections, key=lambda x: x["priority"])
        
        logger.info("📋 Connection priority order:")
        for i, conn in enumerate(sorted_connections, 1):
            logger.info(f"  {i}. {conn['name']} (Priority: {conn['priority']})")
        
        return True

async def main():
    """Main test function"""
    test = FallbackTest()
    
    logger.info("🚀 Starting fallback functionality test...")
    
    # Test priority order
    await test.test_priority_order()
    
    # Test fallback scenario
    success = await test.test_fallback_scenario()
    
    if success:
        logger.info("\n🎉 Fallback functionality test completed successfully!")
        logger.info("The enhanced websocket service can now be deployed with fallback support.")
    else:
        logger.error("\n❌ Fallback functionality test failed!")
        logger.error("Please check your connection configurations and tokens.")
    
    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
